import streamlit as st
import requests

# -----------------------------
# BACKEND CONFIG
# -----------------------------
BACKEND_URL = "http://localhost:5000"


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
        r = requests.post(
            f"{BACKEND_URL}/chats",
            json={"user_id": user_id},
            timeout=10,
        )
        if r.status_code == 201:
            return {"ok": True, "chat": r.json()}
        return {"ok": False, "error": r.json().get("error", "Could not create chat.")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ask_backend(question: str, history: list, user_id: int, chat_id: int) -> str:
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={
                "question": question,
                "history":  history,
                "user_id":  user_id,
                "chat_id":  chat_id,
            },
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


# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="ImmHelp legal adviser AI",
    page_icon="👽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# SESSION STATE DEFAULTS
# -----------------------------
for key, default in {
    "user":               None,   # {"id": ..., "email": ..., "username": ...}
    "all_chats":          {},     # chat_name -> list of messages
    "chat_ids":           {},     # chat_name -> backend chat id
    "active_chat":        None,
    "opened_options_for": None,
    "auth_mode":          "login",  # "login" | "register"
    "user_chat_count":    0,      # how many chats this user has ever created
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ==============================
# AUTH GATE
# ==============================
if st.session_state.user is None:

    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("# 👽 ImmHelp")
        st.markdown("### Your AI Immigration Legal Adviser")
        st.markdown("---")

        mode = st.session_state.auth_mode

        # Tab toggle
        tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

        # ---- LOGIN TAB ----
        with tab_login:
            st.markdown("#### Welcome back")
            login_email    = st.text_input("Email",    key="login_email",    placeholder="you@example.com")
            login_password = st.text_input("Password", key="login_password", type="password", placeholder="••••••••")

            if st.button("Login", use_container_width=True, type="primary", key="login_btn"):
                if not login_email or not login_password:
                    st.error("Please fill in both fields.")
                else:
                    with st.spinner("Logging in…"):
                        result = api_login(login_email, login_password)
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

        # ---- REGISTER TAB ----
        with tab_register:
            st.markdown("#### Create your account")
            reg_username = st.text_input("Username", key="reg_username", placeholder="John Doe")
            reg_email    = st.text_input("Email",    key="reg_email",    placeholder="you@example.com")
            reg_password = st.text_input("Password", key="reg_password", type="password", placeholder="••••••••")
            reg_confirm  = st.text_input("Confirm password", key="reg_confirm", type="password", placeholder="••••••••")

            if st.button("Create account", use_container_width=True, type="primary", key="register_btn"):
                if not all([reg_username, reg_email, reg_password, reg_confirm]):
                    st.error("Please fill in all fields.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating account…"):
                        result = api_register(reg_email, reg_password, reg_username)
                    if result["ok"]:
                        st.session_state.user = result["user"]
                        st.session_state.user_chat_count = 0  # brand new user
                        st.rerun()
                    else:
                        st.error(result["error"])

    st.stop()  # Nothing below renders until logged in


# ==============================
# MAIN APP  (user is logged in)
# ==============================
user    = st.session_state.user
user_id = user["id"]


# SIDEBAR
with st.sidebar:
    st.markdown("# 👽 ImmHelp")
    st.markdown("---")

    # User info + logout
    st.markdown(f"👤 **{user['username']}**")
    st.caption(user["email"])
    if st.button("Logout", use_container_width=True):
        for key in ["user", "all_chats", "chat_ids", "active_chat", "opened_options_for"]:
            st.session_state[key] = {} if key in ("all_chats", "chat_ids") else None
        st.session_state.user_chat_count = 0
        st.rerun()

    st.markdown("---")
    st.markdown("<h2 style='text-align: center;'>Your Chats</h2>", unsafe_allow_html=True)

    for chat_name in list(st.session_state.all_chats.keys()):
        is_active = chat_name == st.session_state.active_chat

        row_col1, row_col2 = st.columns([4, 1])

        with row_col1:
            btn_type = "primary" if is_active else "secondary"
            if st.button(chat_name, key=f"select_{chat_name}", use_container_width=True, type=btn_type):
                st.session_state.active_chat        = chat_name
                st.session_state.opened_options_for = None
                st.rerun()

        with row_col2:
            if st.button("⋮", key=f"options_trigger_{chat_name}", use_container_width=True):
                st.session_state.opened_options_for = (
                    None if st.session_state.opened_options_for == chat_name else chat_name
                )
                st.rerun()

        if st.session_state.opened_options_for == chat_name:
            with st.container(border=True):
                new_title = st.text_input(
                    "✏️ Edit",
                    value=chat_name,
                    key=f"rename_field_{chat_name}",
                )
                if new_title != chat_name and new_title.strip():
                    st.session_state.all_chats[new_title] = st.session_state.all_chats.pop(chat_name)
                    st.session_state.chat_ids[new_title]  = st.session_state.chat_ids.pop(chat_name, None)
                    if st.session_state.active_chat == chat_name:
                        st.session_state.active_chat = new_title
                    st.session_state.opened_options_for = None
                    st.rerun()

                if st.button("🗑️ Delete", key=f"delete_btn_{chat_name}", type="primary", use_container_width=True):
                    st.session_state.all_chats.pop(chat_name)
                    st.session_state.chat_ids.pop(chat_name, None)
                    if st.session_state.active_chat == chat_name:
                        remaining = list(st.session_state.all_chats.keys())
                        st.session_state.active_chat = remaining[0] if remaining else None
                    st.session_state.opened_options_for = None
                    st.rerun()

    st.write("")
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        with st.spinner("Creating chat…"):
            result = api_create_chat(user_id)
        if result["ok"]:
            chat_id = result["chat"]["id"]
            st.session_state.user_chat_count += 1
            new_chat_name = f"Chat {st.session_state.user_chat_count}"
            st.session_state.all_chats[new_chat_name]  = [{"role": "assistant", "content": "How can I help you?"}]
            st.session_state.chat_ids[new_chat_name]   = chat_id
            st.session_state.active_chat               = new_chat_name
            st.session_state.opened_options_for        = None
            st.rerun()
        else:
            st.error(result["error"])


# MAIN AREA
active = st.session_state.active_chat

if active and active in st.session_state.all_chats:
    st.markdown(f"# {active}")
    st.markdown("---")

    current_messages = st.session_state.all_chats[active]

    if not current_messages:
        st.markdown("### Welcome! Ask a new question by typing below.")
    else:
        for message in current_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
else:
    st.markdown("# 👽 ImmHelp Legal Adviser")
    st.markdown("---")
    st.markdown("### 📭 No active conversations.")
    st.caption("Click '➕ New Chat' in the sidebar to get started.")


# INPUT
if user_input := st.chat_input("Type your question here..."):

    # Auto-create a chat if none exists
    if not active or active not in st.session_state.all_chats:
        result = api_create_chat(user_id)
        if not result["ok"]:
            st.error(result["error"])
            st.stop()
        chat_id = result["chat"]["id"]
        st.session_state.user_chat_count += 1
        active  = f"Chat {st.session_state.user_chat_count}"
        st.session_state.all_chats[active] = [{"role": "assistant", "content": "How can I help you?"}]
        st.session_state.chat_ids[active]  = chat_id
        st.session_state.active_chat       = active

    chat_id = st.session_state.chat_ids.get(active)

    st.session_state.all_chats[active].append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history     = st.session_state.all_chats[active][:-1]
            ai_response = ask_backend(user_input, history, user_id, chat_id)
            st.markdown(ai_response)

    st.session_state.all_chats[active].append({"role": "assistant", "content": ai_response})
    st.rerun()
