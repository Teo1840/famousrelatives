import { renderCards } from './card.js';
import { getActiveList } from './main.js';

export function initSwitches() {

  const directToggle = document.getElementById("switch-coParentIsTargetPerson");
  const coParentToggle = document.getElementById("switch-coParentIsPathPerson");

  function update() {
    if (!window.fullList) return;

    renderCards(getActiveList());
    window.currentIndex = 0;
  }

  directToggle.addEventListener("change", update);
  coParentToggle.addEventListener("change", update);

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