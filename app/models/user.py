from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 친구 관계
    friendships = relationship("Friendship", foreign_keys="Friendship.user_id")
    friends = relationship(
        "User",
        secondary="friendships",
        primaryjoin="User.id == Friendship.user_id",
        secondaryjoin="User.id == Friendship.friend_id",
        viewonly=True
    ) 