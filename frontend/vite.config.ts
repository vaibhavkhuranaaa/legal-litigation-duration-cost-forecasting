import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  base: mode === "pages" ? "/legal-litigation-duration-cost-forecasting/" : "/",
  define: {
    "import.meta.env.VITE_STATIC_DEMO": JSON.stringify(mode === "pages" ? "true" : "false"),
  },
  plugins: [react()],
  build:
    mode === "m17"
      ? {
          rollupOptions: { input: "m17.html" },
        }
      : undefined,
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8100",
      "/m17-data": {
        target: "http://127.0.0.1:8765",
        rewrite: (path) => path.replace(/^\/m17-data/, ""),
      },
    },
  },
}));
