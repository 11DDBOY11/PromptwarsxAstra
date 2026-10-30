import { useEffect, useState } from "react";
import { api } from "../api";
import { getTranslation } from "../i18n";
import { getOfflineQueue, getSessionReports, saveReportToSession } from "../offlineQueue";
import { CATEGORY_ICONS, STATUS_COLOR, catLabel, fmt } from "../utils";

export default function TrackView({ lang, initialCode, version }) {
  const [code, setCode] = useState(initialCode || "");
  const [ticket, setTicket] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [deviceReports, setDeviceReports] = useState([]);
  const [offlinePending, setOfflinePending] = useState([]);

  const t = (k) => getTranslation(lang, k);

  const fetchTrack = (searchCode) => {
    if (!searchCode || !searchCode.trim()) return;
    setLoading(true);
    setErr("");
    api.track(searchCode.trim().toUpperCase())
      .then((data) => {
        setTicket(data);
        saveReportToSession(data);
        setErr("");
      })
      .catch((e) => {
        setTicket(null);
        setErr(e.message || (lang === "kn" ? "ಈ ಕೋಡ್‌ನ ಯಾವುದೇ ದೂರು ಲಭ್ಯವಿಲ್ಲ." : "No report found with that tracking code."));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    setDeviceReports(getSessionReports());
    setOfflinePending(getOfflineQueue());
  }, [version]);

  useEffect(() => {
    if (initialCode && initialCode !== "my-reports") {
      setCode(initialCode);
      fetchTrack(initialCode);
    }
  }, [initialCode]);

  useEffect(() => {
    if (ticket?.tracking_code) {
      fetchTrack(ticket.tracking_code);
    }
  }, [version]);

  const currentStep = ticket?.statuses?.indexOf(ticket?.status) ?? -1;

  return (
    <section className="fade-in">
      {/* Search Bar Card */}
      <div className="card track-search-card">
        <div className="badge-pill citizen-badge">{t("citizen")}</div>
        <h2>{t("trackHeader")}</h2>
        <p className="text-muted">{t("trackSub")}</p>

        <form
          className="track-search-form"
          onSubmit={(e) => {
            e.preventDefault();
            fetchTrack(code);
          }}
        >
          <div className="track-input-wrapper">
            <span className="track-input-prefix">🔍</span>
            <input
              type="text"
              className="track-input"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder={t("trackInputPlaceholder")}
              maxLength={12}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary track-btn" disabled={loading}>
            {loading ? "…" : t("checkStatusBtn")}
          </button>
        </form>
      </div>

      {err && (
        <div className="alert-box error-alert fade-in" style={{ marginTop: "14px" }}>
          <b>{lang === "kn" ? "ದೂರು ಕಂಡುಬಂದಿಲ್ಲ:" : "Report Not Found:"}</b> {err}
        </div>
      )}

      {/* Ticket Details & Timeline */}
      {ticket && (
        <div className="card ticket-display-card fade-in">
          <div className="ticket-top-banner">
            <div>
              <span className="ticket-code-tag">{ticket.tracking_code}</span>
              <h3 className="ticket-summary-title">{ticket.summary}</h3>
              <div className="ticket-meta-info">
                <span>{CATEGORY_ICONS[ticket.category] || "📌"} {t(`cat_${ticket.category}`) || catLabel(ticket.category)}</span>
                <span>·</span>
                <span>📍 {ticket.address || "Area location"}</span>
                <span>·</span>
                <span>🕒 {fmt(ticket.created_at)}</span>
              </div>
            </div>
            <div className="ticket-status-bubble">
              <span
                className="status-chip-lg"
                style={{
                  backgroundColor: `${STATUS_COLOR[ticket.status] || "#64748b"}20`,
                  color: STATUS_COLOR[ticket.status] || "#64748b",
                  borderColor: STATUS_COLOR[ticket.status] || "#64748b",
                }}
              >
                ● {ticket.status}
              </span>
            </div>
          </div>

          {/* Stepper Progress Bar */}
          <div className="stepper-wrapper">
            <div className="stepper-track">
              {ticket.statuses.map((stepName, idx) => {
                const isCompleted = idx < currentStep;
                const isCurrent = idx === currentStep;
                return (
                  <div
                    key={stepName}
                    className={`step-node ${isCompleted ? "completed" : ""} ${isCurrent ? "current" : ""}`}
                  >
                    <div className="step-circle">
                      {isCompleted ? "✓" : idx + 1}
                    </div>
                    <span className="step-label">{stepName}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Assignment & Duplicate Callout */}
          <div className="ticket-callouts-grid">
            {ticket.assignee && (
              <div className="callout-box assignee-box">
                <span className="callout-icon">👷</span>
                <div>
                  <span className="callout-label">{lang === "kn" ? "ನಿಯೋಜಿತ ಸಿಬ್ಬಂದಿ" : "Field Assignment"}</span>
                  <p className="callout-value">{ticket.assignee}</p>
                </div>
              </div>
            )}

            {ticket.linked_to_existing && (
              <div className="callout-box duplicate-box">
                <span className="callout-icon">🔗</span>
                <div>
                  <span className="callout-label">{lang === "kn" ? "ಸಂಬಂಧಿತ ದೂರುಗಳು" : "Deduplicated Incident"}</span>
                  <p className="callout-sub">
                    {lang === "kn"
                      ? "ನಿಮ್ಮ ದೂರು ಅದೇ ಸ್ಥಳದ ಹತ್ತಿರದ ದೂರಿಗೆ ಹೊಂದಿಕೆಯಾಗಿದೆ. ಎಲ್ಲಾ ಪ್ರಗತಿ ಅಪ್‌ಡೇಟ್‌ಗಳು ತಕ್ಷಣ ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತವೆ."
                      : "Your report matched a nearby active incident. You receive all progress updates in real-time."}
                  </p>
                </div>
              </div>
            )}
          </div>

          {ticket.image_url && (
            <div className="ticket-photo-section">
              <h4 className="timeline-heading">{lang === "kn" ? "ದಾಖಲಿಸಿದ ಫೋಟೋ ಸಾಕ್ಷ್ಯ" : "Submitted Photographic Evidence"}</h4>
              <img src={ticket.image_url} alt="Civic complaint photo" className="ticket-photo" />
            </div>
          )}

          {/* Timeline Stream */}
          <div className="timeline-section">
            <h4 className="timeline-heading">{lang === "kn" ? "ಪರಿಹಾರ ಪ್ರಗತಿ ಇತಿಹಾಸ" : "Resolution Activity Timeline"}</h4>
            <div className="timeline-stream">
              {[...(ticket.events || [])].reverse().map((event, idx) => (
                <div key={idx} className="timeline-card">
                  <div className="timeline-point" />
                  <div className="timeline-card-content">
                    <div className="timeline-status-row">
                      <span className="timeline-status-title">{event.status}</span>
                      <span className="timeline-time">{fmt(event.at)}</span>
                    </div>
                    {event.assignee && (
                      <div className="timeline-assignee">{event.assignee}</div>
                    )}
                    {event.note && (
                      <p className="timeline-note">"{event.note}"</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Device History: My Reports Wallet (Solves Lost Code problem) */}
      <div className="card my-reports-wallet-card" style={{ marginTop: "24px" }}>
        <div className="card-title-row">
          <div>
            <h3>📱 {t("myReportsTitle")}</h3>
            <p className="text-muted small">{t("myReportsSub")}</p>
          </div>
          <span className="chip">{deviceReports.length} {lang === "kn" ? "ದೂರುಗಳು" : "saved"}</span>
        </div>

        {/* Offline Queued Items (Ghat/Forest region pending sync) */}
        {offlinePending.length > 0 && (
          <div className="alert-box info-alert" style={{ marginTop: "12px" }}>
            <b>📶 {offlinePending.length} {t("pendingOfflineCount")}:</b>
            <div style={{ marginTop: "4px" }}>
              {offlinePending.map((item) => (
                <div key={item.id} className="offline-queue-item-sm">
                  <span>⏳ "{item.text}" ({item.address})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {deviceReports.length === 0 ? (
          <div className="empty-sub-state">
            <p className="text-muted">{t("noReportsYet")}</p>
          </div>
        ) : (
          <div className="device-reports-grid">
            {deviceReports.map((r) => (
              <div
                key={r.tracking_code}
                className={`device-report-card ${ticket?.tracking_code === r.tracking_code ? "active-selected" : ""}`}
                onClick={() => {
                  setCode(r.tracking_code);
                  fetchTrack(r.tracking_code);
                }}
              >
                <div className="report-card-top">
                  <span className="report-card-code">{r.tracking_code}</span>
                  <span
                    className="status-pill-mini"
                    style={{
                      background: `${STATUS_COLOR[r.status] || "#64748b"}20`,
                      color: STATUS_COLOR[r.status] || "#64748b",
                    }}
                  >
                    {r.status}
                  </span>
                </div>
                <div className="report-card-sum">{r.summary || "Civic Complaint"}</div>
                <div className="report-card-meta">
                  <span>{CATEGORY_ICONS[r.category] || "📌"} {t(`cat_${r.category}`) || catLabel(r.category)}</span>
                  <span>·</span>
                  <span>{fmt(r.created_at)}</span>
                </div>
                <button type="button" className="btn-view-ticket">
                  {t("viewReportBtn")} →
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
