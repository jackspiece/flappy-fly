from pathlib import Path
import tempfile
import unittest

import numpy as np

from flappy_fly.learning import ActionDecoder, high_contrast
from flappy_fly.game import Flappy


class LearningTests(unittest.TestCase):
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
