"""시간표 데이터 정의 및 DB 초기화"""

from datetime import time

# 요일: 0=월, 1=화, 2=수, 3=목, 4=금
SCHEDULE = [
    {
        "name": "학제간 캡스톤 설계",
        "room": "",
        "day_of_week": 1,
        "start_time": time(13, 30),
        "end_time": time(15, 30),
    },
    {
        "name": "시민교육과 민주주의",
        "room": "11-108",
        "day_of_week": 1,
        "start_time": time(17, 30),
        "end_time": time(20, 0),
    },
    {
        "name": "정치교육론",
        "room": "11-215",
        "day_of_week": 2,
        "start_time": time(14, 30),
        "end_time": time(16, 0),
    },
    {
        "name": "통합사회교육론",
        "room": "10-1-202",
        "day_of_week": 2,
        "start_time": time(17, 30),
        "end_time": time(19, 30),
    },
    {
        "name": "학제간 캡스톤 설계",
        "room": "",
        "day_of_week": 3,
        "start_time": time(13, 30),
        "end_time": time(15, 30),
    },
]

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


def init_subjects():
    """시간표 데이터를 DB와 동기화 (추가/삭제 반영)"""
    from database import Subject, get_session

    session = get_session()
    try:
        scheduled_names = {entry["name"] for entry in SCHEDULE}

        # SCHEDULE에 없는 과목 삭제
        for subject in session.query(Subject).all():
            if subject.name not in scheduled_names:
                session.delete(subject)

        # 새 과목 추가
        existing_names = {s.name for s in session.query(Subject).all()}
        for entry in SCHEDULE:
            if entry["name"] not in existing_names:
                session.add(Subject(
                    name=entry["name"],
                    room=entry["room"],
                    day_of_week=entry["day_of_week"],
                    start_time=entry["start_time"],
                    end_time=entry["end_time"],
                ))

        session.commit()
    finally:
        session.close()
