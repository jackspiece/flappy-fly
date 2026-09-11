import { FlappyGame, SEEDS, scriptedAction, drawGame } from './game.mjs';
import { EXPERIMENT } from './experiment.mjs';

const $ = (selector) => document.querySelector(selector);
const number = new Intl.NumberFormat('en-US');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const game = new FlappyGame(19);
const canvas = $('#game-canvas');
const arcade = $('#arcade');
let mode = 'watch';
let running = !reducedMotion.matches;
let ready = false;
let queuedFlap = false;
let lastFlap = -100;
let resetAt = 0;
let gameVisible = true;
let replayVisible = false;
let lastScore = 0;
let best = 0;
try {
  best = Number(localStorage.getItem('flappy-fly-best-v1')) || 0;
} catch {}
$('#best-score').textContent = best;

function announce(text) {
  $('#game-announcement').textContent = text;
}
function overlay(label, title, copy, button) {
  $('#overlay-label').textContent = label;
  $('#overlay-title').textContent = title;
  $('#overlay-copy').textContent = copy;
  $('#start-flight').textContent = button;
  $('#game-overlay').hidden = false;
}
function controls() {
  $('#watch-mode').setAttribute('aria-pressed', String(mode === 'watch'));
  $('#play-mode').setAttribute('aria-pressed', String(mode === 'play'));
  $('#mode-tag').textContent = mode === 'watch' ? 'SCRIPTED PREVIEW' : 'YOUR CONTROLS';
  $('#pause-game').textContent = running ? 'Pause' : 'Resume';
  $('#pause-game').setAttribute('aria-label', running ? 'Pause game' : 'Resume game');
  $('#score').textContent = game.score;
  $('#seed-tag').textContent = 'SEED ' + String(game.seed).padStart(4, '0');
}
function reset(seed = game.seed) {
  game.reset(seed);
  lastFlap = -100;
  lastScore = 0;
  resetAt = 0;
  queuedFlap = false;
  $('#game-overlay').hidden = true;
  controls();
  drawGame(canvas, game);
}
function selectMode(next, seed = game.seed) {
  mode = next;
  reset(seed);
  ready = next === 'play';
  running = next === 'watch';
  if (ready)
    overlay(
      'YOUR TURN',
      'Ready to fly?',
      'Tap, press Space, or use Arrow Up.',
      'Start flight →',
    );
  controls();
}
function startFlight() {
  if (game.terminated || game.truncated) reset();
  ready = false;
  running = true;
  $('#game-overlay').hidden = true;
  if (mode === 'play') queuedFlap = true;
  controls();
  canvas.focus({ preventScroll: true });
}
function takeControls(seed = game.seed) {
  selectMode('play', seed);
  canvas.scrollIntoView({
    behavior: reducedMotion.matches ? 'auto' : 'smooth',
    block: 'center',
  });
  canvas.focus({ preventScroll: true });
}
function flap() {
  if (mode !== 'play') selectMode('play');
  if (ready || game.terminated || game.truncated || !running) startFlight();
  queuedFlap = true;
}
function pause() {
  if (!running) {
    if (ready || game.terminated || game.truncated) startFlight();
    else {
      running = true;
      $('#game-overlay').hidden = true;
    }
  } else {
    running = false;
    overlay(
      'PAUSED',
      'A little breather.',
      'Your flight will be right here.',
      'Resume →',
    );
  }
  controls();
}
$('#take-controls').addEventListener('click', () => takeControls());
$('#watch-mode').addEventListener('click', () => selectMode('watch'));
$('#play-mode').addEventListener('click', () => takeControls());
$('#start-flight').addEventListener('click', startFlight);
$('#pause-game').addEventListener('click', pause);
$('#restart-game').addEventListener('click', () => {
  reset();
  ready = mode === 'play';
  running = mode === 'watch';
  if (ready)
    overlay(
      'TRY AGAIN',
      'A fresh flight.',
      'Same layout. Another chance.',
      'Start flight →',
    );
  controls();
});
$('#new-level').addEventListener('click', () =>
  selectMode(mode, SEEDS[(SEEDS.indexOf(game.seed) + 1) % SEEDS.length]),
);
$('.game-screen').addEventListener('pointerdown', (event) => {
  if (event.target.closest('button') || event.button > 0) return;
  flap();
});
arcade.addEventListener('keydown', (event) => {
  if (event.target !== canvas) return;
  if (event.code === 'Space' || event.code === 'ArrowUp') {
    event.preventDefault();
    if (!event.repeat) flap();
  } else if (event.code === 'KeyP') {
    event.preventDefault();
    pause();
  }
});
if (!running)
  overlay(
    'PREVIEW PAUSED',
    'Fly at your pace.',
    'Motion is paused to match your preferences.',
    'Play preview →',
  );
controls();

function advanceGame(now) {
  if (game.terminated || game.truncated) {
    if (mode === 'watch') {
      if (!resetAt) resetAt = now + 950;
      if (now >= resetAt) reset(SEEDS[(SEEDS.indexOf(game.seed) + 1) % SEEDS.length]);
    }
    return;
  }
  const proposed = mode === 'watch' ? scriptedAction(game) : Number(queuedFlap);
  const action = Number(proposed && game.frame - lastFlap >= 4);
  if (action) {
    lastFlap = game.frame;
    queuedFlap = false;
  }
  game.step(action);
  if (game.score !== lastScore) {
    lastScore = game.score;
    $('#score').textContent = game.score;
    if (mode === 'play') {
      announce('Score ' + game.score);
      if (game.score > best) {
        best = game.score;
        $('#best-score').textContent = best;
        try {
          localStorage.setItem('flappy-fly-best-v1', String(best));
        } catch {}
      }
    }
  }
  if ((game.terminated || game.truncated) && mode === 'play') {
    running = false;
    overlay(
      game.truncated ? 'FLIGHT COMPLETE' : 'FLIGHT OVER',
      game.score ? game.score + ' pipes. Nice flight.' : 'The next one is yours.',
      'Your best: ' + best + '. Tap to try the same layout again.',
      'Fly again →',
    );
    announce('Flight ended. Score ' + game.score + '. Your best is ' + best + '.');
    controls();
  }
}

// All telemetry below comes from checked-in measurements, never the browser game.
const measurements = EXPERIMENT.benchmark.measurements;
const chart = $('#sample-chart');
function selectSample(index) {
  const sample = measurements[index];
  chart
    .querySelectorAll('button')
    .forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
  $('#sample-image').src = EXPERIMENT.scenes[index].image;
  $('#sample-image').alt =
    'Recorded model input for sample ' +
    (index + 1) +
    ', game frame ' +
    EXPERIMENT.scenes[index].game_frame;
  $('#sample-caption').textContent =
    'MODEL INPUT / SAMPLE ' + String(index + 1).padStart(2, '0');
  $('#sample-time').replaceChildren(
    document.createTextNode((sample.wall_seconds * 1000).toFixed(1) + ' '),
    Object.assign(document.createElement('small'), { textContent: 'ms' }),
  );
  $('#sample-spikes').textContent = number.format(sample.spikes);
  $('#sample-neurons').textContent = number.format(sample.active_neurons);
}
measurements.forEach((measurement, index) => {
  const button = document.createElement('button');
  button.className = 'sample-bar';
  button.type = 'button';
  button.style.setProperty(
    '--bar',
    ((measurement.wall_seconds * 1000) / 40) * 125 + 'px',
  );
  button.setAttribute(
    'aria-label',
    'Sample ' +
      (index + 1) +
      ': ' +
      (measurement.wall_seconds * 1000).toFixed(1) +
      ' milliseconds, ' +
      number.format(measurement.spikes) +
      ' spikes',
  );
  for (const [className, text] of [
    ['bar-value', (measurement.wall_seconds * 1000).toFixed(1)],
    ['bar', ''],
    ['bar-label', '0' + (index + 1)],
  ]) {
    const span = document.createElement('span');
    span.className = className;
    span.textContent = text;
    button.append(span);
  }
  button.addEventListener('click', () => selectSample(index));
  button.addEventListener('focus', () => selectSample(index));
  chart.append(button);
});
selectSample(0);

const learning = EXPERIMENT.learning;
if (learning) {
  const pilot = EXPERIMENT.learningSource.split('/').at(-1).replace('pilot-', '');
  $('#pilot-label').textContent = 'DECODER PILOT / ' + pilot;
  const complete = learning.status === 'complete';
  const clearedPipe = learning.test?.episodes?.some((episode) => episode.score > 0);
  $('#pilot-status').textContent = complete ? 'RECORDED' : 'INCOMPLETE';
  $('#stage-copy').textContent =
    'Pilot ' +
    pilot +
    (complete
      ? clearedPipe
        ? ' recorded. Explore its test flights.'
        : ' recorded. The first pipe is still the goal.'
      : ' saved. Evaluation is incomplete.');
  const episodes = learning.test?.episodes?.length || 0;
  $('#learning-summary').textContent =
    'Pilot ' +
    pilot +
    ' collected ' +
    number.format(learning.training_examples) +
    ' training examples from the full network. Its selected decoder averaged ' +
    (learning.test?.mean_score || 0).toFixed(2) +
    ' pipes across ' +
    episodes +
    ' unseen layouts. The mapped weights stayed fixed.';
  const rows = [
    ['Learned decoder', learning.test, true],
    ['Random flaps', learning.baselines.random, false],
    ['Periodic flaps', learning.baselines.periodic, false],
    ['Scripted teacher', learning.baselines.teacher, false],
  ];
  $('#learning-scores').replaceChildren();
  for (const [label, result, learned] of rows) {
    const tr = document.createElement('tr');
    if (learned) tr.className = 'learned-row';
    for (const text of [
      label,
      result ? result.mean_score.toFixed(2) : '—',
      result ? result.mean_frames.toFixed(1) : '—',
    ]) {
      const td = document.createElement('td');
      td.textContent = text;
      tr.append(td);
    }
    $('#learning-scores').append(tr);
  }
  $('#learning-report').href =
    'https://github.com/jackspiece/flappy-fly/blob/main/' +
    EXPERIMENT.learningSource +
    '/report.json';
}

let replay = null;
let replayIndex = 0;
let replayRunning = false;
const replayCanvas = $('#replay-canvas');
function renderReplay() {
  if (!replay) {
    drawGame(replayCanvas, new FlappyGame());
    return;
  }
  const frame = replay.frames[replayIndex];
  drawGame(replayCanvas, frame, replayIndex * (1000 / 30));
  $('#replay-position').value = replayIndex;
  $('#replay-frame').textContent = replayIndex + ' / ' + (replay.frames.length - 1);
  $('#replay-score').textContent =
    'SEED ' + replay.seed + ' · ' + frame.score + ' PIPES';
}
if (learning) {
  fetch('assets/learned-replay.json')
    .then((response) => {
      if (!response.ok) throw new Error('Replay unavailable');
      return response.json();
    })
    .then((recording) => {
      if (!Array.isArray(recording.frames) || !recording.frames.length)
        throw new Error('Invalid recording');
      replay = recording;
      $('#replay-position').max = replay.frames.length - 1;
      $('#replay-position').disabled = false;
      $('#replay-toggle').disabled = false;
      renderReplay();
    })
    .catch(() => {
      $('#replay-score').textContent = 'Recording available in the repository';
      renderReplay();
    });
}
$('#replay-toggle').addEventListener('click', () => {
  if (!replay) return;
  if (replayIndex === replay.frames.length - 1) replayIndex = 0;
  replayRunning = !replayRunning;
  $('#replay-toggle').textContent = replayRunning
    ? 'Pause recording'
    : 'Play recording';
});
$('#replay-position').addEventListener('input', (event) => {
  replayRunning = false;
  replayIndex = Number(event.target.value);
  $('#replay-toggle').textContent = 'Play recording';
  renderReplay();
});

const commands = {
  site: [
    'git clone https://github.com/jackspiece/flappy-fly.git\ncd flappy-fly\npython -m http.server 8000 --directory docs',
    'Then open localhost:8000.',
  ],
  benchmark: [
    'python -m pip install -r requirements.txt\npython scripts/prepare_data.py\npython scripts/benchmark.py',
    'Requires Python 3.12+, C++17, and about 1.11 GB of source data.',
  ],
};
document.querySelectorAll('[data-command]').forEach((button) =>
  button.addEventListener('click', () => {
    const [command, note] = commands[button.dataset.command];
    $('#setup-command').textContent = command;
    $('#setup-note').textContent = note;
    document
      .querySelectorAll('[data-command]')
      .forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
  }),
);
$('#copy-command').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($('#setup-command').textContent);
    $('#copy-command').textContent = 'Copied';
    $('#copy-status').textContent = 'Command copied to clipboard.';
    setTimeout(() => {
      $('#copy-command').textContent = 'Copy';
    }, 1600);
  } catch {
    const range = document.createRange();
    range.selectNodeContents($('#setup-command'));
    const selection = getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    $('#copy-status').textContent = 'Command selected. Copy it using your browser.';
  }
});

if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.target === arcade) gameVisible = entry.isIntersecting;
        else replayVisible = entry.isIntersecting;
      }
    },
    { threshold: 0.05 },
  );
  observer.observe(arcade);
  observer.observe(replayCanvas);
} else replayVisible = true;
reducedMotion.addEventListener('change', (event) => {
  if (event.matches) {
    running = false;
    replayRunning = false;
    overlay(
      'PREVIEW PAUSED',
      'Fly at your pace.',
      'Press resume whenever you’re ready.',
      'Resume →',
    );
    controls();
  }
});
let previousTime = performance.now();
let accumulator = 0;
let replayAccumulator = 0;
function tick(now) {
  const elapsed = Math.min(100, now - previousTime);
  previousTime = now;
  if (!document.hidden) {
    if (running && gameVisible) {
      accumulator += elapsed;
      while (accumulator >= 1000 / 30) {
        advanceGame(now);
        accumulator -= 1000 / 30;
        if (!running) break;
      }
    } else accumulator = 0;
    if (gameVisible) drawGame(canvas, game, running ? now : 0);
    if (replayRunning && replayVisible && replay) {
      replayAccumulator += elapsed;
      while (replayAccumulator >= 1000 / 30) {
        replayIndex = Math.min(replay.frames.length - 1, replayIndex + 1);
        replayAccumulator -= 1000 / 30;
        if (replayIndex === replay.frames.length - 1) {
          replayRunning = false;
          $('#replay-toggle').textContent = 'Play recording';
          break;
        }
      }
      renderReplay();
    } else replayAccumulator = 0;
  }
  requestAnimationFrame(tick);
}
window.addEventListener('resize', () => {
  drawGame(canvas, game);
  renderReplay();
});
drawGame(canvas, game);
renderReplay();
requestAnimationFrame(tick);
