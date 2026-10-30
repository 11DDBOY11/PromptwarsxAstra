import { useEffect, useState } from "react";
import { api } from "./api";
import Dashboard from "./components/Dashboard.jsx";
import MapView from "./components/MapView.jsx";
import OfficerLoginModal from "./components/OfficerLoginModal.jsx";
import Queue from "./components/Queue.jsx";
import ReportForm from "./components/ReportForm.jsx";
import TrackView from "./components/TrackView.jsx";
import { getTranslation } from "./i18n";
import { getOfflineQueue, syncOfflineQueue } from "./offlineQueue";

export default function App() {
  const [lang, setLang] = useState(localStorage.getItem("civic_lang") || "en");
  const [tab, setTab] = useState("report");
  const [health, setHealth] = useState(null);
  const [code, setCode] = useState("");
  const [version, setVersion] = useState(0);

  // Officer Auth
  const [officer, setOfficer] = useState(null);
  const [loginModalOpen, setLoginModalOpen] = useState(false);

  // Offline Sync State (Western Ghats & Forest Sections)
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingOffline, setPendingOffline] = useState(getOfflineQueue().length);
  const [syncing, setSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState("");

  const t = (k) => getTranslation(lang, k);

  const switchLang = (newLang) => {
    setLang(newLang);
    localStorage.setItem("civic_lang", newLang);
  };

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch(() => setHealth({ error: true }));

    // Check if an existing officer token is valid
    if (api.getOfficerToken()) {
      api.officerMe()
        .then((res) => setOfficer(res.officer))
        .catch(() => api.officerLogout());
    }

    // Monitor connectivity
    const handleOnline = () => {
      setIsOnline(true);
      triggerSync();
    };
    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const triggerSync = async () => {
    if (syncing) return;
    const queue = getOfflineQueue();
    if (queue.length === 0) return;
    setSyncing(true);
    try {
      const results = await syncOfflineQueue();
      if (results.length > 0) {
        setSyncNotice(
          lang === "kn"
            ? `${results.length} ಆಫ್‌ಲೈನ್ ದೂರುಗಳು ಸರ್ವರ್‌ಗೆ ಸಿಂಕ್ ಆಗಿವೆ!`
            : `${results.length} offline report(s) successfully synchronized!`
        );
        setTimeout(() => setSyncNotice(""), 6000);
        bump();
      }
    } catch (err) {
      console.warn("Sync failed:", err);
    } finally {
      setSyncing(false);
      setPendingOffline(getOfflineQueue().length);
    }
  };

  const bump = () => {
    setVersion((v) => v + 1);
    setPendingOffline(getOfflineQueue().length);
  };

  const goTrack = (c) => {
    setCode(c);
    setTab("track");
  };

  const handleOfficerLoginSuccess = (officerData) => {
    setOfficer(officerData);
    setTab("queue"); // Immediately open Officer Queue
    bump();
  };

  const handleOfficerLogout = () => {
    api.officerLogout();
    setOfficer(null);
    setTab("report");
    bump();
  };

  const reset = async () => {
    if (confirm(lang === "kn" ? "45 ಡೆಮೊ ದೂರುಗಳನ್ನು ಮರುಲೋಡ್ ಮಾಡುವುದೇ? ಇದು ಪ್ರಸ್ತುತ ಬದಲಾವಣೆಗಳನ್ನು ಮರುಹೊಂದಿಸುತ್ತದೆ." : "Reload the 45 synthetic demo reports? This will reset all current changes.")) {
      await api.reset();
      bump();
    }
  };

  return (
    <div className="app-container">
      {/* Offline Status Warning Banner (For Ghats / Remote Areas) */}
      {(!isOnline || pendingOffline > 0) && (
        <div className="offline-floating-banner fade-in">
          <div className="banner-left">
            <span className="banner-icon">{!isOnline ? "📶" : "🔄"}</span>
            <div>
              <b>{!isOnline ? t("offlineTitle") : `${pendingOffline} ${t("pendingOfflineCount")}`}</b>
              <p className="small">{!isOnline ? t("offlineDesc") : ""}</p>
            </div>
          </div>
          {isOnline && pendingOffline > 0 && (
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled={syncing}
              onClick={triggerSync}
            >
              {syncing ? t("syncing") : t("syncNowBtn")}
            </button>
          )}
        </div>
      )}

      {syncNotice && (
        <div className="alert-box success-toast fade-in">
          ✓ {syncNotice}
        </div>
      )}

      {/* Top Header */}
      <header className="top-header">
        <div className="header-inner">
          <div className="brand-lockup">
            <div className="brand-logo">🏛️</div>
            <div>
              <div className="brand-title-row">
                <span className="brand-name">{t("appTitle")}</span>
                <span className="brand-tagline">Karnataka Civic AI</span>
              </div>
              <p className="brand-desc">{t("appSub")}</p>
            </div>
          </div>

          {/* Right Header Controls: Language Switcher + Officer Auth */}
          <div className="header-right-controls">
            {/* Language Switcher Pill */}
            <div className="lang-switcher">
              <button
                type="button"
                className={`lang-btn ${lang === "en" ? "active" : ""}`}
                onClick={() => switchLang("en")}
              >
                English
              </button>
              <button
                type="button"
                className={`lang-btn ${lang === "kn" ? "active" : ""}`}
                onClick={() => switchLang("kn")}
              >
                ಕನ್ನಡ
              </button>
            </div>

            {/* Officer Portal Button / Authenticated Pill */}
            {officer ? (
              <div className="officer-active-pill">
                <span className="officer-status-dot"></span>
                <span className="officer-name-tag">
                  👮 {officer.name} ({officer.department})
                </span>
                <button
                  type="button"
                  className="btn-officer-logout"
                  onClick={handleOfficerLogout}
                  title="Sign out of Officer Portal"
                >
                  {t("officerSignOut")}
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="btn-officer-portal"
                onClick={() => setLoginModalOpen(true)}
              >
                👮 {t("officerPortalBtn")}
              </button>
            )}

            <button type="button" className="btn-reset-demo" onClick={reset} title="Reload the 45 synthetic demo reports">
              ↺ Reset
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="main-nav">
          {/* Public Citizen Navigation */}
          <div className="nav-role-group">
            <span className="nav-group-label">{t("citizen")}</span>
            <button
              type="button"
              className={`nav-tab-btn citizen-tab ${tab === "report" ? "active" : ""}`}
              onClick={() => setTab("report")}
            >
              <span className="tab-icon">📝</span>
              <span className="tab-label">{t("navReport")}</span>
            </button>
            <button
              type="button"
              className={`nav-tab-btn citizen-tab ${tab === "track" ? "active" : ""}`}
              onClick={() => setTab("track")}
            >
              <span className="tab-icon">🔍</span>
              <span className="tab-label">{t("navTrack")}</span>
            </button>
          </div>

          {/* Officer Command Center Navigation (Visible when logged in) */}
          {officer && (
            <>
              <div className="nav-divider" />
              <div className="nav-role-group">
                <span className="nav-group-label">{t("officer")}</span>
                <button
                  type="button"
                  className={`nav-tab-btn officer-tab ${tab === "queue" ? "active" : ""}`}
                  onClick={() => setTab("queue")}
                >
                  <span className="tab-icon">⚡</span>
                  <span className="tab-label">{t("navQueue")}</span>
                </button>
                <button
                  type="button"
                  className={`nav-tab-btn officer-tab ${tab === "map" ? "active" : ""}`}
                  onClick={() => setTab("map")}
                >
                  <span className="tab-icon">🔥</span>
                  <span className="tab-label">{t("navHotspots")}</span>
                </button>
                <button
                  type="button"
                  className={`nav-tab-btn officer-tab ${tab === "dash" ? "active" : ""}`}
                  onClick={() => setTab("dash")}
                >
                  <span className="tab-icon">📊</span>
                  <span className="tab-label">{t("navDashboard")}</span>
                </button>
              </div>
            </>
          )}
        </nav>
      </header>

      {/* Main View Area */}
      <main className="main-content">
        {tab === "report" && (
          <ReportForm
            lang={lang}
            categories={health?.categories || []}
            onTrack={goTrack}
            onChanged={bump}
          />
        )}
        {tab === "track" && (
          <TrackView
            lang={lang}
            initialCode={code}
            version={version}
          />
        )}
        {officer && tab === "queue" && (
          <Queue
            lang={lang}
            statuses={health?.statuses || []}
            version={version}
            onChanged={bump}
          />
        )}
        {officer && tab === "map" && (
          <MapView
            lang={lang}
            version={version}
          />
        )}
        {officer && tab === "dash" && (
          <Dashboard
            lang={lang}
            version={version}
          />
        )}
      </main>

      {/* Officer Login Modal */}
      <OfficerLoginModal
        lang={lang}
        isOpen={loginModalOpen}
        onClose={() => setLoginModalOpen(false)}
        onLoginSuccess={handleOfficerLoginSuccess}
      />

      {/* Footer */}
      <footer className="app-footer">
        <p>
          {lang === "kn"
            ? "ಕರ್ನಾಟಕ ಸರ್ಕಾರ ಪೌರಾಡಳಿತ ನಾವೀನ್ಯತೆ · ಮಂಗಳೂರು ಮಹಾನಗರ ಪಾಲಿಕೆ · ಘಾಟ್ / ಅರಣ್ಯ ಪ್ರದೇಶಗಳಿಗೆ ಆಫ್‌ಲೈನ್ ಸ್ವಯಂ ಸಿಂಕ್ ಸೌಲಭ್ಯ"
            : "Government of Karnataka Municipal Innovation · Mangaluru City Corporation · Offline Auto-Sync for Western Ghats & Remote Zones"}
        </p>
      </footer>
    </div>
  );
}
