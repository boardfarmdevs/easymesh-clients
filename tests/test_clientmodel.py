"""The resolver's rules: python3 -m unittest discover -s tests"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from clientmodel import (ModelError, iwd_conf, key_mgmt, list_models, load,  # noqa: E402
                         resolve, wpa_cli_commands, wpa_conf)
from clientmodel.resolve import BANDS, MODELS  # noqa: E402


class EveryModel(unittest.TestCase):
    def test_every_model_and_behaviour_resolves(self):
        names = list_models()
        self.assertGreaterEqual(len(names["models"]), 14)
        for name in names["models"]:
            with self.subTest(model=name):
                m = load(name)
                self.assertEqual(m["id"], name)
                self.assertIn(m["implementation"], ("wpa_supplicant", "iwd"))
                self.assertTrue(m["sources"], "every model names its sources")
                resolve(name)
        for behaviour in names["behaviours"]:
            with self.subTest(behaviour=behaviour):
                resolve("pixel" + behaviour)

    def test_files_are_named_by_their_id(self):
        for path in MODELS.glob("*.json"):
            self.assertEqual(json.loads(path.read_text())["id"], path.stem)
        for path in (MODELS / "behaviours").glob("*.json"):
            self.assertEqual(json.loads(path.read_text())["id"], "+" + path.stem)


class Baseline(unittest.TestCase):
    def test_baseline_changes_nothing(self):
        r = resolve("baseline")
        self.assertEqual(r["global"], {})
        self.assertEqual(r["network"], {})
        self.assertIsNone(r["key_mgmt_ft"])
        self.assertEqual(wpa_cli_commands(r), [])

    def test_baseline_configuration_is_plain(self):
        text = wpa_conf(resolve("baseline"), "lab", "passphrase")
        self.assertNotIn("bgscan", text)
        self.assertNotIn("roam_", text)
        self.assertIn("key_mgmt=WPA-PSK\n", text)


class Models(unittest.TestCase):
    def test_iphone(self):
        r = resolve("iphone")
        self.assertEqual(r["global"], {})
        self.assertEqual(r["network"], {"bgscan": "model:10:-70:300", "roam_margin": 12,
                                        "roam_margin_active": 8, "roam_active_pps": 10,
                                        "roam_trigger": -70})
        self.assertIs(r["key_mgmt_ft"], True)

    def test_ipad_resolves_as_iphone(self):
        self.assertEqual(resolve("ipad")["network"], resolve("iphone")["network"])

    def test_pixel_load_trigger_in_two_bands(self):
        r = resolve("pixel")
        self.assertEqual(r["network"]["bgscan"], "model:10:-75:120:70:-70:-75:10:-60:-75")
        self.assertEqual(r["global"], {"btm_policy": 1, "btm_min_margin": 0})

    def test_galaxy_one_load_zone(self):
        self.assertEqual(resolve("galaxy")["network"]["bgscan"], "model:10:-75:120:70:-65:-75:10")

    def test_mac_intel_inherits_mac(self):
        r = resolve("mac-intel")
        self.assertEqual(r["network"]["bgscan"], resolve("mac")["network"]["bgscan"])
        self.assertIs(r["key_mgmt_ft"], False)
        self.assertEqual((r["network"]["disable_he"], r["network"]["disable_eht"]), (1, 1))
        self.assertNotIn("disable_vht", r["network"])

    def test_windows_levels(self):
        for name, trigger in [("windows-intel-lowest", -85), ("windows-intel-medium-low", -80),
                              ("windows-intel", -75), ("windows-intel-medium-high", -70),
                              ("windows-intel-highest", -65)]:
            with self.subTest(model=name):
                n = resolve(name)["network"]
                self.assertEqual(n["roam_trigger"], trigger)
                self.assertEqual(n["bgscan"], f"model:10:{trigger}:120")
                self.assertEqual(n["roam_margin"], 10)

    def test_iot_2g4(self):
        r = resolve("iot-2g4")
        freqs = " ".join(str(f) for f in BANDS["2.4"])
        self.assertEqual(r["network"]["freq_list"], freqs)
        self.assertEqual(r["network"]["scan_freq"], freqs)
        self.assertEqual(r["global"], {"disable_btm": 1})
        self.assertNotIn("bgscan", r["network"])
        for flag in ("disable_vht", "disable_he", "disable_eht"):
            self.assertEqual(r["network"][flag], 1)

    def test_iwd(self):
        r = resolve("linux-iwd")
        self.assertEqual(r["implementation"], "iwd")
        text = iwd_conf(r)
        self.assertIn("[General]\nEnableNetworkConfiguration=false\n", text)
        self.assertIn("RoamThreshold5G=-76\n", text)
        with self.assertRaises(ModelError):
            wpa_conf(r, "lab", "passphrase")


class Behaviours(unittest.TestCase):
    def test_refuser_replaces_the_btm_section(self):
        r = resolve("pixel+btm-refuser")
        self.assertEqual(r["global"], {"btm_policy": 2})
        self.assertEqual(r["network"], resolve("pixel")["network"])
        self.assertEqual(load("pixel+btm-refuser")["title"], "Pixel, refuses BTM")

    def test_ignorer_and_no_11v(self):
        self.assertEqual(resolve("iphone+btm-ignorer")["global"], {"btm_policy": 3})
        self.assertEqual(resolve("iphone+no-11v")["global"], {"disable_btm": 1})

    def test_no_behaviour_on_iwd(self):
        with self.assertRaises(ModelError):
            resolve("linux-iwd+btm-refuser")

    def test_unknown_names(self):
        with self.assertRaises(ModelError):
            resolve("nokia")
        with self.assertRaises(ModelError):
            resolve("pixel+teleports")


class Rules(unittest.TestCase):
    def write(self, directory: Path, **models):
        (directory / "behaviours").mkdir(exist_ok=True)
        for name, body in models.items():
            body = {"schema": "client-model/2", "id": name, **body}
            (directory / f"{name}.json").write_text(json.dumps(body))

    def test_rejected_combinations(self):
        cases = {
            "a": {"implementation": "wpa_supplicant", "load_trigger": {"5": {
                "percent": 70, "rssi_high_dbm": -70, "rssi_low_dbm": -75, "hold_s": 10}}},
            "b": {"implementation": "wpa_supplicant", "moving": {"stay_above_trigger": True}},
            "c": {"implementation": "wpa_supplicant", "moving": {"margin_active_db": 8}},
            "d": {"implementation": "wpa_supplicant", "btm": {"policy": "rules", "min_margin_db": 0}},
            "e": {"implementation": "wpa_supplicant", "btm": {"policy": "accept", "reject_status": 3}},
            "f": {"implementation": "wpa_supplicant", "capabilities": {"bands": ["5", "7"]}},
            "g": {"implementation": "wpa_supplicant", "looking": {"trigger_dbm": -70}},
            "h": {"implementation": "wpa_supplicant", "flies": True},
            "i": {"implementation": "iwd", "moving": {"margin_db": 8}},
            "j": {"base": "k"}, "k": {"base": "j"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.write(directory, **cases)
            for name in cases:
                with self.subTest(model=name), self.assertRaises(ModelError):
                    resolve(name, directory)

    def test_reject_status_is_written_when_not_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.write(directory, a={"implementation": "wpa_supplicant",
                                     "btm": {"policy": "reject", "reject_status": 6}})
            self.assertEqual(resolve("a", directory)["global"],
                             {"btm_policy": 2, "btm_reject_status": 6})

    def test_key_management(self):
        self.assertEqual(key_mgmt("WPA-PSK", True), "WPA-PSK FT-PSK")
        self.assertEqual(key_mgmt("SAE WPA-PSK", True), "SAE WPA-PSK FT-SAE FT-PSK")
        self.assertEqual(key_mgmt("WPA-PSK FT-PSK", False), "WPA-PSK")
        self.assertEqual(key_mgmt("WPA-PSK", None), "WPA-PSK")
        with self.assertRaises(ModelError):
            key_mgmt("FT-PSK", False)

    def test_environment_options_stay_apart(self):
        text = wpa_conf(resolve("pixel"), "lab", "passphrase", environment={"freq_list": "5180"})
        self.assertLess(text.index("freq_list=5180"), text.index("btm_policy=1"))
        with self.assertRaises(ModelError):
            wpa_conf(resolve("pixel"), "lab", "passphrase", environment={"btm_policy": 0})

    def test_wpa_cli_commands_end_with_a_reassociation(self):
        commands = wpa_cli_commands(resolve("iphone"), 0)
        self.assertEqual(commands[0], ["set_network", "0", "bgscan", '"model:10:-70:300"'])
        self.assertEqual(commands[-1], ["reassociate"])


if __name__ == "__main__":
    unittest.main()
