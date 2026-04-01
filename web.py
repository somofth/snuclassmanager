"""데스크톱 대시보드 웹 UI"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from database import Assignment, Material, Recording, Subject, get_session
from schedule_data import DAY_NAMES

web_app = FastAPI()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>수업비서 대시보드</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            text-align: center;
            padding: 30px 0 20px;
            border-bottom: 1px solid #2a2a2a;
            margin-bottom: 30px;
        }
        header h1 { font-size: 28px; color: #fff; }
        header p { color: #888; margin-top: 5px; }

        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }

        .card {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 12px;
            padding: 20px;
        }
        .card h2 {
            font-size: 16px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card.full { grid-column: 1 / -1; }

        /* 시간표 */
        .schedule-day { margin-bottom: 15px; }
        .schedule-day h3 {
            font-size: 14px;
            color: #6c9cff;
            margin-bottom: 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid #222;
        }
        .schedule-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            margin-bottom: 4px;
            background: #222;
            border-radius: 8px;
        }
        .schedule-time {
            color: #aaa;
            font-size: 13px;
            min-width: 110px;
            font-variant-numeric: tabular-nums;
        }
        .schedule-name { font-weight: 600; color: #fff; }
        .schedule-room { color: #666; font-size: 13px; margin-left: auto; }

        /* 과제 */
        .assignment-item {
            padding: 12px;
            margin-bottom: 8px;
            background: #222;
            border-radius: 8px;
            border-left: 3px solid #ff6b6b;
        }
        .assignment-item.completed { border-left-color: #51cf66; opacity: 0.6; }
        .assignment-subject { font-size: 12px; color: #6c9cff; margin-bottom: 4px; }
        .assignment-title { font-weight: 600; color: #fff; }
        .assignment-due { font-size: 12px; color: #ff6b6b; margin-top: 4px; }
        .assignment-desc { font-size: 13px; color: #aaa; margin-top: 4px; }

        /* 요약 */
        .summary-item {
            padding: 15px;
            margin-bottom: 10px;
            background: #222;
            border-radius: 8px;
        }
        .summary-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .summary-subject { font-weight: 600; color: #fff; }
        .summary-date { font-size: 12px; color: #666; }
        .summary-type {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
        .summary-type.audio { background: #2d1f3d; color: #b794f6; }
        .summary-type.pdf { background: #1f2d3d; color: #74b9ff; }
        .summary-text {
            font-size: 14px;
            color: #ccc;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }

        .empty { color: #555; font-style: italic; padding: 20px; text-align: center; }

        /* 과목 통계 */
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
        .stat-card {
            background: #222;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .stat-card .name { font-weight: 600; font-size: 14px; color: #fff; margin-bottom: 8px; }
        .stat-card .counts { font-size: 12px; color: #888; }
        .stat-card .counts span { margin: 0 4px; }

        .refresh-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #333;
            color: #fff;
            border: 1px solid #444;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover { background: #444; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>수업비서</h1>
            <p>대학교 수업 관리 대시보드</p>
        </header>

        <div class="grid">
            <!-- 시간표 -->
            <div class="card">
                <h2>📅 시간표</h2>
                {{schedule_html}}
            </div>

            <!-- 미완료 과제 -->
            <div class="card">
                <h2>📋 미완료 과제</h2>
                {{assignments_html}}
            </div>

            <!-- 과목 통계 -->
            <div class="card full">
                <h2>📚 과목 현황</h2>
                {{stats_html}}
            </div>

            <!-- 최근 요약 -->
            <div class="card full">
                <h2>📝 최근 요약</h2>
                {{summaries_html}}
            </div>
        </div>
    </div>

    <button class="refresh-btn" onclick="location.reload()">새로고침</button>
    <script>
        // 60초마다 자동 새로고침
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>"""


def _build_schedule_html(subjects: list[Subject]) -> str:
    if not subjects:
        return '<div class="empty">시간표가 없습니다.</div>'

    html = ""
    current_day = -1
    for s in subjects:
        if s.day_of_week != current_day:
            if current_day != -1:
                html += "</div>"
            current_day = s.day_of_week
            html += f'<div class="schedule-day"><h3>{DAY_NAMES[s.day_of_week]}요일</h3>'
        room = f'<span class="schedule-room">{s.room}</span>' if s.room else ""
        html += (
            f'<div class="schedule-item">'
            f'<span class="schedule-time">{s.start_time.strftime("%H:%M")} - {s.end_time.strftime("%H:%M")}</span>'
            f'<span class="schedule-name">{s.name}</span>{room}</div>'
        )
    html += "</div>"
    return html


def _build_assignments_html(assignments: list[Assignment]) -> str:
    if not assignments:
        return '<div class="empty">미완료 과제가 없습니다! 🎉</div>'

    html = ""
    for a in assignments:
        due = f'<div class="assignment-due">마감: {a.due_date}</div>' if a.due_date else ""
        desc = f'<div class="assignment-desc">{a.description}</div>' if a.description else ""
        html += (
            f'<div class="assignment-item">'
            f'<div class="assignment-subject">{a.subject.name}</div>'
            f'<div class="assignment-title">{a.title}</div>'
            f'{desc}{due}</div>'
        )
    return html


def _build_stats_html(subjects: list[Subject], session) -> str:
    seen = {}
    for s in subjects:
        if s.name not in seen:
            rec_count = session.query(Recording).filter_by(subject_id=s.id).count()
            mat_count = session.query(Material).filter_by(subject_id=s.id).count()
            asgn_count = session.query(Assignment).filter_by(subject_id=s.id, is_completed=False).count()
            seen[s.name] = (rec_count, mat_count, asgn_count)

    html = '<div class="stat-grid">'
    for name, (rec, mat, asgn) in seen.items():
        html += (
            f'<div class="stat-card">'
            f'<div class="name">{name}</div>'
            f'<div class="counts">'
            f'<span>🎙️ {rec}</span><span>📄 {mat}</span><span>📋 {asgn}</span>'
            f'</div></div>'
        )
    html += "</div>"
    return html


def _build_summaries_html(session) -> str:
    recordings = session.query(Recording).order_by(Recording.created_at.desc()).limit(5).all()
    materials = session.query(Material).order_by(Material.created_at.desc()).limit(5).all()

    items = []
    for r in recordings:
        items.append(("audio", r.subject.name, r.summary, r.created_at))
    for m in materials:
        items.append(("pdf", m.subject.name, m.summary, m.created_at))

    items.sort(key=lambda x: x[3] if x[3] else "", reverse=True)

    if not items:
        return '<div class="empty">아직 요약이 없습니다. 텔레그램으로 녹음이나 PDF를 보내세요.</div>'

    html = ""
    for file_type, subject_name, summary, created_at in items[:8]:
        date_str = created_at.strftime("%m/%d %H:%M") if created_at else ""
        type_label = "녹음" if file_type == "audio" else "PDF"
        summary_text = (summary or "(처리 중...)")[:500]
        html += (
            f'<div class="summary-item">'
            f'<div class="summary-header">'
            f'<span class="summary-subject">{subject_name}</span>'
            f'<div>'
            f'<span class="summary-type {file_type}">{type_label}</span> '
            f'<span class="summary-date">{date_str}</span>'
            f'</div></div>'
            f'<div class="summary-text">{summary_text}</div></div>'
        )
    return html


@web_app.get("/", response_class=HTMLResponse)
async def dashboard():
    session = get_session()
    try:
        subjects = session.query(Subject).order_by(Subject.day_of_week, Subject.start_time).all()
        assignments = (
            session.query(Assignment)
            .filter_by(is_completed=False)
            .order_by(Assignment.created_at.desc())
            .all()
        )

        html = HTML_TEMPLATE.replace("{{schedule_html}}", _build_schedule_html(subjects))
        html = html.replace("{{assignments_html}}", _build_assignments_html(assignments))
        html = html.replace("{{stats_html}}", _build_stats_html(subjects, session))
        html = html.replace("{{summaries_html}}", _build_summaries_html(session))

        return HTMLResponse(content=html)
    finally:
        session.close()


@web_app.get("/api/assignments")
async def api_assignments():
    session = get_session()
    try:
        assignments = session.query(Assignment).filter_by(is_completed=False).all()
        return [
            {
                "id": a.id,
                "subject": a.subject.name,
                "title": a.title,
                "description": a.description,
                "due_date": a.due_date,
            }
            for a in assignments
        ]
    finally:
        session.close()


@web_app.post("/api/assignments/{assignment_id}/done")
async def api_done(assignment_id: int):
    session = get_session()
    try:
        a = session.query(Assignment).get(assignment_id)
        if not a:
            return {"error": "not found"}
        a.is_completed = True
        session.commit()
        return {"ok": True}
    finally:
        session.close()
