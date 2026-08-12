import sqlite3

import pandas as pd
import streamlit as st

from app.database import DB_PATH


st.set_page_config(
    page_title="MindSight Database Viewer",
    page_icon="🗄️",
    layout="wide"
)

st.title("🗄️ MindSight Database Viewer")

st.caption(f"Database: {DB_PATH}")


# -------------------------
# Get session IDs
# -------------------------

with sqlite3.connect(DB_PATH) as conn:

    session_df = pd.read_sql_query(
        """
        SELECT DISTINCT session_id
        FROM conversation_logs
        ORDER BY session_id
        """,
        conn
    )


session_ids = session_df["session_id"].tolist()


# -------------------------
# Sidebar filters
# -------------------------

with st.sidebar:

    st.header("Filters")

    selected_session = st.selectbox(
        "Session",
        ["All"] + session_ids
    )

    limit = st.number_input(
        "Maximum rows",
        min_value=1,
        max_value=1000,
        value=100
    )


# -------------------------
# Query database
# -------------------------

with sqlite3.connect(DB_PATH) as conn:

    if selected_session == "All":

        df = pd.read_sql_query(
            """
            SELECT
                id,
                session_id,
                user_input,
                final_response,
                decision,
                risk_level,
                reason,
                rewrite_count,
                created_at
            FROM conversation_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            conn,
            params=(limit,)
        )

    else:

        df = pd.read_sql_query(
            """
            SELECT
                id,
                session_id,
                user_input,
                final_response,
                decision,
                risk_level,
                reason,
                rewrite_count,
                created_at
            FROM conversation_logs
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            conn,
            params=(
                selected_session,
                limit
            )
        )


# -------------------------
# Summary
# -------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Records",
    len(df)
)

if not df.empty:

    col2.metric(
        "Sessions",
        df["session_id"].nunique()
    )

    col3.metric(
        "Rewrites",
        int(
            df["rewrite_count"].sum()
        )
    )

    col4.metric(
        "Handoffs",
        int(
            (df["decision"] == "handoff").sum()
        )
    )

else:

    col2.metric("Sessions", 0)
    col3.metric("Rewrites", 0)
    col4.metric("Handoffs", 0)


st.divider()


# -------------------------
# Table
# -------------------------

st.subheader("Conversation Logs")

if df.empty:

    st.info("No conversation records found.")

else:

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


# -------------------------
# Detailed conversation view
# -------------------------

st.divider()

st.subheader("Conversation Detail")

if selected_session == "All":

    st.caption(
        "Select a specific session in the sidebar "
        "to view it as a conversation."
    )

else:

    conversation_df = df.sort_values(
        "id",
        ascending=True
    )

    for _, row in conversation_df.iterrows():

        with st.chat_message("user"):
            st.markdown(
                row["user_input"]
            )

        with st.chat_message("assistant"):
            st.markdown(
                row["final_response"]
            )

            st.caption(
                f"Decision: {row['decision']} | "
                f"Risk: {row['risk_level']} | "
                f"Rewrites: {row['rewrite_count']}"
            )

            with st.expander(
                "Supervisor reason"
            ):
                st.write(
                    row["reason"]
                )