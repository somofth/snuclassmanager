"""텔레그램 봇 핸들러"""

import json
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, UPLOAD_DIR
from database import Assignment, Material, Recording, Subject, get_session
from schedule_data import DAY_NAMES

logger = logging.getLogger(__name__)

# 사용자가 파일을 보낸 후 과목 선택 대기 상태
pending_files: dict[int, dict] = {}  # chat_id -> {"file_path": ..., "type": "audio"|"pdf", "file_name": ...}
# 과목 선택 후 차시 선택 대기 상태
pending_session: dict[int, dict] = {}  # chat_id -> {위 내용 + "subject_id": ...}


def _save_chat_id(chat_id: int):
    """채팅 ID를 .env에 저장"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith("TELEGRAM_CHAT_ID"):
            lines[i] = f"TELEGRAM_CHAT_ID={chat_id}\n"
            found = True
            break
    if not found:
        lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    _save_chat_id(chat_id)
    await update.message.reply_text(
        "수업비서 봇이 시작되었습니다!\n\n"
        "사용 가능한 명령어:\n"
        "/schedule - 시간표 보기\n"
        "/subjects - 과목 목록\n"
        "/summary <과목명> - 수업 요약 보기\n"
        "/assignments - 미완료 과제\n"
        "/done <과제번호> - 과제 완료\n\n"
        "녹음 파일이나 PDF를 보내면 자동으로 요약합니다."
    )


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session()
    try:
        subjects = session.query(Subject).order_by(Subject.day_of_week, Subject.start_time).all()
        if not subjects:
            await update.message.reply_text("등록된 시간표가 없습니다.")
            return

        text = "📅 **시간표**\n\n"
        current_day = -1
        for s in subjects:
            if s.day_of_week != current_day:
                current_day = s.day_of_week
                text += f"\n**[{DAY_NAMES[s.day_of_week]}요일]**\n"
            room_info = f" ({s.room})" if s.room else ""
            text += f"  {s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')} {s.name}{room_info}\n"

        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        session.close()


async def cmd_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session()
    try:
        subjects = session.query(Subject).order_by(Subject.day_of_week, Subject.start_time).all()
        seen = set()
        text = "📚 **과목 목록**\n\n"
        for s in subjects:
            if s.name not in seen:
                seen.add(s.name)
                rec_count = session.query(Recording).filter_by(subject_id=s.id).count()
                mat_count = session.query(Material).filter_by(subject_id=s.id).count()
                text += f"• {s.name} (녹음 {rec_count}개, 자료 {mat_count}개)\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        session.close()


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /summary <과목명>")
        return

    query = " ".join(context.args)
    session = get_session()
    try:
        subject = session.query(Subject).filter(Subject.name.contains(query)).first()
        if not subject:
            await update.message.reply_text(f"'{query}' 과목을 찾을 수 없습니다.")
            return

        # 최근 녹음 요약
        recordings = (
            session.query(Recording)
            .filter_by(subject_id=subject.id)
            .order_by(Recording.created_at.desc())
            .limit(3)
            .all()
        )
        # 최근 자료 요약
        materials = (
            session.query(Material)
            .filter_by(subject_id=subject.id)
            .order_by(Material.created_at.desc())
            .limit(3)
            .all()
        )

        if not recordings and not materials:
            await update.message.reply_text(f"'{subject.name}'에 대한 요약이 아직 없습니다.")
            return

        text = f"📖 **{subject.name} 요약**\n\n"
        for r in recordings:
            date_str = r.created_at.strftime("%m/%d") if r.created_at else "?"
            text += f"🎙️ [{date_str}] 녹음 요약:\n{r.summary or '(처리 중...)'}\n\n"
        for m in materials:
            date_str = m.created_at.strftime("%m/%d") if m.created_at else "?"
            text += f"📄 [{date_str}] {m.file_name}:\n{m.summary or '(처리 중...)'}\n\n"

        # 텔레그램 메시지 길이 제한
        if len(text) > 4000:
            text = text[:4000] + "\n\n...(너무 길어서 잘림)"
        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        session.close()


async def cmd_assignments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session()
    try:
        assignments = (
            session.query(Assignment)
            .filter_by(is_completed=False)
            .order_by(Assignment.created_at.desc())
            .all()
        )
        if not assignments:
            await update.message.reply_text("미완료 과제가 없습니다! 🎉")
            return

        text = "📋 **미완료 과제**\n\n"
        for a in assignments:
            due = f" (마감: {a.due_date})" if a.due_date else ""
            text += f"[{a.id}] **{a.subject.name}** - {a.title}{due}\n"
            if a.description:
                text += f"    {a.description}\n"
            text += "\n"
        text += "완료하려면: /done <과제번호>"
        await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        session.close()


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /done <과제번호>")
        return

    try:
        assignment_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("과제 번호는 숫자여야 합니다.")
        return

    session = get_session()
    try:
        assignment = session.query(Assignment).get(assignment_id)
        if not assignment:
            await update.message.reply_text("해당 과제를 찾을 수 없습니다.")
            return
        assignment.is_completed = True
        session.commit()
        await update.message.reply_text(f"✅ '{assignment.title}' 과제를 완료했습니다!")
    finally:
        session.close()


def _subject_keyboard():
    """과목 선택 인라인 키보드 생성"""
    session = get_session()
    try:
        subjects = session.query(Subject).order_by(Subject.day_of_week).all()
        seen = {}
        for s in subjects:
            if s.name not in seen:
                seen[s.name] = s.id
        buttons = [[InlineKeyboardButton(name, callback_data=f"subject_{sid}")] for name, sid in seen.items()]
        return InlineKeyboardMarkup(buttons)
    finally:
        session.close()


def _session_keyboard():
    """차시 선택 인라인 키보드 (1~16차시, 4열)"""
    buttons = [
        [InlineKeyboardButton(f"{i}차시", callback_data=f"session_{i}") for i in range(row, min(row + 4, 17))]
        for row in range(1, 17, 4)
    ]
    return InlineKeyboardMarkup(buttons)


async def _download_audio(message, audio) -> tuple[str, str]:
    """오디오 파일 다운로드. (file_path, file_name) 반환."""
    import downloader

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_name = getattr(audio, "file_name", None) or f"recording_{audio.file_id}"
    file_size = getattr(audio, "file_size", None)

    if file_size and file_size > 20 * 1024 * 1024:
        # 20MB 초과 → Telethon으로 다운로드
        if not downloader.is_available():
            raise RuntimeError(
                "대용량 파일 다운로더가 설정되지 않았습니다.\n"
                ".env에 TELEGRAM_API_ID와 TELEGRAM_API_HASH를 추가해 주세요."
            )
        saved_path = await downloader.download_file(
            chat_id=message.chat_id,
            message_id=message.message_id,
            dest_dir=UPLOAD_DIR,
        )
        file_name = os.path.basename(saved_path)
        return saved_path, file_name
    else:
        file = await message.get_bot().get_file(audio.file_id)
        file_path = os.path.join(UPLOAD_DIR, file_name)
        await file.download_to_drive(file_path)
        return file_path, file_name


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """음성/오디오 파일 수신"""
    message = update.message
    audio = message.audio or message.voice or message.document

    if not audio:
        return

    try:
        file_path, file_name = await _download_audio(message, audio)
        chat_id = update.effective_chat.id
        pending_files[chat_id] = {"file_path": file_path, "type": "audio", "file_name": file_name}
        await message.reply_text("🎙️ 녹음 파일을 받았습니다. 어떤 과목인가요?", reply_markup=_subject_keyboard())
    except Exception as e:
        logger.exception("오디오 파일 처리 중 오류")
        await message.reply_text(f"❌ 파일 수신 중 오류가 발생했습니다: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 파일 수신 (PDF 등)"""
    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or f"file_{doc.file_id}"
    is_pdf = file_name.lower().endswith(".pdf")
    is_audio = doc.mime_type and doc.mime_type.startswith("audio/")

    if not is_pdf and not is_audio:
        await update.message.reply_text("녹음 파일(음성) 또는 PDF 파일만 처리할 수 있습니다.")
        return

    try:
        if is_audio:
            file_path, file_name = await _download_audio(update.message, doc)
        else:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            if doc.file_size and doc.file_size > 20 * 1024 * 1024:
                await update.message.reply_text("⚠️ PDF 파일이 20MB를 초과합니다. 더 작은 파일을 보내주세요.")
                return
            file = await context.bot.get_file(doc.file_id)
            file_path = os.path.join(UPLOAD_DIR, file_name)
            await file.download_to_drive(file_path)

        chat_id = update.effective_chat.id
        file_type = "pdf" if is_pdf else "audio"
        pending_files[chat_id] = {"file_path": file_path, "type": file_type, "file_name": file_name}

        emoji = "📄" if is_pdf else "🎙️"
        label = "수업자료" if is_pdf else "녹음 파일"
        await update.message.reply_text(f"{emoji} {label}를 받았습니다. 어떤 과목인가요?", reply_markup=_subject_keyboard())
    except Exception as e:
        logger.exception("문서 파일 처리 중 오류")
        await update.message.reply_text(f"❌ 파일 수신 중 오류가 발생했습니다: {e}")


async def handle_subject_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """인라인 버튼으로 과목 선택 → 차시 선택으로 이동"""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    pending = pending_files.pop(chat_id, None)

    if not pending:
        await query.edit_message_text("처리할 파일이 없습니다. 파일을 다시 보내주세요.")
        return

    subject_id = int(query.data.replace("subject_", ""))
    session = get_session()
    try:
        subject = session.query(Subject).get(subject_id)
        if not subject:
            await query.edit_message_text("과목을 찾을 수 없습니다.")
            return

        # 차시 선택 대기 상태로 저장
        pending_session[chat_id] = {**pending, "subject_id": subject_id, "subject_name": subject.name}
        await query.edit_message_text(
            f"📚 **{subject.name}** — 몇 번째 수업(차시)인가요?",
            reply_markup=_session_keyboard(),
            parse_mode="Markdown",
        )
    finally:
        session.close()


async def handle_session_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """차시 선택 후 파일 처리"""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    pending = pending_session.pop(chat_id, None)

    if not pending:
        await query.edit_message_text("처리할 파일이 없습니다. 파일을 다시 보내주세요.")
        return

    session_number = int(query.data.replace("session_", ""))
    subject_name = pending["subject_name"]

    await query.edit_message_text(
        f"⏳ **{subject_name}** {session_number}차시 처리 중... Gemini가 분석하고 있습니다.",
        parse_mode="Markdown",
    )

    try:
        from summarizer import process_file

        result = await process_file(
            file_path=pending["file_path"],
            file_type=pending["type"],
            subject_id=pending["subject_id"],
            file_name=pending["file_name"],
            session_number=session_number,
        )

        text = f"✅ **{subject_name}** {session_number}차시 처리 완료!\n\n"
        text += f"📝 **요약:**\n{result['summary']}\n"

        if result.get("assignments"):
            text += "\n📋 **발견된 과제:**\n"
            for a in result["assignments"]:
                due = f" (마감: {a['due_date']})" if a.get("due_date") else ""
                text += f"  • {a['title']}{due}\n"

        if len(text) > 4000:
            text = text[:4000] + "\n\n...(너무 길어서 잘림)"
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.exception("파일 처리 중 오류")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 처리 중 오류가 발생했습니다: {e}")


def create_bot_app(post_init=None):
    """텔레그램 봇 Application 생성"""
    builder = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN)
    if post_init:
        builder = builder.post_init(post_init)
    app = builder.build()

    # 명령어 핸들러
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("subjects", cmd_subjects))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("assignments", cmd_assignments))
    app.add_handler(CommandHandler("done", cmd_done))

    # 파일 핸들러
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # 인라인 버튼 핸들러
    app.add_handler(CallbackQueryHandler(handle_subject_selection, pattern=r"^subject_"))
    app.add_handler(CallbackQueryHandler(handle_session_selection, pattern=r"^session_"))

    return app
