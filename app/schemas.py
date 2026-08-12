from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    decision: str
    risk_level: str
    reason: str
    rewrite_count: int
    session_id: str