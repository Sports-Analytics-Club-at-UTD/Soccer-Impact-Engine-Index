import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import localExperimentalRatings from "./dev/experimentalRatingsPlugin.js";
import productionDataAdmission from "./build/productionDataAdmission.js";

export default defineConfig({
  plugins: [react(), localExperimentalRatings(), productionDataAdmission()],
  server: {
    host: "127.0.0.1",
    fs: { deny: ["**/data/derived/**", "**/data/source-evidence/**", "**/*.parquet", ".env", ".env.*", "*.{crt,pem}", "**/.git/**"] },
  },
});
