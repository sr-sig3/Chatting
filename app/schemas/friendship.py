from pydantic import BaseModel
from typing import List
from datetime import datetime

class FriendBase(BaseModel):
    username: str

class Friend(FriendBase):
    created_at: datetime

    class Config:
        from_attributes = True

class FriendList(BaseModel):
    friends: List[Friend]

class FriendAdd(BaseModel):
    username: str 