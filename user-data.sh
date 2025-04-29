#!/bin/bash

# 시스템 업데이트
apt-get update
apt-get upgrade -y

# Docker 설치
apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Docker 서비스 시작 및 자동 시작 설정
systemctl start docker
systemctl enable docker

# Docker Compose 설치
curl -L "https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 애플리케이션 디렉토리 생성
mkdir -p /app
cd /app

# 환경 변수 파일 생성
cat > .env << EOL
DATABASE_URL=postgresql://username:password@your-rds-endpoint:5432/dbname
SECRET_KEY=your-secret-key-here
EOL

# Docker 이미지 빌드 및 실행
docker build -t chatting-backend .
docker run -d --name chatting-backend -p 8002:8002 --env-file .env chatting-backend 