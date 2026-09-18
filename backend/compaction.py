"""Block compaction for long chats.

Long chats get expensive because every turn re-sends the whole history. The naive fix
(keep the last N messages) makes it worse: the window slides by one message per turn, so
the token sequence diverges right after the system message and prompt caching stops
working on everything that follows.

Block compaction instead lets history grow untouched to a high-water mark, then cuts it
back to a low-water mark in one move and holds there:

    turns 1..N   append-only  -> stable prefix -> cache hits
    turn  N+1    one big cut  -> one cache miss
    turns N+2..  append-only  -> cache hits again

You pay a cache miss once per compaction instead of once per turn.

What gets dropped is not simply lost: `extract_profile` distils the discarded block into a
short block of durable facts about the user (nationality, track, whether they are already
in Cyprus, what permit they hold). Those are exactly the facts system_prompt_base.txt says
an answer depends on, and they are usually established in the first few turns — the ones a
naive trim throws away first.

The profile is computed ONCE per compaction and stored. Regenerating it per turn would
change the prefix every turn and destroy the cache benefit this whole module exists for.

NOTE ON STATE: the caller must persist the profile and the cut point. server.py does
this in the `chat_state` table, where `compacted_through_id` is a watermark rather than
a delete - every message stays in the messages table and is still served by /messages,
it is just no longer re-sent to the model. See PROMPT_ROUTING.md.
"""

# ---------------------------------------------------------------------------
# TUNING
# ---------------------------------------------------------------------------
# Compaction triggers on whichever limit is hit first. Tokens are what actually
# cost money; the message counts are a guard against many short turns.
HIGH_WATER_TOKENS = 6000
LOW_WATER_TOKENS  = 3000
HIGH_WATER_MSGS   = 40
LOW_WATER_MSGS    = 20

PROFILE_MODEL = "gpt-4.1-mini"
PROFILE_MAX_TOKENS = 280      # ~140 words of output, with headroom so it is never cut off


# ---------------------------------------------------------------------------
# TOKEN ESTIMATION
# ---------------------------------------------------------------------------
try:
    import tiktoken
    _ENCODING = tiktoken.get_encoding("o200k_base")
except Exception:
    _ENCODING = None


def estimate_tokens(text):
    """Token count. Uses tiktoken when installed, otherwise ~4 chars per token,
    which is close enough for a high/low water mark."""
    if not text:
        return 0
    if _ENCODING is not None:
        return len(_ENCODING.encode(text))
    return max(1, len(text) // 4)


def history_tokens(history):
    return sum(estimate_tokens(m.get("content", "")) for m in history)


# ---------------------------------------------------------------------------
# WHEN AND WHERE TO CUT
# ---------------------------------------------------------------------------
def needs_compaction(history):
    return (
        len(history) > HIGH_WATER_MSGS
        or history_tokens(history) > HIGH_WATER_TOKENS
    )


def split_for_compaction(history):
    """Split into (to_drop, to_keep), keeping roughly the low-water mark.

    The kept block always starts on a user message — starting it on an assistant
    message would leave the model reading a reply to a question it cannot see.
    """
    if not history:
        return [], []

    keep_from = len(history)
    running = 0

    for i in range(len(history) - 1, -1, -1):
        running += estimate_tokens(history[i].get("content", ""))
        keep_from = i
        if running >= LOW_WATER_TOKENS or (len(history) - i) >= LOW_WATER_MSGS:
            break

    while keep_from < len(history) and history[keep_from].get("role") != "user":
        keep_from += 1

    # Degenerate case: nothing after the cut was a user turn. Keep the last turn.
    if keep_from >= len(history):
        keep_from = max(0, len(history) - 1)

    return history[:keep_from], history[keep_from:]


# ---------------------------------------------------------------------------
# PROFILE EXTRACTION
# ---------------------------------------------------------------------------
PROFILE_SYSTEM_PROMPT = """You maintain a compact factual profile of one user of a Cyprus
immigration assistant. You are given the profile so far (possibly empty) and a block of
transcript that is about to be discarded. Return the updated profile.

Record ONLY durable facts about the user's own situation - the kind that change what a
correct answer looks like:
nationality and whether they are an EU/EEA or third-country national; student or worker
track; institution or employer; whether they are already in Cyprus; which visa or permit
they already hold and its expiry; city; family members involved; fixed dates or deadlines.

Rules:
- Under 140 words. Short labelled clauses separated by semicolons.
- Carry forward every fact already in the profile unless the transcript corrects it.
- Do not record the questions the user asked or the advice that was given.
- Record only what the user stated. If a fact is uncertain or was assumed, leave it out.
  Never guess a nationality or a track.
- Output the profile text only, with no preamble."""


def render_block(history):
    """Flatten a transcript block for the extraction call."""
    return "\n\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in history
    )


def extract_profile(client, dropped, previous_profile=""):
    """One model call per compaction, amortised over the turns until the next one.
    On any failure the previous profile is kept - degrading to a plain trim is
    acceptable, losing the accumulated facts is not."""
    if not dropped:
        return previous_profile

    user_content = (
        f"PROFILE SO FAR:\n{previous_profile or '(empty)'}\n\n"
        f"TRANSCRIPT BLOCK BEING DISCARDED:\n{render_block(dropped)}"
    )

    try:
        response = client.chat.completions.create(
            model=PROFILE_MODEL,
            temperature=0,
            max_tokens=PROFILE_MAX_TOKENS,
            messages=[
                {"role": "system", "content": PROFILE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        updated = (response.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"Profile extraction failed ({e}); keeping the previous profile.")
        return previous_profile

    return updated or previous_profile


# ---------------------------------------------------------------------------
# THE ENTRY POINT
# ---------------------------------------------------------------------------
def compact(client, history, profile=""):
    """Compact if the history has crossed the high-water mark.

    Returns (history, profile, compacted). The caller must PERSIST the returned
    history and profile - recomputing them per turn defeats the purpose.
    """
    if not needs_compaction(history):
        return history, profile, False

    dropped, kept = split_for_compaction(history)
    if not dropped:
        return history, profile, False

    return kept, extract_profile(client, dropped, profile), True


def build_messages(system_prompt, profile, history, context_block, question):
    """Assemble the answer call in cache-friendly order.

    [system][profile][history][context][question]

    Everything stable sits in front. `context_block` changes every turn, so it goes
    as late as possible - putting it in the system message (as server.py does today)
    makes the entire history downstream of a varying block and therefore uncacheable.
    """
    messages = [{"role": "system", "content": system_prompt}]

    if profile:
        messages.append({"role": "system", "content": f"Known about this user: {profile}"})

    messages.extend(history)

    if context_block:
        messages.append({"role": "system", "content": context_block})

    messages.append({"role": "user", "content": question})
    return messages
