export function initSwitches() {
  // MOSTRAR PARENTESCOS DEL CONYUGUE
  const toggle = document.getElementById("switchCoParents");
  let hidden = false;

  toggle.addEventListener("change", function() {
    document.querySelectorAll(".card").forEach(c => {
      if (c.dataset.coParent === "true") {
        c.style.display = hidden ? "block" : "none";
      }
    });
    hidden = !hidden;
  });

  // MODO OSCURO
  const darkToggle = document.getElementById("switchDarkMode");
  const darkText = document.getElementById("darkModeText");

  darkToggle.addEventListener("change", function() {
    document.body.classList.toggle("dark-mode");
    darkText.textContent = document.body.classList.contains("dark-mode")
      ? "Modo oscuro"
      : "Modo claro";
  });
}