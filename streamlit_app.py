import uuid

import streamlit as st

from app.graph import run_mindsight
from app.database import (
    init_db,
    get_recent_context,
    save_conversation,
)


# -------------------------
# Initialize database
# -------------------------

init_db()


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


    # Display user message
    with st.chat_message("user"):

        st.markdown(prompt)


    # -------------------------
    # Run MindSight directly
    # -------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "MindSight is thinking..."
        ):

            try:

                # 1. Read previous conversation
                conversation_context = (
                    get_recent_context(
                        st.session_state.session_id
                    )
                )

                # 2. Run LangGraph directly
                final_state = run_mindsight(
                    session_id=(
                        st.session_state.session_id
                    ),
                    user_input=prompt,
                    conversation_context=(
                        conversation_context
                        or ""
                    )
                )

                # 3. Get final response
                answer = final_state[
                    "draft_response"
                ]

                # 4. Save current conversation
                save_conversation(
                    session_id=(
                        st.session_state.session_id
                    ),
                    user_input=prompt,
                    final_response=answer,
                    decision=final_state[
                        "decision"
                    ],
                    risk_level=final_state[
                        "risk_level"
                    ],
                    reason=final_state[
                        "reason"
                    ],
                    rewrite_count=final_state[
                        "rewrite_count"
                    ]
                )

                # 5. Save Supervisor information
                st.session_state.last_supervision = {
                    "decision": final_state[
                        "decision"
                    ],
                    "risk_level": final_state[
                        "risk_level"
                    ],
                    "reason": final_state[
                        "reason"
                    ],
                    "rewrite_count": final_state[
                        "rewrite_count"
                    ]
                }

            except Exception as e:

                print(
                    "Streamlit chat error:",
                    e
                )

                answer = (
                    "MindSight could not process "
                    "the request. Please try again."
                )

                st.error(
                    "An error occurred while "
                    "processing the request."
                )


        st.markdown(answer)


    # Save assistant response
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )


    st.rerun()