from pydantic import BaseModel, Field
from typing import Literal, Optional


class WebSocketMessage(BaseModel):
    type: Literal["chat", "system", "users_list"] = "chat"
    content: str
    sender_username: Optional[str] = None
    room_id: Optional[int] = None
    timestamp: Optional[str] = None


class WebSocketIncomingMessage(BaseModel):
    content: str
    timestamp: Optional[str] = None  # 클라이언트 타임스탬프
    message_type: Literal["chat", "typing", "read"] = "chat"  # 메시지 유형
