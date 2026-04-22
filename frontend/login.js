(function () {
  "use strict";

  const SUPABASE_URL = "https://ejekixebxeaidmhslwjs.supabase.co";
  const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqZWtpeGVieGVhaWRtaHNsd2pzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg0ODYzNDYsImV4cCI6MjA3NDA2MjM0Nn0.TRELbRomO7ERtlDG35MEvCho_voWP-Xfsi1cABqVjCs";

  const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  // Si ya hay sesión activa, redirige directamente al admin
  supabase.auth.getSession().then(({ data: { session } }) => {
    if (session) window.location.href = "admin.html";
  });

  const $email    = document.getElementById("email");
  const $password = document.getElementById("password");
  const $btn      = document.getElementById("btn-login");
  const $error    = document.getElementById("login-error");
  const $errorMsg = document.getElementById("error-msg");

  function showError(msg) {
    $errorMsg.textContent = msg;
    $error.style.display = "block";
  }

  async function login() {
    const email    = $email.value.trim();
    const password = $password.value;

    if (!email || !password) {
      showError("Introduce el correo y la contraseña.");
      return;
    }

    $btn.disabled = true;
    $btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Accediendo...';
    $error.style.display = "none";

    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      showError("Credenciales incorrectas. Verifica tu correo y contraseña.");
      $btn.disabled = false;
      $btn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Entrar';
    } else {
      window.location.href = "admin.html";
    }
  }

  $btn.addEventListener("click", login);

  // Login con Enter
  [$email, $password].forEach(el =>
    el.addEventListener("keydown", e => { if (e.key === "Enter") login(); })
  );
})();
