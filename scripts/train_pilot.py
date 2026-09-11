"""Bounded behavioral-cloning and dataset-aggregation pilot on the real map."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from flappy_fly.game import Flappy
from flappy_fly.learning import ActionDecoder, NeuralFeatures, high_contrast, reference_action


def snapshot(game, action=None, probability=None):
    return {"y": game.y, "velocity": game.velocity, "frame": game.frame, "score": game.score,
            "action": action, "probability": probability,
            "pipes": [{"x": p.x, "center": p.center, "passed": p.passed} for p in game.pipes]}


def baseline(seeds, kind, max_frames):
    episodes = []
    for seed in seeds:
        game = Flappy(seed, max_frames=max_frames)
        rng = np.random.default_rng(seed)
        previous_flap = -100
        while not game.terminated and not game.truncated:
            if kind == "teacher":
                proposed = reference_action(game)
            elif kind == "periodic":
                proposed = int(game.frame % 22 == 0)
            else:
                proposed = int(rng.random() < 0.05)
            action = int(proposed and game.frame - previous_flap >= 4)
            if action:
                previous_flap = game.frame
            game.step(action)
        episodes.append({"seed": seed, "score": game.score, "frames": game.frame})
    return episodes


def summarize(episodes):
    if not episodes:
        return None
    return {"episodes": episodes, "mean_score": float(np.mean([x["score"] for x in episodes])),
            "mean_frames": float(np.mean([x["frames"] for x in episodes]))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wall-seconds", type=int, default=720)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--seed-offset", type=int, default=100)
    parser.add_argument("--output", type=Path, default=ROOT / "results/learning-pilot")
    args = parser.parse_args()
    if not 480 <= args.wall_seconds <= 960 or not 0 <= args.rounds <= 3:
        parser.error("Use a 480–960 second budget and 0–3 aggregation rounds")
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    deadline = started + args.wall_seconds
    report = {
        "method": "behavioral cloning plus dataset aggregation",
        "trained_parameters": "action decoder only",
        "connectome_weights_frozen": True,
        "stimulus": "RGB game frames converted to black/white at luminance 220/255",
        "neural_ms_per_decision": 10,
        "minimum_flap_interval_frames": 4,
        "teacher": "centering controller: flap below gap center + 12 pixels, with a four-frame actuator interval; privileged labels only",
        "training_seeds": [s + args.seed_offset for s in range(1000, 1010)],
        "classification_validation_seeds": [s + args.seed_offset for s in [1100, 1101]],
        "policy_validation_seeds": [s + args.seed_offset for s in [5001, 5002]],
        "test_seeds": [s + args.seed_offset for s in [9001, 9002, 9003]],
        "seed_offset": args.seed_offset,
        "rounds": [], "status": "initializing", "budget_seconds": args.wall_seconds,
        "limitations": ["The biological synaptic weights are not trained in this pilot.", "A small held-out evaluation is preliminary, not evidence that fly wiring beats conventional architectures."],
    }

    def save():
        report["elapsed_seconds"] = time.monotonic() - started
        temporary = args.output / "report.json.partial"
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        temporary.replace(args.output / "report.json")

    def event(**record):
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        with (args.output / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        print(json.dumps(record), flush=True)

    from fly_neural.visual import VisualMemoryBrain
    brain = VisualMemoryBrain()
    if brain.n != 166700 or len(brain.post) != 25582938:
        raise RuntimeError("Unexpected graph; this pilot requires the complete pinned retained map")
    brain.weights_frozen = True
    features = NeuralFeatures(brain)
    report.update({"neurons": brain.n, "edges": len(brain.post), "features": features.description(),
                   "upstream_commit": json.loads((ROOT / "fly_neural/upstream.json").read_text())["commit"],
                   "initial_weight_sha256": hashlib.sha256(brain.weight.tobytes()).hexdigest()})
    save()
    rng = np.random.default_rng(7)

    def episode(seed, model=None, beta=1.0, collect=False, cap=360, stop_at=None, record=False):
        game = Flappy(seed, max_frames=cap)
        brain.reset()
        brain.weights_frozen = True
        features.reset()
        brain.rgb_step(high_contrast(game.render()), 100, learning=False)
        x, y, replay = [], [], []
        last_flap, previous_action = -100, 0
        complete = True
        while not game.terminated and not game.truncated:
            if time.monotonic() >= (deadline if stop_at is None else stop_at):
                complete = False
                break
            spikes, _ = brain.rgb_step(high_contrast(game.render()), 10, learning=False)
            age = game.frame - last_flap
            encoded = features.extract(spikes, previous_action, age)
            target = int(reference_action(game) and age >= 4)
            probability = None if model is None else float(model.probabilities(encoded)[0])
            proposed = target if model is None or rng.random() < beta else int(probability >= model.threshold)
            action = int(proposed and age >= 4)
            if collect:
                x.append(encoded)
                y.append(target)
            if record:
                replay.append(snapshot(game, action, probability))
            if action:
                last_flap = game.frame
            previous_action = action
            game.step(action)
        if record:
            replay.append(snapshot(game))
        result = {"seed": seed, "score": game.score, "frames": game.frame, "complete": complete}
        event(episode=result, teacher_mix=beta)
        return result, x, y, replay

    report["baselines"] = {name: summarize(baseline(report["test_seeds"], name, 600)) for name in ("random", "periodic", "teacher")}
    report["status"] = "collecting_teacher_examples"
    save()
    training_x, training_y, validation_x, validation_y = [], [], [], []
    for seed in report["classification_validation_seeds"]:
        _, x, y, _ = episode(seed, collect=True, stop_at=deadline - 240)
        validation_x.extend(x)
        validation_y.extend(y)
    teacher_episodes = []
    for seed in report["training_seeds"]:
        if time.monotonic() >= deadline - 240:
            break
        result, x, y, _ = episode(seed, collect=True, stop_at=deadline - 240)
        teacher_episodes.append(result)
        training_x.extend(x)
        training_y.extend(y)
    if len(training_x) < 256 or len(validation_x) < 64:
        raise RuntimeError("Too few real-network examples collected within the time budget")
    report["teacher_collection"] = summarize(teacher_episodes)
    validation = (np.asarray(validation_x, dtype=np.float32), np.asarray(validation_y, dtype=np.float32))
    best_model, best_score = None, (-1, -1)
    for round_number in range(args.rounds + 1):
        if time.monotonic() >= deadline - 150:
            break
        report["status"] = "fitting_action_decoder"
        save()
        model = ActionDecoder(features.size, seed=7 + round_number)
        fit = model.fit(training_x, training_y, validation, seed=7 + round_number, deadline=deadline - 150)
        model.save(args.output / f"decoder-round-{round_number}.npz")
        evaluations = []
        for seed in report["policy_validation_seeds"]:
            result, _, _, _ = episode(seed, model, beta=0, cap=360, stop_at=deadline - 120)
            if result["complete"]:
                evaluations.append(result)
        score = summarize(evaluations)
        report["rounds"].append({"round": round_number, "fit": fit, "policy_validation": score})
        key = (-1, -1) if score is None else (score["mean_score"], score["mean_frames"])
        if best_model is None or key > best_score:
            best_model, best_score = model, key
            best_model.save(args.output / "decoder.npz")
            report["selected_round"] = round_number
        event(round_completed=round_number, examples=len(training_x), policy_validation=score)
        save()
        if round_number == args.rounds or time.monotonic() >= deadline - 200:
            break
        report["status"] = "aggregating_learner_visited_states"
        aggregation = []
        for seed in range(1200 + args.seed_offset + 10 * round_number, 1206 + args.seed_offset + 10 * round_number):
            if time.monotonic() >= deadline - 200:
                break
            result, x, y, _ = episode(seed, model, beta=0.5 if round_number == 0 else 0.15, collect=True, stop_at=deadline - 200)
            training_x.extend(x)
            training_y.extend(y)
            aggregation.append(result)
        report["rounds"][-1]["aggregation_seeds"] = [x["seed"] for x in aggregation]
        save()
    if best_model is None:
        raise RuntimeError("No decoder checkpoint was trained")
    report["status"] = "evaluating_unseen_pipe_layouts"
    save()
    test_episodes = []
    for number, seed in enumerate(report["test_seeds"]):
        if time.monotonic() >= deadline:
            break
        result, _, _, replay = episode(seed, best_model, beta=0, cap=600, record=number == 0)
        if result["complete"]:
            test_episodes.append(result)
        if number == 0:
            (args.output / "replay.json").write_text(json.dumps({"label": "Recorded decoder pilot; fixed full connectome", "seed": seed, "episode": result, "frames": replay}, separators=(",", ":")) + "\n")
    report["test"] = summarize(test_episodes)
    report["training_examples"] = len(training_x)
    report["classification_validation_examples"] = len(validation_x)
    report["final_weight_sha256"] = hashlib.sha256(brain.weight.tobytes()).hexdigest()
    if report["initial_weight_sha256"] != report["final_weight_sha256"]:
        raise RuntimeError("Frozen connectome weights changed unexpectedly")
    report["status"] = "complete" if len(test_episodes) == len(report["test_seeds"]) else "checkpoint_saved_evaluation_incomplete"
    report["checkpoint"] = "decoder.npz"
    save()
    event(pilot_status=report["status"], test=report["test"])


if __name__ == "__main__":
    main()
