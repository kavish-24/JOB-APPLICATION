import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";


// Backend: python -m uvicorn app:app --port 8000   (override with API_TARGET)
const target = process.env.API_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/analyze": target, "/compose": target } },
});
