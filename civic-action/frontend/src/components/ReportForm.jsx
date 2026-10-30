import { useState } from "react";
import { api } from "../api";
import { getTranslation } from "../i18n";
import { getCitizenSessionId, saveOfflineReport, saveReportToSession } from "../offlineQueue";
import { CATEGORY_ICONS, catLabel } from "../utils";
import LocationInput from "./LocationInput";
import ResultCard from "./ResultCard";

export default function ReportForm({ lang, categories, onTrack, onChanged }) {
  const [text, setText] = useState("");
  const [category, setCategory] = useState("");
  const [address, setAddress] = useState("");
  const [pos, setPos] = useState(null);
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(null);
  const [savedOffline, setSavedOffline] = useState(null);

  const t = (k) => getTranslation(lang, k);

  const handleImageChange = (e) => {
    const file = e.target.files[0] || null;
    setImage(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setPreview(url);
    } else {
      setPreview(null);
    }
  };

  async function submit(e) {
    e.preventDefault();
    setError("");

    if (!text.trim() || text.trim().length < 5) {
      return setError(lang === "kn" ? "ದಯವಿಟ್ಟು ಕನಿಷ್ಠ 5 ಅಕ್ಷರಗಳಲ್ಲಿ ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ." : "Please provide at least 5 characters describing the issue.");
    }

    const citizenSession = getCitizenSessionId();

    // Check if device is offline (Ghat / Forest section)
    if (!navigator.onLine) {
      const offlineItem = saveOfflineReport({
        text: text.trim(),
        lat: pos?.lat || 12.87,
        lng: pos?.lng || 74.85,
        address: address.trim() || "Area location",
        category: category || null,
      });
      setSavedOffline(offlineItem);
      onChanged();
      return;
    }

    const fd = new FormData();
    fd.append("text", text.trim());
    if (pos) {
      fd.append("lat", pos.lat);
      fd.append("lng", pos.lng);
    }
    if (address) fd.append("address", address.trim());
    if (category) fd.append("category", category);
    if (image) fd.append("image", image);
    fd.append("citizen_session", citizenSession);

    setBusy(true);
    try {
      const res = await api.submit(fd);
      saveReportToSession(res);
      setDone(res);
      onChanged();
    } catch (err) {
      // If network failed mid-flight, fall back to offline queue
      if (!navigator.onLine || err.message?.includes("Failed to fetch") || err.message?.includes("NetworkError")) {
        const offlineItem = saveOfflineReport({
          text: text.trim(),
          lat: pos?.lat || 12.87,
          lng: pos?.lng || 74.85,
          address: address.trim() || "Area location",
          category: category || null,
        });
        setSavedOffline(offlineItem);
        onChanged();
      } else {
        setError(err.message || "Failed to submit report. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  const resetForm = () => {
    setDone(null);
    setSavedOffline(null);
    setText("");
    setImage(null);
    setPreview(null);
    setAddress("");
    setError("");
  };

  // If saved offline in Ghat/Forest section
  if (savedOffline) {
    return (
      <section className="fade-in">
        <div className="card card-offline-success">
          <div className="success-header">
            <span className="offline-icon">📶</span>
            <div>
              <h3>{lang === "kn" ? "ದೂರು ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿ ಉಳಿಸಲಾಗಿದೆ" : "Report Saved Locally (Offline)"}</h3>
              <p className="text-muted">
                {lang === "kn"
                  ? "ನೀವು ನೆಟ್‌ವರ್ಕ್ ಇಲ್ಲದ ಘಾಟ್ ಅಥವಾ ಅರಣ್ಯ ಪ್ರದೇಶದಲ್ಲಿದ್ದೀರಿ. ಇಂಟರ್ನೆಟ್ ಸಂಪರ್ಕಗೊಂಡ ತಕ್ಷಣ ಈ ದೂರು ಸರ್ವರ್‌ಗೆ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ರವಾನೆಯಾಗುತ್ತದೆ."
                  : "You are in an area with low or no cellular connectivity (Ghat/Forest region). Your grievance is safely cached on this device and will auto-sync to municipal servers once connected."}
              </p>
            </div>
          </div>

          <div className="offline-notice-box">
            <b>{savedOffline.text}</b>
            <div className="small text-muted" style={{ marginTop: "4px" }}>
              📍 {savedOffline.address} · 🕒 {new Date(savedOffline.queuedAt).toLocaleTimeString()}
            </div>
          </div>

          <div className="alert-box" style={{ background: "#fffbeb", border: "1px solid #fde68a", color: "#92400e", margin: "14px 0", padding: "10px 14px", borderRadius: "8px", fontSize: "0.85rem" }}>
            ⚠️ <b>{lang === "kn" ? "ಗಮನಿಸಿ:" : "Important Note:"}</b>{" "}
            {lang === "kn"
              ? "ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿ ಫೋಟೋಗಳನ್ನು ಉಳಿಸಲಾಗುವುದಿಲ್ಲ. ಇಂಟರ್ನೆಟ್ ಸಿಂಕ್ ಆದ ನಂತರ ಅಗತ್ಯವಿದ್ದಲ್ಲಿ ಫೋಟೋವನ್ನು ಮರು-ಲಗತ್ತಿಸಬೇಕಾಗುತ್ತದೆ."
              : "Photos are not saved while offline and will need to be re-attached."}
          </div>

          <div className="action-buttons-row">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onTrack("my-reports")}
            >
              📋 {t("navMyReports")}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={resetForm}
            >
              {t("submitAnother")}
            </button>
          </div>
        </div>
      </section>
    );
  }

  // If successfully submitted online
  if (done) {
    return (
      <section className="fade-in">
        <div className="card card-success-banner">
          <div className="success-header">
            <span className="success-icon">✓</span>
            <div>
              <h3>{t("successTitle")}</h3>
              <p className="text-muted">{t("successSub")}</p>
            </div>
          </div>

          <div className="tracking-code-box">
            <span className="tracking-label">{t("trackingCodeLabel")}</span>
            <div className="tracking-code-val">{done.tracking_code}</div>
            <p className="tracking-sub">{t("trackingCodeSub")}</p>
          </div>

          <div className="action-buttons-row">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onTrack(done.tracking_code)}
            >
              🔍 {t("trackBtn")}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={resetForm}
            >
              {t("submitAnother")}
            </button>
          </div>
        </div>

        <div style={{ marginTop: "16px" }}>
          <h4 className="section-title">
            {lang === "kn" ? "ಎಐ ವಿಶ್ಲೇಷಣಾ ವಿವರ" : "AI Processing Breakdown"}
          </h4>
          <ResultCard r={done} lang={lang} />
        </div>
      </section>
    );
  }

  return (
    <form onSubmit={submit} className="card card-elevated fade-in">
      <div className="card-header-styled">
        <div className="badge-pill citizen-badge">{t("citizen")}</div>
        <h2>{t("reportHeader")}</h2>
        <p className="text-muted">{t("reportSub")}</p>
      </div>

      {/* Description Field */}
      <div className="form-group">
        <label htmlFor="issue-desc" className="form-label">
          <span>{t("issueLabel")} <b className="required">*</b></span>
          <span className="label-sub">{text.length}/1000 chars</span>
        </label>
        <textarea
          id="issue-desc"
          className="form-control"
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={1000}
          rows={3}
          required
          minLength={5}
          placeholder={t("issuePlaceholder")}
        />
      </div>

      {/* Category Selection */}
      <div className="form-group">
        <label htmlFor="category-select" className="form-label">
          <span>{t("categoryLabel")}</span>
          <span className="label-sub">{lang === "kn" ? "ಐಚ್ಛಿಕ - ಎಐ ಸ್ವಯಂ ವರ್ಗೀಕರಿಸುತ್ತದೆ" : "Optional - AI auto-detects"}</span>
        </label>
        <select
          id="category-select"
          className="form-control"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">{t("autoClassify")}</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {CATEGORY_ICONS[c] || "📌"}{" "}
              {t(`cat_${c}`) || catLabel(c)}
            </option>
          ))}
        </select>
      </div>

      {/* Location Section */}
      <div className="form-group">
        <LocationInput
          lang={lang}
          pos={pos}
          address={address}
          onPosChange={setPos}
          onAddressChange={setAddress}
        />
      </div>

      {/* Photo Upload */}
      <div className="form-group">
        <label htmlFor="photo-file" className="form-label">
          <span>{t("photoLabel")}</span>
          <span className="label-sub">{t("photoHint")}</span>
        </label>
        <div className="file-upload-wrapper">
          <input
            id="photo-file"
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleImageChange}
            className="file-input-hidden"
          />
          <label htmlFor="photo-file" className="file-upload-btn">
            📷 {image ? t("photoChangeBtn") : t("photoUploadBtn")}
          </label>
          {image && <span className="file-name-tag">{image.name}</span>}
        </div>
        {preview && (
          <div className="image-preview-box">
            <img src={preview} alt="Upload preview" />
            <button
              type="button"
              className="remove-img-btn"
              onClick={() => { setImage(null); setPreview(null); }}
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {error && <div className="alert-box error-alert">{error}</div>}

      <div className="form-footer">
        <button type="submit" className="btn btn-primary btn-lg" disabled={busy}>
          {busy ? (
            <span className="spinner-text">
              <span className="spinner"></span> {t("submittingBtn")}
            </span>
          ) : (
            `🚀 ${t("submitBtn")}`
          )}
        </button>
      </div>
    </form>
  );
}
