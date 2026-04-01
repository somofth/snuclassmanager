"""수업비서 - 메인 진입점"""

import logging
import os
import threading

import uvicorn

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

WEB_PORT = int(os.environ.get("PORT", 9090))


def run_web_server():
    """웹 대시보드를 별도 스레드에서 실행"""
    from web import web_app

    uvicorn.run(web_app, host="0.0.0.0", port=WEB_PORT, log_level="warning")


def main():
    # 1. DB 초기화 & 시간표 등록
    from schedule_data import init_subjects

    init_subjects()
    logger.info("시간표 초기화 완료")

    # 2. 웹 대시보드 시작 (별도 스레드)
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info(f"웹 대시보드: http://localhost:{WEB_PORT}")

    # 3. 텔레그램 봇 생성
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
        logger.info("웹 대시보드만 실행합니다. Ctrl+C로 종료하세요.")
        web_thread.join()
        return

    from bot import create_bot_app

    app = create_bot_app()
    logger.info("텔레그램 봇 준비 완료")

    # 4. 스케줄러 설정
    chat_id = TELEGRAM_CHAT_ID
    if chat_id:
        from scheduler import setup_scheduler

        scheduler = setup_scheduler(app.bot, chat_id)
        scheduler.start()
        logger.info(f"스케줄러 시작 (chat_id: {chat_id})")
    else:
        logger.warning(
            "TELEGRAM_CHAT_ID가 설정되지 않았습니다. "
            "봇에 /start 명령을 보내면 자동으로 등록됩니다. "
            "등록 후 프로그램을 재시작하면 알림이 활성화됩니다."
        )

    # 5. 봇 실행 (polling)
    logger.info("수업비서 봇을 시작합니다...")
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling()


if __name__ == "__main__":
    main()
