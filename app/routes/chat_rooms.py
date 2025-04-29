from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Optional
import logging

from app.database import get_db
from app.models.user import User
from app.models.chat import ChatRoom, ChatRoomParticipant, Message
from app.schemas.chat import (
    ChatRoomCreate, ChatRoomInfo, ChatRoomDetail, ChatRoomList,
    ParticipantInfo, ParticipantAdd
)
from app.utils.auth import get_current_user

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

@router.post("/", response_model=ChatRoomDetail, status_code=status.HTTP_201_CREATED)
async def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 채팅방을 생성합니다."""
    logger.info(f"Creating chat room '{room_data.name}' by user {current_user.username}")
    logger.info(f"Participants: {room_data.participants}")
    
    # 초대할 사용자 목록 검증
    if not room_data.participants:
        logger.error("No participants provided when creating chat room")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one participant is required"
        )
    
    # 자기 자신이 참여자 목록에 있는지 확인
    if current_user.username in room_data.participants:
        logger.info(f"User {current_user.username} included in participants list - will be automatically added as admin")
        # 자기 자신은 이미 자동으로 추가되므로 목록에서 제거
        room_data.participants.remove(current_user.username)
    
    # 초대할 사용자 찾기
    valid_participants = []
    for username in room_data.participants:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.error(f"User with username '{username}' not found when creating chat room")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with username '{username}' not found"
            )
        valid_participants.append(user)
    
    # 채팅방 생성
    new_room = ChatRoom(
        name=room_data.name,
        created_by=current_user.id
    )
    db.add(new_room)
    db.flush()
    logger.info(f"Created chat room with ID {new_room.id}")
    
    # 생성자를 관리자로 추가
    creator_participant = ChatRoomParticipant(
        chat_room_id=new_room.id,
        user_id=current_user.id,
        is_admin=True
    )
    db.add(creator_participant)
    
    # 초대한 사용자 추가
    for user in valid_participants:
        participant = ChatRoomParticipant(
            chat_room_id=new_room.id,
            user_id=user.id,
            is_admin=False
        )
        db.add(participant)
        logger.info(f"Added user {user.username} to chat room {new_room.id}")
    
    db.commit()
    db.refresh(new_room)
    
    # 응답 데이터 준비
    participants_info = []
    
    # 생성자 정보 추가
    creator_participant = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == new_room.id,
            ChatRoomParticipant.user_id == current_user.id
        )
    ).first()
    
    participants_info.append(ParticipantInfo(
        username=current_user.username,
        is_admin=creator_participant.is_admin,
        joined_at=creator_participant.joined_at
    ))
    
    # 다른 참여자 정보 추가
    for user in valid_participants:
        participant = db.query(ChatRoomParticipant).filter(
            and_(
                ChatRoomParticipant.chat_room_id == new_room.id,
                ChatRoomParticipant.user_id == user.id
            )
        ).first()
        
        participants_info.append(ParticipantInfo(
            username=user.username,
            is_admin=participant.is_admin,
            joined_at=participant.joined_at
        ))
    
    logger.info(f"Successfully created chat room {new_room.id} with {len(participants_info)} participants")
    return ChatRoomDetail(
        id=new_room.id,
        name=new_room.name,
        created_by=current_user.username,
        participants_count=len(participants_info),
        created_at=new_room.created_at,
        updated_at=new_room.updated_at,
        last_message=None,
        last_message_time=None,
        participants=participants_info
    )

@router.get("/", response_model=ChatRoomList)
async def get_chat_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자가 참여한 채팅방 목록을 조회합니다."""
    logger.info(f"Getting chat rooms for user {current_user.username}")
    
    # 사용자가 참여한 채팅방 ID 목록 조회
    room_ids = db.query(ChatRoomParticipant.chat_room_id).filter(
        ChatRoomParticipant.user_id == current_user.id
    ).all()
    room_ids = [room_id[0] for room_id in room_ids]
    
    if not room_ids:
        logger.info(f"User {current_user.username} has no chat rooms")
        return ChatRoomList(chat_rooms=[])
    
    # 채팅방 정보 조회
    rooms_info = []
    for room_id in room_ids:
        chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        creator = db.query(User).filter(User.id == chat_room.created_by).first()
        
        # 참여자 수 조회
        participants_count = db.query(ChatRoomParticipant).filter(
            ChatRoomParticipant.chat_room_id == room_id
        ).count()
        
        # 마지막 메시지 조회
        last_message = db.query(Message).filter(
            and_(
                Message.chat_room_id == room_id,
                Message.is_deleted == False
            )
        ).order_by(Message.created_at.desc()).first()
        
        rooms_info.append(ChatRoomInfo(
            id=chat_room.id,
            name=chat_room.name,
            created_by=creator.username,
            participants_count=participants_count,
            created_at=chat_room.created_at,
            updated_at=chat_room.updated_at,
            last_message=last_message.content if last_message else None,
            last_message_time=last_message.created_at if last_message else None
        ))
    
    # 최근 메시지 있는 채팅방을 먼저 보여주도록 정렬
    rooms_info.sort(key=lambda x: x.last_message_time or x.created_at, reverse=True)
    
    logger.info(f"Retrieved {len(rooms_info)} chat rooms for user {current_user.username}")
    return ChatRoomList(chat_rooms=rooms_info)

@router.get("/{room_id}", response_model=ChatRoomDetail)
async def get_chat_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 채팅방의 상세 정보를 조회합니다."""
    logger.info(f"Getting details for chat room {room_id}. User: {current_user.username}")
    
    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found"
        )
    
    # 사용자가 채팅방 참여자인지 확인
    participant = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == current_user.id
        )
    ).first()
    
    if not participant:
        logger.error(f"User {current_user.username} is not a participant of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this chat room"
        )
    
    # 채팅방 생성자 정보
    creator = db.query(User).filter(User.id == chat_room.created_by).first()
    
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
    
    # 마지막 메시지 조회
    last_message = db.query(Message).filter(
        and_(
            Message.chat_room_id == room_id,
            Message.is_deleted == False
        )
    ).order_by(Message.created_at.desc()).first()
    
    return ChatRoomDetail(
        id=chat_room.id,
        name=chat_room.name,
        created_by=creator.username,
        participants_count=len(participant_infos),
        created_at=chat_room.created_at,
        updated_at=chat_room.updated_at,
        last_message=last_message.content if last_message else None,
        last_message_time=last_message.created_at if last_message else None,
        participants=participant_infos
    )

@router.put("/{room_id}", response_model=ChatRoomInfo)
async def update_chat_room(
    room_id: int,
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방 이름을 수정합니다."""
    logger.info(f"Updating chat room {room_id} name to '{name}'. User: {current_user.username}")
    
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
    
    # 채팅방 이름 수정
    old_name = chat_room.name
    chat_room.name = name
    db.commit()
    db.refresh(chat_room)
    logger.info(f"Chat room {room_id} name changed from '{old_name}' to '{name}'")
    
    # 생성자 정보
    creator = db.query(User).filter(User.id == chat_room.created_by).first()
    
    # 참여자 수 조회
    participants_count = db.query(ChatRoomParticipant).filter(
        ChatRoomParticipant.chat_room_id == room_id
    ).count()
    
    # 마지막 메시지 조회
    last_message = db.query(Message).filter(
        and_(
            Message.chat_room_id == room_id,
            Message.is_deleted == False
        )
    ).order_by(Message.created_at.desc()).first()
    
    return ChatRoomInfo(
        id=chat_room.id,
        name=chat_room.name,
        created_by=creator.username,
        participants_count=participants_count,
        created_at=chat_room.created_at,
        updated_at=chat_room.updated_at,
        last_message=last_message.content if last_message else None,
        last_message_time=last_message.created_at if last_message else None
    )

@router.delete("/{room_id}/leave")
async def leave_chat_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """채팅방을 나갑니다."""
    logger.info(f"User {current_user.username} attempting to leave chat room {room_id}")
    
    # 채팅방 존재 확인
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    if not chat_room:
        logger.error(f"Chat room with id {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat room with id {room_id} not found"
        )
    
    # 사용자가 채팅방 참여자인지 확인
    participant = db.query(ChatRoomParticipant).filter(
        and_(
            ChatRoomParticipant.chat_room_id == room_id,
            ChatRoomParticipant.user_id == current_user.id
        )
    ).first()
    
    if not participant:
        logger.error(f"User {current_user.username} is not a participant of chat room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this chat room"
        )
    
    # 채팅방 참여자 삭제
    db.delete(participant)
    logger.info(f"Deleted participant {current_user.username} from chat room {room_id}")
    
    # 마지막 참여자인 경우 채팅방도 삭제
    remaining_participants = db.query(ChatRoomParticipant).filter(
        ChatRoomParticipant.chat_room_id == room_id
    ).count()
    
    if remaining_participants == 0:
        # 채팅방의 메시지 삭제
        messages_count = db.query(Message).filter(Message.chat_room_id == room_id).count()
        db.query(Message).filter(Message.chat_room_id == room_id).delete()
        # 채팅방 삭제
        db.delete(chat_room)
        logger.info(f"Chat room {room_id} deleted as the last participant left. Deleted {messages_count} messages.")
    else:
        logger.info(f"Chat room {room_id} still has {remaining_participants} participants after {current_user.username} left")
    
    db.commit()
    
    return {"message": "Successfully left the chat room"} 