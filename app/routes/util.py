from fastapi import APIRouter, HTTPException
import time
from concurrent.futures import ProcessPoolExecutor
import asyncio
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# 태그 명시적 지정 및 prefix 제거
router = APIRouter()
executor = ProcessPoolExecutor(max_workers=4)


def fibonacci_recursive(n: int) -> int:
    """
    재귀적으로 피보나치 수를 계산합니다.
    의도적으로 비효율적인 구현입니다 (캐싱 없음).
    """
    if n <= 0:
        return 0
    if n == 1:
        return 1

    # 재귀적으로 계산 (매우 비효율적)
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


# 경로 명확히 지정
@router.get(
    "/fibonacci/{n}",
    summary="피보나치 수 계산",
    description="n번째 피보나치 수를 계산합니다",
)
async def get_fibonacci(n: int):
    """
    n번째 피보나치 수를 계산합니다.
    주의: n > 30인 경우 계산 시간이 매우 오래 걸릴 수 있습니다.
    """
    if n < 0:
        raise HTTPException(status_code=400, detail="n은 음수가 될 수 없습니다")

    if n > 50:
        raise HTTPException(status_code=400, detail="n이 너무 큽니다 (최대 35)")

    logger.info(f"피보나치 API 호출: n={n}")
    start_time = time.time()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, fibonacci_recursive, n)
    # result = fibonacci_recursive(n)

    execution_time = time.time() - start_time
    logger.info(
        f"피보나치 API 응답: n={n}, 결과={result}, 실행시간={execution_time:.4f}초"
    )

    return {"n": n, "fibonacci": result, "execution_time_seconds": execution_time}
