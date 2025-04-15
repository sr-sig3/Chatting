# 채팅 애플리케이션 백엔드

FastAPI를 사용한 채팅 애플리케이션 백엔드 서버입니다.

## 설치 방법

1. Python 버전 설정 (pyenv 사용)
```bash
pyenv install 3.11.0
pyenv local 3.11.0
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. 서버 실행
```bash
uvicorn app.main:app --reload
```

## API 문서

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc 