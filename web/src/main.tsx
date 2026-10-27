import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./index.css";

const container = document.getElementById("root")!;

// The built document ships a prerendered landing for crawlers and for visitors
// without JavaScript. React owns #root from here on: there is no hydration, so
// the identical app markup simply replaces it (and the block's own styles go
// with it).
document.getElementById("static-landing")?.remove();
document.getElementById("static-landing-style")?.remove();

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
