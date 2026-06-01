import streamlit as st

# 1. Page Configuration
st.set_page_config(
    page_title="ImmHelp legal adviser AI", 
    page_icon="👽",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "all_chats" not in st.session_state:
    st.session_state.all_chats = {
        "Project Brainstorm": [
            {"role": "assistant", "content": "Hello! Let's flesh out your next big idea."}
        ],
        "Code Debugging": [
            {"role": "assistant", "content": "Paste your stack trace or code snippet here, and let's fix it."}
        ]
    }

if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Project Brainstorm"

# SIDEBAR
with st.sidebar:
    st.markdown("# 👽 ImmHelp")
    st.markdown("---")
    
    
    st.markdown("<h2 style='text-align: center;'> Your Chats </h2>", unsafe_allow_html=True)
    
    # Sidebar Action: New Chat
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_chat_id = f"New Chat {len(st.session_state.all_chats) + 1}"
        st.session_state.all_chats[new_chat_id] = [
            {"role": "assistant", "content": "How can I help you?"}
        ]
        st.session_state.active_chat = new_chat_id
        st.rerun()
    # List available chats as navigation items
    for chat_name in list(st.session_state.all_chats.keys()):
        is_active = chat_name == st.session_state.active_chat
        button_label = f"💬 {chat_name}" if is_active else f"  {chat_name}"
        
        if st.button(button_label, key=chat_name, use_container_width=True):
            st.session_state.active_chat = chat_name
            st.rerun()

    

# MAIN AREA
st.markdown(f"# 🚀 {st.session_state.active_chat}")

# Display the conversation history for the active chat
for message in st.session_state.all_chats[st.session_state.active_chat]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# INPUT
if user_input := st.chat_input("Type your query or paste code here..."):
    
    st.session_state.all_chats[st.session_state.active_chat].append(
        {"role": "user", "content": user_input}
    )
    with st.chat_message("user"):
        st.markdown(user_input)
        