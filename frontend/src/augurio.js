import { apiFetch, requireAuthOrRedirect } from "./api.js";

if (requireAuthOrRedirect()) {
  init();
}

async function init() {
  try {
    const me = await apiFetch("/api/users/me");
    if (me.faction_slug) {
      window.location.href = "/poblado.html";
      return;
    }
  } catch {
    window.location.href = "/index.html";
    return;
  }

  document.querySelectorAll("[data-choice]").forEach((button) => {
    button.addEventListener("click", onChoose);
  });
}

async function onChoose(event) {
  document.querySelectorAll("[data-choice]").forEach((b) => (b.disabled = true));
  const errorBox = document.getElementById("error");
  errorBox.style.display = "none";

  try {
    const faction = await apiFetch("/api/augurio/assign", { method: "POST" });
    showResult(faction);
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.style.display = "block";
    document.querySelectorAll("[data-choice]").forEach((b) => (b.disabled = false));
  }
}

function showResult(faction) {
  document.getElementById("quiz").style.display = "none";
  const result = document.getElementById("result");
  result.style.display = "flex";

  const pill = document.getElementById("result-pill");
  pill.textContent = `${faction.influence_pct}% de influencia en el mundo`;
  pill.style.borderColor = faction.color;
  pill.style.color = faction.color;

  document.getElementById("result-name").textContent = faction.name;
}
