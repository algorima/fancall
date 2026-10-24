# Fancall Backend

AI 아이돌과 실시간 영상 통화 Python 패키지

## 주요 기능

- LiveKit 기반 실시간 음성/영상 통화
- ElevenLabs TTS 음성 합성
- Simli 실시간 립싱크 아바타 (선택)
- 아이돌 답변은 두 문장을 넘지 않게 잘라 음성으로 내보냄 (실제 영통팬싸 화법)
- 동적 설정 (voice_id, avatar_id, system_prompt)

> **Fish Audio에서 옮겨오는 호스트 앱**: `voice_id`는 이제 ElevenLabs voice ID입니다. 기존 Fish Audio `voice_id`를 그대로 넘기면 ElevenLabs에서 찾지 못해 음성 합성이 실패하므로, ElevenLabs voice ID로 바꾸거나 `voice_id`를 비워 기본 목소리를 쓰세요. `create_worker_options()`의 `fish_settings` 인자는 `elevenlabs_settings`로 바뀌었습니다.

## 설치

```bash
cd backend
poetry install
poetry run uvicorn main:app --reload
```

API 문서:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## LiveKit 설정

### 서버

```bash
brew install livekit
livekit-server --dev
```

서버: `ws://localhost:7880` (API Key: `devkey`, Secret: `secret`)

### Agent

```bash
cd backend
export OPENAI_API_KEY=sk-...
export ELEVEN_API_KEY=...

# 개발 모드
python -m fancall.agent.worker dev

# 프로덕션 모드
python -m fancall.agent.worker start

# 특정 룸 연결
python -m fancall.agent.worker connect --room <room-name>
```

## 사용법

### FastAPI 통합

```python
from fancall.api.router import create_fancall_router
from fancall.factories import LiveRoomRepositoryFactory
from fancall.settings import LiveKitSettings

router = create_fancall_router(
    livekit_settings=LiveKitSettings(),
    jwt_settings=jwt_settings,
    db_session_factory=db_session_factory,
    repository_factory=LiveRoomRepositoryFactory(db_session_factory),
)
app.include_router(router, prefix="/api")
```

## 개발

```bash
poetry install
make lint
make type-check
make unit-test
make format
```

## 데이터베이스 마이그레이션

데이터베이스 스키마를 최신 상태로 업데이트하려면:

```bash
make migrate
```

새로운 마이그레이션을 생성하려면 (models.py 변경 후):

```bash
poetry run alembic revision --autogenerate -m "변경 설명"
```

## 환경 변수

### 필수 (Agent 실행 시)

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 |
| `ELEVEN_API_KEY` | ElevenLabs TTS API 키 |

### 선택 (기능 활성화)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `FANCALL_OPENAI_MODEL` | `gpt-4o-mini` | 사용할 OpenAI LLM 모델 |
| `FANCALL_OPENAI_REASONING_EFFORT` | - | thinking 모델의 추론 강도 (`minimal`·`low`·`medium`·`high`). 비우면 플러그인 기본값 |
| `FANCALL_ELEVENLABS_MODEL` | `eleven_flash_v2_5` | 사용할 ElevenLabs TTS 모델 |
| `SIMLI_API_KEY` | - | Simli 아바타 API 키. `avatar_id`(Simli face ID)가 있는 페르소나에 사용 |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | 쿠키를 실은 요청을 허용할 프런트 origin (쉼표로 구분). 운영에서는 실제 도메인으로 설정 |

키가 없거나 `avatar_id`가 없거나 시작에 실패하면 음성 통화로 진행되고, 프런트는 프로필 사진을 보여줍니다.
아바타는 LiveKit 방에 별도 참가자로 접속하므로 `LIVEKIT_URL`이 외부에서 접근 가능해야 합니다 (로컬 `ws://localhost` 불가).

> **Hedra에서 옮겨오는 호스트 앱**: Hedra 실시간 아바타는 서비스가 종료되었습니다. `create_worker_options()`의 `hedra_settings` 인자는 `simli_settings`(`SimliSettings`)로 바뀌었고 `HEDRA_ENABLED`/`HEDRA_API_KEY`는 더 이상 읽지 않습니다. `avatar_id`는 이제 Simli face ID입니다.

> **참고**: LiveKit, 데이터베이스, 모델 등 추가 설정은 기본값으로 로컬 개발 가능합니다.
> 변경이 필요한 경우 `fancall/settings.py`의 Settings 클래스를 참고하세요.

## 의존성

- aioia-core (공통 인프라)
- FastAPI, SQLAlchemy, Pydantic
- livekit-api, livekit-agents

## 라이선스

Apache 2.0
