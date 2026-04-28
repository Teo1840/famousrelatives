import { showPopup } from './popup.js';
import { getActiveList } from './main.js';
import { generarUUID } from './utils.js';

export function initSwitches() {

  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  toggle.addEventListener("change", () => {
    if (!window.fullList) return;

    const hide = toggle.checked;

    // 1. actualizar cards
    document.querySelectorAll(".card").forEach(c => {
      const isTarget = c.dataset.coParentTarget === "true";
      const hasDirect = c.dataset.hasDirectPath === "true";

      if (isTarget && !hasDirect) {
        c.style.display = hide ? "none" : "block";
      }
    });

    // 2. reset index
    window.currentIndex = 0;
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