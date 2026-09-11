// Run the real-browser checks with a temporary, isolated Chromium profile.
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { createWriteStream } from 'node:fs';
import { readFile, mkdir, mkdtemp } from 'node:fs/promises';
import { resolve, dirname, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const resultDir = resolve(root, 'results');
await mkdir(resultDir, { recursive: true });
const profile = await mkdtemp(resolve(resultDir, 'browser-'));
const docs = resolve(root, 'docs');
const mime = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.mjs': 'text/javascript',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.ttf': 'font/ttf',
};
const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(
      new URL(request.url, 'http://localhost').pathname,
    );
    const file = resolve(
      docs,
      '.' + (pathname.endsWith('/') ? pathname + 'index.html' : pathname),
    );
    if (!file.startsWith(docs + sep)) {
      response.writeHead(403);
      response.end();
      return;
    }
    const data = await readFile(file);
    response.writeHead(200, {
      'Content-Type': mime[extname(file)] || 'application/octet-stream',
      'Cache-Control': 'no-store',
    });
    response.end(request.method === 'HEAD' ? undefined : data);
  } catch {
    response.writeHead(404);
    response.end('Not found');
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const chromeLog = createWriteStream(resolve(resultDir, 'browser-chrome.log'));
let chrome;
let checker;
try {
  for (const binary of [
    process.env.CHROME_BIN,
    'google-chrome',
    'google-chrome-stable',
    'chromium-browser',
    'chromium',
  ].filter(Boolean)) {
    const candidate = spawn(
      binary,
      [
        '--headless=new',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--remote-debugging-port=0',
        '--user-data-dir=' + profile,
        'about:blank',
      ],
      { stdio: ['ignore', 'pipe', 'pipe'] },
    );
    const started = await new Promise((resolve) => {
      candidate.once('spawn', () => resolve(true));
      candidate.once('error', () => resolve(false));
    });
    if (!started) continue;
    chrome = candidate;
    chrome.stdout.pipe(chromeLog, { end: false });
    chrome.stderr.pipe(chromeLog, { end: false });
    break;
  }
  if (!chrome)
    throw new Error('Chrome/Chromium is required. Install it or set CHROME_BIN.');
  let port;
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (chrome.exitCode !== null)
      throw new Error(
        'Chrome exited before becoming ready; see results/browser-chrome.log',
      );
    try {
      port = (await readFile(resolve(profile, 'DevToolsActivePort'), 'utf8')).split(
        '\n',
      )[0];
      break;
    } catch {
      await delay(100);
    }
  }
  if (!port)
    throw new Error('Chrome did not become ready; see results/browser-chrome.log');
  const script = process.argv.includes('--capture-brand')
    ? 'capture_brand.mjs'
    : 'check_site.mjs';
  checker = spawn(process.execPath, [resolve(root, 'scripts/' + script)], {
    cwd: root,
    stdio: 'inherit',
    env: {
      ...process.env,
      CHROME_DEBUG_PORT: port,
      SITE_TEST_URL:
        process.env.SITE_TEST_URL || 'http://127.0.0.1:' + server.address().port + '/',
    },
  });
  process.exitCode = await new Promise((resolve, reject) => {
    checker.once('exit', (code) => resolve(code ?? 1));
    checker.once('error', reject);
  });
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  if (checker && checker.exitCode === null) checker.kill('SIGTERM');
  if (chrome && chrome.exitCode === null) {
    const exited = new Promise((resolve) => chrome.once('exit', resolve));
    chrome.kill('SIGTERM');
    await Promise.race([exited, delay(3000)]);
    if (chrome.exitCode === null && chrome.signalCode === null) chrome.kill('SIGKILL');
  }
  chromeLog.end();
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
}
