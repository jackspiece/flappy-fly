import unittest
import numpy as np
from flappy_fly.game import Flappy, Pipe, scene_generator_action


class GameTests(unittest.TestCase):
    def test_seed_and_actions_are_reproducible(self):
        a, b = Flappy(31), Flappy(31)
        for _ in range(180):
            action = scene_generator_action(a)
            self.assertEqual(a.step(action), b.step(action))
            np.testing.assert_array_equal(a.render(), b.render())
            if a.terminated or a.truncated:
                break

    def test_waiting_eventually_hits_ground(self):
        game = Flappy()
        for _ in range(100):
            _, reward, done, _ = game.step(0)
            if done:
                self.assertEqual(reward, -1)
                break
        self.assertTrue(game.terminated)
        with self.assertRaises(RuntimeError):
            game.step(0)

    def test_pipe_collision_and_safe_gap_are_distinct(self):
        hit, safe = Flappy(), Flappy()
        for game in (hit, safe):
            game.pipes[0] = Pipe(game.bird_x, game.ground / 2)
        hit.y = 30
        self.assertTrue(hit.step(0)[2])
        self.assertFalse(safe.step(0)[2])

    def test_pass_is_rewarded_once(self):
        game = Flappy()
        game.pipes[0] = Pipe(game.bird_x - game.radius - game.pipe_width + 1, game.y)
        self.assertGreater(game.step(0)[1], 1)
        self.assertEqual(game.score, 1)
        self.assertLess(game.step(0)[1], 1)
        self.assertEqual(game.score, 1)

    def test_timeout_is_not_a_collision(self):
        game = Flappy(max_frames=1)
        _, _, terminated, truncated = game.step(0)
        self.assertFalse(terminated)
        self.assertTrue(truncated)

    def test_scenes_are_rgb_and_seeds_change_layout(self):
        game = Flappy(1)
        self.assertEqual(game.render().shape, (240, 288, 3))
        self.assertEqual(game.render().dtype, np.uint8)
        self.assertNotEqual(game.pipes[0].center, Flappy(2).pipes[0].center)


if __name__ == "__main__":
    unittest.main()

