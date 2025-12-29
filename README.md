# Fancall

AI-powered video call with virtual companions

---

## 주요 기능

- LiveKit 기반 실시간 음성/영상 통화
- AI 아이돌과 1:1 대화
- Fish Audio TTS 음성 합성
- Hedra 아바타 지원 (선택)

---

## 빠른 시작

### Backend

```bash
cd backend
poetry install
export LIVEKIT_URL=ws://localhost:7880
export LIVEKIT_API_KEY=devkey
export LIVEKIT_API_SECRET=secret
export DATABASE_URL=sqlite:///./fancall.db
poetry run uvicorn main:app --reload
```

API 문서:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### LiveKit Agent

```bash
cd backend
export OPENAI_API_KEY=sk-...
export FISH_API_KEY=...
python -m fancall.agent.worker dev
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

접속: http://localhost:3000

---

## 라이브러리 사용

기존 프로젝트에 통합하려면 [통합 가이드](docs/integration-guide.md)를 참조하세요.

---

## 프로젝트 구조

```
backend/
├── fancall/       # 라이브러리
│   ├── api/       # FastAPI router
│   ├── agent/     # LiveKit agent worker
│   └── services/  # LiveKit service
└── main.py        # Standalone 앱

frontend/
├── src/
│   ├── components/    # React components
│   ├── repositories/  # API clients
│   └── schemas.ts     # TypeScript schemas
└── index.ts       # Library exports
```

---

## 문서

- [통합 가이드](docs/integration-guide.md)
- [기여 가이드](CONTRIBUTING.md)
- [개발 원칙](CLAUDE.md)

---

## 라이선스

Apache 2.0
