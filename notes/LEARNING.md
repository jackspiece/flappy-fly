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
separate seed sets recorded in the report. The final evaluation uses seeds 9001,
9002, and 9003, up to 600 frames each. Random, periodic, and scripted-teacher
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
python scripts/train_pilot.py --wall-seconds 720 --rounds 2
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
