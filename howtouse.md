# 수업비서 사용법

## 1단계: 텔레그램 설치 & 봇 만들기

### 텔레그램 설치
- 아이폰: App Store에서 "Telegram" 검색 후 설치
- 가입은 전화번호만 있으면 됨

### 봇 만들기 (1분 소요)
1. 텔레그램 앱에서 검색창에 **@BotFather** 입력 후 대화 시작
2. `/newbot` 입력
3. 봇 이름 입력 (예: `내 수업비서`)
4. 봇 유저네임 입력 (예: `my_class_bot`) — 반드시 `bot`으로 끝나야 함
5. BotFather가 **토큰**을 알려줌 (예: `7123456789:AAF...` 형태의 긴 문자열)
6. 이 토큰을 복사

### 토큰 등록
프로젝트 폴더의 `.env` 파일을 열어서 토큰 붙여넣기:

```
GEMINI_API_KEY=AIzaSy...
TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 2단계: 프로그램 실행

터미널에서:

```bash
cd 수업비서
source venv/bin/activate
python main.py
```

실행되면 이런 로그가 나옴:
```
시간표 초기화 완료
웹 대시보드: http://localhost:9090
텔레그램 봇 준비 완료
수업비서 봇을 시작합니다...
```

---

## 3단계: 봇 등록

1. 텔레그램 앱에서 아까 만든 봇 이름을 검색 (예: `@my_class_bot`)
2. **시작** 버튼 누르기 (또는 `/start` 입력)
3. 봇이 인사 메시지를 보내면 등록 완료
4. **프로그램을 한 번 재시작** → 수업 알림이 활성화됨

---

## 사용법

### 수업 알림 받기
- 프로그램이 켜져 있으면 수업 5분 전에 자동으로 알림이 옴
- "📚 다문화교육 개론 수업이 5분 후 시작됩니다! 녹음을 켜주세요."
- 수업이 끝나면 "녹음 파일을 보내주세요" 메시지가 옴

### 녹음 보내기
1. 아이폰 기본 녹음 앱(음성 메모)으로 수업 녹음
2. 녹음 끝나면 텔레그램 봇 대화창에서 **📎 클립 아이콘** → **파일** → 녹음 파일 선택해서 전송
3. 봇이 "어떤 과목인가요?" 물어봄 → 해당 과목 버튼 터치
4. Gemini가 분석 후 요약 + 과제 정보를 자동으로 보내줌

### PDF 수업자료 보내기
1. 교수님이 올린 PDF를 텔레그램 봇에게 전송 (클립 → 파일 → PDF 선택)
2. 과목 선택 → 자동 요약

### 봇 명령어
| 명령어 | 설명 |
|--------|------|
| `/start` | 봇 시작 |
| `/schedule` | 시간표 보기 |
| `/subjects` | 과목 목록 + 녹음/자료 개수 |
| `/summary 과목명` | 최근 수업 요약 보기 (예: `/summary 정치교육론`) |
| `/assignments` | 미완료 과제 목록 |
| `/done 번호` | 과제 완료 처리 (예: `/done 3`) |

### 데스크톱 대시보드
- 브라우저에서 **http://localhost:9090** 접속
- 시간표, 과제, 요약을 한눈에 확인 가능

---

## Railway 배포 (무료 서버에서 24시간 실행)

로컬에서 매번 켤 필요 없이, Railway에 올리면 24시간 자동 실행됩니다.

### 사전 준비
- GitHub 계정 (없으면 github.com에서 가입)
- Railway 계정 (없으면 railway.com에서 GitHub으로 가입)

### 배포 순서

**1. GitHub에 코드 올리기**

```bash
cd 수업비서
git init
git add -A
git commit -m "수업비서 초기 버전"
```

GitHub에서 새 저장소(repository) 만들고:
```bash
git remote add origin https://github.com/내아이디/수업비서.git
git branch -M main
git push -u origin main
```

**2. Railway에서 배포**

1. [railway.com](https://railway.com) 접속 → GitHub으로 로그인
2. **New Project** → **Deploy from GitHub repo** 클릭
3. 방금 올린 `수업비서` 저장소 선택
4. 배포가 자동으로 시작됨

**3. 환경변수 설정**

Railway 프로젝트 대시보드에서:
1. 배포된 서비스 클릭 → **Variables** 탭
2. 아래 변수를 추가:

| 변수명 | 값 |
|--------|-----|
| `GEMINI_API_KEY` | Gemini API 키 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 텔레그램에서 /start 후 확인한 채팅 ID |

> 💡 TELEGRAM_CHAT_ID를 아직 모르면 비워두고, 봇에 /start를 보낸 뒤 Railway 로그에서 확인할 수 있습니다.

**4. 웹 대시보드 접속**

- Railway가 자동으로 URL을 생성해줌 (예: `수업비서-xxxx.up.railway.app`)
- Settings → Networking → **Generate Domain** 클릭하면 공개 URL 생성
- 이 URL로 어디서든 대시보드 접속 가능

### 배포 완료 후
- 봇이 24시간 실행됨 → 수업 알림 자동 수신
- 코드를 수정하고 `git push`하면 자동으로 재배포됨
- Railway 무료 크레딧: 월 $5 (이 봇은 충분)

---

## 주의사항
- **로컬 실행 시**: 프로그램(python main.py)이 계속 켜져 있어야 함
- **Railway 배포 시**: 24시간 자동 실행 (컴퓨터 꺼도 됨)
- 텔레그램 파일 전송 제한: 최대 **50MB** (보통 2시간 녹음이 약 30MB)
- 긴 녹음 파일은 분석에 1~2분 걸릴 수 있음
