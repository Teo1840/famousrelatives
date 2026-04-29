import { renderCards } from './card.js';
import { getActiveList } from './main.js';

export function initSwitches() {

  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  toggle.addEventListener("change", () => {
    if (!window.fullList) return;

    // 🔥 RE-RENDER completo (no ocultar a mano)
    renderCards(getActiveList());

    // reset index
    window.currentIndex = 0;
  });

  // 🌙 MODO OSCURO
  const darkToggle = document.getElementById("switchDarkMode");
  const darkText = document.getElementById("darkModeText");

  darkToggle.addEventListener("change", () => {
    document.body.classList.toggle("dark-mode");

    if (darkText) {
      darkText.textContent = document.body.classList.contains("dark-mode")
        ? "Modo oscuro"
        : "Modo claro";
    }
  });
}