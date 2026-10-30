import { useEffect, useState } from "react";
import { api } from "../api";
import { BAND_COLOR, CATEGORY_ICONS, STATUS_COLOR, ago, catLabel, fmt } from "../utils";
import ResultCard from "./ResultCard";

function DetailView({ id, statuses, onChanged }) {
  const [r, setR] = useState(null);
  const [status, setStatus] = useState("");
  const [assignee, setAssignee] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.detail(id).then((d) => {
      setR(d);
      setStatus(d.status);
      setAssignee(d.assignee || "");
    });
  }, [id]);

  if (!r) {
    return (
      <div className="detail-loading">
        <span className="spinner"></span> Loading report details…
      </div>
    );
  }

  const act = (promise) => {
    setSaving(true);
    setErr("");
    promise
      .then((d) => {
        setR(d);
        setStatus(d.status);
        setNote("");
        onChanged();
      })
      .catch((e) => setErr(e.message || "Action failed"))
      .finally(() => setSaving(false));
  };

  return (
    <div className="queue-detail-panel fade-in">
      <div className="detail-description-card">
        <span className="detail-label">Citizen Complaint Text:</span>
        <p className="detail-text">"{r.text}"</p>
        {r.image_url && (
          <div className="detail-photo-wrapper">
            <span className="detail-label">Attached Photo Evidence:</span>
            <img src={r.image_url} alt="Civic complaint photo" className="detail-photo" />
          </div>
        )}
        <div className="detail-meta-row">
          <span>📍 {r.address || "No specific address"}</span>
          <span>🏛️ {r.ward} Ward</span>
          <span>🕒 {fmt(r.created_at)}</span>
          <span>🏷️ Tracking: <b>{r.tracking_code}</b></span>
        </div>
      </div>

      {/* AI Explanation */}
      <ResultCard r={r} />

      {/* Linked Duplicates Section */}
      {r.linked && r.linked.length > 0 && (
        <div className="card linked-duplicates-card">
          <h4>🔗 Subordinate Duplicates ({r.linked.length})</h4>
          <p className="small text-muted">
            These citizen reports matched this incident and will automatically mirror status updates.
          </p>
          <div className="linked-list">
            {r.linked.map((l) => (
              <div key={l.id} className="linked-item">
                <div className="linked-info">
                  <b>#{l.id}</b> {l.summary}
                  <span className="badge-similarity">Similarity: {l.duplicate_score}</span>
                </div>
                <button
                  type="button"
                  className="btn-unlink"
                  onClick={() => act(api.unlink(l.id).then(() => api.detail(id)))}
                >
                  Unlink as Distinct
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* If this report itself was linked to another */}
      {r.duplicate_of && (
        <div className="card alert-box info-alert">
          <p>This report is currently linked to primary ticket <b>#{r.duplicate_of}</b>.</p>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => act(api.unlink(r.id))}
          >
            Unlink & Review Independently
          </button>
        </div>
      )}

      {/* Status Workflow Action Box */}
      <div className="card status-action-card">
        <h4>🛠️ Update Municipal Status & Crew Assignment</h4>
        <div className="status-form-grid">
          <div className="form-group">
            <label className="form-label">Workflow Status</label>
            <select
              className="form-control"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {statuses.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Assigned Field Crew / Officer</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Ward 4 Pothole Team / Officer Shetty"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
            />
          </div>
        </div>

        <div className="form-group" style={{ marginTop: "10px" }}>
          <label className="form-label">Note for Citizen Timeline (Optional)</label>
          <input
            type="text"
            className="form-control"
            placeholder="e.g. Crew inspected site; road patch materials dispatched."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={300}
          />
        </div>

        {err && <div className="alert-box error-alert">{err}</div>}

        <div className="action-buttons-right">
          <button
            type="button"
            className="btn btn-primary"
            disabled={saving}
            onClick={() => act(api.setStatus(id, { status, assignee, note }))}
          >
            {saving ? "Saving…" : "Save Workflow Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Queue({ statuses, version, onChanged }) {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(null);
  const [showDone, setShowDone] = useState(false);
  const [filterBand, setFilterBand] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.list()
      .then(setRows)
      .finally(() => setLoading(false));
  }, [version]);

  const filtered = rows.filter((r) => {
    if (!showDone && r.status === "Resolved") return false;
    if (filterBand !== "all" && r.priority_band !== filterBand) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchText = (r.text || "").toLowerCase();
      const matchSum = (r.summary || "").toLowerCase();
      const matchWard = (r.ward || "").toLowerCase();
      const matchCode = (r.tracking_code || "").toLowerCase();
      if (!matchText.includes(q) && !matchSum.includes(q) && !matchWard.includes(q) && !matchCode.includes(q)) {
        return false;
      }
    }
    return true;
  });

  return (
    <section className="fade-in">
      {/* Top Header */}
      <div className="queue-header">
        <div>
          <h2>Municipal Priority Queue</h2>
          <p className="text-muted">
            Triage stream ordered by explainable urgency score. Duplicates are bundled with their primary complaint.
          </p>
        </div>
        <div className="queue-controls">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showDone}
              onChange={(e) => setShowDone(e.target.checked)}
            />
            <span>Include Resolved</span>
          </label>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="queue-filter-row">
        <div className="band-filters">
          <button
            type="button"
            className={`band-filter-btn ${filterBand === "all" ? "active" : ""}`}
            onClick={() => setFilterBand("all")}
          >
            All ({rows.filter((r) => showDone || r.status !== "Resolved").length})
          </button>
          {["Critical", "High", "Medium", "Low"].map((b) => (
            <button
              key={b}
              type="button"
              className={`band-filter-btn ${filterBand === b ? "active" : ""}`}
              onClick={() => setFilterBand(b)}
            >
              <span className="dot" style={{ background: BAND_COLOR[b] }} />
              {b} ({rows.filter((r) => (showDone || r.status !== "Resolved") && r.priority_band === b).length})
            </button>
          ))}
        </div>

        <div className="search-box">
          <input
            type="text"
            className="form-control form-control-sm"
            placeholder="Search keyword, ward, or tracking code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Reports List */}
      {loading ? (
        <div className="card loading-box">
          <span className="spinner"></span>
          <p>Loading queue…</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card empty-state">
          <span className="empty-icon">🎉</span>
          <h3>No reports matching your criteria</h3>
          <p className="text-muted">All civic reports in this view have been resolved or filtered out.</p>
        </div>
      ) : (
        <div className="queue-list">
          {filtered.map((r) => {
            const isOpen = open === r.id;
            return (
              <div key={r.id} className={`card queue-card ${isOpen ? "expanded" : ""}`}>
                {/* Accessible Clickable Card Header */}
                <button
                  type="button"
                  className="queue-card-header"
                  onClick={() => setOpen(isOpen ? null : r.id)}
                  aria-expanded={isOpen}
                >
                  <div className="queue-card-left">
                    <span
                      className="score-badge"
                      style={{ backgroundColor: BAND_COLOR[r.priority_band] || "#3b82f6" }}
                    >
                      {r.priority_score}
                    </span>
                    <div className="queue-card-titles">
                      <div className="queue-title-row">
                        <span className="queue-title">{r.summary || r.text}</span>
                        {r.linked_count > 0 && (
                          <span className="badge-linked">+{r.linked_count} duplicates</span>
                        )}
                        {r.cluster_id && (
                          <span className="badge-hotspot">🔥 Hotspot</span>
                        )}
                      </div>
                      <div className="queue-meta">
                        <span>#{r.id}</span>
                        <span>·</span>
                        <span>{CATEGORY_ICONS[r.category] || "📌"} {catLabel(r.category)}</span>
                        <span>·</span>
                        <span>📍 {r.ward} Ward</span>
                        <span>·</span>
                        <span>🕒 {ago(r.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="queue-card-right">
                    <span
                      className="status-chip-styled"
                      style={{
                        backgroundColor: `${STATUS_COLOR[r.status] || "#64748b"}18`,
                        color: STATUS_COLOR[r.status] || "#64748b",
                        borderColor: `${STATUS_COLOR[r.status] || "#64748b"}40`,
                      }}
                    >
                      {r.status}
                    </span>
                    <span className="expand-indicator">{isOpen ? "▲" : "▼"}</span>
                  </div>
                </button>

                {/* Detail View when Expanded */}
                {isOpen && (
                  <DetailView
                    id={r.id}
                    statuses={statuses}
                    onChanged={onChanged}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
