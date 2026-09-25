"""Unit tests of the instance reader and the evaluator.

    python -m unittest discover -s scripts
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kpf_instance import Instance, instance_name  # noqa: E402

# four items, capacity 10; the pair {0, 1} is listed twice (costs 3 and 2), the pair {2, 3} once (cost 5)
TINY = """4 3 10
10 8 6 4
5 4 3 2
1 3 2
0 1
1 2 2
1 0
1 5 2
2 3
"""


class EvaluatorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "tiny.txt"
        self.path.write_text(TINY)
        self.ins = Instance.read(self.path, "tiny")

    def tearDown(self):
        self.tmp.cleanup()

    def test_reader(self):
        self.assertEqual((self.ins.n, self.ins.l, self.ins.capacity), (4, 3, 10))
        self.assertEqual(self.ins.pairs, [(0, 1, 3), (1, 0, 2), (2, 3, 5)])

    def test_every_listing_of_a_pair_is_charged(self):
        self.assertEqual(self.ins.evaluate([0, 1]), (10 + 8 - 3 - 2, 9))

    def test_forfeit_needs_both_items(self):
        self.assertEqual(self.ins.evaluate([0, 2]), (16, 8))
        self.assertEqual(self.ins.evaluate([]), (0, 0))

    def test_all_items(self):
        value, weight = self.ins.evaluate([3, 2, 1, 0])
        self.assertEqual((value, weight), (28 - 3 - 2 - 5, 14))
        self.assertGreater(weight, self.ins.capacity)

    def test_invalid_items(self):
        with self.assertRaises(ValueError):
            self.ins.evaluate([0, 0])
        with self.assertRaises(ValueError):
            self.ins.evaluate([4])

    def test_truncated_file(self):
        self.path.write_text(TINY.rsplit("\n", 3)[0])
        with self.assertRaises(ValueError):
            Instance.read(self.path, "tiny")

    def test_instance_name(self):
        name = instance_name("instances/kpf_soco_instances/LK/1000/01_id_116b_objs_1000_size_3000.txt")
        self.assertEqual(name, "LK_1000_01")


if __name__ == "__main__":
    unittest.main()
