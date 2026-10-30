import { useEffect, useRef } from "react";
import L from "leaflet";
import { CENTER } from "../utils";

/** Tap the map (or use GPS) to drop a pin. value = {lat, lng} | null */
export default function LocationPicker({ value, onChange }) {
  const el = useRef(null), map = useRef(null), pin = useRef(null);

  useEffect(() => {
    map.current = L.map(el.current).setView(CENTER, 13);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map.current);
    map.current.on("click", (e) => onChange({ lat: +e.latlng.lat.toFixed(5), lng: +e.latlng.lng.toFixed(5) }));
    return () => map.current.remove();
  }, []);

  useEffect(() => {
    if (!value) return;
    if (!pin.current) pin.current = L.circleMarker([value.lat, value.lng], { radius: 9, color: "#b3261e", fillOpacity: 0.8 }).addTo(map.current);
    pin.current.setLatLng([value.lat, value.lng]);
  }, [value]);

  const locate = () =>
    navigator.geolocation?.getCurrentPosition((p) => {
      const v = { lat: +p.coords.latitude.toFixed(5), lng: +p.coords.longitude.toFixed(5) };
      onChange(v);
      map.current.setView([v.lat, v.lng], 16);
    }, () => alert("Could not read your location. Tap the map instead."));

  return (
    <div>
      <div ref={el} className="picker" />
      <div className="row between small">
        <span>{value ? `Pin: ${value.lat}, ${value.lng}` : "Tap the map to place a pin"}</span>
        <button type="button" className="link" onClick={locate}>Use my location</button>
      </div>
    </div>
  );
}
