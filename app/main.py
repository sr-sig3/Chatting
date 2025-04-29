from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, friends
from app.routes import chat as chat_routes
from app.database import engine
from app.models import user, friendship
from app.models import chat as chat_models

# 데이터베이스 테이블 생성
user.Base.metadata.create_all(bind=engine)
friendship.Base.metadata.create_all(bind=engine)
chat_models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="채팅 애플리케이션 API",
    description="FastAPI를 사용한 채팅 애플리케이션 백엔드",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영 환경에서는 특정 도메인만 허용하도록 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(friends.router, prefix="/friends", tags=["friends"])
app.include_router(chat_routes.router, prefix="/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "채팅 애플리케이션 API에 오신 것을 환영합니다!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 