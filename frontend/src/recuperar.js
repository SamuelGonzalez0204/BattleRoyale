import { apiFetch } from "./api.js";

const formRequest = document.getElementById("form-request");
const formConfirm = document.getElementById("form-confirm");
const successBox = document.getElementById("success");
const errorBox = document.getElementById("error");
const token = new URLSearchParams(window.location.search).get("token");

function showError(message) {
  errorBox.textContent = message;
  errorBox.style.display = message ? "block" : "none";
}

function showSuccess(form, message) {
  form.style.display = "none";
  successBox.textContent = message;
  successBox.style.display = "block";
}

async function submitForm(form, buildRequest) {
  showError("");
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const request = buildRequest(Object.fromEntries(new FormData(form)));
    const { message } = await apiFetch(request.path, { method: "POST", body: JSON.stringify(request.body) });
    showSuccess(form, message);
  } catch (err) {
    showError(err.message);
    button.disabled = false;
  }
}

function requestReset(data) {
  return { path: "/api/auth/password-reset/request", body: { email: data.email } };
}

function confirmReset(data) {
  if (data.new_password !== data.repeat_password) {
    throw new Error("Las dos contraseñas no coinciden.");
  }
  return { path: "/api/auth/password-reset/confirm", body: { token, new_password: data.new_password } };
}

formRequest.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(formRequest, requestReset);
});

formConfirm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(formConfirm, confirmReset);
});

if (token) {
  document.getElementById("title").textContent = "Elige una contraseña nueva";
  formConfirm.style.display = "flex";
} else {
  formRequest.style.display = "flex";
}
