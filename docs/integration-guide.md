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
from fancall.factories import LiveRoomRepositoryFactory
from fancall.settings import LiveKitSettings

livekit_settings = LiveKitSettings()
repository_factory = LiveRoomRepositoryFactory(db_session_factory)

router = create_fancall_router(
    livekit_settings=livekit_settings,
    jwt_settings=jwt_settings,
    db_session_factory=db_session_factory,
    repository_factory=repository_factory,
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

### Entry Points

| 엔트리 | 용도 | 환경 |
|--------|------|------|
| `fancall` | 컴포넌트, Repository | 클라이언트 |
| `fancall/schemas` | 타입, Zod 스키마 | 서버/클라이언트 |
| `fancall/locale` | i18n 리소스 | 서버/클라이언트 |

### 컴포넌트 (클라이언트)

```tsx
import { AgentCall } from "fancall";

<AgentCall roomName={roomName} token={token} />
```

### Repository (클라이언트)

```tsx
import { LiveRoomRepository } from "fancall";

const repository = new LiveRoomRepository(apiService);
await repository.create({ agent_name: "idol-agent" });
```

### 타입 및 스키마 (서버/클라이언트)

```tsx
// 서버 컴포넌트에서 타입 사용
import type { DispatchResponse, LiveRoom } from "fancall/schemas";
import { dispatchResponseSchema } from "fancall/schemas";
```

### i18n 통합

```tsx
// SSR/RSC 환경: locale 엔트리포인트 (권장)
import { fancallTranslations, FANCALL_NS } from "fancall/locale";

// 클라이언트 환경: 메인 엔트리포인트도 가능
import { fancallTranslations, FANCALL_NS } from "fancall";
```

> **SSR/RSC 환경**: `fancall/locale`은 i18n 리소스만 포함하도록 최적화된 엔트리포인트입니다.
> 메인 엔트리포인트는 클라이언트 컴포넌트(`AgentCall`, `StartCallSection`)도 export하므로, 서버 환경에서는 `/locale` 사용을 권장합니다.

```tsx
// 호스트 앱의 i18n 인스턴스에 번역 리소스 추가
Object.entries(fancallTranslations).forEach(([lang, resources]) => {
  i18n.addResourceBundle(lang, FANCALL_NS, resources);
});
```

지원 언어: `en`, `es`, `id`, `ja`, `ko`, `th`, `tl`, `vi`, `zh`

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
