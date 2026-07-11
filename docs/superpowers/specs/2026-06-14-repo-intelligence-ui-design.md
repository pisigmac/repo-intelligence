# Repo Intelligence Web Dashboard — Design Spec

## Overview

Build a React-based web dashboard for Repo Intelligence that exposes the full control plane: repository ingestion, capability/playbook discovery, natural-language query, playbook execution, human approvals, feedback metrics, global knowledge search, and agent orchestration.

## Goals

- Give non-technical and technical users a visual entry point to the platform.
- Surface all public gateway endpoints through an intuitive navigation structure.
- Provide live updates for approvals via the existing WebSocket.
- Keep the UI decoupled from the backend so both can evolve independently.

## Non-Goals

- Authentication/authorization (the gateway currently has none).
- Mobile-native app or responsive-first design (desktop web only for MVP).
- Real-time log streaming for playbook execution (poll-based for MVP).

## Target Audience

Developers and technical operators who want to explore, execute, and improve Repo Intelligence playbooks through a browser.

## Architecture

### Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | React 18 |
| Build tool | Vite 5 |
| Routing | React Router 6 |
| Server state | TanStack Query (React Query) v5 |
| Client state | Zustand |
| Styling | Tailwind CSS |
| HTTP client | Axios |
| Icons | Lucide React |
| Testing | Vitest + React Testing Library + Playwright |

### Project Layout

```
ui/
├── public/
│   └── favicon.svg
├── src/
│   ├── api/
│   │   └── client.ts          # Axios instance + gateway endpoints
│   ├── components/
│   │   ├── Layout.tsx         # Sidebar + main content shell
│   │   ├── Sidebar.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── CodeBlock.tsx
│   │   └── LoadingState.tsx
│   ├── hooks/
│   │   ├── useRepos.ts
│   │   ├── useCapabilities.ts
│   │   ├── usePlaybooks.ts
│   │   ├── useApprovals.ts
│   │   └── useWebSocket.ts
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Repos.tsx
│   │   ├── RepoDetail.tsx
│   │   ├── Capabilities.tsx
│   │   ├── CapabilityDetail.tsx
│   │   ├── Playbooks.tsx
│   │   ├── PlaybookDetail.tsx
│   │   ├── Query.tsx
│   │   ├── Execute.tsx
│   │   ├── Approvals.tsx
│   │   ├── ApprovalDetail.tsx
│   │   ├── Feedback.tsx
│   │   ├── Knowledge.tsx
│   │   └── Agents.tsx
│   ├── store/
│   │   └── uiStore.ts
│   ├── types/
│   │   └── index.ts
│   ├── utils/
│   │   └── formatters.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── playwright.config.ts
```

### Deployment

- **Development:** `npm run dev` starts Vite on `localhost:5173` and proxies `/api` to `localhost:8000`.
- **Production:** `npm run build` emits static assets to `ui/dist/`.
- **Serving:** a new `nginx` service in `docker-compose.yml` serves `ui/dist/` on `localhost:8082` and proxies `/api` to the gateway.

## Pages

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/` | Summary cards and recent activity |
| Repos | `/repos` | List repos, ingest new repo |
| Repo Detail | `/repos/:id` | Status, capabilities, playbooks for a repo |
| Capabilities | `/capabilities` | Filterable list of capabilities |
| Capability Detail | `/capabilities/:id` | Entry points, interfaces, signals |
| Playbooks | `/playbooks` | Filterable list of playbooks |
| Playbook Detail | `/playbooks/:id` | Steps, validation, rollback, observability |
| Query | `/query` | Natural-language search |
| Execute | `/execute/:id?` | Run a playbook with context |
| Approvals | `/approvals` | Pending and historical approvals |
| Approval Detail | `/approvals/:id` | Diff view, approve/reject |
| Feedback | `/feedback` | Metrics per playbook |
| Knowledge | `/knowledge` | Global knowledge search and transfer |
| Agents | `/agents` | Submit tasks, view responses |

## API Integration

All API calls go through `http://localhost:8000` (gateway). The Axios base URL is controlled by `VITE_API_BASE_URL`.

Key endpoints consumed:

- `GET /health`
- `POST /repos`, `GET /repos/:id`, `GET /parse/:repo_id`
- `GET /capabilities` (list returns full objects; detail pages filter the list)
- `GET /playbooks` (list returns full objects; detail pages filter the list)
- `GET /playbooks/:id/versions`, `POST /playbooks/:id/transfer`
- `POST /query`, `POST /knowledge/search`
- `POST /execute`
- `GET /approvals`, `POST /approvals/:id/decision`, `GET /approvals/:id/diff`
- `GET /feedback/:id/metrics`, `POST /feedback`
- `POST /agents/execute`
- `WS /ws/approvals` for live approval updates

**Backend changes required for the UI:**

- Enable CORS on the gateway for `http://localhost:5173` (dev) and `http://localhost:8082` (production).
- Add missing gateway environment variables to `docker-compose.yml`:
  `INGESTION_SERVICE_URL`, `FEEDBACK_SERVICE_URL`, `APPROVAL_SERVICE_URL`, `KNOWLEDGE_SERVICE_URL`, `AGENT_ORCHESTRATOR_URL`.

## State Management

- **Server state:** TanStack Query handles caching, refetching, and optimistic updates.
- **Client state:** Zustand stores sidebar collapse, selected theme, and execution form drafts.
- **Real-time:** `useWebSocket` hook listens to `/ws/approvals` and invalidates the approvals query on new events.

## Error Handling

- Global error boundary catches render errors.
- API errors show a toast notification with the error message.
- Query retries use TanStack Query exponential backoff.
- Form validation uses native HTML + Zod for execution context.

## Testing

- **Unit:** Vitest for utilities and hooks.
- **Component:** React Testing Library for page components with mocked TanStack Query.
- **E2E:** Playwright smoke tests for ingest → capability → playbook flow.

## Open Questions

- Should the UI support dark mode out of the box? (Recommended: yes, via Tailwind `dark` class.)
- Should playbook execution show a live terminal-like log panel? (Recommended: yes, poll execution status every 2s for MVP.)
