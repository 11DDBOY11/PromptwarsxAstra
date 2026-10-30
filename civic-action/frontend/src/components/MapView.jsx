import { useEffect, useState } from "react";
import { api } from "../api";
import { BAND_COLOR, CATEGORY_ICONS, catLabel } from "../utils";

/**
 * Fast, lightweight Hotspots Hub (Zero Map Latency).
 * Eliminates external map tile loading delays while providing clear geographic cluster intelligence.
 */
export default function MapView({ version }) {
  const [clusters, setClusters] = useState([]);
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterWard, setFilterWard] = useState("all");

  useEffect(() => {
    setLoading(true);
    Promise.all([api.list(), api.clusters()])
      .then(([reps, cls]) => {
        setReports(reps);
        setClusters(cls);
        if (cls.length > 0) setSelected(cls[0]);
      })
      .catch((err) => console.error("Error loading hotspots:", err))
      .finally(() => setLoading(false));
  }, [version]);

  const wards = Array.from(new Set(clusters.map((c) => c.ward)));
  const filteredClusters =
    filterWard === "all" ? clusters : clusters.filter((c) => c.ward === filterWard);

  const totalClusteredReports = clusters.reduce((sum, c) => sum + (c.report_count || 0), 0);

  if (loading) {
    return (
      <div className="card loading-box">
        <span className="spinner"></span>
        <p>Loading civic hotspots data…</p>
      </div>
    );
  }

  return (
    <section className="fade-in">
      {/* Top Metric Header */}
      <div className="hotspots-header-banner">
        <div>
          <h2>Civic Hotspots & Action Briefs</h2>
          <p className="text-muted">
            DBSCAN clusters grouping 3+ related civic complaints within 200m radius. Instant dispatch briefs for field teams.
          </p>
        </div>
        <div className="hotspots-kpis">
          <div className="kpi-mini">
            <span className="kpi-num">{clusters.length}</span>
            <span className="kpi-lbl">Active Hotspots</span>
          </div>
          <div className="kpi-mini">
            <span className="kpi-num">{totalClusteredReports}</span>
            <span className="kpi-lbl">Issues Clustered</span>
          </div>
          <div className="kpi-mini">
            <span className="kpi-num">{wards.length}</span>
            <span className="kpi-lbl">Wards Impacted</span>
          </div>
        </div>
      </div>

      {/* Ward Filter Pills */}
      {wards.length > 0 && (
        <div className="filter-bar">
          <span className="filter-label">Filter by Ward:</span>
          <button
            type="button"
            className={`filter-pill ${filterWard === "all" ? "active" : ""}`}
            onClick={() => setFilterWard("all")}
          >
            All Wards ({clusters.length})
          </button>
          {wards.map((w) => (
            <button
              key={w}
              type="button"
              className={`filter-pill ${filterWard === w ? "active" : ""}`}
              onClick={() => setFilterWard(w)}
            >
              {w} ({clusters.filter((c) => c.ward === w).length})
            </button>
          ))}
        </div>
      )}

      {/* Main Content Layout */}
      {filteredClusters.length === 0 ? (
        <div className="card empty-state">
          <span className="empty-icon">✨</span>
          <h3>No Active Hotspots</h3>
          <p className="text-muted">
            All issues in this area are isolated or resolved. No density thresholds currently exceeded.
          </p>
        </div>
      ) : (
        <div className="hotspots-grid">
          {filteredClusters.map((c) => {
            const isSelected = selected?.id === c.id;
            return (
              <div
                key={c.id}
                className={`card hotspot-card ${isSelected ? "selected" : ""}`}
                onClick={() => setSelected(c)}
              >
                <div className="hotspot-top-bar">
                  <div className="ward-badge">
                    📍 {c.ward} Ward
                  </div>
                  <span className="badge-count">
                    {c.report_count} Reports ({c.radius_m}m radius)
                  </span>
                </div>

                {/* Categories Breakdown */}
                <div className="hotspot-categories">
                  {Object.entries(c.categories || {}).map(([cat, count]) => (
                    <span key={cat} className="category-pill-sm">
                      {CATEGORY_ICONS[cat] || "📌"} {count} {catLabel(cat)}
                    </span>
                  ))}
                </div>

                {/* AI Action Brief */}
                <div className="brief-callout">
                  <div className="brief-header">
                    <span className="brief-title">⚡ AI Action Brief for Dispatch</span>
                    <span className="ai-mode-tag">
                      {c.ai_mode === "llm" ? "Groq LLM" : "Rules Engine"}
                    </span>
                  </div>
                  <p className="brief-body">{c.brief}</p>
                </div>

                {/* Clustered Issues List */}
                {c.members && c.members.length > 0 && (
                  <div className="hotspot-members-section">
                    <div className="members-title">
                      Reports included in this incident bundle:
                    </div>
                    <div className="members-list">
                      {c.members.map((m) => (
                        <div key={m.id} className="member-item">
                          <span
                            className="priority-indicator"
                            style={{ background: BAND_COLOR[m.priority_band] || "#94a3b8" }}
                          />
                          <span className="member-id">#{m.id}</span>
                          <span className="member-cat">[{catLabel(m.category)}]</span>
                          <span className="member-summary">{m.summary}</span>
                          <span className="member-status">{m.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
