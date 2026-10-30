import { BAND_COLOR, CATEGORY_ICONS, catLabel } from "../utils";

/**
 * Transparent AI explainability card.
 * Clearly articulates why a ticket was scored at a particular priority level.
 */
export default function ResultCard({ r }) {
  if (!r) return null;

  return (
    <div className="card result-card-elevated">
      {/* Header with Priority Pill and Category */}
      <div className="result-card-header">
        <div className="result-badges">
          <span
            className="priority-badge-lg"
            style={{ backgroundColor: BAND_COLOR[r.priority_band] || "#3b82f6" }}
          >
            {r.priority_band} Priority · {r.priority_score}/100
          </span>
          <span className="category-chip">
            {CATEGORY_ICONS[r.category] || "📌"} {catLabel(r.category)}
          </span>
        </div>
        <span className="engine-badge">
          {r.ai_mode === "llm" ? "⚡ Groq LLM Triage" : "⚙️ Rule-Based Triage"}
        </span>
      </div>

      {/* Summary */}
      <h3 className="result-summary">{r.summary || r.text}</h3>

      {/* Additive Scoring Breakdown */}
      <div className="reasons-section">
        <h4 className="reasons-heading">Transparent Priority Accounting</h4>
        <div className="reasons-grid">
          {(r.reasons && r.reasons.length > 0 ? r.reasons : ["Standard baseline priority"]).map((reason, idx) => (
            <div key={idx} className="reason-item">
              <span className="reason-check">✓</span>
              <span>{reason}</span>
            </div>
          ))}
        </div>
        <p className="reasons-note">
          Every point is accounted for deterministically. The AI extracts situational severity signals; the numerical score is computed by transparent municipal business rules.
        </p>
      </div>

      {/* Duplicate Detection Status */}
      <div className="duplicate-status-box">
        <div className="dup-header">
          <span className="dup-icon">🔗</span>
          <span className="dup-title">Deduplication Intelligence</span>
        </div>
        {r.duplicate_of ? (
          <p className="dup-text">
            Linked to primary incident <b>#{r.duplicate_of}</b>
            {r.duplicate_of_summary ? ` ("${r.duplicate_of_summary}")` : ""} with similarity score{" "}
            <b>{r.duplicate_score}</b>. Stored as duplicate; receives all status updates automatically.
          </p>
        ) : (
          <p className="dup-text">
            No existing duplicate detected within 150m. Established as a new primary report.
            {r.linked && r.linked.length > 0
              ? ` (${r.linked.length} later reports have linked to this issue).`
              : ""}
          </p>
        )}
      </div>

      {/* Hotspot Association */}
      {r.cluster && (
        <div className="hotspot-mention-box">
          <span className="hotspot-tag">🔥 Incident Hotspot</span>
          <p>
            Part of a {r.cluster.report_count}-incident cluster in <b>{r.cluster.ward}</b> Ward.
          </p>
          <div className="mini-brief">{r.cluster.brief}</div>
        </div>
      )}
    </div>
  );
}
