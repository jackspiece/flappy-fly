"""Export reproducible browser levels, benchmark inputs, and measured results."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flappy_fly.game import Flappy, scene_generator_action

ASSETS = ROOT / "docs/assets"
SEEDS = [1, 7, 19, 31, 42, 73, 101, 9001, 9002, 9003, 9101, 9102, 9103]


def png_bytes(frame):
    height, width, _ = frame.shape
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    pixels = b"".join(b"\x00" + row.tobytes() for row in frame)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b"")


def same_png_pixels(left, right):
    def unpack(data):
        position, headers, pixels = 8, None, b""
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        while position < len(data):
            size = struct.unpack(">I", data[position:position + 4])[0]
            kind = data[position + 4:position + 8]
            body = data[position + 8:position + 8 + size]
            if kind == b"IHDR":
                headers = body
            elif kind == b"IDAT":
                pixels += body
            position += 12 + size
        return headers, zlib.decompress(pixels)
    return unpack(left) == unpack(right)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    changes = []
    def write(path, data):
        data = data.encode() if isinstance(data, str) else data
        matches = path.exists() and (same_png_pixels(path.read_bytes(), data) if path.suffix == ".png" else path.read_bytes() == data)
        if not matches:
            changes.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    levels = {}
    for seed in SEEDS:
        rng = random.Random(seed)
        levels[str(seed)] = [rng.uniform(Flappy.gap / 2 + 22, Flappy.ground - Flappy.gap / 2 - 22) for _ in range(96)]
    write(ASSETS / "levels.mjs", "// Generated from Python's seeded environment; do not edit by hand.\nexport const LEVELS = " + json.dumps(levels, separators=(",", ":")) + ";\nexport const SEEDS = " + json.dumps(SEEDS) + ";\n")
    fixtures = []
    for seed in [7, 19, 42]:
        game = Flappy(seed)
        actions, expected = [], []
        for index in range(240):
            action = scene_generator_action(game)
            if seed == 42 and 110 <= index <= 155:
                action = 0
            state, reward, terminated, truncated = game.step(action)
            actions.append(action)
            expected.append([state["frame"], state["y"], state["velocity"], state["score"], reward, terminated, truncated, state["pipe_x"], state["gap_center"]])
            if terminated or truncated:
                break
        fixtures.append({"seed": seed, "actions": actions, "expected": expected})
    write(ROOT / "tests/fixtures/browser-trajectories.json", json.dumps(fixtures, separators=(",", ":")) + "\n")
    source = ROOT / "benchmarks/2026-09-11-github"
    benchmark = json.loads((source / "benchmark.json").read_text())
    run = json.loads((source / "run.json").read_text())
    preparation = json.loads((source / "preparation.json").read_text())
    old_game = subprocess.run(["git", "show", run["tested_commit"] + ":flappy_fly/game.py"], cwd=ROOT, capture_output=True, check=True).stdout
    if hashlib.sha256(old_game).digest() != hashlib.sha256((ROOT / "flappy_fly/game.py").read_bytes()).digest():
        raise RuntimeError("The game changed since this benchmark; do not regenerate its recorded inputs from different physics")
    game = Flappy(19)
    scenes = []
    for sample in range(6):
        for _ in range(12):
            if game.terminated or game.truncated:
                game.reset(19 + sample)
            game.step(scene_generator_action(game))
        write(ASSETS / f"sample-{sample + 1}.png", png_bytes(game.render()))
        scenes.append({"sample": sample, "game_frame": game.frame, "image": f"assets/sample-{sample + 1}.png"})
    candidates = sorted((ROOT / "experiments").glob("pilot-*/report.json")) if (ROOT / "experiments").exists() else []
    learning_path = candidates[-1] if candidates else None
    learning = json.loads(learning_path.read_text()) if learning_path else None
    learning_source = str(learning_path.parent.relative_to(ROOT)) if learning_path else None
    if learning_path and (learning_path.parent / "replay.json").exists():
        write(ASSETS / "learned-replay.json", (learning_path.parent / "replay.json").read_bytes())
    data = {"benchmark": benchmark, "run": run, "preparation": preparation, "scenes": scenes, "learning": learning, "learningSource": learning_source}
    write(ASSETS / "experiment.mjs", "// Generated from checked-in experiment reports.\nexport const EXPERIMENT = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print(json.dumps({"mode": "check" if args.check else "build", "changed": changes}))
    if args.check and changes:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
