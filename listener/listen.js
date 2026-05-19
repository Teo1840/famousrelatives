const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const DEBUG_PORT = 9222;
const ENV_FILE = path.join(__dirname, '..', '.env');

async function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

async function connectChrome(retries = 15, delayMs = 1000) {
    for (let i = 1; i <= retries; i++) {
        try {
            return await CDP({ port: DEBUG_PORT });
        } catch (err) {
            if (err.code === 'ECONNREFUSED' || /ECONNREFUSED/.test(err.message)) {
                console.log(`Chrome not ready yet (attempt ${i}/${retries})...`);
                await sleep(delayMs);
                continue;
            }
            throw err;
        }
    }
    throw new Error(`Unable to connect to Chrome on port ${DEBUG_PORT} after ${retries} retries.`);
}

(async () => {
    try {
        console.log("Connecting to Chrome on port " + DEBUG_PORT + "...");

        const client = await connectChrome();
        const { Network } = client;

        const TARGET_URL = 'https://www.familysearch.org/platform/users/current';
        let sawTargetRequest = false;

        await Network.enable();
        console.log("Network monitoring enabled.");

        Network.requestWillBeSent(params => {
            const url = params.request && params.request.url ? params.request.url : '';
            if (url.startsWith(TARGET_URL)) {
                console.log(`[EVENT] Detected target request: ${url}`);
                sawTargetRequest = true;
            }
        });

        console.log(`Listening for request to ${TARGET_URL}...`);
        console.log("Please log into FamilySearch in the browser...");

        let checkCount = 0;
        while (true) {
            checkCount++;
            if (checkCount % 15 === 0) {
                console.log(`Still waiting... (${checkCount} checks)`);
            }

            if (sawTargetRequest) {
                console.log('[ACTION] Fetching cookies from Chrome...');
                const cookies = await Network.getCookies();
                const fsCookie = cookies.cookies.find(c => c.name === 'fssessionid');

                if (fsCookie) {
                    console.log('[SUCCESS] Found fssessionid cookie:');
                    console.log(fsCookie.value);

                    let envContents = '';
                    if (fs.existsSync(ENV_FILE)) {
                        envContents = fs.readFileSync(ENV_FILE, 'utf8');
                    }

                    const lines = envContents ? envContents.split(/\r?\n/) : [];
                    let found = false;
                    const updated = lines.map(line => {
                        if (line.startsWith('FAMILYSEARCH_TOKEN=')) {
                            found = true;
                            return `FAMILYSEARCH_TOKEN=${fsCookie.value}`;
                        }
                        return line;
                    });

                    if (!found) {
                        updated.push(`FAMILYSEARCH_TOKEN=${fsCookie.value}`);
                    }

                    fs.writeFileSync(ENV_FILE, updated.join('\n'), 'utf8');
                    console.log(`[SAVED] Token written to ${ENV_FILE}`);
                    break;
                } else {
                    console.log('[WARNING] Target request detected but fssessionid cookie not found.');
                    sawTargetRequest = false;
                }
            }

            await sleep(2000);
        }

        await client.close();
        console.log('[COMPLETE] Listener finished successfully.');

    } catch (err) {
        console.log("[ERROR] " + err.message);
        process.exit(1);
    }
})();