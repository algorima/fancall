# Fancall Backend

AI 아이돌과 실시간 영상 통화 Python 패키지

## 주요 기능

- LiveKit 기반 실시간 음성/영상 통화
- Fish Audio TTS 음성 합성
- Hedra 아바타 지원 (선택)
- 동적 설정 (voice_id, avatar_id, system_prompt)

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
export FISH_API_KEY=...

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

## 환경 변수

### 필수 (Agent 실행 시)

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 |
| `FISH_API_KEY` | Fish Audio TTS API 키 |

### 선택 (기능 활성화)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `FANCALL_OPENAI_MODEL` | `gpt-4o-mini` | 사용할 OpenAI LLM 모델 |
| `HEDRA_ENABLED` | `false` | Hedra 아바타 활성화 |
| `HEDRA_API_KEY` | - | Hedra API 키 (enabled=true일 때 필수) |

> **참고**: LiveKit, 데이터베이스, 모델 등 추가 설정은 기본값으로 로컬 개발 가능합니다.
> 변경이 필요한 경우 `fancall/settings.py`의 Settings 클래스를 참고하세요.

## 의존성

- aioia-core (공통 인프라)
- FastAPI, SQLAlchemy, Pydantic
- livekit-api, livekit-agents

## 라이선스

Apache 2.0
