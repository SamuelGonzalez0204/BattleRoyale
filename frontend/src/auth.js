import { apiFetch, setToken } from "./api.js";

const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const formLogin = document.getElementById("form-login");
const formRegister = document.getElementById("form-register");
const errorBox = document.getElementById("error");

function showError(message) {
  errorBox.textContent = message;
  errorBox.style.display = message ? "block" : "none";
}

function showTab(tab) {
  const isLogin = tab === "login";
  formLogin.style.display = isLogin ? "flex" : "none";
  formRegister.style.display = isLogin ? "none" : "flex";
  showError("");
}

tabLogin.addEventListener("click", () => showTab("login"));
tabRegister.addEventListener("click", () => showTab("register"));

async function afterAuth() {
  const me = await apiFetch("/api/users/me");
  window.location.href = me.faction_slug ? "/poblado.html" : "/augurio.html";
}

formLogin.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const data = Object.fromEntries(new FormData(formLogin));
  try {
    const { access_token } = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setToken(access_token);
    await afterAuth();
  } catch (err) {
    showError(err.message);
  }
});

formRegister.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const data = Object.fromEntries(new FormData(formRegister));
  try {
    const { access_token } = await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setToken(access_token);
    await afterAuth();
  } catch (err) {
    showError(err.message);
  }
});
