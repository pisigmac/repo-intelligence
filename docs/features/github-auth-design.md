# GitHub OAuth & Role-Based Access Control (RBAC) Design

This document details the implementation plan for adding GitHub OAuth authentication and authorization to the Repo Intelligence Platform.

## 1. Architecture Overview
Currently, the API Gateway and React UI are completely open. We will secure the platform by introducing a JWT-based authentication layer powered by GitHub OAuth. 

- **Identity Provider:** GitHub (OAuth 2.0).
- **Session Management:** Stateless JSON Web Tokens (JWT) signed by the API Gateway.
- **Enforcement Point:** The FastAPI Gateway will validate tokens before proxying requests to internal microservices.

## 2. Environment Variables
The following environment variables will be added to the Gateway (`docker-compose.yml` and `.env`):
- `GITHUB_CLIENT_ID`: The OAuth App Client ID.
- `GITHUB_CLIENT_SECRET`: The OAuth App Client Secret.
- `JWT_SECRET_KEY`: A secure random string used to sign JWTs.
- `JWT_ALGORITHM`: `HS256`.
- `ALLOWED_GITHUB_ORGS` (Optional): Restrict login to members of specific GitHub organizations.

## 3. Backend Implementation (API Gateway)
The `infra/docker/gateway.py` will be updated to include an authentication router and dependency injection for route protection.

### 3.1 New Endpoints
- `GET /api/auth/github/login`: Redirects the user to `https://github.com/login/oauth/authorize`.
- `GET /api/auth/github/callback`: 
  1. Receives the authorization `code`.
  2. Exchanges the code for a GitHub access token.
  3. Fetches the user's GitHub profile (`https://api.github.com/user`).
  4. Generates a signed JWT containing `sub` (username) and `avatar_url`.
  5. Redirects back to the UI (`http://localhost:5173/auth/callback?token=<JWT>`).
- `GET /api/auth/me`: Returns the current user's profile based on the JWT in the `Authorization: Bearer` header.

### 3.2 Security Dependencies
A FastAPI dependency `get_current_user` will be created to decode and validate the JWT.
- **Read Operations** (e.g., `GET /repos`, `GET /capabilities`): Will remain open (or require basic auth depending on deployment).
- **Write Operations** (e.g., `POST /execute`, `POST /approvals/*/decision`): Will strictly require `get_current_user`.

## 4. Frontend Implementation (React UI)
The React dashboard will be updated to handle authentication state and attach the JWT to all API requests.

### 4.1 State Management
Update `ui/src/store/uiStore.ts` (or create `authStore.ts`):
- Store `token` (JWT) and `user` (profile data).
- Persist token in `localStorage`.

### 4.2 Axios Interceptor
Update `ui/src/api/client.ts` to attach the token:
```typescript
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ri_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### 4.3 UI Components
- **Login Page (`/login`):** A simple page with a "Login with GitHub" button.
- **Auth Callback Page (`/auth/callback`):** Captures the token from the URL query params, saves it to `localStorage`, and redirects to `/`.
- **Sidebar User Profile:** Display the logged-in user's GitHub avatar and username at the bottom of the sidebar.
- **Protected Routes:** Use a React Router wrapper to redirect unauthenticated users to `/login`.

## 5. Implementation Steps
- [ ] **Step 1:** Add PyJWT and httpx dependencies to Gateway `requirements.txt`.
- [ ] **Step 2:** Implement OAuth flow endpoints in `gateway.py`.
- [ ] **Step 3:** Implement JWT validation dependency (`get_current_user`) and protect sensitive routes.
- [ ] **Step 4:** Add auth store and API interceptors to the React UI.
- [ ] **Step 5:** Create Login and Callback components in the React UI.
- [ ] **Step 6:** Update the UI layout to show user profile and handle logout.
