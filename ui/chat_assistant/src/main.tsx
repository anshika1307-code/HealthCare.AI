
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { GoogleOAuthProvider } from "@react-oauth/google";
import App from "./app/App.tsx";
import "./styles/index.css";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? '';

createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </BrowserRouter>
);
