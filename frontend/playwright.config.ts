import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "specification.spec.ts",
  workers: 1,
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:5175" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev -- --port 5175",
    url: "http://127.0.0.1:5175",
    reuseExistingServer: false,
    env: { ADROBOT_API_PROXY: "http://127.0.0.1:8001" },
  },
});
