"""
데이터베이스 마이그레이션 스크립트
이 스크립트는 기존 데이터베이스 테이블을 삭제하고 새로 생성합니다.
주의: 이 스크립트는 모든 데이터를 삭제합니다. 실행 전에 반드시 백업하세요.
"""

from app.database import engine, Base
from app.models import user, friendship, chat as chat_models
import sys


def confirm_migration():
    print("주의: 이 작업은 모든 데이터베이스 테이블을 삭제하고 다시 생성합니다.")
    print("진행하기 전에 반드시 데이터를 백업하세요.")

    confirmation = input("계속하시겠습니까? (y/n): ")
    return confirmation.lower() == "y"


def drop_tables():
    """모든 테이블을 삭제합니다."""
    print("테이블 삭제 중...")
    chat_models.Message.__table__.drop(engine, checkfirst=True)
    chat_models.ChatRoomParticipant.__table__.drop(engine, checkfirst=True)
    chat_models.ChatRoom.__table__.drop(engine, checkfirst=True)
    friendship.Friendship.__table__.drop(engine, checkfirst=True)
    user.User.__table__.drop(engine, checkfirst=True)
    print("모든 테이블이 삭제되었습니다.")


def create_tables():
    """모든 테이블을 새로 생성합니다."""
    print("테이블 생성 중...")
    # 테이블 생성
    user.Base.metadata.create_all(bind=engine)
    friendship.Base.metadata.create_all(bind=engine)
    chat_models.Base.metadata.create_all(bind=engine)
    print("모든 테이블이 생성되었습니다.")


if __name__ == "__main__":
    if not confirm_migration():
        print("마이그레이션이 취소되었습니다.")
        sys.exit(0)

    try:
        drop_tables()
        create_tables()
        print("마이그레이션이 성공적으로 완료되었습니다.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        sys.exit(1)
