"""Fetch the pinned official release and compile the complete retained graph."""

from pathlib import Path
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_verified(target, record):
    if target.exists():
        if target.stat().st_size == record["bytes"] and file_hash(target) == record["sha256"]:
            print(f"Verified cached {target.name}", flush=True)
            return
        raise ValueError(f"Existing {target.name} does not match the pinned release")
    temporary = target.with_suffix(target.suffix + ".partial")
    digest = hashlib.sha256()
    total = 0
    print(f"Downloading {target.name}: {record['bytes']} bytes", flush=True)
    with urllib.request.urlopen(record["url"], timeout=60) as response, temporary.open("wb") as output:
        while block := response.read(4 * 1024 * 1024):
            output.write(block)
            digest.update(block)
            total += len(block)
    if total != record["bytes"] or digest.hexdigest() != record["sha256"]:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"Downloaded {target.name} failed size/hash verification")
    temporary.replace(target)
    print(f"Verified {target.name}", flush=True)


def main():
    started = time.perf_counter()
    destination = Path(os.environ.get("STONKFLY_DATA", ROOT / "data")).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / "fly_neural/sources.lock.json").read_text())
    for name, record in lock.items():
        download_verified(destination / name, record)
    phases = {"download_and_verify_seconds": time.perf_counter() - started}
    env = dict(os.environ, STONKFLY_DATA=str(destination))
    # Separate processes release temporary import/sort buffers before simulation.
    for module, function in [("connectome", "import_graph"), ("prepare", "prepare")]:
        phase_start = time.perf_counter()
        subprocess.run(
            [sys.executable, "-c", f"from fly_neural.{module} import {function}; {function}()"],
            cwd=ROOT, env=env, check=True,
        )
        phases[module + "_seconds"] = time.perf_counter() - phase_start
    import numpy as np
    expected = json.loads((ROOT / "fly_neural/arrays.lock.json").read_text())
    with np.load(destination / "graph.npz", allow_pickle=False) as graph:
        for name, wanted in expected.items():
            actual = hashlib.sha256(graph[name].tobytes()).hexdigest()
            if actual != wanted:
                raise ValueError(f"Prepared array {name} differs from the pinned upstream graph")
        summary = {"verified_full_graph": True, "neurons": len(graph["ids"]), "edges": len(graph["post"])}
    rss_divisor = 1024 ** 2 if sys.platform == "darwin" else 1024
    summary.update({
        "phase_times": phases,
        "total_seconds": time.perf_counter() - started,
        "peak_child_process_rss_mib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / rss_divisor,
        "peak_verifier_process_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / rss_divisor,
    })
    (destination / "preparation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
