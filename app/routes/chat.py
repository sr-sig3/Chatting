from fastapi import APIRouter
from app.routes import chat_rooms, chat_participants, chat_messages, chat_websocket

router = APIRouter()

# 채팅방 라우터
router.include_router(chat_rooms.router, prefix="/rooms", tags=["chat-rooms"])

# 채팅방 참여자 라우터
router.include_router(chat_participants.router, tags=["chat-participants"])

# 채팅 메시지 라우터
router.include_router(chat_messages.router, tags=["chat-messages"])

# WebSocket 라우터
router.include_router(chat_websocket.router, tags=["chat-websocket"])
