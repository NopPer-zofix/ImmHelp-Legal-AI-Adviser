import streamlit as st
import requests

# -----------------------------
# BACKEND CONFIG
# -----------------------------
BACKEND_URL = "http://localhost:5000"

# ==============================
# PAGE CONFIG  (must be first)
# ==============================
st.set_page_config(
    page_title="ImmHelp legal assistant",
    page_icon="👽",
    layout="wide",
    initial_sidebar_state="auto",
)

# ==============================
# GLOBAL CSS
# ==============================
st.markdown("""
<style>
/* ── Google Font ───────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* ── Hide Streamlit chrome cleanly (Keeps header toggle button) ── */
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none; }

/* Removes header background/blur so it doesn't block layout, but leaves buttons visible */
[data-testid="stHeader"] {
    background: transparent !important;
}

/* ── Persistent sidebar toggle (burger) ─────────────────────────
   Keep the collapse/expand control visible at all times, even when
   the sidebar is hidden. */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 999999 !important;
}
/* Make the burger readable against the light main background when collapsed */
[data-testid="stSidebarCollapsedControl"] button {
    color: #1E3A3A !important;
}

/* ── Main app background (chat view) ───────────────────────── */
.stApp { background-color: #EEF2F2 !important; }

/* ══════════════════════════════════════════════════════════════
   SIDEBAR  — only background colour, everything else default
══════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] { background-color: #0A4658 !important; }


/* Sidebar chat buttons — inactive chats */
[data-testid="stSidebar"] button[kind="secondary"],
[data-testid="stSidebar"] [data-testid="baseButton-secondary"] {
    background-color: #0E5C73 !important;
    color: #FFFFFF !important;
    border: 1px solid #0E5C73 !important;
}
/* Sidebar active chat (and other primary buttons) */
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] [data-testid="baseButton-primary"] {
    background-color: #0F7EAD !important;
    color: #FFFFFF !important;
    border: 1px solid #0F7EAD !important;
}

/* Custom HTML labels used inside the sidebar */
.sidebar-logo {
    font-size: 24px; font-weight: 700; color: #FFFFFF;
    letter-spacing: -0.5px; margin-bottom: 16px; padding-left: 2px;
}
.sidebar-section-label {
    font-size: 11px; font-weight: 600; color: #8AACAC;
    letter-spacing: 0.08em; text-transform: uppercase;
    margin-bottom: 6px; padding-left: 2px;
}
.sidebar-footer {
    display: flex; align-items: center; gap: 8px; height: 38px;
}
.user-avatar {
    width: 30px; height: 30px; border-radius: 50%;
    background: #E07B39; color: white; font-size: 12px; font-weight: 600;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.user-name {
    font-size: 13px; color: #C8DCDC; font-weight: 500;
    flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ══════════════════════════════════════════════════════════════
   MAIN AREA 
══════════════════════════════════════════════════════════════ */

.page-title {
    font-size: 26px; font-weight: 700; color: #1A2E2E; margin-bottom: 4px;
}
.page-divider {
    border: none; border-top: 1.5px solid #D4DEDE; margin: 8px 0 20px 0;
}

/* ── Chat input ──────────────────────────────────────────────────
   The surrounding bar matches the main area background so it blends in,
   while the input box itself keeps Streamlit's default styling. */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div {
    background-color: #EEF2F2 !important;
    border-top: none !important;
    box-shadow: none !important;
    padding-bottom: 5px !important;
}
/* Kill the accent-colored focus highlight when the input is active */
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] > div:focus-within,
[data-testid="stChatInput"]:focus-within [data-baseweb="base-input"] {
    border-color: #D4DEDE !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea:focus {
    box-shadow: none !important;
    outline: none !important;
}


/* Assistant message */
.msg-assistant {
    display: flex; align-items: flex-start; gap: 12px;
    margin-bottom: 20px; max-width: 100%;
}
.msg-avatar {
    width: 32px; height: 32px; border-radius: 8px;
    background-color: #2E7D7D; color: white; font-size: 14px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 2px;
}
.msg-bubble-assistant {
    background: #FFFFFF; border-radius: 0 14px 14px 14px;
    padding: 14px 18px; font-size: 14px; color: #1A2E2E;
    line-height: 1.6; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.msg-disclaimer {
    font-size: 11px; color: #9AAEAE; margin-top: 6px; font-style: italic;
}

/* Animated "typing" loader shown while the assistant is responding */
.typing-indicator {
    display: inline-flex; align-items: center; gap: 5px;
    background: #FFFFFF; border-radius: 0 14px 14px 14px;
    padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.typing-indicator span {
    width: 8px; height: 8px; border-radius: 50%;
    background: #2E7D7D; display: inline-block;
    animation: typing-bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
@keyframes typing-bounce {
    0%, 80%, 100% { transform: scale(0.5); opacity: 0.4; }
    40%           { transform: scale(1);   opacity: 1;   }
}

/* Rotating-ring spinner used for sign in / chat creation */
.imm-loader-row {
    display: flex; align-items: center; gap: 12px;
    padding: 8px 0; font-size: 14px; font-weight: 500;
}
.imm-spinner {
    width: 20px; height: 20px; border-radius: 50%;
    border: 3px solid rgba(46,125,125,0.25);
    border-top-color: #2E7D7D;
    animation: imm-spin 0.8s linear infinite;
    display: inline-block; flex-shrink: 0;
}
@keyframes imm-spin { to { transform: rotate(360deg); } }

/* User message */
.msg-user-row { display: flex; justify-content: flex-end; margin-bottom: 20px; }
.msg-bubble-user {
    background: #2E7D7D; color: #FFFFFF;
    border-radius: 14px 14px 0 14px; padding: 10px 18px;
    font-size: 14px; font-weight: 500; line-height: 1.5;
    max-width: 55%; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Empty state */
.empty-state { text-align: center; padding: 80px 40px; color: #9AAEAE; }
.empty-state h2 { font-size: 20px; color: #4A7070; margin-bottom: 8px; }
.empty-state p  { font-size: 14px; }

/* ══════════════════════════════════════════════════════════════
   AUTH PAGE  — dark teal full-page, styled inputs only here
══════════════════════════════════════════════════════════════ */
.auth-field-label {
    font-size: 12px; color: #A8CCCC; font-weight: 500;
    margin-bottom: 4px; letter-spacing: 0.02em;
}
.auth-switch {
    text-align: center; margin-top: 18px; font-size: 13px; color: #A8CCCC;
}
.auth-switch span {
    color: #4ECDC4; cursor: pointer; font-weight: 500; text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# AUTH HELPERS
# -----------------------------
def api_register(email: str, password: str, username: str) -> dict:
    try:
        r = requests.post(
            f"{BACKEND_URL}/users",
            json={"email": email, "password": password, "username": username},
            timeout=10,
        )
        if r.status_code == 201:
            return {"ok": True, "user": r.json()}
        return {"ok": False, "error": r.json().get("error", "Registration failed.")}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Could not connect to the backend."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_login(email: str, password: str) -> dict:
    try:
        r = requests.post(
            f"{BACKEND_URL}/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            return {"ok": True, "user": r.json()}
        return {"ok": False, "error": r.json().get("error", "Login failed.")}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Could not connect to the backend."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fetch_user_chat_count(user_id: int) -> int:
    """Returns how many chats this user already has in the backend."""
    try:
        r = requests.get(f"{BACKEND_URL}/chats/{user_id}", timeout=10)
        if r.status_code == 200:
            return len(r.json())
    except Exception:
        pass
    return 0


def load_user_chats(user_id: int) -> tuple[dict, dict, int]:
    """
    Fetches all chats for the user and their messages.
    Returns (all_chats, chat_ids, chat_count).
    Messages are stored as {role, content} dicts matching the frontend format.
    Assistant messages saved with the '[assistant] ' prefix are stripped.
    """
    all_chats  = {}
    chat_ids   = {}

    try:
        r = requests.get(f"{BACKEND_URL}/chats/{user_id}", timeout=10)
        if r.status_code != 200:
            return all_chats, chat_ids, 0

        chats = r.json()

        for i, chat in enumerate(chats, start=1):
            chat_id   = chat["id"]
            chat_name = f"Chat {i}"
            messages  = []
            try:
                mr = requests.get(f"{BACKEND_URL}/messages/{chat_id}", timeout=10)
                if mr.status_code == 200:
                    for m in mr.json():
                        content = m["message"]
                        if content.startswith("[assistant] "):
                            messages.append({"role": "assistant", "content": content[len("[assistant] "):]})
                        else:
                            messages.append({"role": "user", "content": content})
            except Exception:
                pass  # load chat with no messages rather than failing entirely

            all_chats[chat_name] = messages
            chat_ids[chat_name]  = chat_id

    except Exception:
        pass

    return all_chats, chat_ids, len(all_chats)


def api_create_chat(user_id: int) -> dict:
    try:
        r = requests.post(f"{BACKEND_URL}/chats", json={"user_id": user_id}, timeout=10)
        if r.status_code == 201:
            return {"ok": True, "chat": r.json()}
        return {"ok": False, "error": r.json().get("error", "Could not create chat.")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_save_message(user_id: int, chat_id: int, message: str, role: str = "assistant") -> None:
    """Fire-and-forget: persist a standalone message to the DB."""
    try:
        requests.post(
            f"{BACKEND_URL}/messages",
            json={"user_id": user_id, "chat_id": chat_id, "message": message, "role": role},
            timeout=10,
        )
    except Exception:
        pass  # non-critical — session state already has the message


def ask_backend(question: str, history: list, user_id: int, chat_id: int) -> str:
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={"question": question, "history": history, "user_id": user_id, "chat_id": chat_id},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("answer", "No answer returned from server.")
    except requests.exceptions.ConnectionError:
        return "❌ Could not connect to the backend. Is the Flask server running on port 5000?"
    except requests.exceptions.Timeout:
        return "❌ The request timed out. The backend may be overloaded."
    except requests.exceptions.HTTPError as e:
        return f"❌ Backend error ({e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"


def render_message(role: str, content: str):
    """Render a single chat message with custom HTML styling."""
    if role == "assistant":
        st.markdown(f"""
        <div class="msg-assistant">
            <div class="msg-avatar">i</div>
            <div>
                <div class="msg-bubble-assistant">{content}</div>
                <div class="msg-disclaimer">General info, not legal advice</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg-user-row">
            <div class="msg-bubble-user">{content}</div>
        </div>
        """, unsafe_allow_html=True)


def loader_html(text: str, light: bool = False) -> str:
    """Inline, browser-animated spinner (rotating ring) + label.
    `light=True` tunes the colors for dark backgrounds (auth page / sidebar)."""
    track = "rgba(255,255,255,0.25)" if light else "rgba(46,125,125,0.25)"
    top   = "#4ECDC4" if light else "#2E7D7D"
    color = "#A8CCCC" if light else "#4A7070"
    return f"""
    <div class="imm-loader-row" style="color:{color};">
        <span class="imm-spinner" style="border-color:{track};border-top-color:{top};"></span>
        <span>{text}</span>
    </div>"""


# -----------------------------
# SESSION STATE DEFAULTS
# -----------------------------
for key, default in {
    "user":               None,
    "all_chats":          {},
    "chat_ids":           {},
    "active_chat":        None,
    "opened_options_for": None,
    "user_chat_count":    0,
    "pending_prompt":     None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ==============================
# AUTH GATE
# ==============================
if st.session_state.user is None:

    # Dark background layout
    st.markdown("""
    <style>
    .stApp { background-color: #0A4658 !important; }
    .main .block-container { padding: 0 !important; max-width: 100% !important; }

    /* Inactive toggle / secondary buttons */
    .stApp button[kind="secondary"],
    .stApp [data-testid="baseButton-secondary"] {
        background-color: #0E5C73 !important;
        color: #FFFFFF !important;
        border: 1px solid #0E5C73 !important;
    }
    /* Active toggle, Sign in, Create account / primary buttons */
    .stApp button[kind="primary"],
    .stApp [data-testid="baseButton-primary"] {
        background-color: #0F7EAD !important;
        color: #FFFFFF !important;
        border: 1px solid #0F7EAD !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Session toggle: "login" | "register" ───────────────────
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    # ── Centered layout ─────────────────────────────────────────
    _, col_c, _ = st.columns([1, 0.9, 1])
    with col_c:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

        # Logo + tagline
        st.markdown("""
        <div style="text-align:center; margin-bottom:32px;">
            <div style="font-size:44px; font-weight:800; color:#FFFFFF;
                        letter-spacing:-1.5px; line-height:1;">immhelp</div>
            <div style="width:52px; height:3px; background:#4ECDC4;
                        border-radius:2px; margin:8px auto 14px auto;"></div>
            <div style="font-size:15px; color:#9ECECE; font-weight:400;">
                Immigration, made clear.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Mode toggle (Login / Register) ──────────────────────
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            login_active = "background:rgba(78,205,196,0.18);color:#FFFFFF;border-radius:8px;" \
                if st.session_state.auth_mode == "login" else "color:rgba(255,255,255,0.45);"
            if st.button("Login", key="toggle_login", use_container_width=True,
                         type="primary" if st.session_state.auth_mode == "login" else "secondary"):
                st.session_state.auth_mode = "login"
                st.rerun()
        with t_col2:
            if st.button("Register", key="toggle_register", use_container_width=True,
                         type="primary" if st.session_state.auth_mode == "register" else "secondary"):
                st.session_state.auth_mode = "register"
                st.rerun()

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # ── LOGIN FORM ──────────────────────────────────────────
        if st.session_state.auth_mode == "login":
            st.markdown('<p class="auth-field-label">Email</p>', unsafe_allow_html=True)
            login_email = st.text_input(
                "", key="login_email", placeholder="Email",
                label_visibility="collapsed",
            )
            st.markdown('<p class="auth-field-label">Password</p>', unsafe_allow_html=True)
            login_password = st.text_input(
                "", key="login_password", type="password", placeholder="Password",
                label_visibility="collapsed",
            )
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            if st.button("Sign in →", use_container_width=True, type="primary", key="login_btn"):
                if not login_email or not login_password:
                    st.error("Please fill in both fields.")
                else:
                    loader = st.empty()
                    loader.markdown(loader_html("Logging in…", light=True), unsafe_allow_html=True)
                    result = api_login(login_email, login_password)
                    loader.empty()
                    if result["ok"]:
                        st.session_state.user = result["user"]
                        all_chats, chat_ids, count = load_user_chats(result["user"]["id"])
                        st.session_state.all_chats       = all_chats
                        st.session_state.chat_ids        = chat_ids
                        st.session_state.user_chat_count = count
                        st.session_state.active_chat     = next(iter(all_chats), None)
                        st.rerun()
                    else:
                        st.error(result["error"])

        # ── REGISTER FORM ───────────────────────────────────────
        else:
            st.markdown('<p class="auth-field-label">How should we call you?</p>', unsafe_allow_html=True)
            reg_username = st.text_input(
                "", key="reg_username", placeholder="Name",
                label_visibility="collapsed",
            )
            st.markdown('<p class="auth-field-label">Email</p>', unsafe_allow_html=True)
            reg_email = st.text_input(
                "", key="reg_email", placeholder="Email",
                label_visibility="collapsed",
            )
            st.markdown('<p class="auth-field-label">Password</p>', unsafe_allow_html=True)
            reg_password = st.text_input(
                "", key="reg_password", type="password", placeholder="Password",
                label_visibility="collapsed",
            )
            st.markdown('<p class="auth-field-label">Repeat Password</p>', unsafe_allow_html=True)
            reg_confirm = st.text_input(
                "", key="reg_confirm", type="password", placeholder="Password",
                label_visibility="collapsed",
            )
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            if st.button("Create account →", use_container_width=True, type="primary", key="register_btn"):
                if not all([reg_username, reg_email, reg_password, reg_confirm]):
                    st.error("Please fill in all fields.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    loader = st.empty()
                    loader.markdown(loader_html("Creating account…", light=True), unsafe_allow_html=True)
                    result = api_register(reg_email, reg_password, reg_username)
                    loader.empty()
                    if result["ok"]:
                        st.session_state.user = result["user"]
                        st.session_state.user_chat_count = 0
                        st.rerun()
                    else:
                        st.error(result["error"])

    st.stop()


# ==============================
# MAIN APP
# ==============================
user    = st.session_state.user
user_id = user["id"]
username = user.get("username", "User")
initials = username[:2].upper()


# ── SIDEBAR ────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown("""
        <div style="text-align:center; margin-bottom:32px;">
            <div style="font-size:44px; font-weight:800; color:#FFFFFF;
                        letter-spacing:-1.5px; line-height:1;">immhelp</div>
            <div style="width:52px; height:3px; background:#4ECDC4;
                        border-radius:2px; margin:8px auto 14px auto;"></div>
        </div>
        """, unsafe_allow_html=True)

    # New Chat
    if st.button("+ New Chat", use_container_width=True, type="primary", key="new_chat_btn"):
        loader = st.empty()
        loader.markdown(loader_html("Creating chat…", light=True), unsafe_allow_html=True)
        result = api_create_chat(user_id)
        loader.empty()
        if result["ok"]:
            chat_id = result["chat"]["id"]
            st.session_state.user_chat_count += 1
            new_name = f"Chat {st.session_state.user_chat_count}"
            st.session_state.all_chats[new_name]  = [{"role": "assistant", "content": "How can I help you today?"}]
            st.session_state.chat_ids[new_name]   = chat_id
            st.session_state.active_chat          = new_name
            st.session_state.opened_options_for   = None
            st.rerun()
        else:
            st.error(result["error"])

    # Recent label
    st.markdown('<div class="sidebar-section-label">Recent</div>', unsafe_allow_html=True)

    # Chat list — reversed so the most recently created chats appear on top
    for chat_name in reversed(list(st.session_state.all_chats.keys())):
        is_active = (chat_name == st.session_state.active_chat)
        col1, col2 = st.columns([5, 1])

        with col1:
            btn_type = "primary" if is_active else "secondary"
            label = chat_name[:18] + "…" if len(chat_name) > 18 else chat_name
            if st.button(label, key=f"select_{chat_name}", use_container_width=True, type=btn_type):
                st.session_state.active_chat        = chat_name
                st.session_state.opened_options_for = None
                st.rerun()

        with col2:
            if st.button("⋮", key=f"opt_{chat_name}", use_container_width=True):
                st.session_state.opened_options_for = (
                    None if st.session_state.opened_options_for == chat_name else chat_name
                )
                st.rerun()

        if st.session_state.opened_options_for == chat_name:
            with st.container(border=True):
                new_title = st.text_input("✏️ Rename", value=chat_name, key=f"rename_{chat_name}")
                if new_title != chat_name and new_title.strip():
                    st.session_state.all_chats[new_title] = st.session_state.all_chats.pop(chat_name)
                    st.session_state.chat_ids[new_title]  = st.session_state.chat_ids.pop(chat_name, None)
                    if st.session_state.active_chat == chat_name:
                        st.session_state.active_chat = new_title
                    st.session_state.opened_options_for = None
                    st.rerun()
                if st.button("🗑️ Delete", key=f"del_{chat_name}", type="primary", use_container_width=True):
                    st.session_state.all_chats.pop(chat_name)
                    st.session_state.chat_ids.pop(chat_name, None)
                    if st.session_state.active_chat == chat_name:
                        remaining = list(st.session_state.all_chats.keys())
                        st.session_state.active_chat = remaining[0] if remaining else None
                    st.session_state.opened_options_for = None
                    st.rerun()

    # Spacer + footer
    st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border:none;border-top:1px solid #2E5C5C;margin:12px 0 8px 0;'>",
                unsafe_allow_html=True)
    foot_col1, foot_col2 = st.columns([4, 1], vertical_alignment="center")
    with foot_col1:
        st.markdown(f"""
        <div class="sidebar-footer">
            <div class="user-avatar">{initials}</div>
            <span class="user-name">{username}</span>
        </div>
        """, unsafe_allow_html=True)
    with foot_col2:
        if st.button("⏻", key="logout_btn", help="Logout"):
            for key in ["user", "all_chats", "chat_ids", "active_chat", "opened_options_for"]:
                st.session_state[key] = {} if key in ("all_chats", "chat_ids") else None
            st.session_state.user_chat_count = 0
            st.rerun()


# ── MAIN AREA ──────────────────────────────────────────────────
active = st.session_state.active_chat

if active and active in st.session_state.all_chats:
    # Title
    st.markdown(f'<div class="page-title">{active}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="page-divider">', unsafe_allow_html=True)

    # Messages
    current_messages = st.session_state.all_chats[active]
    if not current_messages:
        st.markdown("""
        <div class="empty-state">
            <h2>Start the conversation</h2>
            <p>Ask any immigration-related question below.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in current_messages:
            render_message(msg["role"], msg["content"])

    # While waiting on the backend, show an animated typing loader, then fetch.
    if st.session_state.pending_prompt:
        st.markdown("""
        <div class="msg-assistant">
            <div class="msg-avatar">i</div>
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
        """, unsafe_allow_html=True)

        prompt   = st.session_state.pending_prompt
        chat_id  = st.session_state.chat_ids.get(active)
        history  = st.session_state.all_chats[active][:-1]
        ai_response = ask_backend(prompt, history, user_id, chat_id)

        st.session_state.all_chats[active].append({"role": "assistant", "content": ai_response})
        st.session_state.pending_prompt = None
        st.rerun()

else:
    st.markdown("""
    <div class="empty-state">
        <h2>👽 Welcome to ImmHelp</h2>
        <p>Click <strong>+ New Chat</strong> in the sidebar to get started.</p>
    </div>
    """, unsafe_allow_html=True)


# ── CHAT INPUT ─────────────────────────────────────────────────
if user_input := st.chat_input("Ask about visas, permits, citizenship…"):

    if not active or active not in st.session_state.all_chats:
        result = api_create_chat(user_id)
        if not result["ok"]:
            st.error(result["error"])
            st.stop()
        chat_id = result["chat"]["id"]
        st.session_state.user_chat_count += 1
        active = f"Chat {st.session_state.user_chat_count}"
        st.session_state.all_chats[active] = []
        st.session_state.chat_ids[active]   = chat_id
        st.session_state.active_chat       = active

    # Show the user's message immediately, then let the main area render the
    # animated loader and fetch the answer on the next run.
    st.session_state.all_chats[active].append({"role": "user", "content": user_input})
    st.session_state.pending_prompt = user_input
    st.rerun()