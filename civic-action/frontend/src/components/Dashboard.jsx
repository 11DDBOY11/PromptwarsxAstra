import { useEffect, useState } from "react";
import { api } from "../api";
import { BAND_COLOR, CATEGORY_ICONS, catLabel } from "../utils";

const ProgressBar = ({ label, icon, value, max, color = "#0284c7" }) => {
  const percent = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="progress-item">
      <div className="progress-label-row">
        <span className="progress-name">
          {icon && <span className="progress-icon">{icon}</span>}
          {label}
        </span>
        <span className="progress-val">{value} ({percent}%)</span>
      </div>
      <div className="progress-track">
        <div
          className="progress-fill"
          style={{ width: `${percent}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
};

export default function Dashboard({ version }) {
  const [stats, setStats] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([api.stats(), api.clusters()])
      .then(([s, cls]) => {
        setStats(s);
        setClusters(cls);
      })
      .catch((err) => console.error("Error loading dashboard stats:", err))
      .finally(() => setLoading(false));
  }, [version]);

  if (loading || !stats) {
    return (
      <div className="card loading-box">
        <span className="spinner"></span>
        <p>Generating civic intelligence dashboard…</p>
      </div>
    );
  }

  const sortedCats = Object.entries(stats.by_category || {}).sort((a, b) => b[1] - a[1]);
  const wards = Array.from(new Set((stats.ward_category || []).map((x) => x.ward)));
  const getCellCount = (w, c) =>
    stats.ward_category.find((x) => x.ward === w && x.category === c)?.count || 0;
  const maxCell = Math.max(1, ...(stats.ward_category || []).map((x) => x.count));
  const maxDayCount = Math.max(1, ...(stats.per_day || []).map((d) => d.count));

  return (
    <section className="fade-in">
      {/* Overview Stat Cards */}
      <div className="stats-metric-grid">
        <div className="metric-card metric-open">
          <div className="metric-header">
            <span className="metric-title">Active Grievances</span>
            <span className="metric-icon">📋</span>
          </div>
          <div className="metric-value">{stats.open}</div>
          <div className="metric-footer">Total recorded: {stats.total}</div>
        </div>

        <div className="metric-card metric-critical">
          <div className="metric-header">
            <span className="metric-title">Critical Urgency</span>
            <span className="metric-icon">🚨</span>
          </div>
          <div className="metric-value">{stats.by_band?.Critical || 0}</div>
          <div className="metric-footer">Immediate safety hazard</div>
        </div>

        <div className="metric-card metric-hotspots">
          <div className="metric-header">
            <span className="metric-title">Active Hotspots</span>
            <span className="metric-icon">🔥</span>
          </div>
          <div className="metric-value">{stats.hotspots || 0}</div>
          <div className="metric-footer">DBSCAN clusters identified</div>
        </div>

        <div className="metric-card metric-duplicates">
          <div className="metric-header">
            <span className="metric-title">Duplicates Deduplicated</span>
            <span className="metric-icon">🔗</span>
          </div>
          <div className="metric-value">{stats.duplicates_linked || 0}</div>
          <div className="metric-footer">Noise eliminated for crews</div>
        </div>
      </div>

      {/* Action Briefs Callout */}
      {clusters.length > 0 && (
        <div className="card briefs-dashboard-card">
          <div className="card-title-row">
            <h3>⚡ Hotspot Action Briefs for Municipal Dispatch</h3>
            <span className="chip chip-accent">{clusters.length} Areas</span>
          </div>
          <div className="briefs-stream">
            {clusters.slice(0, 4).map((c) => (
              <div key={c.id} className="brief-card-mini">
                <div className="brief-ward-tag">📍 {c.ward} Ward ({c.report_count} reports)</div>
                <p className="brief-text-sm">{c.brief}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Progress Bars (Priority + Categories) */}
      <div className="dashboard-two-col">
        <div className="card">
          <h3>Open Issues by Priority</h3>
          <p className="text-muted small">Additive score tiers based on safety and population impact</p>
          <div className="progress-stack" style={{ marginTop: "14px" }}>
            {["Critical", "High", "Medium", "Low"].map((band) => (
              <ProgressBar
                key={band}
                label={band}
                value={stats.by_band?.[band] || 0}
                max={stats.open}
                color={BAND_COLOR[band]}
              />
            ))}
          </div>
        </div>

        <div className="card">
          <h3>Top Complaint Categories</h3>
          <p className="text-muted small">Distribution of active issues reported by citizens</p>
          <div className="progress-stack" style={{ marginTop: "14px" }}>
            {sortedCats.slice(0, 6).map(([cat, count]) => (
              <ProgressBar
                key={cat}
                label={catLabel(cat)}
                icon={CATEGORY_ICONS[cat]}
                value={count}
                max={sortedCats[0]?.[1] || 1}
                color="#0284c7"
              />
            ))}
          </div>
        </div>
      </div>

      {/* Ward × Category Heatmap Table */}
      <div className="card">
        <h3>Ward × Category Grievance Matrix</h3>
        <p className="text-muted small">
          Darker cells pinpoint recurring localized infrastructure failures requiring systematic rehabilitation.
        </p>
        <div className="table-responsive" style={{ marginTop: "12px" }}>
          <table className="heat-table">
            <thead>
              <tr>
                <th className="heat-corner-th">Ward Name</th>
                {sortedCats.map(([c]) => (
                  <th key={c}>
                    <span className="heat-th-text">{catLabel(c)}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {wards.map((w) => (
                <tr key={w}>
                  <td className="heat-ward-cell">📍 {w}</td>
                  {sortedCats.map(([c]) => {
                    const count = getCellCount(w, c);
                    const opacity = count > 0 ? 0.15 + 0.75 * (count / maxCell) : 0;
                    return (
                      <td
                        key={c}
                        style={{
                          backgroundColor: count > 0 ? `rgba(220, 38, 38, ${opacity})` : "transparent",
                          color: count / maxCell > 0.5 ? "#ffffff" : "inherit",
                          fontWeight: count > 0 ? "700" : "normal",
                        }}
                      >
                        {count > 0 ? count : "-"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 10-Day Intake Trend */}
      {stats.per_day && stats.per_day.length > 0 && (
        <div className="card">
          <h3>Intake Trend (Past 10 Days)</h3>
          <p className="text-muted small">Daily volume of incoming citizen complaints</p>
          <div className="sparkline-container">
            {stats.per_day.map((day) => {
              const heightPercent = maxDayCount > 0 ? (day.count / maxDayCount) * 100 : 0;
              return (
                <div key={day.date} className="sparkline-col" title={`${day.date}: ${day.count} reports`}>
                  <div className="sparkline-bar-box">
                    <span className="sparkline-bar-val">{day.count}</span>
                    <div
                      className="sparkline-bar"
                      style={{ height: `${Math.max(6, heightPercent)}%` }}
                    />
                  </div>
                  <span className="sparkline-label">{day.date.slice(5)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
