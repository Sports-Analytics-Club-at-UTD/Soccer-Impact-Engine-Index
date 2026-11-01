// Builds the whole site into ONE html file (preview/index.html) for quick sharing.
// Vercel does not use this — it runs the normal `vite build`.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";
import productionDataAdmission from "./build/productionDataAdmission.js";

export default defineConfig({
  plugins: [react(), viteSingleFile(), productionDataAdmission()],
  build: { outDir: "preview", emptyOutDir: true, assetsInlineLimit: 100000000 },
});
