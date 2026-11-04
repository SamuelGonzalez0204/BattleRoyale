// Full-screen explorer of El Valle de la Grieta. `mapa.html#<region-or-poi-id>` focuses that place.
import { createMapViewer } from "./map/viewer.js";
import { parsePlaceHash } from "./map/hash.js";

const viewer = createMapViewer(document.getElementById("app"), { assetBase: "/mapa/" });
viewer.ready.catch(() => {
  // The loader already shows the error message; nothing else to do here.
});

function focusFromHash() {
  const id = parsePlaceHash(window.location.hash);
  if (id) viewer.focusPlace(id); // unknown ids are ignored by the viewer
}

focusFromHash();
window.addEventListener("hashchange", focusFromHash);
