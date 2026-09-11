# The flight log

These are preliminary decoder-learning pilots using the complete retained MaleCNS graph.
The mapped synaptic weights remain fixed. Each folder preserves the report, selected
checkpoint, first-test replay, and source/run receipt.

## Pilot 02 · September 11, 2026

**Result: 0, 0, 0 pipes on test seeds 9101, 9102, 9103.** Each episode ended after 58
frames. The privileged teacher cleared 9 pipes per test layout at the 600-frame cap. The
selected decoder is not a reliable controller.

The run collected 6,212 training examples in three fitting rounds. Round 1 was selected
by policy-validation score and then mean frames alive; its checkpoint was fitted on
5,292 examples. Final test performance did not determine checkpoint selection. Total
training-script elapsed time was 313.79 seconds.

The experiment corrected the scene-generator teacher and centered the retinal spike
grids. Both changes are part of the same pilot, so the result does not isolate either
change. Feature schema: `centered-spike-grids-v2`.

- [Report](pilot-02/report.json)
- [Selected checkpoint](pilot-02/decoder.npz)
- [First-test recording](pilot-02/replay.json)
- [Run provenance and file hashes](pilot-02/run.json)
- [GitHub Actions execution](https://github.com/jackspiece/flappy-fly/actions/runs/34625990529)

## Pilot 01 · September 11, 2026

**Result: 0, 0, 0 pipes on test seeds 9001, 9002, 9003.** The pilot collected 1,935
examples; the selected decoder was fitted on 1,437. Its original teacher also failed all
three test layouts; that scene-generating controller flapped too early for reliable
play.

One validation episode cleared two pipes. That validation result is not the held-out
result. The original report and checkpoint remain available:

- [Report](pilot-01/report.json)
- [Checkpoint](pilot-01/decoder.npz)
- [First-test recording](pilot-01/replay.json)
- [Run provenance](pilot-01/run.json)

## What we know so far

The complete retained graph fits within the measured CPU runner’s memory and supports
short learning pilots. Neither pilot has demonstrated reliable game control or an
advantage over simpler representations. A useful next experiment would test whether the
visual adapter and features preserve the information needed for control, with matched
simpler and shuffled-network baselines.

The two pilots use different test layouts. They are records of separate experiments, not
a controlled before-and-after comparison.

To reproduce an archive, use its recorded source commit and feature schema. All neural
checkpoints use NumPy files read with `allow_pickle=False`. See
[the method](../notes/LEARNING.md) for seeds, selection, and collection rules.
