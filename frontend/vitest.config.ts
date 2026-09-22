import path from "node:path";
import { defineConfig } from "vitest/config";

// Deliberately separate from vite.config.ts: that config's plugins (visual
// edits, the branded dev overlay, polling file watchers) are dev-server-only
// concerns that have no business running inside a test process, and loading
// them there risks slowing down or destabilizing `vitest run` for no benefit.
// This file only needs the same `@` path alias the app itself uses.
export default defineConfig({
  resolve: {
    alias: [{ find: "@", replacement: path.resolve(__dirname, "./src") }],
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
