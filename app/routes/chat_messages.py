from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import Optional
from datetime import datetime
import logging

from app.database import get_db
from app.models.user import User
from app.models.chat import ChatRoom, ChatRoomParticipant, Message
from app.schemas.chat import MessageCreate, MessageInfo, MessageList
from app.utils.auth import get_current_user

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()


@router.post("/{room_id}/messages", response_model=MessageInfo)
async def send_message(
    room_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """채팅방에 새 메시지를 전송합니다."""
    logger.info(f"Sending message to room {room_id}. User: {current_user.username}")

    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found",
        )

    # 사용자가 채팅방 참여자인지 확인
    is_participant = (
        db.query(ChatRoomParticipant)
        .filter(
            and_(
                ChatRoomParticipant.chat_room_id == room_id,
                ChatRoomParticipant.user_id == current_user.id,
            )
        )
        .first()
        is not None
    )

    if not is_participant:
        logger.error(
            f"User {current_user.username} is not a participant of chat room {room_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this chat room",
        )

    # 메시지 내용 확인
    if not message_data.content.strip():
        logger.error(
            f"User {current_user.username} attempted to send empty message to room {room_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty",
        )

    # 클라이언트 사용자명 확인 (제공된 경우)
    if (
        message_data.sender_username
        and message_data.sender_username != current_user.username
    ):
        # 실제 사용자와 클라이언트가 보낸 사용자명이 다른 경우 (보안 검증)
        logger.error(
            f"Invalid sender username: {message_data.sender_username} (actual: {current_user.username})"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sender username"
        )

    # 새 메시지 생성
    new_message = Message(
        chat_room_id=room_id, sender_id=current_user.id, content=message_data.content
    )

    # 클라이언트 타임스탬프가 제공된 경우 저장
    if message_data.timestamp:
        try:
            # ISO 형식 문자열을 datetime으로 변환
            client_timestamp = datetime.fromisoformat(
                message_data.timestamp.replace("Z", "+00:00")
            )
            new_message.client_timestamp = client_timestamp
            logger.info(f"Using client timestamp: {message_data.timestamp}")
        except ValueError:
            # 잘못된 형식이면 무시
            logger.warning(f"Invalid timestamp format: {message_data.timestamp}")
            pass

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # 채팅방 업데이트 시간 갱신
    chat_room.updated_at = new_message.created_at
    db.commit()

    logger.info(
        f"Message sent to room {room_id} by user {current_user.username} (message_id: {new_message.id})"
    )
    return MessageInfo(
        id=new_message.id,
        sender_username=current_user.username,
        content=new_message.content,
        created_at=new_message.created_at,
        is_deleted=new_message.is_deleted,
        client_timestamp=message_data.timestamp,  # 클라이언트 타임스탬프 반환
    )


@router.get("/{room_id}/messages", response_model=MessageList)
async def get_messages(
    room_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """채팅방의 메시지 목록을 조회합니다."""
    logger.info(
        f"Getting messages for room {room_id}. User: {current_user.username}, Page: {page}, Page size: {page_size}"
    )

    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found",
        )

    # 사용자가 채팅방 참여자인지 확인
    is_participant = (
        db.query(ChatRoomParticipant)
        .filter(
            and_(
                ChatRoomParticipant.chat_room_id == room_id,
                ChatRoomParticipant.user_id == current_user.id,
            )
        )
        .first()
        is not None
    )

    if not is_participant:
        logger.error(
            f"User {current_user.username} is not a participant of chat room {room_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this chat room",
        )

    # 메시지 총 개수 조회
    total_count = db.query(Message).filter(Message.chat_room_id == room_id).count()

    # 메시지 목록 조회 (최신 메시지부터)
    messages = (
        db.query(Message)
        .filter(Message.chat_room_id == room_id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # 메시지 정보 구성
    message_infos = []
    for message in messages:
        sender = db.query(User).filter(User.id == message.sender_id).first()

        # 클라이언트 타임스탬프 처리
        client_ts = None
        if message.client_timestamp:
            client_ts = message.client_timestamp.isoformat()

        message_infos.append(
            MessageInfo(
                id=message.id,
                sender_username=sender.username if sender else "[사용자 없음]",
                content=(
                    message.content if not message.is_deleted else "[삭제된 메시지]"
                ),
                created_at=message.created_at,
                is_deleted=message.is_deleted,
                client_timestamp=client_ts,
            )
        )

    # 시간순으로 정렬 (오래된 메시지부터)
    message_infos.reverse()

    logger.info(
        f"Retrieved {len(message_infos)} messages for room {room_id} (total: {total_count})"
    )
    return MessageList(
        messages=message_infos, total_count=total_count, page=page, page_size=page_size
    )


@router.delete("/{room_id}/messages/{message_id}")
async def delete_message(
    room_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """메시지를 삭제합니다."""
    logger.info(
        f"Deleting message {message_id} in room {room_id}. User: {current_user.username}"
    )

    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found",
        )

    # 메시지 존재 확인
    message = (
        db.query(Message)
        .filter(and_(Message.id == message_id, Message.chat_room_id == room_id))
        .first()
    )

    if not message:
        logger.error(f"Message with id {message_id} not found in chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message with id {message_id} not found in chat room {room_id}",
        )

    # 이미 삭제된 메시지인지 확인
    if message.is_deleted:
        logger.info(f"Message {message_id} is already deleted")
        return {"message": "Message is already deleted"}

    # 자신의 메시지인지 또는 관리자인지 확인
    is_own_message = message.sender_id == current_user.id
    is_admin = (
        db.query(ChatRoomParticipant)
        .filter(
            and_(
                ChatRoomParticipant.chat_room_id == room_id,
                ChatRoomParticipant.user_id == current_user.id,
                ChatRoomParticipant.is_admin == True,
            )
        )
        .first()
        is not None
    )

    if not (is_own_message or is_admin):
        logger.error(
            f"User {current_user.username} tried to delete message {message_id} without permission"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages or need admin rights",
        )

    # 메시지 삭제 처리 (실제로는 is_deleted 플래그만 설정)
    message.is_deleted = True
    db.commit()

    logger.info(
        f"Message {message_id} successfully deleted by user {current_user.username}"
    )
    return {"message": "Message successfully deleted"}
