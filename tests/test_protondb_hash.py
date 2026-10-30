import json, os, random, shutil, subprocess, sys, unittest
import stubs; stubs.install()
from protondb_hash import VARIANTS, _mix, js_hash, ordered_variants, report_hash

HERE = os.path.dirname(os.path.abspath(__file__))
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node not available")
class JsParity(unittest.TestCase):
    """Compare the Python port with real JavaScript executed by Node."""

    def test_js_hash_matches_node(self):
        rng = random.Random(1234)
        samples = ["a", "p412345p513625178900*vRT1245620p1245620all-devices", "é€😀 unicode"]
        for _ in range(300):
            samples.append("".join(rng.choice("abcXYZ0123456789*-p ") for _ in range(rng.randint(1, 120))))
        out = subprocess.run([NODE, os.path.join(HERE, "js_hash_reference.js")],
                             input="\n".join(samples) + "\n", capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(len(out), len(samples))
        for s, expected in zip(samples, out):
            self.assertEqual(js_hash(s), int(expected), s)

    def test_full_string_and_hash_match_node(self):
        rng = random.Random(99)
        for _ in range(40):
            appid = rng.choice([10, 730, 1245620, 2561580, 3125250, rng.randint(1, 4_000_000)])
            reports = rng.randint(1000, 900_000)
            ts = rng.randint(1_600_000_000, 1_800_000_000)
            for v in VARIANTS:
                res = subprocess.run([NODE, os.path.join(HERE, "js_reference.js"), str(appid), str(reports),
                                      str(ts), str(v.page), v.tail], capture_output=True, text=True, check=True)
                js_string, js_digest = res.stdout.split("\n")[:2]
                py_string = "p" + _mix(appid, str(reports), ts) + "*vRT" + _mix(v.page, str(appid), ts) + v.tail
                self.assertEqual(py_string, js_string)
                self.assertEqual(report_hash(appid, reports, ts, v), js_digest)


class Basics(unittest.TestCase):
    def test_known_vector_from_node(self):
        # produced by: node js_reference.js 1245620 412345 1730000000 1 all-devices
        self.assertEqual(report_hash(1245620, 412345, 1730000000, VARIANTS[0]), "1833617288")

    def test_mix_rejects_bad_timestamp(self):
        with self.assertRaises(ValueError):
            _mix(1, "5", 0)

    def test_values_stay_below_float_precision_limit(self):
        # JS Numbers lose integer precision above 2**53; real inputs are far below.
        self.assertLess(4_000_000 * 900_000, 2 ** 53)

    def test_variant_ordering(self):
        names = [v.name for v in ordered_variants("page0+all")]
        self.assertEqual(names[0], "page0+all")
        self.assertEqual(sorted(names), sorted(v.name for v in VARIANTS))
        self.assertEqual(ordered_variants(None)[0], VARIANTS[0])


if __name__ == "__main__":
    unittest.main()
