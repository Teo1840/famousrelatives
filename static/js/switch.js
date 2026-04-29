import { renderCards } from './card.js';
import { getActiveList, updateListCount } from './main.js';

export function initSwitches() {

  const directToggle = document.getElementById("switch-coParentIsTargetPerson");
  const coParentToggle = document.getElementById("switch-coParentIsPathPerson");

  function update() {
    if (!window.fullList) return;

    const list = getActiveList();
    renderCards(list);
    updateListCount();

    window.currentIndex = 0;
  }

  if (directToggle) {
    directToggle.addEventListener("change", update);
  }

  if (coParentToggle) {
    coParentToggle.addEventListener("change", update);
  }

  // 🌙 MODO OSCURO
  const darkToggle = document.getElementById("switchDarkMode");
  const darkText = document.getElementById("darkModeText");

  if (darkToggle) {
    darkToggle.addEventListener("change", () => {
      document.body.classList.toggle("dark-mode");

      if (darkText) {
        darkText.textContent = document.body.classList.contains("dark-mode")
          ? "Modo oscuro"
          : "Modo claro";
      }
    });
  }
}