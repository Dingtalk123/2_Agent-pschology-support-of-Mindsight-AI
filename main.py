from fastapi import FastAPI, HTTPException
from app.graph import run_mindsight
from app.schemas import ChatRequest, ChatResponse
from contextlib import asynccontextmanager
from app.database import init_db, save_conversation,get_recent_context

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    print("Database initialized.")

    yield

app = FastAPI(
    title="MindSight AI",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
def root():
    return {
        "message": "MindSight API  running"
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        # 1. 先读取这个 session 之前的对话
        conversation_context = get_recent_context(
            request.session_id
        )

        print("\n--- Conversation Context ---")

        if conversation_context:
            print(conversation_context)
        else:
            print("(No previous conversation)")

        # 2. 把当前输入 + 历史一起交给 LangGraph
        final_state = run_mindsight(
            session_id=request.session_id,
            user_input=request.message,
            conversation_context=conversation_context
        )

        # 3. Agent 执行完成后，再保存当前这一轮
        save_conversation(
            session_id=request.session_id,
            user_input=request.message,
            final_response=final_state["draft_response"],
            decision=final_state["decision"],
            risk_level=final_state["risk_level"],
            reason=final_state["reason"],
            rewrite_count=final_state["rewrite_count"]
        )

        # 4. 返回给客户端
        return ChatResponse(
            session_id=request.session_id,
            response=final_state["draft_response"],
            decision=final_state["decision"],
            risk_level=final_state["risk_level"],
            reason=final_state["reason"],
            rewrite_count=final_state["rewrite_count"]
        )

    except Exception as e:
        print("Chat endpoint error:")
        print(e)

        raise HTTPException(
            status_code=500,
            detail="MindSight failed to process the request."
        )