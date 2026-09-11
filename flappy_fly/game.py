"""Headless game with original geometry, deterministic seeds, and RGB frames."""

from dataclasses import dataclass
import math
import random

import numpy as np


@dataclass
class Pipe:
    x: float
    center: float
    passed: bool = False


class Flappy:
    width = 288
    height = 240
    ground = 232
    bird_x = 66.0
    radius = 5.0
    pipe_width = 30.0
    gap = 78.0
    spacing = 140.0
    scroll = 2.5
    gravity = 0.45
    impulse = -5.2

    def __init__(self, seed=0, max_frames=3600):
        if max_frames < 1:
            raise ValueError("max_frames must be positive")
        self.max_frames = max_frames
        self.reset(seed)

    def reset(self, seed=0):
        self.rng = random.Random(seed)
        self.seed = seed
        self.y = self.ground / 2
        self.velocity = 0.0
        self.frame = self.score = 0
        self.terminated = self.truncated = False
        self.pipes = [self._pipe(self.width + i * self.spacing) for i in range(3)]
        return self.observe()

    def _pipe(self, x):
        return Pipe(x, self.rng.uniform(self.gap / 2 + 22, self.ground - self.gap / 2 - 22))

    def observe(self):
        ahead = next(p for p in self.pipes if p.x + self.pipe_width >= self.bird_x - self.radius)
        return {
            "y": self.y,
            "velocity": self.velocity,
            "pipe_x": ahead.x,
            "gap_center": ahead.center,
            "score": self.score,
            "frame": self.frame,
        }

    def _hit_rectangle(self, left, top, right, bottom):
        x = min(max(self.bird_x, left), right)
        y = min(max(self.y, top), bottom)
        return (x - self.bird_x) ** 2 + (y - self.y) ** 2 <= self.radius ** 2

    def step(self, action):
        if self.terminated or self.truncated:
            raise RuntimeError("Reset the game after an episode ends")
        if not isinstance(action, (int, np.integer)) or action not in (0, 1):
            raise ValueError("Action must be 0 (wait) or 1 (flap)")
        if action:
            self.velocity = self.impulse
        self.velocity = min(self.velocity + self.gravity, 8.0)
        self.y += self.velocity
        self.frame += 1
        for pipe in self.pipes:
            pipe.x -= self.scroll
        self.terminated = self.y - self.radius <= 0 or self.y + self.radius >= self.ground
        for pipe in self.pipes:
            left, right = pipe.x, pipe.x + self.pipe_width
            self.terminated |= self._hit_rectangle(left, 0, right, pipe.center - self.gap / 2)
            self.terminated |= self._hit_rectangle(left, pipe.center + self.gap / 2, right, self.ground)
        reward = -1.0 if self.terminated else 0.01
        if not self.terminated:
            for pipe in self.pipes:
                if not pipe.passed and pipe.x + self.pipe_width < self.bird_x - self.radius:
                    pipe.passed = True
                    self.score += 1
                    reward += 1.0
        self.pipes = [p for p in self.pipes if p.x + self.pipe_width >= 0]
        while len(self.pipes) < 3:
            self.pipes.append(self._pipe(self.pipes[-1].x + self.spacing))
        self.truncated = self.frame >= self.max_frames and not self.terminated
        return self.observe(), reward, self.terminated, self.truncated

    def render(self):
        frame = np.empty((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (226, 242, 249)
        for pipe in self.pipes:
            left = max(0, math.floor(pipe.x))
            right = min(self.width, math.ceil(pipe.x + self.pipe_width))
            if right <= left:
                continue
            top = max(0, math.floor(pipe.center - self.gap / 2))
            bottom = min(self.ground, math.ceil(pipe.center + self.gap / 2))
            frame[:top, left:right] = (42, 142, 84)
            frame[bottom:self.ground, left:right] = (42, 142, 84)
        yy, xx = np.ogrid[:self.height, :self.width]
        bird = (xx - self.bird_x) ** 2 + (yy - self.y) ** 2 <= self.radius ** 2
        frame[bird] = (252, 188, 40)
        frame[self.ground:] = (150, 110, 65)
        return frame


def scene_generator_action(game):
    """Scripted stimulus generator only; never scored as a neural controller."""
    state = game.observe()
    return int(state["y"] + 5 * state["velocity"] > state["gap_center"] + 3)

