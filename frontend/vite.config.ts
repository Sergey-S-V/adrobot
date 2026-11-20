import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      ["/api"].map((path) => [
        path,
        {
          target: process.env.ADROBOT_API_PROXY ?? "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      ]),
    ),
  },
});
