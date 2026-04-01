"""대용량 파일 다운로드 (Telethon MTProto - 최대 2GB)"""

import logging

from telethon import TelegramClient, events
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None
_message_cache: dict[tuple[int, int], object] = {}  # (chat_id, message_id) -> telethon message


async def init_downloader(api_id: int, api_hash: str, bot_token: str):
    global _client
    _client = TelegramClient(StringSession(), api_id, api_hash)
    await _client.start(bot_token=bot_token)

    @_client.on(events.NewMessage)
    async def cache_message(event):
        """미디어가 있는 메시지를 캐싱"""
        if event.message.media:
            _message_cache[(event.chat_id, event.message.id)] = event.message

    logger.info("대용량 파일 다운로더 초기화 완료 (Telethon)")


async def download_file(chat_id: int, message_id: int, dest_dir: str) -> str:
    """캐싱된 Telethon 메시지에서 파일 다운로드. 저장된 파일 경로 반환."""
    if _client is None:
        raise RuntimeError("대용량 파일 다운로더가 설정되지 않았습니다.\n.env에 TELEGRAM_API_ID와 TELEGRAM_API_HASH를 추가해 주세요.")

    msg = _message_cache.pop((chat_id, message_id), None)
    if msg is None:
        raise RuntimeError("파일을 캐시에서 찾을 수 없습니다. 파일을 다시 보내주세요.")

    saved_path = await _client.download_media(msg.media, dest_dir)
    return saved_path


def is_available() -> bool:
    return _client is not None
