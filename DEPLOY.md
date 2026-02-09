# Deploying Backend (Render) + Frontend (AWS Amplify)

This project has a **FastAPI backend** and a **Vite/React frontend**. To run them with the backend on Render and the frontend on AWS Amplify, follow these steps.

---

## 1. Backend on Render

### 1.1 Create a Web Service

1. Go to [Render](https://render.com) and connect your repo (e.g. this repo).
2. Create a **Web Service**.
3. Configure:
   - **Root directory:** `backend`
   - **Build command:** `pip install -r requirements.txt` (or leave Render’s default if it detects Python)
   - **Start command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free or paid

Render sets `PORT`; your app must listen on `0.0.0.0` and that port.

### 1.2 CORS (required for Amplify)

The backend already uses FastAPI’s `CORSMiddleware`. Set an environment variable in Render so the browser allows requests from your Amplify URL:

- **Key:** `CORS_ORIGINS`
- **Value:** Your Amplify app URL(s), comma-separated. For this app:
  `https://main.d3f30e6npwa1ai.amplifyapp.com`

No trailing slashes. For local dev, the default also allows `http://localhost:5173` and `http://localhost:3000`.

### 1.3 Backend URL

This app’s backend is at:

**https://better-uo-scheduler.onrender.com**

Use this as the API base URL in the frontend (Amplify env var).

---

## 2. Frontend on AWS Amplify

### 2.1 Connect the repo

1. In [AWS Amplify Console](https://console.aws.amazon.com/amplify/), connect the same Git repository.
2. Choose the branch to deploy (e.g. `main` or `staging`).
3. Amplify should detect the app; set:
   - **Root directory:** `frontend` (or leave root and set build to run from `frontend`)
   - **Build command:** `npm ci && npm run build` (or `npm run build` if you use `npm install`)
   - **Output directory:** `dist` (Vite’s default)

### 2.2 Set the API URL

So the frontend calls the Render backend in production:

1. In Amplify: **App settings → Environment variables**.
2. Add:
   - **Key:** `VITE_API_URL`
   - **Value:** `https://better-uo-scheduler.onrender.com` (no trailing slash)

Redeploy after changing env vars so the build picks up `VITE_API_URL`.

### 2.3 Add Amplify URL to backend CORS

In Render, set `CORS_ORIGINS` to `https://main.d3f30e6npwa1ai.amplifyapp.com`. If you use multiple branches, add each URL comma-separated.

---

## 3. Local development

- **Backend:** From `backend/`, run `uvicorn app:app --reload`. Default CORS allows `http://localhost:5173`.
- **Frontend:** From `frontend/`, run `npm run dev`. Create `frontend/.env` with:
  ```bash
  VITE_API_URL=http://localhost:8000
  ```
  so the app talks to your local API. (If you don’t set it, the frontend defaults to `http://localhost:8000`.)

---

## 4. Summary (this app)

| Where        | What to set |
|-------------|-------------|
| **Render**  | `CORS_ORIGINS` = `https://main.d3f30e6npwa1ai.amplifyapp.com`; start command `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| **Amplify** | `VITE_API_URL` = `https://better-uo-scheduler.onrender.com` |
| **Local**   | `frontend/.env`: `VITE_API_URL=http://localhost:8000` (optional; that’s the default) |

- **Frontend:** [https://main.d3f30e6npwa1ai.amplifyapp.com](https://main.d3f30e6npwa1ai.amplifyapp.com/)
- **Backend API:** [https://better-uo-scheduler.onrender.com](https://better-uo-scheduler.onrender.com/)

---

## 5. How to check if it works

### Backend is up (Render)

1. **Health check:** Open [https://better-uo-scheduler.onrender.com/health](https://better-uo-scheduler.onrender.com/health) in a browser. You should see `{"status":"ok"}`.
2. **API docs:** Open [https://better-uo-scheduler.onrender.com/docs](https://better-uo-scheduler.onrender.com/docs). You should see Swagger UI with `POST /audit/cs` and `POST /transcript/parse`.
3. **Try the audit from the docs:** On the docs page, open **POST /audit/cs** → “Try it out” → use this body (or leave one attempt), then Execute. You should get a 200 response with audit results.

### Frontend can reach the API (Amplify → Render)

1. Open your app: [https://main.d3f30e6npwa1ai.amplifyapp.com](https://main.d3f30e6npwa1ai.amplifyapp.com/).
2. Open **Developer Tools** (F12 or right‑click → Inspect) → **Network** tab.
3. Do something in the app that calls the API (e.g. run a degree audit).
4. In Network, look for a request to `better-uo-scheduler.onrender.com`. It should:
   - **Status:** 200 (success). If you see **CORS error** in the **Console** tab, add your Amplify URL to `CORS_ORIGINS` on Render and redeploy the backend.
   - **Response:** JSON (e.g. audit result).

### From the command line (no CORS)

```bash
# Health check
curl https://better-uo-scheduler.onrender.com/health

# Audit (minimal body)
curl -X POST https://better-uo-scheduler.onrender.com/audit/cs \
  -H "Content-Type: application/json" \
  -d '{"taken_attempts":[]}'
```

If these return JSON (and the audit returns a result), the backend is working. The main thing that can still fail in the browser is CORS; that’s fixed by setting `CORS_ORIGINS` on Render to your Amplify URL.

The frontend uses `api.ts` and `apiUrl()` / `auditCs()` so all requests go to the correct backend in dev and production.

---

## 6. Troubleshooting: "Cannot fetch" from Amplify

If the Amplify app shows **Request failed** or **Network error** when calling the API:

1. **Confirm the API URL in the app**  
   The UI shows "Backend: …" with the resolved base URL. If it shows `http://localhost:8000` on Amplify, `VITE_API_URL` was not set or not used at build time.

2. **Redeploy Amplify after setting `VITE_API_URL`**  
   Vite bakes `VITE_*` env vars into the bundle at **build time**. After adding or changing `VITE_API_URL` in Amplify, trigger a new build (Redeploy this version / Redeploy branch). Otherwise the old bundle still has the previous (or empty) URL.

3. **Set CORS on Render**  
   In Render → your service → **Environment** → add:
   - **Key:** `CORS_ORIGINS`
   - **Value:** Your **exact** Amplify app URL, e.g. `https://main.d3f30e6npwa1ai.amplifyapp.com` (no trailing slash). Get the URL from the Amplify app overview (branch URL).  
   Save and let the service redeploy. If the origin doesn’t match exactly, the browser will block the response (CORS error).

4. **Check the browser**  
   Open DevTools (F12) → **Console** and **Network**. When you hit "Check API health", look for:
   - **CORS error** → fix `CORS_ORIGINS` on Render (step 3).
   - **Failed to fetch / net::ERR_** → backend unreachable (e.g. Render service down or cold start; try again after 30–60 s on free tier).

5. **Confirm the backend is up**  
   Open `https://better-uo-scheduler.onrender.com/health` in a new tab. You should see `{"status":"ok"}`. If it never loads, the Render service may be down or sleeping.
