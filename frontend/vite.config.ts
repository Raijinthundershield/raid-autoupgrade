import path from "path";
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiPort = env.RAID_AUTOUPGRADE_API_PORT ?? "8765";
  const vitePort = parseInt(env.RAID_AUTOUPGRADE_VITE_PORT ?? "5173");

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
      port: vitePort,
      proxy: {
        "/api": `http://127.0.0.1:${apiPort}`,
        "/ws": { target: `ws://127.0.0.1:${apiPort}`, ws: true },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test-setup.ts"],
    },
  };
});
