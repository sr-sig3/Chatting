from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# 채팅방 관련 스키마
class ChatRoomCreate(BaseModel):
    name: str
    participants: List[str]  # 초대할 사용자명 목록


class ParticipantInfo(BaseModel):
    username: str
    is_admin: bool
    joined_at: datetime

    class Config:
        from_attributes = True


class ChatRoomInfo(BaseModel):
    id: int
    name: str
    created_by: str  # 생성자 사용자명
    participants_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatRoomDetail(ChatRoomInfo):
    participants: List[ParticipantInfo]

    class Config:
        from_attributes = True


class ChatRoomList(BaseModel):
    chat_rooms: List[ChatRoomInfo]


# 참여자 관련 스키마
class ParticipantAdd(BaseModel):
    usernames: List[str]


# 메시지 관련 스키마
class MessageCreate(BaseModel):
    content: str
    sender_username: Optional[str] = None  # 클라이언트 측 사용자명 (검증용)
    timestamp: Optional[str] = None  # 클라이언트 측 타임스탬프


class MessageInfo(BaseModel):
    id: int
    sender_username: str
    content: str
    created_at: datetime
    is_deleted: bool
    client_timestamp: Optional[str] = None  # 클라이언트 타임스탬프

    class Config:
        from_attributes = True


class MessageList(BaseModel):
    messages: List[MessageInfo]
    total_count: int
    page: int
    page_size: int
