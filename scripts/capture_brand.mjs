// Render the editable vector identity and an honestly labeled arcade screenshot.
import { readFile, writeFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const built = spawnSync(process.env.PYTHON || 'python', ['scripts/build_brand.py'], {
  cwd: root,
  stdio: 'inherit',
});
if (built.error || built.status !== 0)
  throw built.error || new Error('Vector build failed');
const results = resolve(root, 'results');
const port =
  process.env.CHROME_DEBUG_PORT ||
  (await readFile(resolve(results, 'chrome-profile/DevToolsActivePort'), 'utf8')).split(
    '\n',
  )[0];
const preview = process.env.SITE_TEST_URL
  ? null
  : JSON.parse(await readFile(resolve(results, 'site-server.json'), 'utf8'));
const base = process.env.SITE_TEST_URL || 'http://127.0.0.1:' + preview.port + '/';
const target = await (
  await fetch('http://127.0.0.1:' + port + '/json/new?about:blank', { method: 'PUT' })
).json();
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let sequence = 0;
const pending = new Map();
const captured = [];
socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  if (!pending.has(message.id)) return;
  const request = pending.get(message.id);
  pending.delete(message.id);
  clearTimeout(request.timer);
  if (message.error) request.reject(new Error(message.error.message));
  else request.resolve(message.result);
});
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error('CDP timeout: ' + method));
    }, 15000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const data = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (data.exceptionDetails) throw new Error(data.exceptionDetails.text);
  return data.result.value;
}
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function navigate(path, width, height) {
  await send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await send('Page.navigate', { url: base + path });
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (
      await evaluate(
        'document.readyState === "complete" && location.href === ' +
          JSON.stringify(base + path),
      )
    ) {
      await evaluate('document.fonts.ready');
      return;
    }
    await delay(100);
  }
  throw new Error('Asset load timed out: ' + path);
}
async function screenshot(name, clip) {
  const data = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
    clip: { ...clip, scale: 1 },
  });
  const bytes = Buffer.from(data.data, 'base64');
  await writeFile(resolve(root, 'docs/assets', name), bytes);
  captured.push({
    file: 'docs/assets/' + name,
    bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'),
  });
}
try {
  await send('Page.enable');
  await send('Runtime.enable');
  for (const [stem, height] of [
    ['readme-hero', 560],
    ['social-card', 672],
  ]) {
    await navigate('assets/' + stem + '.svg', 1280, height);
    await screenshot(stem + '.png', { x: 0, y: 0, width: 1280, height });
  }
  await navigate('', 1280, 1000);
  await evaluate(
    'document.querySelector("#watch-mode").click(); document.querySelector(".arcade-shell").scrollIntoView({block:"start",behavior:"instant"})',
  );
  await delay(4100);
  const clip = await evaluate(
    '(() => { const r = document.querySelector(".arcade-shell").getBoundingClientRect(); return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}; })()',
  );
  await screenshot('arcade-preview.png', clip);
  await writeFile(
    resolve(results, 'brand-capture.json'),
    JSON.stringify(captured, null, 2) + '\n',
  );
  console.log(JSON.stringify({ captured }));
} finally {
  socket.close();
  await fetch('http://127.0.0.1:' + port + '/json/close/' + target.id).catch(() => {});
}
