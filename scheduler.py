"""수업 알림 스케줄러"""

import logging
from datetime import datetime, time, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import ALERT_MINUTES_BEFORE
from database import Subject, get_session
from schedule_data import DAY_NAMES

logger = logging.getLogger(__name__)

# 요일 매핑 (APScheduler는 mon~fri 사용)
CRON_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _alert_time(start_time: time) -> time:
    """수업 시작 시간에서 ALERT_MINUTES_BEFORE 만큼 빼기"""
    dt = datetime(2000, 1, 1, start_time.hour, start_time.minute)
    dt -= timedelta(minutes=ALERT_MINUTES_BEFORE)
    return dt.time()


def _end_message_time(end_time: time) -> time:
    """수업 종료 시간에 2분 후"""
    dt = datetime(2000, 1, 1, end_time.hour, end_time.minute)
    dt += timedelta(minutes=2)
    return dt.time()


async def send_class_alert(bot, chat_id: str, subject_name: str, room: str, start_time: str):
    """수업 시작 전 알림"""
    room_info = f" ({room})" if room else ""
    text = (
        f"📚 **{subject_name}** 수업이 {ALERT_MINUTES_BEFORE}분 후 시작됩니다!\n"
        f"🎙️ 녹음을 켜주세요!{room_info}\n"
        f"⏰ {start_time}"
    )
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"알림 전송 실패: {e}")


async def send_class_end(bot, chat_id: str, subject_name: str):
    """수업 종료 후 녹음 제출 유도"""
    text = (
        f"🔔 **{subject_name}** 수업이 끝났습니다!\n"
        f"녹음 파일이나 수업자료를 보내주세요."
    )
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"종료 알림 전송 실패: {e}")


def setup_scheduler(bot, chat_id: str) -> AsyncIOScheduler:
    """APScheduler에 수업 알림 등록"""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    session = get_session()
    try:
        subjects = session.query(Subject).all()
        for s in subjects:
            # 수업 시작 전 알림
            alert = _alert_time(s.start_time)
            scheduler.add_job(
                send_class_alert,
                CronTrigger(
                    day_of_week=CRON_DAYS[s.day_of_week],
                    hour=alert.hour,
                    minute=alert.minute,
                    timezone="Asia/Seoul",
                ),
                args=[bot, chat_id, s.name, s.room, s.start_time.strftime("%H:%M")],
                id=f"alert_{s.id}",
                replace_existing=True,
            )

            # 수업 종료 후 녹음 제출 유도
            end = _end_message_time(s.end_time)
            scheduler.add_job(
                send_class_end,
                CronTrigger(
                    day_of_week=CRON_DAYS[s.day_of_week],
                    hour=end.hour,
                    minute=end.minute,
                    timezone="Asia/Seoul",
                ),
                args=[bot, chat_id, s.name],
                id=f"end_{s.id}",
                replace_existing=True,
            )
            logger.info(
                f"스케줄 등록: {s.name} ({DAY_NAMES[s.day_of_week]}) "
                f"알림 {alert.strftime('%H:%M')}, 종료 {end.strftime('%H:%M')}"
            )
    finally:
        session.close()

    return scheduler
