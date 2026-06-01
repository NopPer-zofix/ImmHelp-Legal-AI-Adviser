import streamlit as st
import requests

# -----------------------------
# BACKEND CONFIG
# -----------------------------
BACKEND_URL = "http://localhost:5000"
HARDCODED_USER_ID = 1
HARDCODED_CHAT_ID = 1


def ask_backend(question: str) -> str:
    """Send a question to the /ask endpoint and return the answer."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={
                "question": question,
                "user_id": HARDCODED_USER_ID,
                "chat_id": HARDCODED_CHAT_ID,
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


st.set_page_config(
    page_title="ImmHelp legal adviser AI", 
    page_icon="👽",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Legal Adviser"

if "opened_options_for" not in st.session_state:
    st.session_state.opened_options_for = None


# SIDEBAR
with st.sidebar:
    st.markdown("# 👽 ImmHelp")
    st.markdown("---")
    st.markdown("<h2 style='text-align: center;'> Your Chats </h2>", unsafe_allow_html=True)
    
    for chat_name in list(st.session_state.all_chats.keys()):
        is_active = chat_name == st.session_state.active_chat
        
        row_col1, row_col2 = st.columns([4, 1])
        
        with row_col1:
            btn_type = "primary" if is_active else "secondary"
            if st.button(chat_name, key=f"select_{chat_name}", use_container_width=True, type = btn_type):
                st.session_state.active_chat = chat_name
                st.session_state.opened_options_for = None 
                st.rerun()
                
        with row_col2:
            if st.button("⋮", key=f"options_trigger_{chat_name}", use_container_width=True):
                if st.session_state.opened_options_for == chat_name:
                    st.session_state.opened_options_for = None
                else:
                    st.session_state.opened_options_for = chat_name
                st.rerun()

        if st.session_state.opened_options_for == chat_name:
            with st.container(border=True):

                # Edit
                new_title = st.text_input(
                    "✏️ Edit", 
                    value=chat_name, 
                    key=f"rename_field_{chat_name}",
                    label_visibility="visible"
                )
                if new_title != chat_name and new_title.strip() != "":
                    st.session_state.all_chats[new_title] = st.session_state.all_chats.pop(chat_name)
                    if st.session_state.active_chat == chat_name:
                        st.session_state.active_chat = new_title
                    st.session_state.opened_options_for = None
                    st.rerun()
                
                # Delete
                if st.button("🗑️ Delete", key=f"delete_btn_{chat_name}", type="primary", use_container_width=True):
                    st.session_state.all_chats.pop(chat_name)
                    if st.session_state.active_chat == chat_name:
                        remaining_chats = list(st.session_state.all_chats.keys())
                        st.session_state.active_chat = remaining_chats[0] if remaining_chats else "Legal Adviser"
                    st.session_state.opened_options_for = None
                    st.rerun()

    st.write("")
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_chat_id = f"New Chat {len(st.session_state.all_chats) + 1}"
        st.session_state.all_chats[new_chat_id] = [
            {"role": "assistant", "content": "How can I help you?"}
        ]
        st.session_state.active_chat = new_chat_id
        st.session_state.opened_options_for = None
        st.rerun()


# MAIN AREA
if "all_chats" in st.session_state and st.session_state.active_chat in st.session_state.all_chats:
    st.markdown(f"# {st.session_state.active_chat}")
    st.markdown("---")
    
    current_messages = st.session_state.all_chats[st.session_state.active_chat]
    
    if len(current_messages) == 0:
        st.markdown("### Welcome! Ask a new question by typing below.")
    else:
        for message in current_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
else:
    st.markdown("# Legal Adviser")
    st.markdown("---")
    st.markdown("### 📭 No active conversations found.")
    st.caption("Click '➕ New Chat' in the sidebar or type a message below to start.")


# --- INPUT ---
if user_input := st.chat_input("Type your question here..."):
    
    if "all_chats" not in st.session_state or not st.session_state.all_chats:
        st.session_state.all_chats = {}
        st.session_state.active_chat = "New Chat 1"
        
    if st.session_state.active_chat not in st.session_state.all_chats:
        st.session_state.all_chats[st.session_state.active_chat] = []

    st.session_state.all_chats[st.session_state.active_chat].append(
        {"role": "user", "content": user_input}
    )
    
    with st.chat_message("user"):
        st.markdown(user_input)
        
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            ai_response = ask_backend(user_input)
            st.markdown(ai_response)
            
    st.session_state.all_chats[st.session_state.active_chat].append(
        {"role": "assistant", "content": ai_response}
    )
    
    st.rerun()