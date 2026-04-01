"""Gemini API를 사용한 녹음/PDF 요약"""

import json
import logging
from datetime import datetime

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from database import Assignment, Material, Recording, get_session

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

AUDIO_PROMPT = """당신은 대학교 수업 녹음을 분석하는 비서입니다.
이 녹음을 듣고 다음을 추출해주세요:

1. **수업 내용 요약**: 주요 개념, 핵심 내용을 구조화하여 정리 (한국어)
2. **과제/시험 정보**: 교수님이 언급한 과제, 시험, 제출 사항을 모두 추출

반드시 아래 JSON 형식으로 응답해주세요:
{
    "summary": "수업 내용 요약 (마크다운 형식)",
    "assignments": [
        {
            "title": "과제 제목",
            "description": "상세 설명",
            "due_date": "마감일 (언급된 경우)"
        }
    ]
}

과제가 없으면 assignments를 빈 배열로 두세요.
JSON만 출력하세요. 다른 텍스트는 포함하지 마세요.
"""

PDF_PROMPT = """당신은 대학교 수업 자료를 분석하는 비서입니다.
이 PDF 수업자료를 분석하고 다음을 추출해주세요:

1. **내용 요약**: 핵심 개념, 주요 내용을 구조화하여 정리 (한국어)
2. **과제/시험 정보**: 과제, 시험, 제출 사항이 있으면 추출

반드시 아래 JSON 형식으로 응답해주세요:
{
    "summary": "내용 요약 (마크다운 형식)",
    "assignments": [
        {
            "title": "과제 제목",
            "description": "상세 설명",
            "due_date": "마감일 (언급된 경우)"
        }
    ]
}

과제가 없으면 assignments를 빈 배열로 두세요.
JSON만 출력하세요. 다른 텍스트는 포함하지 마세요.
"""


def _parse_response(text: str) -> dict:
    """Gemini 응답에서 JSON 파싱"""
    # ```json ... ``` 블록 제거
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # 첫 줄(```json)과 마지막 줄(```) 제거
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(f"JSON 파싱 실패, 원본 텍스트를 요약으로 사용: {text[:200]}")
        return {"summary": text, "assignments": []}


async def process_file(file_path: str, file_type: str, subject_id: int, file_name: str) -> dict:
    """파일을 Gemini로 분석하고 DB에 저장"""

    # Gemini File API로 파일 업로드
    uploaded_file = client.files.upload(file=file_path)
    logger.info(f"파일 업로드 완료: {uploaded_file.name}")

    # 프롬프트 선택
    prompt = AUDIO_PROMPT if file_type == "audio" else PDF_PROMPT

    # Gemini API 호출
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type),
                    types.Part.from_text(text=prompt),
                ]
            )
        ],
    )

    result = _parse_response(response.text)
    logger.info(f"Gemini 분석 완료: 요약 {len(result.get('summary', ''))}자, 과제 {len(result.get('assignments', []))}개")

    # DB에 저장
    session = get_session()
    try:
        if file_type == "audio":
            recording = Recording(
                subject_id=subject_id,
                file_path=file_path,
                summary=result.get("summary", ""),
                recorded_at=datetime.now(),
            )
            session.add(recording)
            session.flush()
            source_recording_id = recording.id
            source_material_id = None
        else:
            material = Material(
                subject_id=subject_id,
                file_path=file_path,
                file_name=file_name,
                summary=result.get("summary", ""),
            )
            session.add(material)
            session.flush()
            source_recording_id = None
            source_material_id = material.id

        # 과제 저장
        for a in result.get("assignments", []):
            assignment = Assignment(
                subject_id=subject_id,
                recording_id=source_recording_id,
                material_id=source_material_id,
                title=a.get("title", "제목 없음"),
                description=a.get("description", ""),
                due_date=a.get("due_date", ""),
            )
            session.add(assignment)

        session.commit()
    finally:
        session.close()

    # 업로드된 파일 정리
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass

    return result
