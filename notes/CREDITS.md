# Credits and sources

Flappy Fly is an independent community experiment. The institutions below made the
underlying research or tools; they do not endorse this project.

## The mapped anatomy

**MaleCNS v1.0**, from HHMI Janelia’s FlyEM team, Google Research, and their
collaborators, supplies the anatomical connectivity. Its upstream reconstruction,
annotation, and proofreading are the foundation of this experiment.

- [Official MaleCNS project](https://male-cns.janelia.org/)
- [Official release downloads](https://male-cns.janelia.org/download/)
- [Exact source URLs, sizes, and SHA-256 hashes](../fly_neural/sources.lock.json)
- [Recorded import and preparation reports](../benchmarks/2026-09-11-github/)

The data is distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Flappy Fly transforms release tables into directed, weighted graph arrays under the
upstream inclusion policy. The retained network excludes glia and unresolved objects; a
connection map does not fully specify physiological dynamics.

## Neural software

The `fly_neural/` directory is copied from
[`nftechie/stonkfly`](https://github.com/nftechie/stonkfly), commit
`78ef3e05ab0fa086032098558d893667068944a0`.

Its approximate spiking dynamics, display projection, import code, and experimental
plasticity code retain the [upstream MIT license](../fly_neural/UPSTREAM_LICENSE),
copyright 2026 nftechie and DOOMFLY contributors. The current Flappy Fly pilots hold the
mapped weights fixed; the presence of upstream plasticity code does not mean it was
trained.

## Learning method

The collection of teacher labels on learner-visited states follows the idea of dataset
aggregation:

Stéphane Ross, Geoffrey Gordon, and J. Andrew Bagnell (2011),
[A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning](https://proceedings.mlr.press/v15/ross11a.html).

The concrete implementation and its limits are documented in [LEARNING.md](LEARNING.md).

## Game and visual identity

The one-button obstacle mechanic is inspired by **Flappy Bird**, created by Dong Nguyen.
The game code, fly illustration, branding, interface, and scenery in this repository are
original project assets; no original Flappy Bird sprites or audio are bundled.

The fly specimen is a stylized illustration, not an anatomical rendering of the dataset.
The game’s scenery is decorative. Measured model inputs and responses are explicitly
labeled in the evidence explorer. The artwork’s editable source is
[build_brand.py](../scripts/build_brand.py).

## Type and tooling

The site self-hosts **Barlow Condensed**, **Sora**, and **DM Mono**, sourced from the
[Google Fonts repository](https://github.com/google/fonts). Each font retains its SIL
Open Font License. Download locations and SHA-256 hashes are recorded in
[`docs/assets/fonts/sources.json`](../docs/assets/fonts/sources.json).

Python, NumPy, pandas, Apache Arrow, native C++, and GitHub Actions support the
experiments. The browser arcade uses platform canvas and JavaScript APIs; it has no
third-party runtime scripts, tracking, or hosted font requests.
