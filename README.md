# Boo키우기 Backend

한국외국어대학교 학생을 위한 캐릭터 육성 앱 **Boo키우기**의 FastAPI 백엔드입니다.

회원가입 이메일 인증, JWT 인증, 퀴즈, 학식 먹이기, 친구, 코인/하트, 미니게임 랭킹, 상점/마이룸, 방명록, 업적, 졸업 요약 API를 제공합니다.

## 기술 스택

| 구분 | 기술 |
| --- | --- |
| Backend | FastAPI, Uvicorn |
| Database | SQLAlchemy, SQLite(local fallback), PostgreSQL(production) |
| Auth | JWT, OAuth2 Bearer, `python-jose` |
| Validation | Pydantic |
| Email | Resend API 또는 SMTP |
| Deploy | Railway, Railpack |

## 프로젝트 구조

```text
.
├── app/
│   ├── core/              # 보안, 이메일, 공통 에러, 업적 로직
│   ├── data/              # 초기 seed 데이터
│   ├── routers/           # 기능별 API 라우터
│   ├── database.py        # DB 연결 및 런타임 스키마 보강
│   ├── main.py            # FastAPI 앱 진입점
│   ├── models.py          # SQLAlchemy 모델
│   └── schemas.py         # Pydantic 스키마
├── docs/ERD.md
├── index.py               # Railway 배포 진입점
├── railpack.json
├── requirements.txt
└── README.md
```

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

별도 `DATABASE_URL`이 없으면 로컬에서는 `boo_app.db` SQLite 파일을 사용합니다.

## 환경 변수

`.env` 파일은 프로젝트 루트에 둡니다. 실제 비밀값은 Git에 올리지 않습니다.

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
SECRET_KEY=change-this-secret

# Resend 사용 시
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=no-reply@your-domain.com
RESEND_FROM_NAME=Boo키우기
EMAIL_API_TIMEOUT_SECONDS=10

# SMTP 사용 시
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender@example.com
SMTP_PASSWORD=app-password
SMTP_FROM_EMAIL=sender@example.com
SMTP_FROM_NAME=Boo키우기
SMTP_USE_TLS=true
SMTP_FORCE_IPV4=true
SMTP_TIMEOUT_SECONDS=10

# 비밀번호 재설정 링크용, 선택
APP_BASE_URL=https://your-frontend-domain.com
PASSWORD_RESET_URL=https://your-frontend-domain.com/password-reset
```

메일 발송은 `RESEND_API_KEY`가 있으면 Resend를 우선 사용하고, 없으면 SMTP 설정을 사용합니다.

## Railway 배포

Railway에서는 `railpack.json`의 start command를 사용합니다.

```json
{
  "deploy": {
    "startCommand": "uvicorn index:app --host 0.0.0.0 --port ${PORT:-8000}"
  }
}
```

Railway Variables에 최소 아래 값을 등록합니다.

```text
DATABASE_URL
SECRET_KEY
RESEND_API_KEY 또는 SMTP_*
```

GitHub `main` 브랜치에 push하면 Railway 연동 설정에 따라 자동 재배포됩니다.

## 주요 정책

### 회원가입/로그인

- 회원가입은 학교 이메일 인증 후 최종 사용자 정보를 입력하는 3단계 흐름입니다.
- 이메일은 `@hufs.ac.kr` 도메인만 허용합니다.
- 로그인 ID는 이메일이 아니라 9자리 숫자 학번입니다.
- 로그인 성공 시 `access_token`, `refresh_token`을 발급합니다.

### 퀴즈

- 퀴즈는 O/X 형식입니다.
- 한 번 푼 퀴즈는 같은 유저에게 다시 출제되지 않습니다.
- 하루 최대 3문제, 문제 풀이 후 3시간 쿨타임입니다.
- 정답: `+30 XP`, `+10 coin`
- 오답: `-10 XP`

### 학식 먹이기

- 평일에는 학식, 주말에는 외대 근처 맛집을 먹일 수 있습니다.
- 조식 `08:00~10:00`, 중식 `11:00~13:00`, 석식 `17:00~19:00`
- 각 시간대마다 하루 1회만 먹일 수 있습니다.
- 먹이기 성공 시 `+50 XP`, `-4 coin`

### 코인/하트/미니게임

- 코인은 퀴즈, 미니게임, 업적 등으로 획득하고 상점/학식에 사용합니다.
- 하트는 `0~5개`이며 미니게임 시작 시 1개 소모됩니다.
- 하트는 30분마다 1개 회복됩니다.
- 미니게임은 `start -> play -> reward -> results` 흐름을 권장합니다.
- `play_session_id` 기준으로 결과 중복 저장을 방지합니다.

### 마이룸/상점

- 상점 아이템 타입은 `wallpaper`, `bed`, `closet`, `table`입니다.
- 유저는 타입별로 1개씩 장착할 수 있습니다.
- 아이템은 `item_key`로 프론트 asset과 안정적으로 매핑합니다.
- 친구 방에 방문해 방명록을 남길 수 있습니다.

### 업적

- 업적은 서버가 조건을 판단하고 보상을 자동 지급합니다.
- 보상 타입은 `coin`, `xp`, `skin`을 지원합니다.
- 주요 행동 API 응답에는 `unlocked_achievements`가 포함될 수 있습니다.
- 같은 업적은 유저별 1회만 지급됩니다.

## API 요약

인증이 필요한 API는 `Authorization: Bearer <access_token>` 헤더를 사용합니다.

### Auth/User

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| POST | `/user/signup/email` | 학교 이메일 인증번호 발송 | No |
| POST | `/user/signup/verify` | 인증번호 검증 | No |
| POST | `/user/` | 회원가입 완료 | No |
| POST | `/user/login` | 학번/비밀번호 로그인 | No |
| POST | `/user/refresh` | 토큰 재발급 | No |
| POST | `/user/logout` | refresh token 폐기 | No |
| GET | `/user/me` | 내 계정 조회 | Yes |
| PUT | `/user/me` | 닉네임/비밀번호 등 수정 | Yes |
| DELETE | `/user/me` | 회원 탈퇴 | Yes |
| POST | `/user/password-reset-request` | 비밀번호 재설정 요청 | No |
| POST | `/user/password-reset-confirm` | 새 비밀번호 설정 | No |
| POST | `/user/me/image` | 프로필 이미지 URL 저장 | Yes |
| DELETE | `/user/me/image` | 프로필 이미지 삭제 | Yes |
| GET | `/user/me/preferences` | 튜토리얼/설정 조회 | Yes |
| PUT | `/user/me/preferences` | 튜토리얼/설정 저장 | Yes |

### App

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/app/config` | 서버 정책값 조회 | No |
| GET | `/app/bootstrap` | 로그인 직후 초기 상태 통합 조회 | Yes |

### Quizzes

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/quizzes/play-status` | 오늘 풀이 가능 여부/쿨타임 조회 | Yes |
| GET | `/quizzes/next` | 다음 미풀이 퀴즈 조회 | Yes |
| POST | `/quizzes/submit` | 정답 제출 | Yes |
| GET | `/quizzes/available` | 미풀이 퀴즈 목록 조회 | Yes |

### School Foods

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/school-foods/` | 학식/맛집 목록 조회 | No |
| GET | `/school-foods/today` | 오늘 제공할 음식 섹션 조회 | No |
| GET | `/school-foods/feed-status` | 오늘 먹이기 상태 조회 | Yes |
| POST | `/school-foods/feed` | 음식 먹이기 | Yes |

### Economy/Minigames

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/economy/status` | 코인/하트 상태 조회 | Yes |
| POST | `/economy/minigame/start` | 하트 차감 및 플레이 세션 생성 | Yes |
| POST | `/economy/minigame/reward` | 미니게임 보상 지급 | Yes |
| POST | `/minigames/results` | 미니게임 결과 저장 | Yes |
| GET | `/minigames/results/me` | 내 미니게임 기록 조회 | Yes |
| GET | `/minigames/ranking/me` | 내 전체 랭킹 조회 | Yes |
| GET | `/minigames/rankings` | 전체 랭킹 조회 | Yes |
| GET | `/minigames/rankings/friends` | 친구 랭킹 조회 | Yes |

### Friends

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/friends/` | 친구 목록 조회 | Yes |
| POST | `/friends/` | 학번으로 친구 바로 추가 | Yes |
| GET | `/friends/search/{student_id}` | 학번으로 유저 검색 | Yes |
| GET | `/friends/{friend_id}` | 친구 상세 조회 | Yes |
| DELETE | `/friends/{friend_id}` | 친구 삭제 | Yes |
| GET | `/friends/requests` | 친구 요청 목록 조회 | Yes |
| POST | `/friends/requests` | 친구 요청 생성 | Yes |
| POST | `/friends/requests/{request_id}/accept` | 친구 요청 수락 | Yes |
| DELETE | `/friends/requests/{request_id}` | 친구 요청 삭제 | Yes |

### Characters

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/characters/me` | 내 캐릭터 조회 | Yes |
| PUT | `/characters/me` | 캐릭터 이름/상태/스킨 수정 | Yes |
| POST | `/characters/me/xp` | XP 변경 | Yes |
| POST | `/characters/me/evolve/confirm` | 진화 확정 | Yes |
| GET | `/characters/me/meal-health` | 배고픔/끼니 상태 조회 | Yes |
| POST | `/characters/me/meal-penalty/apply` | 끼니 누락 패널티 적용 | Yes |

### Shop/Rooms

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/shop/item-types` | 상점 아이템 타입 조회 | No |
| GET | `/shop/items` | 상점 아이템 목록 조회 | Yes |
| POST | `/shop/items/{item_id}/purchase` | 아이템 구매 | Yes |
| GET | `/rooms/me` | 내 방 조회 | Yes |
| PUT | `/rooms/me/equip` | 방 아이템 장착 | Yes |
| DELETE | `/rooms/me/equip/{slot}` | 방 아이템 장착 해제 | Yes |
| GET | `/rooms/{user_id}` | 유저 방 조회 | Yes |
| GET | `/rooms/{user_id}/guestbook` | 방명록 목록 조회 | Yes |
| POST | `/rooms/{user_id}/guestbook` | 방명록 작성 | Yes |
| PUT | `/rooms/guestbook/{entry_id}` | 방명록 수정 | Yes |
| DELETE | `/rooms/guestbook/{entry_id}` | 방명록 삭제 | Yes |

### Achievements/Graduation

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| GET | `/achievements/` | 업적 마스터 목록 조회 | No |
| GET | `/achievements/me` | 내 업적 진행도 조회 | Yes |
| POST | `/achievements/events` | 방 입장/캠퍼스 방문 등 이벤트 처리 | Yes |
| GET | `/graduation/summary` | 졸업 요약 조회 | Yes |
| POST | `/graduation/confirm` | 졸업 확정 | Yes |

### Debug/Admin

| Method | Endpoint | 설명 | Auth |
| --- | --- | --- | --- |
| PATCH | `/debug/me` | 관리자용 내 코인/XP/캐릭터 상태 조작 | Admin |

## 초기 데이터

앱 시작 시 아래 seed 데이터가 자동 보강됩니다.

- `app/data/quizzes.json`
- `app/data/school_foods.json`
- `app/data/room_items.json`

## ERD

ERD 문서는 [docs/ERD.md](docs/ERD.md)를 참고합니다.

## 운영 메모

- 서버 응답 필드는 snake_case입니다. 프론트에서는 mapper를 통해 camelCase로 변환하는 방식을 권장합니다.
- 관리자용 CRUD와 debug API는 일반 앱 화면에서 직접 호출하지 않습니다.
- Railway에서 SMTP 포트 연결이 제한될 수 있으므로 운영 메일은 Resend 같은 HTTP 기반 메일 API 사용을 권장합니다.
- PostgreSQL 운영 DB를 직접 수정할 때는 foreign key 제약을 고려해야 합니다.
