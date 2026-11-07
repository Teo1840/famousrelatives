// Al tocar el ícono de la extensión se abre la app en una pestaña.
// Si ya estaba abierta, se vuelve a esa pestaña en vez de abrir otra.
const APP_URL = chrome.runtime.getURL("app.html");

chrome.action.onClicked.addListener(async () => {
  const { appTabId } = await chrome.storage.session.get("appTabId");
  if (appTabId != null) {
    try {
      const tab = await chrome.tabs.get(appTabId);
      if (tab.url?.startsWith(APP_URL) || tab.pendingUrl?.startsWith(APP_URL)) {
        await chrome.tabs.update(appTabId, { active: true });
        await chrome.windows.update(tab.windowId, { focused: true });
        return;
      }
    } catch (_) {
      // la pestaña ya se cerró
    }
  }
  const tab = await chrome.tabs.create({ url: APP_URL });
  await chrome.storage.session.set({ appTabId: tab.id });
});

// Al instalar por primera vez, abrir la app directamente.
chrome.runtime.onInstalled.addListener(async ({ reason }) => {
  if (reason === "install") {
    const tab = await chrome.tabs.create({ url: APP_URL });
    await chrome.storage.session.set({ appTabId: tab.id });
  }
});
