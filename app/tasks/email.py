import asyncio
import random
from app.celery_worker import celery_app

import time


@celery_app.task(bind=True, max_retries=5)
def send_email(self, user_id: int):
    """
    이메일 전송을 시뮬레이션하는 태스크
    10% 확률로 실패하며, 실패 시 최대 5회까지 재시도
    """
    try:
        # 10% 확률로 실패
        if random.random() < 0.1:
            raise Exception("이메일 전송 실패")

        # 이메일 전송 시뮬레이션 (3초 대기)
        time.sleep(3)

        print(f"이메일 전송 성공: {user_id}@test.com")
        return {"status": "success", "email": f"{user_id}@test.com"}

    except Exception as exc:
        print(
            f"이메일 전송 실패 (시도 {self.request.retries + 1}/5): {user_id}@test.com"
        )
        # 재시도
        self.retry(exc=exc, countdown=2**self.request.retries)  # 지수 백오프
