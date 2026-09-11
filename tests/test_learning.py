from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from flappy_fly.learning import ActionDecoder, NeuralFeatures, high_contrast, reference_action
from flappy_fly.game import Flappy


class LearningTests(unittest.TestCase):
    def test_spatial_features_remove_shared_rate_but_keep_contrast(self):
        brain = SimpleNamespace(
            retina=np.asarray([0, 1]), uv=np.asarray([[0, 0.5], [1, 0.5]]),
            r8=np.asarray([0, 1]), r8_uv=np.asarray([[0, 0.5], [1, 0.5]]),
            r8_channel=np.asarray([1, 2]), superclass=np.asarray(["sensory", "sensory"]),
        )
        features = NeuralFeatures(brain, columns=2, rows=1)
        uniform = features.extract(np.ones(2), 0, 20)
        np.testing.assert_allclose(uniform[:2], 0)
        contrast = features.extract(np.asarray([0, 1]), 0, 21)
        self.assertLess(contrast[0], 0)
        self.assertGreater(contrast[1], 0)
        self.assertTrue(np.isfinite(contrast).all())

    def test_reference_teacher_can_navigate_development_layouts(self):
        for seed in range(1400, 1405):
            game = Flappy(seed, max_frames=1200)
            last_flap = -100
            while not (game.terminated or game.truncated):
                action = int(reference_action(game) and game.frame - last_flap >= 4)
                if action:
                    last_flap = game.frame
                game.step(action)
            self.assertEqual(game.score, 20, f"Teacher failed seed {seed}")

    def test_decoder_learns_and_checkpoint_preserves_predictions(self):
        rng = np.random.default_rng(3)
        x = rng.normal(size=(800, 6)).astype(np.float32)
        y = (x[:, 0] + 0.6 * x[:, 1] > 0.7).astype(np.float32)
        model = ActionDecoder(6, hidden=16)
        before = model.classification(model.probabilities(x[600:]), y[600:])["loss"]
        result = model.fit(x[:600], y[:600], (x[600:], y[600:]))
        after = model.classification(model.probabilities(x[600:]), y[600:], model.threshold)
        self.assertLess(after["loss"], before * 0.65)
        self.assertGreater(after["f1"], 0.85)
        self.assertGreater(result["positive_examples"], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decoder.npz"
            model.save(path)
            loaded = ActionDecoder.load(path)
            np.testing.assert_allclose(model.probabilities(x), loaded.probabilities(x), atol=1e-7)
            self.assertEqual(model.threshold, loaded.threshold)

    def test_training_requires_both_actions(self):
        model = ActionDecoder(3)
        x = np.zeros((10, 3), dtype=np.float32)
        with self.assertRaises(ValueError):
            model.fit(x, np.zeros(10), (x, np.zeros(10)))

    def test_contrast_adapter_uses_pixels_and_preserves_dimensions(self):
        original = Flappy().render()
        converted = high_contrast(original)
        self.assertEqual(converted.shape, original.shape)
        self.assertEqual(converted.dtype, np.uint8)
        self.assertEqual(set(np.unique(converted).tolist()), {0, 255})
        np.testing.assert_array_equal(converted[:, :, 0], converted[:, :, 1])


if __name__ == "__main__":
    unittest.main()
