"""Integration checks that visual drive propagates through the native graph."""

from pathlib import Path
import tempfile
import unittest

import numpy as np

from fly_neural.brain import MemoryBrain
from scripts.benchmark import empty_circuit


class NeuralPathTests(unittest.TestCase):
    def make_brain(self, path, connected):
        np.savez(
            path,
            ptr=np.asarray([0, int(connected), int(connected), int(connected)], dtype=np.int64),
            post=np.asarray([1] if connected else [], dtype=np.int32),
            weight=np.asarray([200] if connected else [], dtype=np.float32),
            ids=np.arange(3, dtype=np.int64),
            retina=np.asarray([0], dtype=np.int32),
            uv=np.asarray([[0.5, 0.5]], dtype=np.float32),
            lamina=np.empty(0, dtype=np.int32),
            sugar=np.empty(0, dtype=np.int32),
            superclass=np.asarray(["synthetic"] * 3, dtype="U64"),
        )
        return MemoryBrain(
            path=path, circuit=empty_circuit(3),
            modulation_mask=np.zeros(3, dtype=np.uint8),
        )

    def test_connected_neuron_responds_but_isolated_neuron_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            counts = []
            for connected in (False, True):
                brain = self.make_brain(Path(directory) / f"{connected}.npz", connected)
                spikes, _ = brain.step(np.ones(1, dtype=np.float32), 60, learning=False)
                self.assertGreater(spikes[0], 0)
                self.assertEqual(spikes[2], 0)
                self.assertTrue(np.isfinite(brain.v).all())
                counts.append(spikes)
            self.assertEqual(counts[0][1], 0)
            self.assertGreater(counts[1][1], 0)


if __name__ == "__main__":
    unittest.main()
