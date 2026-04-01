"""대용량 파일 다운로드 (Telethon MTProto - 최대 2GB)"""

import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None


async def init_downloader(api_id: int, api_hash: str, bot_token: str):
    global _client
    _client = TelegramClient(StringSession(), api_id, api_hash)
    await _client.start(bot_token=bot_token)
    logger.info("대용량 파일 다운로더 초기화 완료 (Telethon)")


async def download_file(chat_id: int, message_id: int, dest_dir: str) -> str:
    """텔레그램 메시지에서 파일을 다운로드. 저장된 파일 경로 반환."""
    if _client is None:
        raise RuntimeError("다운로더가 초기화되지 않았습니다.")
    message = await _client.get_messages(chat_id, ids=message_id)
    if message is None or message.media is None:
        raise ValueError("메시지에서 파일을 찾을 수 없습니다.")
    saved_path = await _client.download_media(message.media, dest_dir)
    return saved_path


def is_available() -> bool:
    return _client is not None
