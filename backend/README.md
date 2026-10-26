# Fancall Backend

AI 아이돌과 실시간 영상 통화 Python 패키지

## 주요 기능

- LiveKit 기반 실시간 음성/영상 통화
- ElevenLabs TTS 음성 합성
- 실시간 립싱크 아바타 (Simli · LemonSlice, 선택)
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
| `FANCALL_ELEVENLABS_MODEL` | `eleven_v4_turbo` | 사용할 ElevenLabs TTS 모델 |
| `FANCALL_CALL_DURATION_SECONDS` | `180` | 통화 길이(초). 끝나기 전에 아이돌이 작별 인사 후 종료 |
| `SIMLI_API_KEY` | - | Simli 아바타 API 키. `avatar_id`(Simli face ID)가 있는 페르소나에 사용 |
| `LEMONSLICE_API_KEY` | - | LemonSlice 아바타 API 키. `profile_picture_url`만 있는 페르소나에 사용 |

| `RENDER_URL` | - | 우리 GPU 렌더 서버의 WebSocket 주소 (예: `ws://gpu-box:8765/`). 있으면 호스팅 아바타보다 먼저 쓴다 |
| `RENDER_PHOTO` | - | 렌더 서버가 움직일 사진 (서버에서 열 수 있는 경로나 URL). 페르소나에 http 프로필 사진이 있으면 그것을 쓴다 |
| `RENDER_LAYOUT` | - | 얼굴을 상반신 통화 사진 위에 얹는 배치 JSON의 서버 쪽 경로 (선택) |
| `RENDER_IDLE_DIR` | - | 듣고 있는 얼굴 JPEG 프레임 폴더(`clip.json`에 fps). `RENDER_URL` 없이 이것만 있으면 GPU 없이 입만 그려 통화한다 |
| `RENDER_WIDTH` / `RENDER_HEIGHT` | `720` / `1280` | 내보내는 영상 크기 |

아바타 키가 없거나 아바타 시작이 실패하면 음성 통화로 진행됩니다.
호스팅 아바타(Simli 등)는 LiveKit 방에 별도 참가자로 접속하므로 `LIVEKIT_URL`이 외부에서 접근 가능해야 합니다 (로컬 `ws://localhost` 불가).

### 직접 그리는 아바타 (렌더 서버)

`RENDER_URL`을 쓰면 에이전트가 연습생 얼굴을 자기 영상 트랙에 직접 올립니다. 말소리를 40ms 단위로
렌더 서버에 보내 얼굴 프레임을 받고, 같은 40ms의 음성과 짝지어 내보내므로 입과 소리가 어긋나지
않습니다. 말이 없을 때도 무음을 계속 보내 듣는 얼굴(깜빡임·고갯짓)이 멈추지 않습니다.

렌더 서버는 `tools/ditto_render_server.py`입니다. NVIDIA GPU가 있는 서버에서
[Ditto](https://github.com/antgroup/ditto-talkinghead)(Apache-2.0) 체크아웃 옆에 띄웁니다.

```bash
python tools/ditto_render_server.py --ditto /path/to/ditto-talkinghead \
  --data-root checkpoints/ditto_trt_Ampere_Plus \
  --cfg checkpoints/ditto_cfg/v0.4_hubert_cfg_trt_online.pkl --port 8765
```

Ditto는 한 프레임을 그리는 데 그 뒤 80ms의 소리가 더 필요해서 프레임이 두 장 늦게 옵니다.
에이전트는 그만큼 음성을 들고 있다가 프레임과 함께 내보냅니다. GPU 한 장이 통화 하나를 맡습니다.

> **참고**: LiveKit, 데이터베이스, 모델 등 추가 설정은 기본값으로 로컬 개발 가능합니다.
> 변경이 필요한 경우 `fancall/settings.py`의 Settings 클래스를 참고하세요.

## 의존성

- aioia-core (공통 인프라)
- FastAPI, SQLAlchemy, Pydantic
- livekit-api, livekit-agents

## 라이선스

Apache 2.0
