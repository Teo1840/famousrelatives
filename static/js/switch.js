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
    const isDark = localStorage.getItem("darkMode") === "true";
    if (isDark) {
      document.body.classList.add("dark-mode");
      darkToggle.checked = true;
      if (darkText) darkText.textContent = "Modo oscuro";
    }

    darkToggle.addEventListener("change", () => {
      document.body.classList.toggle("dark-mode");
      const nowDark = document.body.classList.contains("dark-mode");
      localStorage.setItem("darkMode", nowDark);

      if (darkText) {
        darkText.textContent = nowDark ? "Modo oscuro" : "Modo claro";
      }

      const popup = document.getElementById('popup');
      if (popup?.style.display === 'flex' && window.showPopup) {
        window.showPopup(window.currentIndex);
      }
    });
  }
}