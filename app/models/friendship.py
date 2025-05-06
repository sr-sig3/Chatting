from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계 정의
    user = relationship("User", foreign_keys=[user_id], back_populates="friendships")
    friend = relationship("User", foreign_keys=[friend_id])

    # 사용자-친구 쌍이 유일하도록 제약 조건 추가
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="unique_friendship"),
    )
