import { apiFetch, getToken } from "./api.js";

const resultBox = document.getElementById("result");
const errorBox = document.getElementById("error");
const nextLink = document.getElementById("next");

function showNext() {
  nextLink.href = getToken() ? "/poblado.html" : "/index.html";
  nextLink.style.display = "block";
}

function showError(message) {
  resultBox.style.display = "none";
  errorBox.textContent = message;
  errorBox.style.display = "block";
  showNext();
}

async function verify() {
  const token = new URLSearchParams(window.location.search).get("token");
  if (!token) {
    showError("Falta el token de verificación en el enlace.");
    return;
  }
  try {
    const { message } = await apiFetch(`/api/auth/verify?token=${encodeURIComponent(token)}`);
    resultBox.textContent = message;
    showNext();
  } catch (err) {
    showError(err.message);
  }
}

verify();
