import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # 봇 시작 후 자동 저장

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "class_assistant.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")

# 수업 시작 몇 분 전에 알림을 보낼지
ALERT_MINUTES_BEFORE = 5
