from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
import logging

from app.database import get_db
from app.models.user import User
from app.models.chat import ChatRoom, ChatRoomParticipant
from app.schemas.chat import ParticipantInfo, ParticipantAdd
from app.utils.auth import get_current_user

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

@router.post("/{room_id}/participants", status_code=status.HTTP_201_CREATED)
async def add_participants(
    room_id: int,
    participant_data: ParticipantAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방에 새로운 참여자를 추가합니다."""
    logger.info(f"Adding participants to room {room_id}. User: {current_user.username}, Participants: {participant_data.usernames}")
    
    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found"
        )
    
    # 사용자가 채팅방 관리자인지 확인
    participant = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == current_user.id,
            ChatRoomParticipant.is_admin == True
        )
    ).first()
    
    if not participant:
        logger.error(f"User {current_user.username} is not an admin of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an admin of this chat room"
        )
    
    # 추가할 사용자 확인
    added_users = []
    for username in participant_data.usernames:
        # 사용자 존재 확인
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.error(f"User with username '{username}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with username '{username}' not found"
            )
        
        # 이미 참여자인지 확인
        existing_participant = db.query(ChatRoomParticipant).filter(
            and_(
                ChatRoomParticipant.chat_room_id == room_id,
                ChatRoomParticipant.user_id == user.id
            )
        ).first()
        
        if existing_participant:
            logger.info(f"User {username} is already a participant in room {room_id}")
            continue  # 이미 참여자인 경우 건너뜀
        
        # 새 참여자 추가
        new_participant = ChatRoomParticipant(
            chat_room_id=room_id,
            user_id=user.id,
            is_admin=False
        )
        db.add(new_participant)
        added_users.append(username)
    
    db.commit()
    
    if not added_users:
        logger.info(f"No new participants added to room {room_id}")
        return {"message": "No new participants added"}
    
    logger.info(f"Added {', '.join(added_users)} to chat room {room_id}")
    return {"message": f"Added {', '.join(added_users)} to the chat room"}

@router.get("/{room_id}/participants", response_model=List[ParticipantInfo])
async def get_participants(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방 참여자 목록을 조회합니다."""
    logger.info(f"Getting participants for room {room_id}. User: {current_user.username}")
    
    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found"
        )
    
    # 사용자가 채팅방 참여자인지 확인
    is_participant = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == current_user.id
        )
    ).first() is not None
    
    if not is_participant:
        logger.error(f"User {current_user.username} is not a participant of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this chat room"
        )
    
    # 참여자 목록 조회
    participants = db.query(
        ChatRoomParticipant, User
    ).join(
        User, ChatRoomParticipant.user_id == User.id
    ).filter(
        ChatRoomParticipant.chat_room_id == room_id
    ).all()
    
    participant_infos = []
    for participant, user in participants:
        participant_infos.append(ParticipantInfo(
            username=user.username,
            is_admin=participant.is_admin,
            joined_at=participant.joined_at
        ))
    
    logger.info(f"Retrieved {len(participant_infos)} participants for room {room_id}")
    return participant_infos

@router.delete("/{room_id}/participants/{username}")
async def remove_participant(
    room_id: int,
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방에서 참여자를 제거합니다."""
    logger.info(f"Removing participant {username} from room {room_id}. User: {current_user.username}")
    
    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found"
        )
    
    # 사용자가 채팅방 관리자인지 확인
    admin_check = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == current_user.id,
            ChatRoomParticipant.is_admin == True
        )
    ).first()
    
    if not admin_check:
        logger.error(f"User {current_user.username} is not an admin of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an admin of this chat room"
        )
    
    # 제거할 사용자 확인
    user_to_remove = db.query(User).filter(User.username == username).first()
    if not user_to_remove:
        logger.error(f"User with username '{username}' not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{username}' not found"
        )
    
    # 자기 자신을 제거하려는 경우
    if user_to_remove.id == current_user.id:
        logger.error(f"User {current_user.username} attempting to remove themselves")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself. Use the leave endpoint instead"
        )
    
    # 참여자 확인
    participant_to_remove = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == user_to_remove.id
        )
    ).first()
    
    if not participant_to_remove:
        logger.error(f"User '{username}' is not a participant of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' is not a participant of this chat room"
        )
    
    # 채팅방 생성자는 제거할 수 없음
    if chat_room.created_by == user_to_remove.id:
        logger.error(f"Cannot remove the creator of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the creator of the chat room"
        )
    
    # 참여자 제거
    db.delete(participant_to_remove)
    db.commit()
    
    logger.info(f"Successfully removed {username} from chat room {room_id}")
    return {"message": f"Successfully removed {username} from the chat room"}

@router.post("/{room_id}/admins/{username}")
async def set_admin(
    room_id: int,
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방의 참여자를 관리자로 설정합니다."""
    logger.info(f"Setting {username} as admin in room {room_id}. User: {current_user.username}")
    
    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found"
        )
    
    # 사용자가 채팅방 관리자인지 확인
    admin_check = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == current_user.id,
            ChatRoomParticipant.is_admin == True
        )
    ).first()
    
    if not admin_check:
        logger.error(f"User {current_user.username} is not an admin of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an admin of this chat room"
        )
    
    # 대상 사용자 확인
    target_user = db.query(User).filter(User.username == username).first()
    if not target_user:
        logger.error(f"User with username '{username}' not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{username}' not found"
        )
    
    # 참여자 확인
    participant = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == target_user.id
        )
    ).first()
    
    if not participant:
        logger.error(f"User '{username}' is not a participant of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' is not a participant of this chat room"
        )
    
    # 이미 관리자인 경우
    if participant.is_admin:
        logger.info(f"{username} is already an admin of chat room {room_id}")
        return {"message": f"{username} is already an admin of this chat room"}
    
    # 관리자로 설정
    participant.is_admin = True
    db.commit()
    
    logger.info(f"Successfully set {username} as an admin of chat room {room_id}")
    return {"message": f"Successfully set {username} as an admin of this chat room"}

@router.delete("/{room_id}/admins/{username}")
async def remove_admin(
    room_id: int,
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방의 관리자 권한을 제거합니다."""
    logger.info(f"Removing admin status from {username} in room {room_id}. User: {current_user.username}")
    
    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found"
        )
    
    # 사용자가 채팅방 관리자인지 확인
    admin_check = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == current_user.id,
            ChatRoomParticipant.is_admin == True
        )
    ).first()
    
    if not admin_check:
        logger.error(f"User {current_user.username} is not an admin of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an admin of this chat room"
        )
    
    # 대상 사용자 확인
    target_user = db.query(User).filter(User.username == username).first()
    if not target_user:
        logger.error(f"User with username '{username}' not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{username}' not found"
        )
    
    # 채팅방 생성자는 관리자 권한 제거 불가
    if chat_room.created_by == target_user.id:
        logger.error(f"Cannot remove admin rights from the creator of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin rights from the creator of the chat room"
        )
    
    # 참여자 확인
    participant = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == target_user.id
        )
    ).first()
    
    if not participant:
        logger.error(f"User '{username}' is not a participant of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' is not a participant of this chat room"
        )
    
    # 관리자 권한이 없는 경우
    if not participant.is_admin:
        logger.info(f"{username} is not an admin of chat room {room_id}")
        return {"message": f"{username} is not an admin of this chat room"}
    
    # 관리자 권한 제거
    participant.is_admin = False
    db.commit()
    
    logger.info(f"Successfully removed admin rights from {username} in chat room {room_id}")
    return {"message": f"Successfully removed admin rights from {username}"} 