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

document.querySelector(".btn-download").addEventListener("click", async () => {
    const arbolesData = window.arboles || [];

  // 1. CSS
  const css = await getCSSContent();

  // 2. JS FILES
  const vis = await fetch("/static/js/vis-network.min.js").then(r => r.text());
  const utils = cleanJS(await fetch("/static/js/utils.js").then(r => r.text()));
  const popup = cleanJS(await fetch("/static/js/popup.js").then(r => r.text()));
  const switchJS = cleanJS(await fetch("/static/js/switch.js").then(r => r.text()));
  const graph = cleanJS(await fetch("/static/js/graph.js").then(r => r.text()));
  const main = cleanJS(await fetch("/static/js/main.js").then(r => r.text()));

  // 3. BODY limpio
  let bodyHTML = document.body.innerHTML;

  bodyHTML = bodyHTML
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<link[\s\S]*?>/gi, "")
    .replace(/<button class="btn-download"[\s\S]*?<\/button>/, "");

  // cerrar popup
  bodyHTML = bodyHTML.replace(
    /<div id="popup"([^>]*)style="[^"]*"/,
    '<div id="popup"$1 style="display:none"'
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
<script>${popup}</script>
<script>${switchJS}</script>
<script>${graph}</script>
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