// Browser integration check against a local preview and an isolated Chrome profile.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const results = resolve(root, 'results');
const preview = process.env.SITE_TEST_URL
  ? null
  : JSON.parse(await readFile(resolve(results, 'site-server.json'), 'utf8'));
const port =
  process.env.CHROME_DEBUG_PORT ||
  (await readFile(resolve(results, 'chrome-profile/DevToolsActivePort'), 'utf8')).split(
    '\n',
  )[0];
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
const errors = [];
const checks = [];
socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const item = pending.get(message.id);
    pending.delete(message.id);
    clearTimeout(item.timer);
    if (message.error) item.reject(new Error(message.error.message));
    else item.resolve(message.result);
  } else if (message.method === 'Runtime.exceptionThrown') {
    errors.push(
      message.params.exceptionDetails.exception?.description ||
        message.params.exceptionDetails.text,
    );
  } else if (
    message.method === 'Network.responseReceived' &&
    message.params.response.status >= 400
  ) {
    errors.push(message.params.response.status + ' ' + message.params.response.url);
  }
});
function send(method, params = {}) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error('CDP timeout: ' + method));
    }, 15000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const response = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
    userGesture: true,
  });
  if (response.exceptionDetails)
    throw new Error(
      response.exceptionDetails.exception?.description ||
        response.exceptionDetails.text,
    );
  return response.result.value;
}
const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));
async function waitFor(expression, timeout = 10000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await evaluate(expression)) return;
    await delay(120);
  }
  throw new Error('Page condition timed out: ' + expression);
}
function check(name, value) {
  checks.push({ name, passed: Boolean(value) });
  if (!value) throw new Error('Failed: ' + name);
}
const noOverflow =
  'document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1';
async function viewport(width, height) {
  await send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  });
}
async function screenshot(name, full = false) {
  let options = { format: 'png', captureBeyondViewport: false };
  if (full) {
    const metrics = await send('Page.getLayoutMetrics');
    options = {
      format: 'png',
      captureBeyondViewport: true,
      clip: {
        x: 0,
        y: 0,
        width: metrics.cssContentSize.width,
        height: Math.min(metrics.cssContentSize.height, 10000),
        scale: 1,
      },
    };
  }
  const image = await send('Page.captureScreenshot', options);
  await writeFile(resolve(results, name), Buffer.from(image.data, 'base64'));
}
async function click(selector) {
  await evaluate(
    'document.querySelector(' +
      JSON.stringify(selector) +
      ').scrollIntoView({block:"center",behavior:"instant"})',
  );
  await delay(80);
  await evaluate('document.querySelector(' + JSON.stringify(selector) + ').click()');
}

try {
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await viewport(1280, 960);
  await send('Page.navigate', { url: base });
  await waitFor(
    'document.readyState === "complete" && document.querySelectorAll(".sample-bar").length === 6',
  );
  await evaluate('document.fonts.ready');
  await waitFor('!document.querySelector("#replay-toggle").disabled');
  check('desktop has no horizontal overflow', await evaluate(noOverflow));
  check(
    'main controller is clearly labeled',
    await evaluate(
      'document.querySelector("#mode-tag").textContent === "SCRIPTED PREVIEW"',
    ),
  );
  await click('.sample-bar:nth-child(3)');
  check(
    'sample selection updates actual measurements',
    await evaluate(
      'document.querySelector("#sample-caption").textContent.endsWith("03") && document.querySelector("#sample-spikes").textContent === "6,287"',
    ),
  );
  await click('#take-controls');
  check(
    'manual mode opens a ready screen',
    await evaluate(
      'document.querySelector("#mode-tag").textContent === "YOUR CONTROLS" && !document.querySelector("#game-overlay").hidden',
    ),
  );
  await send('Input.dispatchKeyEvent', {
    type: 'keyDown',
    code: 'Space',
    key: ' ',
    windowsVirtualKeyCode: 32,
  });
  await send('Input.dispatchKeyEvent', {
    type: 'keyUp',
    code: 'Space',
    key: ' ',
    windowsVirtualKeyCode: 32,
  });
  await delay(150);
  check(
    'Space starts a manual flight',
    await evaluate('document.querySelector("#game-overlay").hidden'),
  );
  await click('#pause-game');
  await delay(90);
  const pausedImage = await evaluate(
    'document.querySelector("#game-canvas").toDataURL()',
  );
  await delay(160);
  check(
    'pause freezes the game canvas',
    pausedImage ===
      (await evaluate('document.querySelector("#game-canvas").toDataURL()')),
  );
  await click('#replay-toggle');
  await delay(230);
  check(
    'recorded replay advances after activation',
    await evaluate('Number(document.querySelector("#replay-position").value) > 0'),
  );
  await click('#replay-toggle');
  await click('[data-command="benchmark"]');
  check(
    'setup tabs reveal the benchmark command',
    await evaluate(
      'document.querySelector("#setup-command").textContent.includes("prepare_data.py")',
    ),
  );
  await click('#copy-command');
  check(
    'copy has accessible feedback',
    await evaluate('document.querySelector("#copy-status").textContent.length > 0'),
  );
  await click('#watch-mode');
  await evaluate('window.scrollTo({top:0,behavior:"instant"})');
  await delay(3800);
  await screenshot('site-desktop.png');
  await screenshot('site-desktop-full.png', true);
  await viewport(390, 844);
  await delay(250);
  await evaluate('window.scrollTo({top:0,behavior:"instant"})');
  check('390px layout has no horizontal overflow', await evaluate(noOverflow));
  await screenshot('site-mobile.png');
  await click('#play-mode');
  await evaluate(
    'document.querySelector("#game-canvas").scrollIntoView({block:"center",behavior:"instant"})',
  );
  await send('Emulation.setTouchEmulationEnabled', {
    enabled: true,
    maxTouchPoints: 1,
  });
  const tap = await evaluate(
    '(() => { const r = document.querySelector("#start-flight").getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()',
  );
  await send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: tap.x, y: tap.y }],
  });
  await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await delay(100);
  check(
    'touch starts a manual flight on mobile',
    await evaluate(
      'document.querySelector("#game-overlay").hidden && document.querySelector("#mode-tag").textContent === "YOUR CONTROLS"',
    ),
  );
  await send('Emulation.setTouchEmulationEnabled', { enabled: false });
  await click('#watch-mode');
  await evaluate(
    'document.querySelector("#game-canvas").scrollIntoView({block:"center",behavior:"instant"})',
  );
  await delay(900);
  await screenshot('site-mobile-arcade.png');
  await evaluate(
    'document.querySelector("#evidence").scrollIntoView({block:"start",behavior:"instant"})',
  );
  await delay(120);
  await screenshot('site-mobile-evidence.png');
  await viewport(320, 800);
  await delay(150);
  await evaluate('window.scrollTo({top:0,behavior:"instant"})');
  check('320px layout has no horizontal overflow', await evaluate(noOverflow));
  await screenshot('site-small-phone.png');
  await viewport(768, 1024);
  await delay(120);
  check('768px tablet layout has no horizontal overflow', await evaluate(noOverflow));
  await screenshot('site-tablet.png');
  await viewport(1440, 960);
  await delay(120);
  check('1440px layout has no horizontal overflow', await evaluate(noOverflow));
  await send('Emulation.setEmulatedMedia', {
    features: [{ name: 'prefers-reduced-motion', value: 'reduce' }],
  });
  await send('Page.reload', { ignoreCache: false });
  await waitFor(
    'document.readyState === "complete" && document.querySelectorAll(".sample-bar").length === 6',
  );
  check(
    'reduced motion starts with the preview paused',
    await evaluate(
      '!document.querySelector("#game-overlay").hidden && document.querySelector("#pause-game").textContent === "Resume"',
    ),
  );
  check(
    'all local images loaded',
    await evaluate(
      'Array.from(document.images).filter(i=>!i.loading || i.loading !== "lazy").every(i=>i.complete && i.naturalWidth > 0)',
    ),
  );
  await delay(200);
  check('no browser exceptions or failed resource requests', errors.length === 0);
  await mkdir(results, { recursive: true });
  await writeFile(
    resolve(results, 'site-browser-check.json'),
    JSON.stringify({ passed: true, checks, errors, base }, null, 2) + '\n',
  );
  console.log(
    JSON.stringify({
      passed: true,
      checks: checks.length,
      screenshots: [
        'site-desktop.png',
        'site-desktop-full.png',
        'site-mobile.png',
        'site-mobile-arcade.png',
        'site-mobile-evidence.png',
        'site-small-phone.png',
        'site-tablet.png',
      ],
      errors,
    }),
  );
} catch (error) {
  await screenshot('site-failure.png').catch(() => {});
  await writeFile(
    resolve(results, 'site-browser-check.json'),
    JSON.stringify(
      { passed: false, checks, errors, error: String(error), base },
      null,
      2,
    ) + '\n',
  );
  console.error(
    JSON.stringify({
      passed: false,
      error: String(error),
      checks,
      browser_errors: errors,
    }),
  );
  process.exitCode = 1;
} finally {
  socket.close();
  await fetch('http://127.0.0.1:' + port + '/json/close/' + target.id).catch(() => {});
}
