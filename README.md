# Boo키우기 API

FastAPI backend for the Boo키우기 app.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## ERD

See [docs/ERD.md](docs/ERD.md).

---


# 26.05.13 이전 구현 내용 (백)

## 1. 기술 스택

| 구분 | 기술 |
|---|---|
| Backend Framework | FastAPI |
| Authentication | JWT, python-jose |
| Email | smtplib |

## 2. 주요 기능

### 2.1 회원가입

1. 학교 이메일 입력
2. 이메일로 전송된 6자리 인증번호 입력 (발신자의 아이디와 비밀번호를 SMTP 설정에 입력하면 정상 작동; 현재는 작동 X)
3. 인증 완료 후 학번, 비밀번호, 이름, 닉네임 등 사용자 정보 입력

사용 가능한 이메일은 `@hufs.ac.kr` 도메인으로 제한됩니다.
로그인 ID는 이메일이 아니라 9자리 숫자 학번입니다.

관련 API:
| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/user/signup/email` | 학교 이메일 인증번호 발송 |
| POST | `/user/signup/verify` | 6자리 인증번호 검증 |
| POST | `/user/` | 최종 회원가입 |

### 2.2 로그인 및 인증

로그인은 학번과 비밀번호 입력
로그인 성공 시 access token과 refresh token을 발급합니다.

관련 API:

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/user/login` | 학번/비밀번호 로그인 |
| POST | `/user/refresh` | refresh token으로 토큰 재발급 |
| GET | `/user/me` | 현재 로그인한 사용자 정보 조회 |
| POST | `/user/logout` | refresh token 폐기 |

### 2.3 비밀번호 재설정

사용자는 학번을 입력해 비밀번호 재설정 요청을 할 수 있습니다.
서버는 해당 유저의 이메일로 재설정 토큰을 발송

관련 API:

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/user/password-reset-request` | 비밀번호 재설정 토큰 요청 |
| POST | `/user/password-reset-confirm` | 새 비밀번호 설정 |

### 2.4 O/X 퀴즈

퀴즈는 O/X 형식으로 구성
사용자는 아직 풀지 않은 퀴즈만 받을 수 있으며, 한 번 푼 퀴즈는 다시 풀 수 없습니다.

퀴즈 경험치 정책:

| 결과 | 경험치 |
|---|---:|
| 정답 | +30 |
| 오답 | -10 |

퀴즈 제한 정책:

- 하루 최대 3개까지 풀이 가능
- 퀴즈 1개 풀이 후 3시간 쿨타임 적용
- 풀이 기록은 `user_quiz_connect` 테이블에 저장

관련 API:

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/quizzes/available` | 사용자가 아직 풀지 않은 퀴즈 목록 조회 |
| GET | `/quizzes/next` | 다음 미풀이 퀴즈 1개 조회 |
| GET | `/quizzes/play-status` | 오늘 풀이 가능 여부, 남은 개수, 쿨타임 조회 |
| POST | `/quizzes/submit` | 퀴즈 정답 제출 |

### 2.5 학식 먹이기

캐릭터에게 평일에는 학식, 주말에는 외대 근처 맛집을 먹일 수 있습니다.

음식 구분:

| type | 의미 |
|---|---|
| weekday | 평일 학식 |
| weekend | 주말 외대 근처 맛집 |

먹이기 시간대:

| meal_slot | 시간 |
|---|---|
| breakfast | 08:00 ~ 10:00 |
| lunch | 11:00 ~ 13:00 |
| dinner | 17:00 ~ 19:00 |

먹이기 정책:

- 각 시간대마다 하루 1회만 먹이기 가능
- 먹이기 성공 시 경험치 +50
- `user_id + feed_date + meal_slot` 조합으로 중복 먹이기 방지

관련 API:

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/school-foods/` | 전체 학식/맛집 목록 조회 |
| GET | `/school-foods/?type=weekday` | 평일 학식 목록 조회 |
| GET | `/school-foods/?type=weekend` | 주말 맛집 목록 조회 |
| GET | `/school-foods/today` | 오늘 요일에 맞는 음식 목록 조회 |
| GET | `/school-foods/feed-status` | 오늘 먹이기 가능 상태 조회 |
| POST | `/school-foods/feed` | 캐릭터에게 음식 먹이기 |

### 2.6 캐릭터

사용자별 캐릭터 정보를 저장합니다.
캐릭터는 이름과 성장 단계 값을 가집니다.

관련 API:

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/characters/` | 캐릭터 생성 |
| GET | `/characters/` | 캐릭터 목록 조회 |
| GET | `/characters/{character_id}` | 캐릭터 단건 조회 |
| PUT | `/characters/{character_id}` | 캐릭터 정보 수정 |
| DELETE | `/characters/{character_id}` | 캐릭터 삭제 |
