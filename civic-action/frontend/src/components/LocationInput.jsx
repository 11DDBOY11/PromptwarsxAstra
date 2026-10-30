import { useEffect, useState } from "react";
import { getTranslation } from "../i18n";
import { CENTER, WARDS } from "../utils";

export default function LocationInput({ lang, pos, address, onPosChange, onAddressChange }) {
  const [geoStatus, setGeoStatus] = useState("detecting"); // "detecting" | "ready" | "denied" | "unsupported"
  const [geoLabel, setGeoLabel] = useState("");

  const t = (k) => getTranslation(lang, k);

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setGeoStatus("unsupported");
      setGeoLabel(lang === "kn" ? "ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಜಿಪಿಎಸ್ ಬೆಂಬಲವಿಲ್ಲ" : "Geolocation not supported by browser");
      return;
    }
    setGeoStatus("detecting");
    setGeoLabel(t("autoGpsAcquiring"));
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const lat = +p.coords.latitude.toFixed(5);
        const lng = +p.coords.longitude.toFixed(5);
        onPosChange({ lat, lng });
        setGeoStatus("ready");
        setGeoLabel(`${t("gpsLocked")}: ${lat}, ${lng} (±${Math.round(p.coords.accuracy)}m)`);
      },
      (err) => {
        setGeoStatus("denied");
        setGeoLabel(
          lang === "kn"
            ? "ಜಿಪಿಎಸ್ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ. ದಯವಿಟ್ಟು ಕೆಳಗೆ ಸ್ಥಳದ ಹೆಸರು ಬರೆಯಿರಿ."
            : "GPS unavailable or denied. You can select an area or enter text below."
        );
        if (!pos) {
          onPosChange({ lat: CENTER[0], lng: CENTER[1] });
        }
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  useEffect(() => {
    detectLocation();
  }, []);

  const selectWard = (ward) => {
    onPosChange({ lat: ward.lat, lng: ward.lng });
    const wardName = ward.name;
    const newAddr = address ? `${address} (${wardName})` : `${wardName} Ward`;
    onAddressChange(newAddr);
    setGeoStatus("ready");
    setGeoLabel(
      lang === "kn"
        ? `${wardName} ವಾರ್ಡ್ ಆಯ್ಕೆ ಮಾಡಲಾಗಿದೆ (${ward.lat}, ${ward.lng})`
        : `Location set to ${wardName} Ward (${ward.lat}, ${ward.lng})`
    );
  };

  return (
    <div className="location-section">
      {/* Auto Location Status Banner */}
      <div className={`geo-badge ${geoStatus}`}>
        <div className="geo-badge-left">
          <span className="geo-icon">
            {geoStatus === "detecting" ? "🔄" : geoStatus === "ready" ? "📍" : "⚠️"}
          </span>
          <span className="geo-text">
            {geoStatus === "detecting" ? t("autoGpsAcquiring") : geoLabel}
          </span>
        </div>
        <button
          type="button"
          className="btn-text-sm"
          onClick={detectLocation}
          title="Re-run GPS detection"
        >
          {geoStatus === "detecting" ? "…" : t("refreshGps")}
        </button>
      </div>

      {/* Manual / Text Location Input */}
      <div className="form-group" style={{ marginTop: "12px" }}>
        <label htmlFor="address-input" className="form-label">
          <span>{t("landmarkLabel")}</span>
          <span className="label-sub">{lang === "kn" ? "ಹೆಸರು ಬರೆಯಿರಿ ಅಥವಾ ವಾರ್ಡ್ ಆಯ್ಕೆ ಮಾಡಿ" : "Type address or pick a quick area below"}</span>
        </label>
        <div className="input-with-icon">
          <span className="input-prefix-icon">🏢</span>
          <input
            id="address-input"
            type="text"
            className="form-control"
            value={address}
            onChange={(e) => onAddressChange(e.target.value)}
            placeholder={t("landmarkPlaceholder")}
            maxLength={200}
          />
        </div>
      </div>

      {/* Quick Ward / Area Pills */}
      <div className="ward-quick-picker">
        <span className="quick-picker-title">{t("quickAreas")}</span>
        <div className="ward-pills">
          {WARDS.map((w) => (
            <button
              key={w.name}
              type="button"
              className={`ward-pill ${address.includes(w.name) ? "active" : ""}`}
              onClick={() => selectWard(w)}
            >
              {w.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
