// Builds the whole site into ONE html file (preview/index.html) for quick sharing.
// Vercel does not use this — it runs the normal `vite build`.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: { outDir: "preview", emptyOutDir: true, assetsInlineLimit: 100000000 },
});
