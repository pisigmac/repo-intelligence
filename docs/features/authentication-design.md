# Universal Authentication & Role-Based Access Control (RBAC) Design

This document details the implementation plan and architecture for the authentication and authorization layer in the Repo Intelligence Platform. The platform supports both local email/password sign-in and GitHub OAuth.

## 1. Architecture Overview
The platform uses a secure JWT-based authentication layer implemented in a universal `auth_module`.

- **Identity Providers:** Local Database (Email/Password) and GitHub (OAuth 2.0).
- **Session Management:** Stateless JSON Web Tokens (JWT) signed by the API Gateway.
- **Enforcement Point:** The FastAPI Gateway validates tokens before proxying requests to internal microservices via the `get_current_user_factory` dependency.

## 2. Universal Auth Module (`libs/auth_module`)
The authentication logic has been abstracted into a highly reusable, framework-agnostic package.
- `core.py`: Contains `GitHubAuthenticator` for managing the OAuth flow and JWT creation based on GitHub profiles.
- `router.py`: Contains `AuthRouter` for local authentication, exposing `/register`, `/login`, and `/refresh` endpoints using `OAuth2PasswordRequestForm`.
- `security.py`: Handles bcrypt password hashing and token generation.
- `dependencies.py`: Provides FastAPI dependency injection for resolving the current user.

## 3. Environment Variables
The following environment variables configure the Gateway:
- `GITHUB_CLIENT_ID`: The OAuth App Client ID.
- `GITHUB_CLIENT_SECRET`: The OAuth App Client Secret.
- `JWT_SECRET_KEY`: A secure random string used to sign JWTs.
- `JWT_ALGORITHM`: `HS256`.

## 4. Backend Implementation (API Gateway)
The `infra/docker/gateway.py` integrates both local and GitHub authentication:

### 4.1 Local Endpoints (`/auth`)
- `POST /auth/register`: Accepts email/password and creates a user.
- `POST /auth/login`: Validates credentials and returns a JWT access token.

### 4.2 GitHub Endpoints (`/auth/github`)
- `GET /auth/github/login`: Redirects the user to GitHub OAuth authorization.
- `GET /auth/github/callback`: Exchanges code for token, fetches profile, generates JWT, and redirects to UI.

### 4.3 Security Dependencies
The unified `get_current_user` dependency protects mutating operations:
- **Read Operations** (e.g., `GET /repos`): Remain open (or require basic auth).
- **Write Operations** (e.g., `POST /execute`, `POST /repos`): Strictly require `Depends(get_current_user)`.

## 5. Frontend Implementation (React UI)
The React dashboard (`ui/`) maintains authentication state.

### 5.1 State Management
`ui/src/store/authStore.ts` uses Zustand to store the JWT `token` and `user` profile, persisting them to `localStorage`.

### 5.2 Axios Interceptor
`ui/src/api/client.ts` attaches the token to outbound requests and handles global `401 Unauthorized` responses by kicking the user back to `/login`.

### 5.3 UI Components
- **Login Page (`/login`):** An elegant dual-purpose form for local Sign Up / Sign In, accompanied by a "Continue with GitHub" button.
- **Auth Callback Page (`/auth/callback`):** Handles the GitHub OAuth redirect and saves the token.
- **Protected Routes (`App.tsx`):** Wraps internal views ensuring unauthenticated users cannot access them.
- **Sidebar (`Sidebar.tsx`):** Displays the authenticated user's profile and provides a logout button.

## 6. Completion Status
- [x] **Step 1:** Add PyJWT, passlib[bcrypt], and python-multipart to Gateway `requirements.txt`.
- [x] **Step 2:** Extract local auth logic into `libs/auth_module`.
- [x] **Step 3:** Implement OAuth flow alongside local AuthRouter in `gateway.py`.
- [x] **Step 4:** Implement unified JWT validation dependency (`get_current_user`) and protect sensitive routes.
- [x] **Step 5:** Add auth store and API interceptors to the React UI.
- [x] **Step 6:** Create unified Login (email + GitHub) and Callback components in the React UI.
- [x] **Step 7:** Update the UI layout to show user profile and handle logout.
