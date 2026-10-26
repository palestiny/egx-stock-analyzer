import "./TechnicalIndicatorPanel.css";

const SERIES = [
  { key: "close", label: "Close", color: "#172033" },
  { key: "sma_20", label: "SMA 20", color: "#2563eb" },
  { key: "sma_50", label: "SMA 50", color: "#0f766e" },
  { key: "sma_200", label: "SMA 200", color: "#b45309" },
];

function formatValue(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  return Number(value).toFixed(2);
}

function IndicatorChart({ points }) {
  const values = points.flatMap((point) =>
    SERIES.map(({ key }) => point[key]).filter(
      (value) => value != null && Number.isFinite(Number(value)),
    ).map(Number),
  );
  if (points.length === 0 || values.length === 0) {
    return <p className="muted">No indicator history is available yet. Run a fresh analysis after loading enough price bars.</p>;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const width = 900;
  const height = 260;
  const padding = { top: 14, right: 18, bottom: 24, left: 18 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  function polyline(key) {
    return points
      .map((point, index) => {
        const value = point[key];
        if (value == null || !Number.isFinite(Number(value))) return null;
        const x = padding.left + (points.length === 1 ? plotWidth / 2 : index * plotWidth / (points.length - 1));
        const y = padding.top + ((max - Number(value)) / spread) * plotHeight;
        return x + "," + y;
      })
      .filter(Boolean)
      .join(" ");
  }

  return (
    <div className="indicator-chart-wrap">
      <svg
        className="indicator-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Closing price with SMA 20, SMA 50 and SMA 200"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = padding.top + ratio * plotHeight;
          return <line key={ratio} x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke="#e5eaf2" strokeWidth="1" />;
        })}
        {SERIES.map(({ key, label, color }) => (
          <polyline
            key={key}
            points={polyline(key)}
            fill="none"
            stroke={color}
            strokeWidth={key === "close" ? "2.4" : "1.8"}
            strokeLinejoin="round"
            strokeLinecap="round"
            aria-label={label}
          />
        ))}
      </svg>
      <div className="indicator-legend">
        {SERIES.map(({ key, label, color }) => (
          <span key={key}><i style={{ backgroundColor: color }} />{label}</span>
        ))}
      </div>
    </div>
  );
}

export function TechnicalIndicatorPanel({ history, loading, error }) {
  const points = history?.points ?? [];
  const latest = points.at(-1);

  return (
    <section className="panel history-panel" aria-label="technical indicator history">
      <p className="eyebrow">TECHNICAL INTELLIGENCE</p>
      <h3>Price & indicator history</h3>
      {loading && <p role="status" className="muted">Loading technical indicator history...</p>}
      {error && <p role="alert" className="error-message">{error.message || "Technical indicator history is unavailable."}</p>}
      {!loading && !error && history?.available === false && (
        <p className="muted">This saved analysis predates indicator-history storage. Run a fresh analysis to generate chart data.</p>
      )}
      {!loading && !error && history?.available && (
        <>
          <p className="muted">{history.returned_points} of {history.total_points} points · {history.methodology_version}</p>
          <IndicatorChart points={points} />
          <div className="metrics-grid indicator-metrics">
            <div className="metric"><span className="metric-label">RSI (14)</span><strong>{formatValue(latest?.rsi_14)}</strong></div>
            <div className="metric"><span className="metric-label">MACD Histogram</span><strong>{formatValue(latest?.macd_histogram)}</strong></div>
            <div className="metric"><span className="metric-label">ATR (14)</span><strong>{formatValue(latest?.atr_14)}</strong></div>
            <div className="metric"><span className="metric-label">ADX (14)</span><strong>{formatValue(latest?.adx_14)}</strong></div>
          </div>
          <div className="detail-row">
            <span>Latest candle evidence</span>
            <strong>{latest?.candlestick_patterns?.length ? latest.candlestick_patterns.join(", ") : "No recognized pattern"}</strong>
          </div>
          <p className="muted indicator-note">Indicators are descriptive evidence, not standalone buy/sell instructions. Missing values mean the selected history does not yet contain the required warm-up period.</p>
        </>
      )}
    </section>
  );
}
