// Captura el token de FamilySearch (cookie fssessionid) desde el mismo
// navegador donde está abierta la app: abre FamilySearch en una pestaña
// nueva, espera el login, guarda el token en .env, cierra esa pestaña y
// vuelve a la pestaña de la app.
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const DEBUG_PORT = 9222;
const ENV_FILE = path.join(__dirname, '..', '.env');
const FS_URL = 'https://www.familysearch.org/en/global';
const TARGET_URL = 'https://www.familysearch.org/platform/users/current';
const APP_URL = /^https?:\/\/(localhost|127\.0\.0\.1):5000\//;

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function waitForBrowser(retries = 15, delayMs = 1000) {
    for (let i = 1; i <= retries; i++) {
        try {
            return await CDP.Version({ port: DEBUG_PORT });
        } catch (err) {
            console.log(`Navegador no disponible todavía (intento ${i}/${retries})...`);
            await sleep(delayMs);
        }
    }
    throw new Error(`No se pudo conectar al navegador en el puerto ${DEBUG_PORT}.`);
}

function saveToken(value) {
    const contents = fs.existsSync(ENV_FILE) ? fs.readFileSync(ENV_FILE, 'utf8') : '';
    const lines = contents ? contents.split(/\r?\n/) : [];
    let found = false;
    const updated = lines.map(line => {
        if (line.startsWith('FAMILYSEARCH_TOKEN=')) {
            found = true;
            return `FAMILYSEARCH_TOKEN=${value}`;
        }
        return line;
    });
    if (!found) updated.push(`FAMILYSEARCH_TOKEN=${value}`);
    fs.writeFileSync(ENV_FILE, updated.join('\n'), 'utf8');
    console.log(`[SAVED] Token guardado en ${ENV_FILE}`);
}

(async () => {
    let tab = null;
    let client = null;
    try {
        console.log(`Conectando al navegador en el puerto ${DEBUG_PORT}...`);
        await waitForBrowser();

        // Pestaña en blanco primero, para empezar a escuchar antes de que
        // FamilySearch haga su primer pedido (si ya hay sesión, es inmediato).
        tab = await CDP.New({ port: DEBUG_PORT, url: 'about:blank' });
        client = await CDP({ port: DEBUG_PORT, target: tab.id });
        const { Network, Page } = client;

        let sawTargetRequest = false;
        Network.requestWillBeSent(params => {
            const url = params.request?.url || '';
            if (url.startsWith(TARGET_URL)) sawTargetRequest = true;
        });
        await Network.enable();
        await Page.navigate({ url: FS_URL });
        await CDP.Activate({ port: DEBUG_PORT, id: tab.id });
        console.log('Esperando login en FamilySearch...');

        while (true) {
            if (sawTargetRequest) {
                const { cookies } = await Network.getCookies({ urls: ['https://www.familysearch.org/'] });
                const fsCookie = cookies.find(c => c.name === 'fssessionid');
                if (fsCookie) {
                    saveToken(fsCookie.value);
                    break;
                }
                console.log('[WARNING] Pedido detectado pero sin cookie fssessionid.');
                sawTargetRequest = false;
            }
            await sleep(1000);
        }

        await client.close();
        client = null;

        // Volver a la pestaña de la app y cerrar la de FamilySearch.
        const targets = await CDP.List({ port: DEBUG_PORT });
        const appTab = targets.find(t => t.type === 'page' && APP_URL.test(t.url));
        if (appTab) await CDP.Activate({ port: DEBUG_PORT, id: appTab.id });
        await CDP.Close({ port: DEBUG_PORT, id: tab.id });

        console.log('[COMPLETE] Captura terminada.');
        process.exit(0);
    } catch (err) {
        console.log('[ERROR] ' + err.message);
        if (client) await client.close().catch(() => {});
        process.exit(1);
    }
})();
