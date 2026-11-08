async function getCSSContent() {
  const paths = [
    "/static/css/components/buttons.css",
    "/static/css/components/popups.css",
    "/static/css/components/switches.css",
    "/static/css/base.css"
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
    const vis = await fetch("/static/js/vis-network.min.js").then(r => r.text());
    const utils = cleanJS(await fetch("/static/js/utils.js").then(r => r.text()));
    const relationship = cleanJS(await fetch("/static/js/relationship.js").then(r => r.text()));
    const graph = cleanJS(await fetch("/static/js/graph.js").then(r => r.text()));
    const card = cleanJS(await fetch("/static/js/card.js").then(r => r.text()));
    const popup = cleanJS(await fetch("/static/js/popup.js").then(r => r.text()));
    const switchJS = cleanJS(await fetch("/static/js/switch.js").then(r => r.text()));
    const main = cleanJS(await fetch("/static/js/main.js").then(r => r.text()));

    // 3. BODY limpio
    // Se clona y se poda con el DOM (no con regex) porque el boton "..." y su
    // desplegable tienen HTML anidado que una regex no puede recortar bien.
    const bodyClone = document.body.cloneNode(true);
    bodyClone.querySelectorAll("script").forEach(el => el.remove());
    bodyClone.querySelectorAll("link").forEach(el => el.remove());
    bodyClone.querySelector(".btn-download")?.remove();
    // El boton "..." (capturar token, buscar personas nuevas, cerrar sesion,
    // etc.) depende del servidor y no tiene sentido en el archivo offline.
    // El modo claro/oscuro vive en ese menú: se pasa al de ajustes para no perderlo.
    const modoOscuro = bodyClone.querySelector("#opcion-modo-oscuro");
    if (modoOscuro) bodyClone.querySelector("#settings-actions")?.appendChild(modoOscuro);
    bodyClone.querySelector(".header-menu")?.remove();

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
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect x='10.6' y='15' width='2.8' height='8' fill='%236e4828'/%3E%3Cg fill='%234a9e22'%3E%3Ccircle cx='12' cy='6' r='5'/%3E%3Cellipse cx='7.5' cy='12' rx='5.5' ry='5'/%3E%3Cellipse cx='16.5' cy='12' rx='5.5' ry='5'/%3E%3C/g%3E%3C/svg%3E">

<style>
${css}
</style>

</head>

<body class="${dark ? 'dark-mode' : ''}">
${bodyHTML}

<script>
window.arboles = ${JSON.stringify(arbolesData)};
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