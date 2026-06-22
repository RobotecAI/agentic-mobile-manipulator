import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter";
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource-variable/jetbrains-mono";
import App from "./App";
import { RosProvider } from "./ros/RosProvider";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RosProvider>
      <App />
    </RosProvider>
  </StrictMode>,
);
