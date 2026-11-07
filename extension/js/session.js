// Sesión de FamilySearch (reemplaza al capturador listener/listen.js).
// No hay usuario ni contraseña propios: la cuenta de FamilySearch abierta en
// este navegador es el usuario.
import { fetchCurrentUser, getToken, SessionExpired } from "./fs-api.js";

const FS_HOME = "https://www.familysearch.org/es/";

// { personId, nombre } de la cuenta con sesión abierta, o null si no hay sesión.
// Lanza Error si FamilySearch no respondió (sin conexión, caído).
export async function obtenerCuenta() {
  if (!(await getToken())) return null;
  let data;
  try {
    data = await fetchCurrentUser();
  } catch (e) {
    if (e instanceof SessionExpired) return null;
    throw e;
  }
  if (!data || typeof data !== "object") {
    throw new Error("FamilySearch no respondió. Revisá tu conexión e intentá de nuevo.");
  }
  const user = (data.users || [])[0] || {};
  if (!user.personId) return null;
  return {
    personId: user.personId,
    nombre: user.displayName || user.contactName || user.personId,
  };
}

export function abrirFamilySearch() {
  chrome.tabs.create({ url: FS_HOME });
}

// Espera hasta que haya una sesión válida. Revisa cada vez que cambia la
// cookie de FamilySearch y, por las dudas, cada 5 segundos.
export function esperarLogin() {
  return new Promise(resolve => {
    let revisando = false;
    let terminado = false;

    async function revisar() {
      if (revisando || terminado) return;
      revisando = true;
      try {
        const cuenta = await obtenerCuenta();
        if (cuenta) {
          terminado = true;
          chrome.cookies.onChanged.removeListener(onCookie);
          clearInterval(timer);
          resolve(cuenta);
        }
      } catch (_) {
        // sin conexión: se vuelve a intentar
      } finally {
        revisando = false;
      }
    }

    function onCookie({ cookie }) {
      if (cookie.domain.endsWith("familysearch.org") && cookie.name === "fssessionid") revisar();
    }

    chrome.cookies.onChanged.addListener(onCookie);
    const timer = setInterval(revisar, 5000);
    revisar();
  });
}

// Llama a onCambio cuando se abre o cierra sesión en FamilySearch en otra
// pestaña (por ejemplo, entra otra persona de la familia).
export function vigilarCambioDeCuenta(onCambio) {
  chrome.cookies.onChanged.addListener(({ cookie, removed }) => {
    if (cookie.domain.endsWith("familysearch.org") && cookie.name === "fssessionid" && !removed) {
      onCambio();
    }
  });
}
