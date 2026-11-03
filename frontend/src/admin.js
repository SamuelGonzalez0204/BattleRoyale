import { apiFetch, getToken } from "./api.js";

// El backend es quien protege /api/admin (403 sin permisos); esto solo decide qué se pinta.

const REASON_LABELS = { bot: "Bot", suplantacion: "Suplantación", abuso: "Abuso", otro: "Otro" };
const PHASE_LABELS = {
  construccion: "Construcción",
  conflicto: "Conflicto",
  convergencia: "Convergencia",
  colapso: "Colapso",
};

const $ = (id) => document.getElementById(id);

function setText(id, message) {
  const box = $(id);
  box.textContent = message || "";
  box.style.display = message ? "block" : "none";
}

function el(tag, { text, className, style } = {}, children = []) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  if (style) node.style.cssText = style;
  children.forEach((child) => node.appendChild(child));
  return node;
}

function button(label, onClick, secondary = false) {
  const node = el("button", { text: label, className: secondary ? "btn secondary" : "btn" });
  node.type = "button";
  node.style.padding = "8px 14px";
  node.addEventListener("click", () => onClick(node));
  return node;
}

function row(children) {
  return el(
    "div",
    { style: "display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:12px 14px;border:1px solid var(--border);border-radius:12px;background:var(--card-soft);" },
    children,
  );
}

function renderList(containerId, items, renderItem, emptyMessage) {
  const container = $(containerId);
  container.replaceChildren();
  if (!items.length) {
    container.appendChild(el("p", { text: emptyMessage, className: "muted", style: "margin:0;font-size:13px;" }));
    return;
  }
  items.forEach((item) => container.appendChild(renderItem(item)));
}

// Ejecuta una acción con el botón deshabilitado y muestra el error en su sección.
async function runAction(node, errorId, action) {
  setText(errorId, "");
  node.disabled = true;
  try {
    await action();
  } catch (err) {
    setText(errorId, err.message);
    node.disabled = false;
  }
}

// --- Temporadas -------------------------------------------------------------

function seasonRow(season) {
  const phase = PHASE_LABELS[season.phase] || season.phase;
  const info = el("div", {}, [
    el("div", { text: `Temporada ${season.number} · ${season.name}`, style: "font-weight:600;" }),
    el("div", {
      text: `${phase}${season.is_active ? " · activa" : ""} · fase desde ${new Date(season.phase_started_at).toLocaleString("es-ES")}`,
      className: "muted",
      style: "font-size:13px;",
    }),
  ]);
  if (!season.next_phase) {
    return row([info, el("span", { text: "Última fase", className: "muted", style: "font-size:13px;" })]);
  }
  const label = `Avanzar a ${PHASE_LABELS[season.next_phase] || season.next_phase}`;
  return row([info, button(label, (node) => advancePhase(node, season))]);
}

async function advancePhase(node, season) {
  setText("seasons-status", "");
  await runAction(node, "seasons-error", async () => {
    const updated = await apiFetch(`/api/admin/seasons/${season.id}/advance-phase`, { method: "POST" });
    setText("seasons-status", `Temporada ${updated.number} ahora en ${PHASE_LABELS[updated.phase] || updated.phase}.`);
    await loadSeasons();
  });
}

async function loadSeasons() {
  const seasons = await apiFetch("/api/admin/seasons");
  renderList("seasons", seasons, seasonRow, "No hay temporadas.");
}

// --- Decisión de emergencia -------------------------------------------------

function parseEffects(raw, label) {
  const text = (raw || "").trim() || "{}";
  try {
    const value = JSON.parse(text);
    if (value && typeof value === "object" && !Array.isArray(value)) return value;
  } catch {
    // se informa abajo con un mensaje claro
  }
  throw new Error(`Los efectos de la opción ${label} deben ser un objeto JSON, p. ej. {"comida": 5}.`);
}

function emergencyPayload(form) {
  const data = Object.fromEntries(new FormData(form));
  return {
    question: data.question.trim(),
    option_a: data.option_a.trim(),
    option_b: data.option_b.trim(),
    effects_a: parseEffects(data.effects_a, "A"),
    effects_b: parseEffects(data.effects_b, "B"),
    role_affinity: data.role_affinity || null,
  };
}

async function submitEmergency(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = form.querySelector("button[type=submit]");
  setText("emergency-status", "");
  await runAction(submit, "emergency-error", async () => {
    const decision = await apiFetch("/api/admin/decisions/emergency", {
      method: "POST",
      body: JSON.stringify(emergencyPayload(form)),
    });
    setText("emergency-status", `Publicada: «${decision.question}».`);
    submit.disabled = false;
  });
}

// --- Reports ------------------------------------------------------------------

function reportRow(report) {
  const details = report.details ? ` — ${report.details}` : "";
  const info = el("div", { style: "flex:1 1 280px;" }, [
    el("div", { text: `@${report.reporter_handle} denuncia a @${report.reported_handle}`, style: "font-weight:600;" }),
    el("div", {
      text: `${REASON_LABELS[report.reason] || report.reason} · ${new Date(report.created_at).toLocaleString("es-ES")}${details}`,
      className: "muted",
      style: "font-size:13px;",
    }),
  ]);
  const actions = el("div", { style: "display:flex;gap:8px;" }, [
    button("Revisado", (node) => moderateReport(node, report.id, "reviewed")),
    button("Descartar", (node) => moderateReport(node, report.id, "dismissed"), true),
  ]);
  return row([info, actions]);
}

async function moderateReport(node, reportId, status) {
  await runAction(node, "reports-error", async () => {
    await apiFetch(`/api/admin/reports/${reportId}`, { method: "POST", body: JSON.stringify({ status }) });
    await loadReports();
  });
}

async function loadReports() {
  const reports = await apiFetch("/api/admin/reports?status=open");
  renderList("reports", reports, reportRow, "No hay reports abiertos.");
}

// --- Handles ------------------------------------------------------------------

function handleRow(request) {
  const requested = request.requested_at ? new Date(request.requested_at).toLocaleString("es-ES") : "—";
  const info = el("div", { style: "flex:1 1 280px;" }, [
    el("div", { text: `@${request.handle} · código ${request.code || "—"}`, style: "font-weight:600;" }),
    el("div", { text: `${request.email} · pedido ${requested}`, className: "muted", style: "font-size:13px;" }),
  ]);
  const actions = el("div", { style: "display:flex;gap:8px;" }, [
    button("Verificar", (node) => reviewHandle(node, request.user_id, "verified")),
    button("Rechazar", (node) => reviewHandle(node, request.user_id, "rejected"), true),
  ]);
  return row([info, actions]);
}

async function reviewHandle(node, userId, decision) {
  await runAction(node, "handles-error", async () => {
    await apiFetch(`/api/admin/handles/${userId}`, { method: "POST", body: JSON.stringify({ decision }) });
    await loadHandles();
  });
}

async function loadHandles() {
  const requests = await apiFetch("/api/admin/handles?status=pending");
  renderList("handles", requests, handleRow, "No hay handles pendientes.");
}

// --- Arranque -----------------------------------------------------------------

function showGate(message, linkVisible) {
  $("gate").style.display = "flex";
  $("gate-message").textContent = message;
  $("gate-link").style.display = linkVisible ? "inline" : "none";
}

async function loadSection(loader, errorId) {
  try {
    await loader();
  } catch (err) {
    setText(errorId, err.message);
  }
}

async function init() {
  if (!getToken()) {
    showGate("Necesitas entrar con tu cuenta de administración.", true);
    return;
  }
  let me;
  try {
    me = await apiFetch("/api/users/me");
  } catch (err) {
    showGate(`No se pudo comprobar tu sesión: ${err.message}`, true);
    return;
  }
  if (!me.is_admin) {
    showGate("Tu cuenta no tiene permisos de administración.", false);
    return;
  }
  $("who").textContent = `@${me.handle}`;
  $("panel").style.display = "flex";
  $("emergency-form").addEventListener("submit", submitEmergency);
  await Promise.all([
    loadSection(loadSeasons, "seasons-error"),
    loadSection(loadReports, "reports-error"),
    loadSection(loadHandles, "handles-error"),
  ]);
}

init();
