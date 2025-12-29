# Fancall Frontend

AI 아이돌 실시간 영상 통화 React 컴포넌트

## 주요 컴포넌트

- **AgentCall**: 음성 기반 AI 에이전트 통화 컴포넌트
- **LiveRoomRepository**: API 클라이언트

## 설치

```bash
npm install fancall @aioia/core @livekit/components-react livekit-client
```

## 사용법

### 컴포넌트

```tsx
import { AgentCall } from "fancall";

<AgentCall roomName={roomName} token={token} />;
```

### Repository

```tsx
import { LiveRoomRepository } from "fancall";

const repository = new LiveRoomRepository(apiService);
const response = await repository.create({ agent_name: "idol-agent" });
```

### i18n 통합

[통합 가이드](../docs/integration-guide.md#i18n-통합) 참조

## Peer Dependencies

- React 18+
- Next.js 13 또는 14
- Tailwind CSS with DaisyUI
- @aioia/core
- @livekit/components-react
- livekit-client

## 라이선스

Apache 2.0
