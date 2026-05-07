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
        console.log("Connecting to Chrome...");

        const client = await connectChrome();
        const { Network } = client;

        const TARGET_URL = 'https://www.familysearch.org/platform/users/current';
        let sawTargetRequest = false;

        await Network.enable();

        Network.requestWillBeSent(params => {
            if (params.request && params.request.url && params.request.url.startsWith(TARGET_URL)) {
                console.log(`Detected target request: ${params.request.url}`);
                sawTargetRequest = true;
            }
        });

        console.log(`Connected. Waiting for request to ${TARGET_URL} and fssessionid cookie...`);

        while (true) {
            if (sawTargetRequest) {
                const cookies = await Network.getCookies();
                const fsCookie = cookies.cookies.find(c => c.name === 'fssessionid');

                if (fsCookie) {
                    console.log('FOUND SESSION COOKIE AFTER TARGET REQUEST:');
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
                    console.log(`Token written to ${ENV_FILE}`);
                    break;
                }
            }

            await sleep(2000);
        }

        await client.close();
        console.log('Listener finished.');

    } catch (err) {
        console.log("ERROR:");
        console.log(err.message);
    }
})();