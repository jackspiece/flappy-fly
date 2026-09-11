"""Small trainable action decoder; the upstream connectome stays frozen."""

from pathlib import Path
import time

import numpy as np


def sigmoid(values):
    return 1.0 / (1.0 + np.exp(-np.clip(values, -30, 30)))


class ActionDecoder:
    def __init__(self, inputs, hidden=48, seed=7):
        rng = np.random.default_rng(seed)
        self.parameters = {
            "w1": (rng.normal(size=(inputs, hidden)) * np.sqrt(2 / inputs)).astype(np.float32),
            "b1": np.zeros(hidden, dtype=np.float32),
            "w2": (rng.normal(size=(hidden, 1)) * 0.02).astype(np.float32),
            "b2": np.zeros(1, dtype=np.float32),
        }
        self.mean = np.zeros(inputs, dtype=np.float32)
        self.scale = np.ones(inputs, dtype=np.float32)
        self.prior = 0.0
        self.threshold = 0.5

    def _normalize(self, x):
        return np.clip((np.asarray(x, dtype=np.float32) - self.mean) / self.scale, -8, 8)

    def _forward(self, x):
        p = self.parameters
        hidden = np.maximum(x @ p["w1"] + p["b1"], 0)
        return (hidden @ p["w2"] + p["b2"]).ravel(), hidden

    def probabilities(self, x):
        z, _ = self._forward(self._normalize(np.atleast_2d(x)))
        return sigmoid(z + self.prior)

    def action(self, x):
        return int(self.probabilities(x)[0] >= self.threshold)

    @staticmethod
    def classification(probability, target, threshold=0.5):
        predicted = probability >= threshold
        target = np.asarray(target, dtype=bool)
        tp = int(np.sum(predicted & target))
        fp = int(np.sum(predicted & ~target))
        fn = int(np.sum(~predicted & target))
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        loss = -np.mean(target * np.log(np.clip(probability, 1e-7, 1)) + (~target) * np.log(np.clip(1 - probability, 1e-7, 1)))
        return {"loss": float(loss), "precision": precision, "recall": recall,
                "f1": 2 * precision * recall / max(1e-9, precision + recall)}

    def fit(self, x, y, validation, *, epochs=120, seed=7, deadline=None):
        x, y = np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.float32)
        if x.ndim != 2 or y.shape != (len(x),) or not np.isfinite(x).all() or not np.isin(y, [0, 1]).all():
            raise ValueError("Invalid training data")
        positive, negative = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
        if not len(positive) or not len(negative):
            raise ValueError("Both action classes are required")
        self.mean = x.mean(axis=0)
        self.scale = np.maximum(x.std(axis=0), 0.025)
        self.prior = float(np.log(len(positive) / len(negative)))
        normalized = self._normalize(x)
        rng = np.random.default_rng(seed)
        first = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        second = {k: np.zeros_like(v) for k, v in self.parameters.items()}
        best = None
        best_loss = float("inf")
        history = []
        step = 0
        completed = 0
        for epoch in range(epochs):
            if deadline is not None and time.monotonic() >= deadline:
                break
            for _ in range(max(1, int(np.ceil(len(x) / 256)))):
                indices = np.r_[rng.choice(positive, 128), rng.choice(negative, 128)]
                batch, target = normalized[indices], y[indices]
                z, hidden = self._forward(batch)
                dz = (sigmoid(z) - target)[:, None] / len(batch)
                dh = (dz @ self.parameters["w2"].T) * (hidden > 0)
                gradients = {
                    "w2": hidden.T @ dz + 1e-4 * self.parameters["w2"],
                    "b2": dz.sum(axis=0),
                    "w1": batch.T @ dh + 1e-4 * self.parameters["w1"],
                    "b1": dh.sum(axis=0),
                }
                norm = np.sqrt(sum(float(np.sum(g * g)) for g in gradients.values()))
                factor = min(1.0, 5.0 / max(norm, 1e-9))
                step += 1
                for name, gradient in gradients.items():
                    gradient *= factor
                    first[name] *= 0.9
                    first[name] += 0.1 * gradient
                    second[name] *= 0.999
                    second[name] += 0.001 * gradient * gradient
                    self.parameters[name] -= 0.001 * (first[name] / (1 - 0.9 ** step)) / (np.sqrt(second[name] / (1 - 0.999 ** step)) + 1e-8)
            measurement = self.classification(self.probabilities(validation[0]), validation[1])
            completed += 1
            if measurement["loss"] < best_loss:
                best_loss = measurement["loss"]
                best = {k: v.copy() for k, v in self.parameters.items()}
            if epoch % 5 == 0 or epoch == epochs - 1:
                history.append({"epoch": epoch + 1, **measurement})
        if best is None:
            raise RuntimeError("No optimization step completed within the budget")
        self.parameters = best
        probability = self.probabilities(validation[0])
        candidates = [(self.classification(probability, validation[1], float(t)), float(t)) for t in np.linspace(0.025, 0.8, 32)]
        metric, self.threshold = max(candidates, key=lambda item: (item[0]["f1"], item[0]["precision"], -abs(item[1] - 0.5)))
        return {"examples": len(x), "positive_examples": len(positive), "threshold": self.threshold,
                "validation": metric, "epochs_completed": completed, "history": history}

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **self.parameters, mean=self.mean, scale=self.scale,
                            prior=np.asarray(self.prior), threshold=np.asarray(self.threshold))

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as record:
            model = cls(record["w1"].shape[0], record["w1"].shape[1])
            model.parameters = {k: record[k].copy() for k in model.parameters}
            model.mean, model.scale = record["mean"].copy(), record["scale"].copy()
            model.prior, model.threshold = float(record["prior"]), float(record["threshold"])
        return model


def high_contrast(frame):
    """Pixel-only display transform; no coordinates or hidden game state."""
    luminance = frame.astype(np.float32) @ np.asarray([0.2126, 0.7152, 0.0722], dtype=np.float32)
    light = np.where(luminance >= 220, 255, 0).astype(np.uint8)
    return np.repeat(light[:, :, None], 3, axis=2)


class NeuralFeatures:
    """Activity grids, anatomical population rates, and the agent's own actions."""
    def __init__(self, brain, columns=16, rows=12):
        self.brain = brain
        self.columns, self.rows = columns, rows
        self.groups = []
        for indices, uv in [
            (brain.retina, brain.uv),
            (brain.r8[brain.r8_channel == 2], brain.r8_uv[brain.r8_channel == 2]),
            (brain.r8[brain.r8_channel == 1], brain.r8_uv[brain.r8_channel == 1]),
        ]:
            cell = np.minimum((uv[:, 0] * columns).astype(int), columns - 1) + columns * np.minimum((uv[:, 1] * rows).astype(int), rows - 1)
            self.groups.append((indices, cell, np.maximum(1, np.bincount(cell, minlength=columns * rows))))
        self.regions, self.region_index, self.region_size = np.unique(brain.superclass, return_inverse=True, return_counts=True)
        self.base_size = 3 * columns * rows + len(self.regions)
        self.size = 2 * self.base_size + 2
        self.reset()

    def reset(self):
        self.smooth = None

    def extract(self, spikes, previous_action, frames_since_flap):
        parts = [np.bincount(cell, weights=spikes[indices], minlength=self.columns * self.rows) / size for indices, cell, size in self.groups]
        parts.append(np.bincount(self.region_index, weights=spikes, minlength=len(self.regions)) / self.region_size)
        raw = np.concatenate(parts).astype(np.float32)
        old = raw if self.smooth is None else self.smooth
        self.smooth = old * 0.5 + raw * 0.5
        return np.r_[self.smooth, self.smooth - old, float(previous_action), min(frames_since_flap, 40) / 40].astype(np.float32)

    def description(self):
        return {"size": self.size, "grid": [self.columns, self.rows], "regions": self.regions.tolist(),
                "signals": ["R1-R6 spike grids", "R8p spike grids", "R8y spike grids", "superclass mean spike counts", "activity changes", "previous action", "frames since own flap"],
                "hidden_game_state_used_by_decoder": False}
