WindLens
WindLens is a dashboard for comparing day-ahead wind generation forecasts with actual wind generation in Great Britain. It helps users review forecast performance for a selected delivery date.

Live app: https://windlens-rxjo.onrender.com/
Health check: https://windlens-rxjo.onrender.com/api/health

WindLens is a decision-support prototype. It does not make trading decisions or recommend how much electricity to buy.
What it does
- Lets users select a delivery date in January 2026.
- Retrieves forecast and actual wind-generation data from the Elexon API.
- Shows forecast and actual values on a graph, with an interval table.
- Reports MAE, RMSE, signed bias, WAPE, and data coverage.
- Caches Elexon responses in memory for one hour.
- Displays upstream API errors rather than treating failed requests as valid results.
Data and assumptions
- Date range: 1–31 January 2026.
- Forecast data: WINDFOR.
- Actual data: FUELHH, filtered to fuelType=WIND.
- Forecast cutoff: 10:00 Europe/London on the day before delivery. This is a configurable pilot assumption, not a confirmed trading deadline.
- Time intervals: WINDFOR records are hourly and FUELHH records are half-hourly. The app averages the two half-hourly actual values to compare them with an hourly forecast. Missing values are not interpolated.
- Metrics: Calculated only for intervals that have both forecast and actual values. Signed bias is forecast minus actual.
The app uses Elexon data directly at runtime; it is not intended to present sample values as real data.

Elexon references:
- FUELHH dataset documentation
- WINDFOR dataset documentation
How it works
1. The user selects a date in the dashboard.
2. The React frontend requests GET /api/analysis?date=YYYY-MM-DD.
3. FastAPI checks the requested date, fetches the relevant Elexon data, and caches responses for one hour.
4. The analytics code selects the latest eligible forecast publication for each delivery interval at or before the configured cutoff.
5. Hourly forecast intervals are aligned with actual generation, and the metrics are calculated for matched intervals.
6. The frontend displays the graph, metrics, coverage, and issue timestamps.
Project structure
Path	Purpose
backend/app/main.py	FastAPI routes, Elexon API access, caching, date validation, and serving the built frontend
backend/app/analytics.py	Forecast selection, interval alignment, and accuracy metrics
backend/tests/test_analytics.py	Tests for cutoff selection and missing-data handling
backend/requirements.txt	Python dependencies
frontend/src/App.tsx	Dashboard, date selection, charts, metrics, and interval table
frontend/src/style.css	Dashboard styling
frontend/src/main.tsx	React entry point
frontend/package.json	Frontend scripts and dependencies
frontend/vite.config.ts	Local development API proxy
Dockerfile	Builds the frontend and packages the backend into one image
docker-compose.yml	Local Docker Compose configuration
.dockerignore	Files excluded from the Docker build context


Deployment on Render
The live app is deployed on Render as one Docker web service. The service uses the root Dockerfile to build the React frontend and run the FastAPI backend. The backend serves the frontend and API from the same origin.

Deployment settings:
1. Connect the public GitHub repository to a new Render Web Service.
2. Choose Docker as the runtime and keep the root directory as ..
3. Set DECISION_CUTOFF_LOCAL=10:00.
4. Set CACHE_TTL_SECONDS=3600.
5. Set the health check path to /api/health, if available.
6. Deploy and verify the live app and health endpoint.
The Render free service may sleep while idle, so the first request after a period of inactivity can take longer.
Run locally
Using Docker
From the project root, run:
docker compose up --build
Then open http://localhost:8000. The health endpoint is http://localhost:8000/api/health.
Running the frontend and backend separately
You need Python 3.11+ and Node.js 20+.

In PowerShell, from the project root:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload --port 8000
In a second terminal:
cd frontend
npm install
npm run dev
Open http://localhost:5173. The Vite development server proxies /api requests to the backend on port 8000.
Configuration
Variable	Default	Purpose
DECISION_CUTOFF_LOCAL	10:00	Forecast snapshot cutoff in Europe/London local time (HH:MM)
CACHE_TTL_SECONDS	3600	Elexon response cache duration in seconds
CORS_ORIGINS	http://localhost:5173	Comma-separated allowed browser origins
VITE_API_BASE_URL	Empty (same origin)	Optional API origin when frontend and backend are hosted separately


Tests and build
Run backend unit tests:
python -m unittest discover -s backend\tests
Build the frontend:
cd frontend
npm run build

Before operational use
The January 2026 date range and 10:00 Europe/London cutoff are pilot assumptions. Confirm the cutoff and interval-alignment approach with the intended users before using the metrics for operational decisions.
