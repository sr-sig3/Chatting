from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # 채팅방 이름
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # 생성자
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    participants = relationship("ChatRoomParticipant", back_populates="chat_room")
    messages = relationship("Message", back_populates="chat_room")
    creator = relationship("User", foreign_keys=[created_by])


class ChatRoomParticipant(Base):
    __tablename__ = "chat_room_participants"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_admin = Column(Boolean, default=False)  # 관리자 여부
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    chat_room = relationship("ChatRoom", back_populates="participants")
    user = relationship("User")

    __table_args__ = (
        Index("idx_chat_room_participant", chat_room_id, user_id, unique=True),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)  # 메시지 삭제 여부
    client_timestamp = Column(
        DateTime(timezone=True), nullable=True
    )  # 클라이언트 타임스탬프

    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User")
