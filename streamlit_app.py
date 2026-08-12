import uuid

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000/chat"


# -------------------------
# Page configuration
# -------------------------

st.set_page_config(
    page_title="MindSight AI",
    page_icon="🧠",
    layout="centered"
)


st.title("🧠 MindSight AI")

st.caption(
    "A supportive AI conversation system "
    "with supervised response generation."
)


# -------------------------
# Initialize session state
# -------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = str(
        uuid.uuid4()
    )


if "messages" not in st.session_state:
    st.session_state.messages = []


if "last_supervision" not in st.session_state:
    st.session_state.last_supervision = None


# -------------------------
# Sidebar
# -------------------------

with st.sidebar:

    st.header("MindSight")

    st.subheader("Session ID")

    st.code(
        st.session_state.session_id
    )


    if st.button("New conversation"):

        st.session_state.session_id = str(
            uuid.uuid4()
        )

        st.session_state.messages = []

        st.session_state.last_supervision = None

        st.rerun()


    st.divider()

    st.subheader("Supervisor")


    if st.session_state.last_supervision:

        supervision = (
            st.session_state.last_supervision
        )

        st.write(
            "Decision:",
            supervision["decision"]
        )

        st.write(
            "Risk level:",
            supervision["risk_level"]
        )

        st.write(
            "Rewrite count:",
            supervision["rewrite_count"]
        )

        st.write("Reason:")

        st.caption(
            supervision["reason"]
        )

    else:

        st.caption(
            "No response has been reviewed yet."
        )


# -------------------------
# Display chat history
# -------------------------

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# -------------------------
# Chat input
# -------------------------

prompt = st.chat_input(
    "Type your message..."
)


if prompt:

    # Save user message in frontend history
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    # Immediately display user message
    with st.chat_message("user"):

        st.markdown(prompt)


    payload = {
        "session_id": st.session_state.session_id,
        "message": prompt
    }


    data = None


    # Display assistant container
    with st.chat_message("assistant"):

        with st.spinner(
            "MindSight is thinking..."
        ):

            try:

                response = requests.post(
                    API_URL,
                    json=payload,
                    timeout=60
                )

                response.raise_for_status()

                data = response.json()

                answer = data["response"]


            except requests.RequestException as e:

                answer = (
                    "MindSight could not connect "
                    "to the backend service."
                )

                st.error(
                    f"Backend request failed: {e}"
                )


        st.markdown(answer)


    # Save assistant response
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )


    # Save Supervisor information
    if data:

        st.session_state.last_supervision = {
            "decision": data["decision"],
            "risk_level": data["risk_level"],
            "reason": data["reason"],
            "rewrite_count": data["rewrite_count"]
        }


    st.rerun()