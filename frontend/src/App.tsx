import { useEffect, useMemo, useState } from "react";

type Point = {
  startTime: string;
  publishTime: string;
  forecastMw: number;
  actualMw: number | null;
  errorMw: number | null;
};

type Analysis = {
  deliveryDate: string;
  decisionCutoffLocal: string;
  cutoff: string;
  latestPublishTime: string | null;
  resolutionMinutes: number;
  points: Point[];
  metrics: {
    maeMw: number | null;
    rmseMw: number | null;
    biasMw: number | null;
    wapePercent: number | null;
    pairedIntervals: number;
    forecastIntervals: number;
    expectedIntervals: number;
    actualHalfHours: number;
    coveragePercent: number;
  };
};

const JANUARY_START = "2026-01-01";
const JANUARY_END = "2026-01-31";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

function londonTime(value: string, options: Intl.DateTimeFormatOptions = {}) {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London",
    ...options,
  }).format(new Date(value));
}

function number(value: number | null, digits = 0) {
  return value === null
    ? "—"
    : new Intl.NumberFormat("en-GB", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(value);
}

function Chart({ points }: { points: Point[] }) {
  const width = 860;
  const height = 250;
  const pad = { top: 18, right: 16, bottom: 30, left: 48 };
  const data = points.filter((point) => point.actualMw !== null);
  if (!data.length) {
    return <div className="chart-empty">No matched forecast and actual intervals for this date.</div>;
  }
  const values = data.flatMap((point) => [point.forecastMw, point.actualMw ?? 0]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const innerWidth = width - pad.left - pad.right;
  const innerHeight = height - pad.top - pad.bottom;
  const x = (index: number) => pad.left + (index / Math.max(data.length - 1, 1)) * innerWidth;
  const y = (value: number) => pad.top + ((max - value) / range) * innerHeight;
  const path = (key: "forecastMw" | "actualMw") =>
    data
      .map((point, index) => `${index === 0 ? "M" : "L"} ${x(index)} ${y(point[key] ?? 0)}`)
      .join(" ");
  const labels = [0, Math.floor(data.length / 2), data.length - 1];

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Hourly forecast compared with actual wind generation">
        {[0, 0.5, 1].map((fraction) => {
          const value = min + range * (1 - fraction);
          const yPos = pad.top + innerHeight * fraction;
          return (
            <g key={fraction}>
              <line x1={pad.left} x2={width - pad.right} y1={yPos} y2={yPos} className="grid-line" />
              <text x={pad.left - 9} y={yPos + 4} textAnchor="end" className="axis-label">
                {(value / 1000).toFixed(0)}k
              </text>
            </g>
          );
        })}
        <path d={path("forecastMw")} className="line-forecast" />
        <path d={path("actualMw")} className="line-actual" />
        {labels.map((index) => (
          <text key={index} x={x(index)} y={height - 7} textAnchor="middle" className="axis-label">
            {londonTime(data[index].startTime, { hour: "2-digit", minute: "2-digit" })}
          </text>
        ))}
      </svg>
    </div>
  );
}

function App() {
  const [deliveryDate, setDeliveryDate] = useState("2026-01-15");
  const [data, setData] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    fetch(`${API_BASE_URL}/api/analysis?date=${deliveryDate}`, { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
        return body as Analysis;
      })
      .then(setData)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Unable to load Elexon data.");
        setData(null);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [deliveryDate]);

  const stats = data?.metrics;
  const maxForecast = useMemo(
    () => data?.points.reduce((largest, point) => Math.max(largest, point.forecastMw), 0) ?? 0,
    [data],
  );
  const bias = stats?.biasMw ?? null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="WindLens home">
          <span className="brand-mark">W</span>
          <span>windlens<span className="brand-period">.</span></span>
        </a>
        <div className="nav-caption">WORKSPACE</div>
        <a className="nav-item active" href="#overview"><span className="nav-icon">◫</span> Forecast desk</a>
        <div className="sidebar-note">
          <span className="live-dot" />
          <div><strong>Elexon BMRS</strong><small>Data connection</small></div>
        </div>
        <div className="sidebar-footer">PILOT WORKSPACE<br /><span>Great Britain · National</span></div>
      </aside>

      <main className="main" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Portfolio <span>/</span> Wind forecast desk</div>
          <div className="topbar-right"><span className="status-label"><span className="live-dot" /> ELEXON API</span><span className="avatar">GB</span></div>
        </header>

        <div className="content">
          <section className="page-heading">
            <div>
              <div className="eyebrow">DAY-AHEAD PROCUREMENT · GREAT BRITAIN</div>
              <h1>Wind forecast desk</h1>
              <p>One clear view of the forecast you could act on — and how it performed.</p>
            </div>
            <div className="date-control">
              <label htmlFor="delivery-date">DELIVERY DATE</label>
              <input
                id="delivery-date"
                type="date"
                min={JANUARY_START}
                max={JANUARY_END}
                value={deliveryDate}
                onChange={(event) => setDeliveryDate(event.target.value)}
              />
            </div>
          </section>

          <section className="snapshot-banner">
            <div className="snapshot-icon">↗</div>
            <div className="snapshot-copy">
              <strong>Decision snapshot</strong>
              <span>Latest WINDFOR issue published by <b>10:00 UK time on the day before delivery.</b></span>
            </div>
            <div className="snapshot-date">{data?.latestPublishTime ? <>LATEST ISSUE <b>{londonTime(data.latestPublishTime, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</b></> : "No forecast issue available"}</div>
          </section>

          {error && <div className="alert" role="alert"><strong>Could not load Elexon data.</strong><span>{error}</span></div>}
          {loading && <div className="loading-card"><span className="spinner" /> Loading the selected day from Elexon BMRS…</div>}

          {!loading && data && (
            <>
              <section className="metric-grid" aria-label="Forecast accuracy summary">
                <article className="metric-card hero-metric">
                  <div className="metric-top"><span>DAY-AHEAD WIND FORECAST</span><span className="metric-icon">↗</span></div>
                  <div className="metric-value">{number(maxForecast / 1000, 1)}<small> GW</small></div>
                  <div className="metric-foot">Peak forecast generation · {data.points.length} forecast intervals</div>
                </article>
                <article className="metric-card">
                  <div className="metric-top"><span>MEAN ABSOLUTE ERROR</span><span className="metric-icon neutral">MAE</span></div>
                  <div className="metric-value">{number(stats?.maeMw ?? null)}<small> MW</small></div>
                  <div className="metric-foot">Average absolute miss per interval</div>
                </article>
                <article className="metric-card">
                  <div className="metric-top"><span>ROOT MEAN SQUARED ERROR</span><span className="metric-icon neutral">RMSE</span></div>
                  <div className="metric-value">{number(stats?.rmseMw ?? null)}<small> MW</small></div>
                  <div className="metric-foot">Penalizes larger forecast misses</div>
                </article>
                <article className="metric-card">
                  <div className="metric-top"><span>WEIGHTED ABSOLUTE ERROR</span><span className="metric-icon neutral">WAPE</span></div>
                  <div className="metric-value">{number(stats?.wapePercent ?? null, 1)}<small>%</small></div>
                  <div className="metric-foot">Absolute error relative to actual output</div>
                </article>
                <article className="metric-card">
                  <div className="metric-top"><span>FORECAST BIAS</span><span className={`bias-tag ${bias === null ? "neutral" : bias > 0 ? "warm" : ""}`}>{bias === null ? "N/A" : Math.abs(bias) < 0.5 ? "BALANCED" : bias > 0 ? "OVER" : "UNDER"}</span></div>
                  <div className="metric-value">{number(stats?.biasMw ?? null)}<small> MW</small></div>
                  <div className="metric-foot">Forecast minus actual · signed average</div>
                </article>
              </section>

              <section className="panel chart-panel">
                <div className="panel-heading">
                  <div><div className="panel-kicker">FORECAST VS. REALIZED</div><h2>Generation through the day</h2></div>
                  <div className="chart-legend"><span><i className="legend-dot forecast" />Day-ahead forecast</span><span><i className="legend-dot actual" />Actual generation</span></div>
                </div>
                <Chart points={data.points} />
                <div className="chart-footnote">
                  <span>{data.metrics.pairedIntervals} of {data.metrics.expectedIntervals} expected intervals matched ({number(data.metrics.coveragePercent, 0)}% coverage)</span>
                  <span>Values in MW · {data.resolutionMinutes}-minute forecast cadence</span>
                </div>
              </section>

              <section className="panel table-panel">
                <div className="panel-heading table-heading">
                  <div><div className="panel-kicker">INTERVAL DETAIL</div><h2>Forecast checkpoints</h2></div>
                  <span className="record-count">{data.points.length} intervals</span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead><tr><th>DELIVERY TIME (UK)</th><th>FORECAST ISSUE (UK)</th><th>FORECAST</th><th>ACTUAL</th><th>ERROR</th></tr></thead>
                    <tbody>
                      {data.points.map((point) => (
                        <tr key={point.startTime}>
                          <td className="time-cell">{londonTime(point.startTime, { weekday: "short", hour: "2-digit", minute: "2-digit" })}</td>
                          <td>{londonTime(point.publishTime, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</td>
                          <td>{number(point.forecastMw)} <small>MW</small></td>
                          <td>{point.actualMw === null ? "—" : <>{number(point.actualMw)} <small>MW</small></>}</td>
                          <td className={point.errorMw === null ? "" : point.errorMw > 0 ? "error-positive" : "error-negative"}>{point.errorMw === null ? "—" : `${point.errorMw > 0 ? "+" : ""}${number(point.errorMw)} MW`}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <footer className="methodology">
                <span><b>Method</b> · MAE, RMSE and bias use matched intervals. WAPE = sum of absolute errors ÷ sum of actual generation.</span>
                <span>Source: Elexon BMRS FUELHH &amp; WINDFOR · Pilot decision cutoff: 10:00 UK.</span>
              </footer>
            </>
          )}

          <div className="scope-note"><span className="scope-mark">i</span><span>January 2026 pilot · National wind generation only · No demand, prices, or other generation sources included.</span></div>
        </div>
      </main>
    </div>
  );
}

export default App;
