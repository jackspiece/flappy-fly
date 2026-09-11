import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { FlappyGame } from '../docs/assets/game.mjs';

const fixtures = JSON.parse(
  readFileSync(new URL('./fixtures/browser-trajectories.json', import.meta.url)),
);
for (const fixture of fixtures) {
  test(`browser physics matches Python for seed ${fixture.seed}`, () => {
    const game = new FlappyGame(fixture.seed);
    fixture.actions.forEach((action, index) => {
      const result = game.step(action);
      const s = result.state;
      const actual = [
        s.frame,
        s.y,
        s.velocity,
        s.score,
        result.reward,
        result.terminated,
        result.truncated,
        s.pipe_x,
        s.gap_center,
      ];
      actual.forEach((value, column) => {
        const expected = fixture.expected[index][column];
        if (typeof value === 'number')
          assert.ok(
            Math.abs(value - expected) < 1e-9,
            `step ${index}, column ${column}`,
          );
        else assert.equal(value, expected);
      });
    });
  });
}
test('invalid actions and unknown levels fail clearly', () => {
  assert.throws(() => new FlappyGame(123456), /Unknown/);
  assert.throws(() => new FlappyGame().step(2), /Action/);
});
