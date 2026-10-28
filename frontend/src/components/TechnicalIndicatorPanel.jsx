import "./TechnicalIndicatorPanel.css";

const SERIES = [
  { key: "close", label: "Close", color: "#172033" },
  { key: "sma_20", label: "SMA 20", color: "#2563eb" },
  { key: "sma_50", label: "SMA 50", color: "#0f766e" },
  { key: "sma_200", label: "SMA 200", color: "#b45309" },
  { key: "ema_20", label: "EMA 20", color: "#7c3aed" },
  { key: "ema_50", label: "EMA 50", color: "#be185d" },
  { key: "ema_200", label: "EMA 200", color: "#64748b" },
  { key: "bollinger_upper", label: "Bollinger upper", color: "#0891b2" },
  { key: "bollinger_lower", label: "Bollinger lower", color: "#0e7490" },
];

const DETAIL_METRICS = [
  ["EMA 9", "ema_9"],
  ["EMA 20", "ema_20"],
  ["EMA 50", "ema_50"],
  ["EMA 200", "ema_200"],
  ["RSI (14)", "rsi_14"],
  ["MACD line", "macd_line"],
  ["MACD signal", "macd_signal"],
  ["MACD histogram", "macd_histogram"],
  ["Bollinger upper", "bollinger_upper"],
  ["Bollinger middle", "bollinger_middle"],
  ["Bollinger lower", "bollinger_lower"],
  ["ATR (14)", "atr_14"],
  ["Stochastic %K", "stochastic_k_14"],
  ["Stochastic %D", "stochastic_d_3"],
  ["CCI (20)", "cci_20"],
  ["OBV", "obv"],
  ["MFI (14)", "mfi_14"],
  ["+DI (14)", "plus_di_14"],
  ["-DI (14)", "minus_di_14"],
  ["ADX (14)", "adx_14"],
  ["Ichimoku conversion", "ichimoku_conversion_9"],
  ["Ichimoku base", "ichimoku_base_26"],
  ["Ichimoku span A (unshifted)", "ichimoku_span_a_unshifted"],
  ["Ichimoku span B (unshifted)", "ichimoku_span_b_unshifted"],
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
        aria-label="Closing price with SMA, EMA and Bollinger overlays"
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
            strokeWidth={key === "close" ? "2.4" : "1.4"}
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

function PriceStructureEvidence({ latest }) {
  const swings = latest?.confirmed_swings ?? [];
  const retracements = latest?.fibonacci_retracements ?? [];
  const extensions = latest?.fibonacci_extensions ?? [];

  return (
    <div className="indicator-structure">
      <h4>Confirmed price structure</h4>
      <div className="detail-row">
        <span>Newly confirmed swing points</span>
        <strong>
          {swings.length
            ? swings.map(([kind, price]) => `${kind.toUpperCase()} ${formatValue(price)}`).join(" · ")
            : "No new swing confirmed on this bar"}
        </strong>
      </div>
      <div className="detail-row">
        <span>Fibonacci retracement</span>
        <strong>{latest?.fibonacci_direction ?? "Insufficient confirmed swing anchors"}</strong>
      </div>
      {retracements.length > 0 && (
        <ul className="fibonacci-levels">
          {retracements.map(([ratio, price]) => (
            <li key={String(ratio)}><span>{(Number(ratio) * 100).toFixed(1)}%</span><strong>{formatValue(price)}</strong></li>
          ))}
        </ul>
      )}
      <div className="detail-row">
        <span>Fibonacci extension</span>
        <strong>{latest?.fibonacci_extension_direction ?? "Requires three confirmed alternating swings"}</strong>
      </div>
      {extensions.length > 0 && (
        <ul className="fibonacci-levels">
          {extensions.map(([ratio, price]) => (
            <li key={String(ratio)}><span>{(Number(ratio) * 100).toFixed(1)}%</span><strong>{formatValue(price)}</strong></li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ElliottWaveEvidence({ latest }) {
  const candidates = latest?.elliott_candidates ?? [];
  const corrections = latest?.elliott_corrections ?? [];

  return (
    <div className="indicator-structure">
      <h4>Elliott wave candidates</h4>
      {candidates.length === 0 ? (
        <p className="muted">No confirmed six-pivot impulse candidate is available for this bar.</p>
      ) : (
        <ul className="fibonacci-levels">
          {candidates.map((item) => (
            <li key={`${item.start_index}-${item.end_index}-${item.candidate.direction}`}>
              <span>
                {item.candidate.direction.toUpperCase()} · pivots {item.start_index}–{item.end_index}
                <br />
                {item.candidate.points.map(formatValue).join(" → ")}
                {item.rule_violations.length > 0 && (
                  <small> · Rule issues: {item.rule_violations.join(", ")}</small>
                )}
                {item.warnings.length > 0 && (
                  <small> · Warnings: {item.warnings.join(", ")}</small>
                )}
              </span>
              <strong>
                {item.is_rule_consistent ? "Rule-consistent" : "Rule violations"}
                <br />
                Invalidation {formatValue(item.wave_two_invalidation_price)}
              </strong>
            </li>
          ))}
        </ul>
      )}
      <h4>ABC zigzag correction candidates</h4>
      {corrections.length === 0 ? (
        <p className="muted">No confirmed four-pivot ABC zigzag candidate is available for this bar.</p>
      ) : (
        <ul className="fibonacci-levels">
          {corrections.map((item) => (
            <li key={`${item.start_index}-${item.end_index}-${item.candidate.direction}`}>
              <span>
                {item.candidate.direction.toUpperCase()} · pivots {item.start_index}–{item.end_index}
                <br />
                {item.candidate.points.map(formatValue).join(" → ")}
                {item.rule_violations.length > 0 && (
                  <small> · Rule issues: {item.rule_violations.join(", ")}</small>
                )}
              </span>
              <strong>
                {item.is_rule_consistent ? "Rule-consistent" : "Rule violations"}
                <br />
                B-wave origin boundary {formatValue(item.wave_b_origin_boundary_price)}
              </strong>
            </li>
          ))}
        </ul>
      )}
      <p className="muted indicator-note">
        Impulse and ABC zigzag counts are mechanical candidates based on confirmed swings, not probabilities or forecasts. Flat, triangle, and complex corrections are not inferred.
      </p>
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
            {DETAIL_METRICS.map(([label, key]) => (
              <div className="metric" key={key}><span className="metric-label">{label}</span><strong>{formatValue(latest?.[key])}</strong></div>
            ))}
          </div>
          <PriceStructureEvidence latest={latest} />
          <ElliottWaveEvidence latest={latest} />
          <div className="detail-row">
            <span>Latest candle evidence</span>
            <strong>{latest?.candlestick_patterns?.length ? latest.candlestick_patterns.join(", ") : "No recognized pattern"}</strong>
          </div>
          <p className="muted indicator-note">Indicators are descriptive evidence, not standalone buy/sell instructions. Missing values mean the selected history does not yet contain the required warm-up period. Fibonacci levels use explicitly identified, confirmed swing anchors; they are not forecasts.</p>
        </>
      )}
    </section>
  );
}
