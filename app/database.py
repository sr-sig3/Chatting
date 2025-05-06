from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Docker 환경에서의 기본 데이터베이스 URL
DEFAULT_DATABASE_URL = "postgresql://kihoon_chat:kihoon@db:5432/chatting"

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
