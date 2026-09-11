# Build with Flappy Fly

The next useful contribution could be a better question, a clearer measurement, or a
more enjoyable flight. Small, reproducible changes are welcome.

## Work on the arcade

Serve `docs/` with any static web server. No bundler is required. The editable interface
is in `docs/index.html`, `docs/assets/site.css`, and `docs/assets/app.mjs`. Browser
physics and rendering live in `docs/assets/game.mjs`.

For development checks, use Node.js 24+, Python 3.12+, NumPy, a C++17 compiler, and
Chrome or Chromium:

```sh
npm ci
python -m pip install numpy
python -m unittest discover -s tests -v
npm test
npm run test:browser
python scripts/build_site_data.py --check
npm run format:check
```

`npm run test:browser` starts a local server and an isolated headless browser, checks
interactions and responsive layouts, saves screenshots in `results/`, and stops its own
processes. Set `CHROME_BIN` if the browser is not on your PATH. It never uses your
personal browser profile.

Use `npm run format` before submitting frontend or documentation changes. The formatter
excludes vendored neural code, generated data, and recorded results.

Check phone and desktop screenshots. Keep keyboard focus visible, touch controls usable,
reduced motion supported, and controller labels accurate. A scripted game preview must
never be presented as a trained model’s performance.

## Reproduce or extend the science

Start with [the method](notes/LEARNING.md) and
[the experiment log](experiments/README.md). The complete runtime packages are in
`requirements.txt`; preparing the map downloads about 1.11 GB.

State the hypothesis before comparing models. Record the exact source revision, feature
schema, seeds, training budget, trained parameters, checkpoint-selection rule, and
held-out results. Keep the scripted teacher’s privileged information out of decoder
inputs.

Keep archived reports intact. Add a new pilot directory for a new experiment, including
a report, checkpoint, first-test replay, and source/run receipt. Feature changes require
a new schema identifier. Do not tune on the final test layouts.

`scripts/build_site_data.py` exports the latest archived pilot to the site and
reproduces benchmark input frames. Its `--check` mode verifies that generated assets are
current. Use a full Git checkout: the exporter checks the original benchmark’s
historical game source before reproducing those frames.

The native source in `fly_neural/` is pinned upstream code. Document and test any
intentional divergence; do not reformat it as part of unrelated work.

## Open a change

Describe the problem, the resulting behavior, and the checks you ran. For visual
changes, include desktop and phone screenshots. For experiments, link the raw report and
include weak results as well as strong ones.

Use an issue to propose a larger experiment or report a reproducibility problem. Be
specific, curious, and respectful of other contributors.
