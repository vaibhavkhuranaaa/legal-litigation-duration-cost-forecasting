import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  base: mode === "pages" ? "/legal-litigation-duration-cost-forecasting/" : "/",
  plugins: [react()],
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8100",
    },
  },
}));
