# 통합 가이드

기존 프로젝트에 Fancall 라이브러리를 통합하는 방법

> Standalone 실행: [README.md](../README.md) 참조

## 라이브러리로 통합

## FastAPI 프로젝트

### 설치

```bash
pip install git+https://github.com/algorima/fancall.git#subdirectory=backend
```

### 사용

```python
from fancall.api.router import create_fancall_router
from fancall.factories import LiveRoomManagerFactory
from fancall.settings import LiveKitSettings

livekit_settings = LiveKitSettings()
manager_factory = LiveRoomManagerFactory(db_session_factory)

router = create_fancall_router(
    livekit_settings=livekit_settings,
    jwt_settings=jwt_settings,
    db_session_factory=db_session_factory,
    manager_factory=manager_factory,
    user_info_provider=user_info_provider,
)
app.include_router(router, prefix="/api")
```

### 환경 변수

```bash
export DATABASE_URL=postgresql://...
export LIVEKIT_URL=wss://...
export LIVEKIT_API_KEY=...
export LIVEKIT_API_SECRET=...
export OPENAI_API_KEY=sk-...
export FISH_API_KEY=...
```

---

## React/Next.js 프로젝트

### 설치

```bash
npm install fancall @aioia/core @livekit/components-react livekit-client
```

### Tailwind 설정 (필수)

```ts
// tailwind.config.ts
content: [
  "./src/**/*.{js,ts,jsx,tsx}",
  "./node_modules/fancall/dist/**/*.{js,jsx,ts,tsx}",
  "./node_modules/@aioia/core/dist/**/*.{js,jsx,ts,tsx}",
]
```

### 컴포넌트

```tsx
import { AgentCall } from "fancall";

<AgentCall roomName={roomName} token={token} />
```

### Repository

```tsx
import { LiveRoomRepository } from "fancall";

const repository = new LiveRoomRepository(apiService);
await repository.create({ agent_name: "idol-agent" });
```

### i18n 통합

```tsx
import { fancallTranslations, FANCALL_NS } from "fancall/locale";

// 호스트 앱의 i18n 인스턴스에 번역 리소스 추가
Object.entries(fancallTranslations).forEach(([lang, resources]) => {
  i18n.addResourceBundle(lang, FANCALL_NS, resources);
});
```

지원 언어: `en`, `ko`, `ja`, `zh`, `es`, `id`

---

## 데이터베이스

### Migration

```bash
cd fancall/backend
alembic upgrade head
```

### 테이블

`live_rooms`: 통화방 정보 (user_id: nullable, FK 없음)

## 개발

```bash
# Backend
make format lint type-check

# Frontend
npm run lint type-check
npm run build:lib  # 라이브러리만 빌드
```
