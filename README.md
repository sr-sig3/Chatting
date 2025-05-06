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

## 프로젝트 실행 방법

### 1. PostgreSQL 설치 및 실행

- **로컬**:  
  ```bash
  brew install postgresql
  brew services start postgresql
  ```
  또는  
  ```bash
  sudo apt-get install postgresql
  sudo service postgresql start
  ```
- **도커**: codker-compose.yml 활용하면 자동 설치됨

### 2. PostgreSQL 데이터베이스 및 사용자 생성

```bash
psql postgres
```

```sql
CREATE DATABASE dbname;
CREATE USER username WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE dbname TO username;
```

### 3. 환경 변수 설정 (.env 파일)

이 프로젝트는 환경 변수 파일(.env)을 필요로 합니다.  
`.env` 파일은 보안상 깃허브에 포함되어 있지 않으니, 아래와 같이 직접 생성해 주세요.

```env
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
SECRET_KEY=your-secret-key-here
```

- `username`, `password`, `dbname`은 실제로 생성한 PostgreSQL 정보로 변경하세요.
- `SECRET_KEY`는 임의의 안전한 문자열로 설정하세요.

### 4. 테이블 생성

아래 명령어로 마이그레이션 스크립트를 실행하여 테이블을 생성합니다.

```bash
python migrate_db.py
```

### 5. 서버 실행 및 테스트

FastAPI 서버를 실행합니다.

```bash
uvicorn app.main:app --reload
```

- 회원가입, 로그인 등 기능이 정상 동작하는지 확인하세요.

---

이렇게 하면 누구나 프로젝트를 클론한 뒤,  
PostgreSQL 설치부터 서버 실행까지 순서대로 진행할 수 있습니다! 