// Full-screen explorer of El Valle de la Grieta (same widgets as the published artifact).
import { createMapViewer } from "./map/viewer.js";

const viewer = createMapViewer(document.getElementById("app"), { assetBase: "/mapa/" });
viewer.ready.catch(() => {
  // The loader already shows the error message; nothing else to do here.
});
