from app.database import (
    get_recent_context,
    save_conversation
)

from app.graph import run_mindsight


def process_chat(
    session_id: str,
    message: str
) -> dict:

    # 1. 查询历史
    conversation_context = get_recent_context(
        session_id
    )

    # 2. 运行 MindSight Agent
    final_state = run_mindsight(
        session_id=session_id,
        user_input=message,
        conversation_context=conversation_context
    )

    # 3. 保存当前轮
    save_conversation(
        session_id=session_id,
        user_input=message,
        final_response=final_state["draft_response"],
        decision=final_state["decision"],
        risk_level=final_state["risk_level"],
        reason=final_state["reason"],
        rewrite_count=final_state["rewrite_count"]
    )

    # 4. 返回统一结果
    return {
        "session_id": session_id,
        "response": final_state["draft_response"],
        "decision": final_state["decision"],
        "risk_level": final_state["risk_level"],
        "reason": final_state["reason"],
        "rewrite_count": final_state["rewrite_count"]
    }