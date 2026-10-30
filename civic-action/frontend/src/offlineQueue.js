import { api } from "./api";

const SESSION_KEY = "civic_citizen_session_id";
const REPORTS_KEY = "civic_citizen_reports";
const QUEUE_KEY = "civic_offline_queue";
const FAILED_KEY = "civic_offline_failed";

export function getOfflineFailed() {
  try {
    return JSON.parse(localStorage.getItem(FAILED_KEY) || "[]");
  } catch {
    return [];
  }
}

export function getCitizenSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = "cit_" + Math.random().toString(36).substring(2, 9) + "_" + Date.now().toString(36);
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function saveReportToSession(report) {
  if (!report || !report.tracking_code) return;
  const list = getSessionReports();
  // Avoid duplicates in local history
  const filtered = list.filter((r) => r.tracking_code !== report.tracking_code);
  filtered.unshift({
    tracking_code: report.tracking_code,
    summary: report.summary,
    category: report.category,
    status: report.status || "Submitted",
    created_at: report.created_at || new Date().toISOString(),
    address: report.address || "Area location",
    ward: report.ward || "",
  });
  localStorage.setItem(REPORTS_KEY, JSON.stringify(filtered.slice(0, 30)));
}

export function getSessionReports() {
  try {
    return JSON.parse(localStorage.getItem(REPORTS_KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveOfflineReport(reportData) {
  const queue = getOfflineQueue();
  const item = {
    id: "offline_" + Date.now(),
    text: reportData.text,
    lat: reportData.lat,
    lng: reportData.lng,
    address: reportData.address,
    category: reportData.category,
    queuedAt: new Date().toISOString(),
    citizen_session: getCitizenSessionId(),
  };
  queue.push(item);
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  return item;
}

export function getOfflineQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
  } catch {
    return [];
  }
}

export async function syncOfflineQueue(onProgress) {
  const queue = getOfflineQueue();
  if (queue.length === 0) return [];

  const syncedResults = [];
  const remaining = [];

  for (const item of queue) {
    try {
      const fd = new FormData();
      fd.append("text", item.text);
      if (item.lat) fd.append("lat", item.lat);
      if (item.lng) fd.append("lng", item.lng);
      if (item.address) fd.append("address", item.address);
      if (item.category) fd.append("category", item.category);
      if (item.citizen_session) fd.append("citizen_session", item.citizen_session);

      const res = await api.submit(fd);
      saveReportToSession(res);
      syncedResults.push(res);
      if (onProgress) onProgress(res);
    } catch (err) {
      console.warn("Failed to sync offline item:", item, err);
      if (err && err.status >= 400 && err.status < 500) {
        // 4xx error: remove from queue and record in civic_offline_failed
        try {
          const failed = getOfflineFailed();
          failed.push({
            id: item.id,
            text: item.text,
            status: err.status,
            error: err.message || "Client rejection",
            failedAt: new Date().toISOString(),
          });
          localStorage.setItem(FAILED_KEY, JSON.stringify(failed.slice(-20)));
        } catch {
          // ignore localStorage error
        }
      } else {
        // Network error or 5xx: keep retrying
        remaining.push(item);
      }
    }
  }

  localStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
  return syncedResults;
}

