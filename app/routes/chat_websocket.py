from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict
from datetime import datetime
import json
from pydantic import ValidationError
import logging

from app.database import get_db
from app.models.user import User
from app.models.chat import ChatRoom, ChatRoomParticipant, Message
from app.schemas.websocket import WebSocketMessage, WebSocketIncomingMessage
from app.utils.websocket_manager import manager
from app.utils.auth import get_current_user_ws

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()


@router.websocket("/rooms/{room_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket, room_id: int, token: str = None, db: Session = Depends(get_db)
):
    """WebSocket 연결을 통한 실시간 채팅"""
    if not token:
        # 토큰이 없으면 연결 거부
        logger.error(f"WebSocket connection attempt to room {room_id} without token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # 토큰으로 사용자 인증
        user = await get_current_user_ws(token, db)
        logger.info(
            f"WebSocket authentication for user {user.username}, connecting to room {room_id}"
        )

        # 채팅방 존재 확인
        chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not chat_room:
            logger.error(
                f"Chat room with id {room_id} not found for WebSocket connection"
            )
            await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
            return

        # 사용자가 채팅방 참여자인지 확인
        is_participant = (
            db.query(ChatRoomParticipant)
            .filter(
                and_(
                    ChatRoomParticipant.chat_room_id == room_id,
                    ChatRoomParticipant.user_id == user.id,
                )
            )
            .first()
            is not None
        )

        if not is_participant:
            logger.error(
                f"User {user.username} tried to connect to room {room_id} but is not a participant"
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 웹소켓 연결 수락
        await manager.connect(websocket, room_id, user.id, user.username)
        logger.info(
            f"WebSocket connection established for user {user.username} in room {room_id}"
        )

        try:
            while True:
                # 클라이언트로부터 메시지 수신
                data = await websocket.receive_text()
                logger.info(
                    f"Received WebSocket message from user {user.username} in room {room_id}: {data}"
                )

                # 메시지 처리
                try:
                    # JSON 데이터 파싱 시도
                    try:
                        message_data = json.loads(data)
                        # 스키마 검증
                        logger.info(f"Parsed message data: {message_data}")
                        incoming_message = WebSocketIncomingMessage(**message_data)
                        message_content = incoming_message.content
                        client_timestamp = incoming_message.timestamp
                        message_type = incoming_message.message_type
                        logger.info(
                            f"Parsed WebSocket message: type={message_type}, content={message_content}, timestamp={client_timestamp}"
                        )
                    except (json.JSONDecodeError, ValidationError) as e:
                        # JSON 형식이 아니면 텍스트 메시지로 취급
                        logger.warning(f"Invalid WebSocket message format: {str(e)}")
                        message_content = data.strip()
                        client_timestamp = None
                        message_type = "chat"

                    if not message_content or message_type != "chat":
                        # 채팅 메시지가 아니거나 내용이 없으면 건너뜀
                        # 다른 메시지 타입(typing, read 등)은 별도 처리 가능
                        if message_type in ["typing", "read"]:
                            # 타이핑 중, 읽음 표시 등 DB에 저장하지 않는 이벤트 처리
                            logger.debug(
                                f"Broadcasting {message_type} event from {user.username} in room {room_id}"
                            )
                            await manager.broadcast(
                                room_id=room_id,
                                message={
                                    "type": message_type,
                                    "sender_username": user.username,
                                    "timestamp": client_timestamp
                                    or datetime.now().isoformat(),
                                },
                            )
                        continue

                    # 메시지 저장
                    new_message = Message(
                        chat_room_id=room_id, sender_id=user.id, content=message_content
                    )

                    # 클라이언트 타임스탬프 저장
                    if client_timestamp:
                        try:
                            client_ts = datetime.fromisoformat(
                                client_timestamp.replace("Z", "+00:00")
                            )
                            new_message.client_timestamp = client_ts
                            logger.debug(f"Using client timestamp: {client_timestamp}")
                        except ValueError as e:
                            logger.warning(
                                f"Invalid timestamp format: {client_timestamp}, Error: {str(e)}"
                            )
                            pass  # 형식이 잘못되면 무시

                    db.add(new_message)
                    db.commit()
                    db.refresh(new_message)

                    # 채팅방 업데이트 시간 갱신
                    chat_room.updated_at = new_message.created_at
                    db.commit()

                    # 모든 사용자에게 메시지 브로드캐스트
                    server_timestamp = new_message.created_at.isoformat()
                    logger.info(
                        f"Saved and broadcasting message from {user.username} in room {room_id} (message_id: {new_message.id})"
                    )
                    await manager.broadcast(
                        room_id=room_id,
                        message={
                            "type": "chat",
                            "content": message_content,
                            "sender_username": user.username,
                            "timestamp": server_timestamp,
                            "client_timestamp": client_timestamp,  # 클라이언트 타임스탬프 포함
                            "id": new_message.id,
                        },
                    )

                except Exception as e:
                    # 에러 발생 시 개인 메시지로 에러 알림
                    logger.error(f"Error processing WebSocket message: {str(e)}")
                    await manager.send_personal_message(
                        {"type": "system", "content": f"Error: {str(e)}"}, websocket
                    )

        except WebSocketDisconnect:
            # 연결 종료 처리
            logger.info(
                f"WebSocket disconnected for user {user.username} in room {room_id}"
            )
            disconnect_message = manager.disconnect(room_id, user.id, user.username)
            if disconnect_message and room_id in manager.active_connections:
                # 다른 사용자들에게 나갔다는 메시지 전송
                logger.info(
                    f"Broadcasting disconnect event for user {user.username} in room {room_id}"
                )
                await manager.broadcast(room_id=room_id, message=disconnect_message)
                await manager.send_active_users(room_id)

    except Exception as e:
        # 인증 실패 등의 이유로 연결 거부
        logger.error(f"WebSocket Error: {str(e)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
