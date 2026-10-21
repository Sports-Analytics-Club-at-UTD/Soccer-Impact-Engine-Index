import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
// Fonts are self-hosted (no Google Fonts request): Latin subsets only.
import "@fontsource/chakra-petch/latin-600.css";
import "@fontsource/chakra-petch/latin-700.css";
import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/latin-500.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-600.css";
import "./styles.css";

createRoot(document.getElementById("root")).render(<App />);
