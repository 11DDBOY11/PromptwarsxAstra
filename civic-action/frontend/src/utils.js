export const BAND_COLOR = {
  Critical: "#dc2626",
  High: "#ea580c",
  Medium: "#d97706",
  Low: "#2563eb",
};

export const STATUS_COLOR = {
  Submitted: "#64748b",
  "Under review": "#f59e0b",
  Assigned: "#8b5cf6",
  "In progress": "#0284c7",
  Resolved: "#10b981",
};

export const CENTER = [12.87, 74.85];

export const WARDS = [
  { name: "Bunder", lat: 12.8697, lng: 74.8420 },
  { name: "Kadri", lat: 12.8885, lng: 74.8530 },
  { name: "Kankanady", lat: 12.8640, lng: 74.8590 },
  { name: "Bejai", lat: 12.8860, lng: 74.8400 },
  { name: "Attavar", lat: 12.8650, lng: 74.8350 },
  { name: "Falnir", lat: 12.8750, lng: 74.8500 },
  { name: "Surathkal", lat: 12.9850, lng: 74.8030 },
  { name: "Ullal", lat: 12.8100, lng: 74.8450 },
];

export const CATEGORY_ICONS = {
  drainage_waterlogging: "🌊",
  road_damage: "🚧",
  waste: "🗑️",
  streetlight: "💡",
  electrical_hazard: "⚡",
  safety_hazard: "⚠️",
  water_supply: "🚰",
  other: "📌",
};

export const catLabel = (c) => (c ? c.replace(/_/g, " ").replace(/^./, (m) => m.toUpperCase()) : "Unclassified");

export const fmt = (iso) => (iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "");

export function ago(iso) {
  if (!iso) return "";
  const h = (Date.now() - new Date(iso)) / 36e5;
  return h < 1 ? "just now" : h < 24 ? `${Math.floor(h)}h ago` : `${Math.floor(h / 24)}d ago`;
}
