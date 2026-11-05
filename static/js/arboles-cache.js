// Copia local de los árboles del usuario (IndexedDB).
// Al cargar el dashboard se pide solo la versión al servidor; si coincide con
// la copia local se usa esa, y si no se descargan los datos de /api/arboles.
// main.js espera a window.arbolesPromise antes de dibujar las tarjetas.
(function () {
  const DB_NAME = "famousrelatives";
  const STORE = "arboles";
  const key = "user-" + window.ARBOLES_USER_ID;

  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  function withStore(mode, fn) {
    return openDB().then(db => new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const req = fn(tx.objectStore(STORE));
      tx.oncomplete = () => { db.close(); resolve(req.result); };
      tx.onerror = () => { db.close(); reject(tx.error); };
    }));
  }

  const leerLocal = () => withStore("readonly", s => s.get(key)).catch(() => undefined);
  const guardarLocal = (entry) => withStore("readwrite", s => s.put(entry, key)).catch(() => {});

  async function fetchJSON(url) {
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) throw new Error(url + " → " + r.status);
    return r.json();
  }

  async function cargarArboles() {
    const local = await leerLocal();

    try {
      if (local) {
        const { version } = await fetchJSON("/api/arboles/version");
        if (version === local.version) return local.arboles;
      }
      const fresh = await fetchJSON("/api/arboles");
      await guardarLocal({ version: fresh.version, arboles: fresh.arboles });
      return fresh.arboles;
    } catch (err) {
      // Sin red (o error del servidor): usar la copia local si hay.
      console.error("No se pudieron cargar los árboles:", err);
      return local ? local.arboles : [];
    }
  }

  window.arbolesPromise = cargarArboles();

  // Mientras se procesan árboles en el servidor: devuelve la lista nueva si
  // cambió la versión (o siempre, con forzar), o null si no hay nada nuevo.
  let versionActual = null;
  window.recargarArboles = async function (forzar = false) {
    try {
      if (!forzar) {
        const { version } = await fetchJSON("/api/arboles/version");
        if (version === versionActual) return null;
      }
      const fresh = await fetchJSON("/api/arboles");
      versionActual = fresh.version;
      await guardarLocal({ version: fresh.version, arboles: fresh.arboles });
      return fresh.arboles;
    } catch (err) {
      console.error("No se pudieron recargar los árboles:", err);
      return null;
    }
  };

  window.clearArbolesCache = function () {
    return new Promise(resolve => {
      try {
        const req = indexedDB.deleteDatabase(DB_NAME);
        req.onsuccess = req.onerror = req.onblocked = () => resolve();
      } catch (_) {
        resolve();
      }
    });
  };
})();
