"""수업비서 - 메인 진입점"""

import logging
import os
import threading

import uvicorn

from config import TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

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

    # 4. post_init 콜백 준비 (Telethon + 스케줄러)
    async def on_startup(app):
        # Telethon 대용량 다운로더
        if TELEGRAM_API_ID and TELEGRAM_API_HASH:
            try:
                from downloader import init_downloader
                await init_downloader(TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN)
                logger.info("대용량 파일 다운로더 초기화 완료")
            except Exception:
                logger.exception("Telethon 초기화 실패 — 20MB 초과 파일 처리 불가 (봇은 계속 실행)")
        else:
            logger.warning("TELEGRAM_API_ID/HASH 미설정 — 20MB 초과 파일 처리 불가")

        # 스케줄러
        try:
            chat_id = TELEGRAM_CHAT_ID
            if chat_id:
                from scheduler import setup_scheduler
                scheduler = setup_scheduler(app.bot, chat_id)
                scheduler.start()
                logger.info(f"스케줄러 시작 (chat_id: {chat_id})")
            else:
                logger.warning(
                    "TELEGRAM_CHAT_ID가 설정되지 않았습니다. "
                    "봇에 /start 명령을 보내면 자동으로 등록됩니다."
                )
        except Exception:
            logger.exception("스케줄러 시작 실패 (봇은 계속 실행)")

    from bot import create_bot_app

    app = create_bot_app(post_init=on_startup)
    logger.info("텔레그램 봇 준비 완료")

    # 5. 봇 실행
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
