"""Measure block compaction against the alternatives on a synthetic 60-turn chat.

Uses the project's real prompt files so the system-message sizes are honest.
No API calls - the profile extraction is stubbed and its cost counted separately.

Cache model: OpenAI prompt caching matches the longest common PREFIX of the token
sequence, in 128-token blocks, with a 1024-token minimum. Here we compare each turn's
serialized prompt against the previous turn's. Real caching can match against several
recent requests, so this slightly understates hit rates for all strategies equally.
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import compaction

TURNS = 60
CACHED_RATE = 0.25      # cached input billed at this fraction of normal input
CACHE_BLOCK = 128
CACHE_MIN = 1024

rng = random.Random(7)


def load(name):
    with open(name, encoding="utf-8") as f:
        return f.read().strip()


BASE = load("system_prompt_base.txt")
TOPIC_PROMPTS = {
    "VISA": load("system_prompt_visa.txt"),
    "TRANSPORT": load("system_prompt_transport.txt"),
    "REAL_ESTATE": load("system_prompt_realestate.txt"),
}

# A chat that wanders: visa, then transport, then property, then back to visa
def topic_for(turn):
    if turn < 20:
        return "VISA"
    if turn < 35:
        return "TRANSPORT"
    if turn < 45:
        return "REAL_ESTATE"
    return "VISA"


def filler(n_chars, seed):
    r = random.Random(seed)
    words = ["permit", "renewal", "document", "registration", "deadline", "application",
             "authority", "insurance", "certificate", "deposit", "transfer", "licence"]
    out = []
    while sum(len(w) + 1 for w in out) < n_chars:
        out.append(r.choice(words))
    return " ".join(out)


TURN_DATA = []
for t in range(TURNS):
    TURN_DATA.append({
        "topic": topic_for(t),
        "question": filler(rng.randint(60, 180), 1000 + t),
        "answer": filler(rng.randint(1600, 3600), 2000 + t),      # ~400-900 tokens
        "context": filler(5000, 3000 + t),                        # 5 chunks x 1000 chars
    })

tok = compaction.estimate_tokens


def serialize(messages):
    return "\n\x00\n".join(f"{m['role']}\x01{m['content']}" for m in messages)


def cached_tokens(prev_serial, serial):
    """Tokens served from cache, given the previous turn's prompt."""
    if prev_serial is None:
        return 0
    limit = min(len(prev_serial), len(serial))
    i = 0
    while i < limit and prev_serial[i] == serial[i]:
        i += 1
    prefix_tokens = i // 4
    blocks = (prefix_tokens // CACHE_BLOCK) * CACHE_BLOCK
    return blocks if blocks >= CACHE_MIN else 0


def run(strategy):
    history = []
    profile = ""
    prev_serial = None
    total = cached = 0
    overhead = 0
    compactions = 0

    for t, d in enumerate(TURN_DATA):
        system_core = BASE + "\n\n" + TOPIC_PROMPTS[d["topic"]]
        context_block = "Answer using the provided context.\n\nContext:\n" + d["context"]

        if strategy == "current":
            # context lives INSIDE the system message, ahead of the history
            messages = ([{"role": "system", "content": system_core + "\n\n" + context_block}]
                        + history + [{"role": "user", "content": d["question"]}])

        elif strategy == "reorder":
            messages = compaction.build_messages(
                system_core, "", history, context_block, d["question"])

        elif strategy == "sliding":
            window = history[-20:]
            messages = compaction.build_messages(
                system_core, "", window, context_block, d["question"])

        elif strategy == "block":
            if compaction.needs_compaction(history):
                dropped, kept = compaction.split_for_compaction(history)
                if dropped:
                    # stubbed extraction; count what the real call would cost
                    overhead += tok(compaction.PROFILE_SYSTEM_PROMPT) + \
                                tok(compaction.render_block(dropped)) + tok(profile)
                    profile = ("Ukrainian national, third-country; student track at Frederick "
                               "University; not yet in Cyprus; no permit held; targeting the "
                               "September intake; travelling alone.")
                    history = kept
                    compactions += 1
            messages = compaction.build_messages(
                system_core, profile, history, context_block, d["question"])

        serial = serialize(messages)
        n = sum(tok(m["content"]) for m in messages)
        c = min(cached_tokens(prev_serial, serial), n)

        total += n
        cached += c
        prev_serial = serial

        history = history + [{"role": "user", "content": d["question"]},
                             {"role": "assistant", "content": d["answer"]}]

    billed = (total - cached) + cached * CACHED_RATE + overhead
    return {
        "total": total, "cached": cached, "uncached": total - cached,
        "overhead": overhead, "billed": billed, "compactions": compactions,
    }


NAMES = {
    "current":  "current code (context in system msg, no trim)",
    "reorder":  "reorder only (context next to question)",
    "sliding":  "reorder + sliding window (last 20)",
    "block":    "reorder + block compaction",
}

print(f"\n{TURNS}-turn chat, 3 topic switches, cached input billed at {CACHED_RATE:g}x\n")
print(f"{'strategy':<46}{'sent':>10}{'cached':>10}{'hit%':>7}{'billed':>10}{'vs now':>9}")
print("-" * 92)

baseline = None
for key in ("current", "reorder", "sliding", "block"):
    r = run(key)
    if baseline is None:
        baseline = r["billed"]
    delta = f"{(r['billed'] / baseline - 1) * 100:+.0f}%" if baseline else "-"
    hit = r["cached"] / r["total"] * 100 if r["total"] else 0
    print(f"{NAMES[key]:<46}{r['total']:>10,}{r['cached']:>10,}{hit:>6.0f}%{r['billed']:>10,.0f}{delta:>9}")
    if key == "block":
        print(f"{'':<46}{'':>10}{'':>10}{'':>7}  ({r['compactions']} compactions, "
              f"{r['overhead']:,} tokens of extraction overhead included)")

print("\nper-turn prompt size (tokens sent, before caching):")
print(f"{'turn':>6}{'current':>12}{'reorder':>12}{'sliding':>12}{'block':>12}")
sizes = {}
for key in ("current", "reorder", "sliding", "block"):
    history = []
    profile = ""
    sizes[key] = []
    for t, d in enumerate(TURN_DATA):
        system_core = BASE + "\n\n" + TOPIC_PROMPTS[d["topic"]]
        context_block = "Answer using the provided context.\n\nContext:\n" + d["context"]
        if key == "current":
            msgs = ([{"role": "system", "content": system_core + "\n\n" + context_block}]
                    + history + [{"role": "user", "content": d["question"]}])
        elif key == "sliding":
            msgs = compaction.build_messages(system_core, "", history[-20:], context_block, d["question"])
        elif key == "block":
            if compaction.needs_compaction(history):
                dropped, kept = compaction.split_for_compaction(history)
                if dropped:
                    profile = "x" * 200
                    history = kept
            msgs = compaction.build_messages(system_core, profile, history, context_block, d["question"])
        else:
            msgs = compaction.build_messages(system_core, "", history, context_block, d["question"])
        sizes[key].append(sum(tok(m["content"]) for m in msgs))
        history = history + [{"role": "user", "content": d["question"]},
                             {"role": "assistant", "content": d["answer"]}]

for t in (0, 9, 19, 29, 39, 49, 59):
    print(f"{t+1:>6}" + "".join(f"{sizes[k][t]:>12,}" for k in ("current", "reorder", "sliding", "block")))
