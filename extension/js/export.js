async function getCSSContent() {
  const paths = [
    "css/components/buttons.css",
    "css/components/popups.css",
    "css/components/switches.css",
    "css/base.css",
    "css/header.css"
  ];

  let styles = "";

  for (const path of paths) {
    const res = await fetch(path);
    const text = await res.text();
    styles += text + "\n";
  }

  return styles;
}

// limpia imports y exports
function cleanJS(code) {
  return code
    .replace(/import[\s\S]*?;/g, "")
    .replace(/export\s+/g, "");
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.querySelector(".btn-download");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const arbolesData = window.arboles || [];

    // 1. CSS
    const css = await getCSSContent();

    // 2. JS FILES (orden IMPORTANTE)
    const vis = await fetch("lib/vis-network.min.js").then(r => r.text());
    const utils = cleanJS(await fetch("js/utils.js").then(r => r.text()));
    const relationship = cleanJS(await fetch("js/relationship.js").then(r => r.text()));
    const graph = cleanJS(await fetch("js/graph.js").then(r => r.text()));
    const card = cleanJS(await fetch("js/card.js").then(r => r.text()));
    const popup = cleanJS(await fetch("js/popup.js").then(r => r.text()));
    const switchJS = cleanJS(await fetch("js/switch.js").then(r => r.text()));
    const main = cleanJS(await fetch("js/main.js").then(r => r.text()));

    // 3. BODY limpio
    // Se clona y se poda con el DOM (no con regex) porque el boton "..." y su
    // desplegable tienen HTML anidado que una regex no puede recortar bien.
    const bodyClone = document.body.cloneNode(true);
    bodyClone.querySelectorAll("script").forEach(el => el.remove());
    bodyClone.querySelectorAll("link").forEach(el => el.remove());
    bodyClone.querySelector(".btn-download")?.remove();
    // El boton "..." (capturar token, buscar personas nuevas, cerrar sesion,
    // etc.) depende del servidor y no tiene sentido en el archivo offline.
    bodyClone.querySelector(".header-menu")?.remove();
    // Cosas de la extensión que no sirven en el archivo descargado.
    ["login-panel", "app-aviso", "progreso-busqueda", "cuenta-estado"]
      .forEach(id => bodyClone.querySelector("#" + id)?.remove());

    let bodyHTML = bodyClone.innerHTML;

    // 🔥 asegurar popup oculto (robusto)
    bodyHTML = bodyHTML.replace(
      /<div id="popup"([^>]*)>/,
      '<div id="popup"$1 style="display:none">'
    );

    // 4. estado UI
    const dark = document.getElementById("switchDarkMode")?.checked;

    // 5. HTML FINAL
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Famous Relatives</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M8 19a4 4 0 0 1-2.24-7.32A3.5 3.5 0 0 1 9 6.03V6a3 3 0 1 1 6 0v.04a3.5 3.5 0 0 1 3.24 5.65A4 4 0 0 1 16 19Z'/%3E%3Cpath d='M12 19v3' fill='none'/%3E%3C/svg%3E">

<style>
${css}
</style>

</head>

<body class="${dark ? 'dark-mode' : ''}">
${bodyHTML}

<script>
window.arboles = ${JSON.stringify(arbolesData)};
window.CATEGORIAS = ${JSON.stringify(window.CATEGORIAS || {})};
window.currentIndex = 0;
</script>

<script>${vis}</script>
<script>${utils}</script>
<script>${relationship}</script>
<script>${graph}</script>
<script>${card}</script>
<script>${popup}</script>
<script>${switchJS}</script>
<script>${main}</script>

</body>
</html>
`;

    // 6. Descargar
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "famous-relatives-offline-full.html";
    a.click();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
});