import { LEVELS, SEEDS } from './levels.mjs';
export { SEEDS };

export class FlappyGame {
  static width = 288;
  static height = 240;
  static ground = 232;
  static birdX = 66;
  static radius = 5;
  static pipeWidth = 30;
  static gap = 78;
  static spacing = 140;

  constructor(seed = 19, maxFrames = 3600) {
    this.maxFrames = maxFrames;
    this.reset(seed);
  }

  reset(seed = 19) {
    if (!LEVELS[String(seed)]) throw new Error('Unknown browser level seed');
    this.seed = seed;
    this.level = LEVELS[String(seed)];
    this.nextPipe = 0;
    this.y = FlappyGame.ground / 2;
    this.velocity = this.frame = this.score = 0;
    this.terminated = this.truncated = false;
    this.pipes = Array.from({ length: 3 }, (_, i) => this.makePipe(288 + i * 140));
    return this.observe();
  }

  makePipe(x) {
    if (this.nextPipe >= this.level.length) throw new Error('Seeded level exhausted');
    return { x, center: this.level[this.nextPipe++], passed: false };
  }

  observe() {
    const pipe = this.pipes.find((p) => p.x + 30 >= 61);
    return {
      y: this.y,
      velocity: this.velocity,
      pipe_x: pipe.x,
      gap_center: pipe.center,
      score: this.score,
      frame: this.frame,
    };
  }

  hits(left, top, right, bottom) {
    const x = Math.min(Math.max(66, left), right);
    const y = Math.min(Math.max(this.y, top), bottom);
    return (x - 66) ** 2 + (y - this.y) ** 2 <= 25;
  }

  step(action) {
    if (this.terminated || this.truncated)
      throw new Error('Reset after an episode ends');
    if (action !== 0 && action !== 1) throw new Error('Action must be 0 or 1');
    if (action) this.velocity = -5.2;
    this.velocity = Math.min(this.velocity + 0.45, 8);
    this.y += this.velocity;
    this.frame += 1;
    for (const pipe of this.pipes) pipe.x -= 2.5;
    this.terminated = this.y - 5 <= 0 || this.y + 5 >= 232;
    for (const pipe of this.pipes) {
      this.terminated ||= this.hits(pipe.x, 0, pipe.x + 30, pipe.center - 39);
      this.terminated ||= this.hits(pipe.x, pipe.center + 39, pipe.x + 30, 232);
    }
    let reward = this.terminated ? -1 : 0.01;
    if (!this.terminated) {
      for (const pipe of this.pipes) {
        if (!pipe.passed && pipe.x + 30 < 61) {
          pipe.passed = true;
          this.score += 1;
          reward += 1;
        }
      }
    }
    this.pipes = this.pipes.filter((p) => p.x + 30 >= 0);
    while (this.pipes.length < 3)
      this.pipes.push(this.makePipe(this.pipes.at(-1).x + 140));
    this.truncated = this.frame >= this.maxFrames && !this.terminated;
    return {
      state: this.observe(),
      reward,
      terminated: this.terminated,
      truncated: this.truncated,
    };
  }
}

export function scriptedAction(game) {
  const state = game.observe();
  return Number(state.y > state.gap_center + 12);
}

export function drawGame(canvas, game, time = 0) {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(globalThis.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.round(rect.width * ratio));
  const height = Math.max(1, Math.round(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(width / 288, 0, 0, height / 240, 0, 0);
  const sky = ctx.createLinearGradient(0, 0, 0, 240);
  sky.addColorStop(0, '#10261f');
  sky.addColorStop(0.55, '#213d2a');
  sky.addColorStop(1, '#476344');
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, 288, 240);
  const light = ctx.createRadialGradient(220, 75, 0, 210, 95, 175);
  light.addColorStop(0, '#b2c88020');
  light.addColorStop(1, '#b2c88000');
  ctx.fillStyle = light;
  ctx.fillRect(0, 0, 288, 240);
  // Atmospheric scenery, independent of the neural simulation.
  for (let i = 0; i < 28; i++) {
    const x = ((((i * 73.7 - game.frame * 0.13) % 304) + 304) % 304) - 8;
    const y = ((i * 43.3) % 195) + 12;
    ctx.fillStyle = i % 3 === 0 ? '#d3e3a44d' : '#bdce9c24';
    ctx.fillRect(x, y, i % 4 === 0 ? 0.9 : 0.55, i % 4 === 0 ? 0.9 : 0.55);
  }
  for (let layer = 0; layer < 3; layer++) {
    ctx.beginPath();
    ctx.moveTo(0, 232);
    for (let x = 0; x <= 292; x += 4) {
      const offset = x + game.frame * (0.09 + layer * 0.1);
      const y =
        165 +
        layer * 23 +
        Math.sin(offset * 0.018 + layer * 2) * 13 +
        Math.sin(offset * 0.05 + layer) * 3;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(292, 232);
    ctx.closePath();
    ctx.fillStyle = ['#436044', '#334f37', '#273f2e'][layer];
    ctx.fill();
  }
  ctx.strokeStyle = '#abc78312';
  ctx.lineWidth = 0.4;
  for (let x = 0; x < 288; x += 24) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, 232);
    ctx.stroke();
  }
  for (const pipe of game.pipes) {
    for (const [y, h] of [
      [0, pipe.center - 39],
      [pipe.center + 39, 232 - pipe.center - 39],
    ]) {
      const metal = ctx.createLinearGradient(pipe.x, 0, pipe.x + 30, 0);
      metal.addColorStop(0, '#799765');
      metal.addColorStop(0.13, '#a8bd7b');
      metal.addColorStop(0.32, '#6a8a55');
      metal.addColorStop(0.8, '#344e32');
      metal.addColorStop(1, '#243f2b');
      ctx.fillStyle = '#0c1e1466';
      ctx.fillRect(pipe.x + 3, y + 3, 30, h);
      ctx.fillStyle = metal;
      ctx.fillRect(pipe.x, y, 30, h);
      ctx.fillStyle = '#d6e3a261';
      ctx.fillRect(pipe.x + 2, y, 0.7, h);
      ctx.fillStyle = '#223e2966';
      ctx.fillRect(pipe.x + 23, y, 1, h);
      ctx.fillStyle = '#182f2659';
      for (let rib = y + 12; rib < y + h - 7; rib += 14)
        ctx.fillRect(pipe.x + 4, rib, 22, 0.6);
      const capY = y === 0 ? h - 7 : y;
      ctx.fillStyle = '#182e23';
      ctx.fillRect(pipe.x, capY, 30, 7);
      ctx.fillStyle = '#829e62';
      ctx.fillRect(pipe.x + 0.5, capY + 0.5, 29, 5);
      ctx.fillStyle = '#d3e5a0';
      ctx.fillRect(pipe.x + 0.5, capY + (y === 0 ? 5 : 0.5), 29, 0.85);
      ctx.fillStyle = '#263d25';
      ctx.fillRect(pipe.x + 25, capY + 0.5, 4.5, 4.5);
      ctx.fillStyle = '#cbdc97';
      ctx.fillRect(pipe.x + 4, capY + 2, 1, 1);
      ctx.fillStyle = '#334b2e';
      ctx.fillRect(pipe.x + 21, capY + 2, 1, 1);
    }
  }
  ctx.fillStyle = '#17291c';
  ctx.fillRect(0, 232, 288, 8);
  ctx.fillStyle = '#98b06d';
  ctx.fillRect(0, 232, 288, 0.8);
  ctx.fillStyle = '#4b653b';
  for (let x = -((game.frame * 2.5) % 8); x < 288; x += 8) ctx.fillRect(x, 235, 4, 1.5);
  ctx.save();
  ctx.translate(66, game.y);
  ctx.rotate(Math.max(-0.3, Math.min(0.6, game.velocity * 0.065)));
  const wing = 0.55 + 0.45 * Math.sin(time * 0.045);
  ctx.fillStyle = '#e5f2cfd9';
  ctx.strokeStyle = '#b0c494';
  ctx.lineWidth = 0.45;
  for (const sign of [-1, 1]) {
    ctx.beginPath();
    ctx.ellipse(-1.5, sign * (4 + wing * 2), 6.5, 2.5, sign * 0.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
  ctx.strokeStyle = '#182b20';
  ctx.lineWidth = 0.7;
  for (const offset of [-3, 0, 3]) {
    ctx.beginPath();
    ctx.moveTo(offset, 2);
    ctx.lineTo(offset - 2, 6);
    ctx.stroke();
  }
  ctx.fillStyle = '#d6af70';
  ctx.beginPath();
  ctx.ellipse(-2.5, 0, 5, 3.4, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#526446';
  ctx.fillRect(-5, -2.5, 1, 5);
  ctx.fillRect(-2.5, -3, 1, 6);
  ctx.fillStyle = '#59714e';
  ctx.beginPath();
  ctx.ellipse(1, 0, 3.5, 3.3, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#bfd298';
  ctx.beginPath();
  ctx.ellipse(0.4, -1.5, 2, 0.8, -0.1, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#213326';
  ctx.beginPath();
  ctx.arc(4.2, -0.2, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#ff805c';
  ctx.beginPath();
  ctx.arc(5.2, -1, 2.2, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#ffe5b7';
  ctx.fillRect(5, -2, 0.7, 0.7);
  ctx.restore();
}
