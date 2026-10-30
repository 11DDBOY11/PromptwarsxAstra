import { useState } from "react";
import { api } from "../api";
import { getTranslation } from "../i18n";

const PRESET_OFFICERS = [
  {
    role: "Roads & Infrastructure (PWD)",
    name: "Inspector B. Shetty",
    email: "officer.pwd@mangaluru.gov.in",
    pass: "officer123",
  },
  {
    role: "Stormwater Drainage & Sanitation",
    name: "Engineer K. Poojary",
    email: "officer.drainage@mangaluru.gov.in",
    pass: "officer123",
  },
  {
    role: "Municipal Commissioner (Admin)",
    name: "Commissioner Rai",
    email: "officer.admin@mangaluru.gov.in",
    pass: "admin123",
  },
];

export default function OfficerLoginModal({ lang, isOpen, onClose, onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const t = (k) => getTranslation(lang, k);

  const fillPreset = (preset) => {
    setEmail(preset.email);
    setPassword(preset.pass);
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.officerLogin(email, password);
      onLoginSuccess(res.officer);
      onClose();
    } catch (err) {
      setError(err.message || "Authentication failed. Check your municipal credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop fade-in" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-row">
            <span className="modal-icon">🏛️</span>
            <div>
              <h3>{t("officerModalTitle")}</h3>
              <p className="modal-sub">{t("officerModalSub")}</p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Quick Demo Accounts Selection */}
        <div className="demo-accounts-box">
          <span className="demo-accounts-title">{t("demoAccountsTitle")}</span>
          <div className="demo-account-pills">
            {PRESET_OFFICERS.map((p) => (
              <button
                key={p.email}
                type="button"
                className={`demo-acc-pill ${email === p.email ? "active" : ""}`}
                onClick={() => fillPreset(p)}
              >
                <b>{p.name}</b>
                <span className="acc-role">{p.role}</span>
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ marginTop: "14px" }}>
          <div className="form-group">
            <label className="form-label">{t("emailLabel")}</label>
            <input
              type="email"
              className="form-control"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="officer.name@mangaluru.gov.in"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">{t("pinLabel")}</label>
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && <div className="alert-box error-alert">{error}</div>}

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? "Verifying Credentials…" : t("loginSubmitBtn")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

