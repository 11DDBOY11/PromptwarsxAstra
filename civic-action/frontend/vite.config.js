import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy API + uploads to FastAPI. Prod: `npm run build` -> dist/, served by FastAPI itself.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000", "/uploads": "http://localhost:8000" } },
});
