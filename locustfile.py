from locust import HttpUser, task, between
import random
import json

class AuthUser(HttpUser):
    # 각 사용자 요청 사이의 대기 시간 (3초)
    wait_time = between(3, 3)
    
    def on_start(self):
        """사용자가 시작될 때 실행되는 메서드"""
        # 랜덤한 이메일과 비밀번호 생성
        self.username = f"test{random.randint(1, 100000000)}"
        self.password = "testpassword123"
        
        # 회원가입
        register_data = {
            "username": self.username,
            "password": self.password
        }
        
        with self.client.post("/auth/register", 
                            json=register_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"회원가입 실패: {response.text}")
        
        # 로그인하여 토큰 얻기
        login_data = {
            "username": self.username,
            "password": self.password
        }
        
        with self.client.post("/auth/token",
                            data=login_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                response.success()
            else:
                response.failure(f"로그인 실패: {response.text}")

    @task
    def test_me(self):
        """me API를 호출하는 태스크"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        with self.client.get("/auth/me",
                           headers=headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"me API 호출 실패: {response.text}")
