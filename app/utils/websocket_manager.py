from fastapi import WebSocket
from typing import Dict, List, Set
import json
import logging

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ConnectionManager:
    def __init__(self):
        # {room_id: {user_id: websocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        # {room_id: {username}}
        self.active_users: Dict[int, Set[str]] = {}
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, room_id: int, user_id: int, username: str):
        await websocket.accept()
        logger.info(f"Accepting WebSocket connection for user {username} (ID: {user_id}) in room {room_id}")
        
        # 채팅방이 아직 매니저에 등록되지 않은 경우
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
            self.active_users[room_id] = set()
            logger.info(f"Created new room entry for room {room_id}")
        
        # 사용자 연결 정보 저장
        self.active_connections[room_id][user_id] = websocket
        self.active_users[room_id].add(username)
        logger.info(f"User {username} connected to room {room_id}. Active users: {len(self.active_users[room_id])}")
        
        # 새로운 사용자가 접속했다는 메시지를 모든 사용자에게 전송
        await self.broadcast(
            room_id=room_id,
            message={"type": "system", "content": f"{username} 님이 입장했습니다."}
        )
        
        # 현재 접속 중인 사용자 목록 전송
        await self.send_active_users(room_id)
    
    def disconnect(self, room_id: int, user_id: int, username: str):
        # 연결 종료 시 사용자 정보 제거
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            del self.active_connections[room_id][user_id]
            self.active_users[room_id].discard(username)
            logger.info(f"User {username} disconnected from room {room_id}")
            
            # 채팅방에 아무도 없으면 채팅방 정보도 제거
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                del self.active_users[room_id]
                logger.info(f"Room {room_id} removed from connection manager (no active users)")
                return
            
            logger.info(f"Room {room_id} has {len(self.active_users[room_id])} active users after disconnect")
            # 나간 사용자 정보 전송 (비동기 함수지만 disconnect에서는 직접 호출할 수 없으므로 별도 처리 필요)
            return {"type": "system", "content": f"{username} 님이 나갔습니다."}
        else:
            logger.warning(f"Attempted to disconnect user {username} from room {room_id}, but user or room not found")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))
        logger.info(f"Sent personal message: {message}")
    
    async def broadcast(self, room_id: int, message: dict, exclude_user_id: int = None):
        # 특정 채팅방의 모든 사용자에게 메시지 전송 (특정 사용자 제외 가능)
        if room_id in self.active_connections:
            recipients_count = 0
            logger.info(f"Broadcasting message to room {room_id}: {message}")
            for user_id, connection in self.active_connections[room_id].items():
                if exclude_user_id is None or user_id != exclude_user_id:
                    await connection.send_text(json.dumps(message))
                    recipients_count += 1
            logger.info(f"Broadcasted message to {recipients_count} users in room {room_id}")
        else:
            logger.warning(f"Attempted to broadcast to room {room_id}, but room not found")
    
    async def send_active_users(self, room_id: int):
        # 현재 채팅방에 접속 중인 사용자 목록 전송
        if room_id in self.active_users:
            message = {
                "type": "users_list",
                "users": list(self.active_users[room_id])
            }
            await self.broadcast(room_id, message)
            logger.info(f"Sent active users list for room {room_id}: {len(self.active_users[room_id])} users")
        else:
            logger.warning(f"Attempted to send user list for room {room_id}, but room not found")

# 전역 연결 관리자 인스턴스
manager = ConnectionManager() 