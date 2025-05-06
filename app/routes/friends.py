from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.user import User
from app.models.friendship import Friendship
from app.schemas.friendship import FriendList, Friend, FriendAdd
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=FriendList)
async def get_friends(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """현재 사용자의 친구 목록을 조회합니다."""
    # 현재 사용자의 친구 관계를 조회
    friendships = (
        db.query(Friendship).filter(Friendship.user_id == current_user.id).all()
    )

    # 친구 목록 생성
    friend_list = []
    for friendship in friendships:
        friend = db.query(User).filter(User.id == friendship.friend_id).first()
        if friend:
            friend_list.append(
                Friend(username=friend.username, created_at=friendship.created_at)
            )

    return FriendList(friends=friend_list)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_friend(
    friend_data: FriendAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """새로운 친구를 추가합니다."""
    # 자기 자신을 친구로 추가하는 것 방지
    if friend_data.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add yourself as a friend",
        )

    # 친구로 추가할 사용자가 존재하는지 확인
    friend = db.query(User).filter(User.username == friend_data.username).first()
    if not friend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{friend_data.username}' not found",
        )

    # 이미 친구인지 확인
    existing_friendship = (
        db.query(Friendship)
        .filter(
            Friendship.user_id == current_user.id, Friendship.friend_id == friend.id
        )
        .first()
    )

    if existing_friendship:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Already friends with {friend_data.username}",
        )

    # 친구 관계 생성
    try:
        friendship = Friendship(user_id=current_user.id, friend_id=friend.id)
        db.add(friendship)
        db.commit()
        db.refresh(friendship)

        return {"message": f"Successfully added {friend.username} as a friend"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error adding friend"
        )
