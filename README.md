# WindLens

WindLens is a pilot day-ahead wind forecasting workspace for a Great Britain electricity procurement team. It displays the latest Elexon national wind forecast available at a configured decision snapshot and scores that forecast against realized generation.

This is a decision-support prototype, not a trading recommendation. It does not include demand, prices, thermal generation, other fuel types, or non-Elexon datasets.

## Product decisions and assumptions

- Scope is limited to delivery dates from **1–31 January 2026**.
- The pilot snapshot cutoff is **10:00 Europe/London on the day before delivery**. It is an explicit, configurable assumption for the demo—not a claim that this is the client's approved trading deadline.
- The application selects the most recently published `WINDFOR` value per delivery interval at or before that cutoff.
- Actuals come from `FUELHH` with `fuelType=WIND`; forecasts come from `WINDFOR`.
- The observed WINDFOR records are hourly while FUELHH actuals are half-hourly. To compare like with like, the app averages the two 30-minute actual values in each hourly forecast interval. It reports coverage and forecast cadence; it does not interpolate missing data.
- Metrics are calculated only for intervals with both a forecast and actual: mean absolute error (MAE), root mean squared error (RMSE), signed bias (forecast minus actual), and weighted absolute percentage error (WAPE).
- The Elexon API is queried directly at runtime; no sample or synthetic generation data is presented as real.
- Source references: [Elexon FUELHH documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) and [Elexon WINDFOR documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream).

## Contents

| Path | Purpose |
| --- | --- |
| `backend/app/main.py` | FastAPI routes, Elexon API access, caching, January scope guard, and production static-file serving |
| `backend/app/analytics.py` | Forecast version selection, interval alignment, and accuracy metrics |
| `backend/tests/test_analytics.py` | Unit tests for cutoff selection and missing-data handling |
| `backend/requirements.txt` | Python runtime dependencies |
| `frontend/src/App.tsx` | React dashboard, date selection, charts, metrics, and interval table |
| `frontend/src/style.css` | Responsive dashboard styling |
| `frontend/src/main.tsx` | React application entry point |
| `frontend/package.json` | Frontend scripts and dependencies |
| `frontend/vite.config.ts` | Development API proxy configuration |
| `Dockerfile` | Multi-stage frontend build and Python application image |
| `docker-compose.yml` | Local Docker Compose configuration |
| `.dockerignore` | Excludes local dependencies and build output from the Docker context |

## Architecture and analysis

The browser requests `GET /api/analysis?date=YYYY-MM-DD`. FastAPI rejects dates outside January 2026, fetches wind actuals and forecast history from the two Elexon datasets, and caches each Elexon response in memory for one hour. The analytics layer keeps the latest forecast publication per target interval at or before the configured UK-local cutoff, aligns hourly WINDFOR intervals to the mean of their two half-hour FUELHH actuals, and returns interval data plus summary metrics. The React view renders the forecast/actual comparison, coverage, metrics, and issue timestamps. Upstream failures are returned as explicit API errors and shown in the UI.

## Video walkthrough outline

Keep the combined recording at or under 10 minutes. Suggested talking points:

### Part 1 — buyer-facing product walkthrough (up to 5 minutes)

1. **0:00–0:45:** Frame the use case: the desk needs a trustworthy national wind view before a day-ahead procurement decision; show the delivery-date selector.
2. **0:45–1:45:** Explain the selected snapshot and cutoff, and show the timestamp of the latest forecast issue actually used.
3. **1:45–3:00:** Walk the forecast-versus-actual chart and interval table; explain hourly forecasts are compared with aligned half-hourly actual averages.
4. **3:00–4:15:** Explain MAE, RMSE, WAPE, signed bias, and coverage in plain language; connect error size and direction to procurement risk without presenting a trading recommendation.
5. **4:15–5:00:** Be candid about scope: national wind only, no demand or market prices, and confirm the cutoff/alignment with the client before operational use.

### Part 2 — technical lead handoff (up to 5 minutes)

1. **0:00–1:00:** Show the React → FastAPI → Elexon request/data flow and identify the main source files from the contents table.
2. **1:00–2:00:** Explain the `FUELHH`/`WINDFOR` filters, London time cutoff, per-interval latest-publication selection, and one-hour cache.
3. **2:00–3:00:** Explain hourly/half-hourly alignment, the metric formulas, missing-data behavior, and coverage denominator.
4. **3:00–4:00:** Show the unit tests, frontend production build, dependency audit, API health endpoint, and explicit upstream error handling.
5. **4:00–5:00:** Show Docker Compose and the Heroku-compatible image setup; call out deployment not yet configured, plus the assumptions to validate before production.

## Run locally

### Docker (recommended)

```powershell
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Check service status at [http://localhost:8000/api/health](http://localhost:8000/api/health).

### Run frontend and backend separately

Python 3.11+ and Node.js 20+ are required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite development server proxies `/api` requests to port 8000.

## Publish to GitHub

First create a **public, empty** repository on GitHub (do not initialize it with a README, license, or `.gitignore`). Choose a short random repository name. In PowerShell, from the project root:

```powershell
git init -b main
git add .
git status
git commit -m "Build WindLens pilot dashboard"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/YOUR_RANDOM_REPO_NAME.git
git push -u origin main
```

Replace the two `YOUR_...` placeholders with your GitHub details. Before `git add .`, make sure you have not saved credentials, tokens, or private configuration files in the project. Check `git status`; `.venv`, `node_modules`, and `.env` are ignored. GitHub will prompt you to authenticate when pushing. Afterward, refresh the repository page and confirm the code and README are public.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DECISION_CUTOFF_LOCAL` | `10:00` | Local Europe/London snapshot cutoff (`HH:MM`) |
| `CACHE_TTL_SECONDS` | `3600` | In-memory Elexon response cache duration |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed browser origins |
| `VITE_API_BASE_URL` | empty (same-origin) | Frontend build-time API origin; set only when the frontend and backend are hosted separately |

## Validation

Run the backend unit tests:

```powershell
python -m unittest discover -s backend\tests
```

Build the frontend:

```powershell
cd frontend
npm run build
```

## Deployment

The root Dockerfile can be used as a container deployment on Heroku or any Docker host. For Heroku, create an app, configure the Container stack, then push the image using Heroku's container registry. Set `DECISION_CUTOFF_LOCAL` to the cutoff agreed with the client. Elexon must be reachable from the deployed application.

### Render (recommended: one full-stack Docker service)

1. Push the project to GitHub using the steps above.
2. In Render, choose **New + → Web Service**, connect GitHub, and select the repository.
3. Select **Docker** as the runtime. Leave the root directory as `.` and use the root `Dockerfile`.
4. Add `DECISION_CUTOFF_LOCAL=10:00` and `CACHE_TTL_SECONDS=3600` under environment variables.
5. Set the health check path to `/api/health` if that setting is available, then create the service.
6. Wait for the Docker build and deploy to finish. Open the `onrender.com` URL: the Python service serves both the React app and API on the same origin.
7. Verify the app loads real data and `/api/health` responds with `{"status":"ok"}`. Render's free service may sleep while idle; its first request afterward can take longer.

### Vercel frontend + Render backend (optional split deployment)

Vercel deploys the React frontend; it does **not** run this app's Docker image as a container. Deploy the project to Render as a Docker web service first, then use:

1. Create a Vercel project from the same GitHub repository and set its **Root Directory** to `frontend`.
2. Set the Vercel environment variable `VITE_API_BASE_URL` to your Render service origin, for example `https://your-service.onrender.com` (no trailing slash). Redeploy after setting it; Vite reads this value at build time.
3. In Render, add `CORS_ORIGINS` with your exact Vercel origin, for example `https://your-project.vercel.app`. If you use a Vercel preview domain, include each origin you need, separated by commas.
4. Open the Vercel URL and verify the dashboard can load data. The Render URL also serves the dashboard; the Vercel URL is the separate frontend deployment.
5. Test both public URLs in a private/incognito browser window.

Choose one public demo URL for your submission (usually the Vercel URL if using the split deployment).

**Hosted demo URL:** not deployed yet. Deployment requires access to your GitHub and hosting accounts. Replace this line with the final public URL after deployment and verify it in a private/incognito browser window.

## Demo and submission checklist

This workspace build does not create or publish a public GitHub repository, deploy a hosted application, record/upload a YouTube video, or submit the company's form. Those actions require your personal accounts, final client-approved settings, and permission to publish. Before submission:

1. Create a public repository with an anonymous name and push this code.
2. Deploy the Docker image and replace the hosted demo URL above.
3. Record a video no longer than 10 minutes: up to 5 minutes for the buyer-facing product walkthrough and up to 5 minutes for technical architecture, data handling, analytics, tests, and limitations. Upload it as unlisted and test its access in a private browser.
4. Open the public repository, hosted app, and unlisted video in a private/incognito browser, then complete the submission form.
5. Agree with the client on the decision cutoff and confirm hourly forecast alignment before treating metrics as operational.

## AI assistance

AI tools were used to assist with the initial application design and implementation. Review the data assumptions and validate the live Elexon responses before using this pilot operationally.
