# Fancall

AI-powered video call with virtual companions

## 주요 기능

- LiveKit 기반 실시간 음성/영상 통화
- AI 아이돌과 1:1 대화
- Fish Audio TTS 음성 합성
- Hedra 아바타 지원 (선택)

## 빠른 시작

### Backend

LiveKit 서버:
```bash
brew install livekit
livekit-server --dev
```

API 서버:
```bash
cd backend
poetry install
poetry run uvicorn main:app --reload
```

자세한 내용: [backend/README.md](backend/README.md)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

자세한 내용: [frontend/README.md](frontend/README.md)

## 라이브러리 통합

기존 프로젝트에 통합: [docs/integration-guide.md](docs/integration-guide.md)

## 문서

- [Backend](backend/README.md) - Python 패키지
- [Frontend](frontend/README.md) - React 컴포넌트
- [통합 가이드](docs/integration-guide.md)
- [기여 가이드](CONTRIBUTING.md)

## 라이선스

Apache 2.0
