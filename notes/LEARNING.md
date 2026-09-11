# The first learning pilot

This pilot trains an action decoder from the activity of the complete retained
MaleCNS network. The biological connections and their simulated weights remain
fixed. It is a test of learning a useful readout, not evidence that the fly's
synapses have learned Flappy Bird or that the connectome beats conventional AI.

Each game image is converted to high-contrast black and white using a luminance
threshold. The full neural simulation processes that image for 10 ms. Inputs to
the decoder are spatial groups of photoreceptor spikes, anatomical population
rates, recent activity changes, and the controller's own previous action and
flap timing. Bird coordinates, pipe coordinates, velocity, score, and the
teacher's decision never enter the decoder inputs.

The decoder is a small neural network with a 48-unit hidden layer, trained with
Adam. The first stage is behavioral cloning from the scripted teacher. Later
rounds add teacher labels on states visited by a mixture of the current decoder
and the teacher, following the idea of dataset aggregation (DAgger). This is
imitation learning; reward-based fine-tuning is a separate future experiment.

## Evaluation

Training, classification validation, policy selection, and final evaluation use
separate seed sets recorded in the report. A seed offset distinguishes pilots;
pilot 02 evaluates on 9101, 9102, and 9103, up to 600 frames each. Random,
periodic, and scripted-teacher
controllers run on the same evaluation seeds. The teacher has privileged game
state and is a reference, not a fair architecture comparison.

The first evaluation seed supplies the replay, regardless of its score. Results
are not selected for an impressive video. Three seeds provide a preliminary
check, not a broad generalization claim. The input contrast and learned decoder
also mean these results should not be confused with the earlier runtime test's
unmodified RGB inputs.

## Reproduce

After preparing the full map:

```sh
python scripts/train_pilot.py --wall-seconds 720 --rounds 2 --seed-offset 100
```

The manual **Learning pilot** workflow uses the same command on a standard
Ubuntu runner with a 20-minute job limit. It saves intermediate decoder
checkpoints, optimization histories, episode scores, the first test replay, and
weight hashes confirming that the underlying connectome stayed fixed. The
script reserves time for evaluation and can report an incomplete evaluation if
its budget runs out. Raw training feature arrays are not uploaded.

Reports and checkpoints are written under `results/learning-pilot/` and uploaded
as a seven-day workflow artifact. Loading checkpoints uses NumPy with
`allow_pickle=False`.

Reference: Ross, Gordon, and Bagnell (2011),
[A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning](https://proceedings.mlr.press/v15/ross11a.html).

## Pilot 01 and the reference correction

Pilot 01 trained a decoder on 1,935 examples, but cleared no pipes on its three
test layouts. Its scripted teacher also failed all three. That teacher was a
scene generator for the runtime test, and its lookahead made it flap too early
for reliable navigation.

Pilot 02 uses a centering reference: flap when the fly falls below the gap
center plus 12 pixels, respecting a four-frame actuator interval. It cleared
20 pipes on each of 20 development seeds, 1000–1019, at a 1,200-frame cap.
The game physics and the earlier benchmark's recorded input scenes are
unchanged. Pilot 01's report and checkpoint remain available under
`experiments/pilot-01/`; pilot 02 uses fresh test seeds.

Pilot 02 also centers each spatial spike grid by its occupied-cell mean, to
reduce shared firing-rate variation while keeping spatial contrast. Its
feature schema is `centered-spike-grids-v2`; pilot 01 checkpoints must be used
with their recorded source commit, which used uncentered grids. The teacher and
feature changes are recorded together, so this is not an isolated causal test
of either change.
