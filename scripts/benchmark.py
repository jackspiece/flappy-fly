"""Measure full-map inference, or explicitly labeled synthetic scale checks."""

import argparse
import gc
import json
import math
import os
from pathlib import Path
import platform
import resource
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from flappy_fly.game import Flappy, scene_generator_action


def synthetic_graph(path, neurons, edges, seed=5):
    rng = np.random.default_rng(seed)
    retina = np.arange(max(1, neurons // 100), dtype=np.int32)
    np.savez(
        path,
        ptr=np.arange(neurons + 1, dtype=np.int64) * edges // neurons,
        post=rng.integers(0, neurons, size=edges, dtype=np.int32),
        weight=np.full(edges, 0.04, dtype=np.float32),
        ids=np.arange(neurons, dtype=np.int64),
        retina=retina,
        uv=np.column_stack([np.linspace(0, 1, len(retina)), np.full(len(retina), 0.5)]).astype(np.float32),
        lamina=np.empty(0, dtype=np.int32),
        sugar=np.empty(0, dtype=np.int32),
        superclass=np.full(neurons, "synthetic", dtype="U64"),
    )


def empty_circuit(neurons):
    return {
        "kc": np.empty(0, dtype=np.int32),
        "dan": np.empty(0, dtype=np.int32),
        "pre": np.empty(0, dtype=np.int32),
        "edges": np.empty(0, dtype=np.int64),
        "gain": np.zeros((0, 0), dtype=np.float32),
        "kc_mask": np.zeros(neurons, dtype=np.uint8),
        "dan_index": np.full(neurons, -1, dtype=np.int8),
        "report": {},
    }


def run(args, graph_path):
    from fly_neural.brain import MemoryBrain
    from fly_neural.sensory import retinal_samples
    start = time.perf_counter()
    if args.synthetic:
        brain = MemoryBrain(
            path=graph_path,
            circuit=empty_circuit(args.neurons),
            modulation_mask=np.zeros(args.neurons, dtype=np.uint8),
        )
        def advance(frame):
            return brain.step(retinal_samples(frame, brain.uv), args.neural_ms, learning=False)
    else:
        from fly_neural.visual import VisualMemoryBrain
        brain = VisualMemoryBrain(path=graph_path)
        def advance(frame):
            return brain.rgb_step(frame, args.neural_ms, learning=False)
    brain.weights_frozen = True
    load_seconds = time.perf_counter() - start
    graph_bytes = brain.ptr.nbytes + brain.post.nbytes + brain.weight.nbytes
    game = Flappy(seed=19)
    warmup_start = time.perf_counter()
    warmup_steps = math.ceil(args.warmup_ms / args.neural_ms)
    for _ in range(warmup_steps):
        advance(game.render())
    warmup_seconds = time.perf_counter() - warmup_start
    measurements = []
    for sample in range(args.samples):
        for _ in range(12):
            if game.terminated or game.truncated:
                game.reset(19 + sample)
            game.step(scene_generator_action(game))
        start = time.perf_counter()
        counts, kernel_seconds = advance(game.render())
        elapsed = time.perf_counter() - start
        if not np.isfinite(brain.v).all() or not np.isfinite(brain.weight).all():
            raise RuntimeError("Nonfinite neural state")
        measurement = {
            "sample": sample, "wall_seconds": elapsed,
            "kernel_seconds": kernel_seconds,
            "spikes": int(counts.sum()), "active_neurons": int(np.count_nonzero(counts)),
        }
        measurements.append(measurement)
        print(json.dumps(measurement), flush=True)
    seconds = [m["wall_seconds"] for m in measurements]
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux and Android report KiB; macOS reports bytes.
    rss_mib = rss / (1024 ** 2 if sys.platform == "darwin" else 1024)
    report = {
        "purpose": "inference runtime only; no policy has been trained",
        "connectivity": "synthetic random graph" if args.synthetic else "full retained MaleCNS v1.0 graph",
        "stimulus_controller": "scripted scene generator; game score is not neural performance",
        "upstream_commit": json.loads((ROOT / "fly_neural/upstream.json").read_text())["commit"],
        "neurons": brain.n, "edges": len(brain.post), "graph_array_mib": graph_bytes / 1024 ** 2,
        "peak_process_rss_mib": rss_mib, "load_seconds": load_seconds,
        "warmup_neural_ms": warmup_steps * args.neural_ms,
        "warmup_wall_seconds": warmup_seconds,
        "neural_ms_per_decision": args.neural_ms,
        "mean_decision_seconds": float(np.mean(seconds)),
        "median_decision_seconds": float(np.median(seconds)),
        "estimated_minutes_per_10000_decisions": float(np.mean(seconds)) * 10000 / 60,
        "timing_limit": "Short-run estimate; training, repeated initialization, and long-term throttling are not included.",
        "hardware": {"machine": platform.machine(), "cpu_count": os.cpu_count(), "python": platform.python_version()},
        "measurements": measurements,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "measurements"}), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true", help="Explicitly use random connectivity, not a fly map")
    parser.add_argument("--neurons", type=int, default=166700)
    parser.add_argument("--edges", type=int, default=25600000)
    parser.add_argument("--samples", type=int, default=6)
    parser.add_argument("--neural-ms", type=float, default=10)
    parser.add_argument("--warmup-ms", type=float, default=100)
    parser.add_argument("--output", type=Path, default=ROOT / "results/benchmark.json")
    args = parser.parse_args()
    if args.neurons < 1 or args.edges < 0 or args.samples < 1 or not np.isfinite(args.neural_ms) or not 0.1 <= args.neural_ms <= 100:
        parser.error("Invalid graph size, sample count, or neural interval")
    if not np.isfinite(args.warmup_ms) or not 0 <= args.warmup_ms <= 1000:
        parser.error("Warmup must be between 0 and 1000 ms")
    if args.synthetic:
        with tempfile.TemporaryDirectory(prefix="flappy-fly-scale-") as directory:
            graph = Path(directory) / "graph.npz"
            synthetic_graph(graph, args.neurons, args.edges)
            gc.collect()
            run(args, graph)
    else:
        data = Path(os.environ.get("STONKFLY_DATA", ROOT / "data"))
        run(args, data / "graph.npz")


if __name__ == "__main__":
    main()
