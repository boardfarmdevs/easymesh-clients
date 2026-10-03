#!/usr/bin/env python3
"""The roaming bench: a client model between two access points.

  bench.py run MODEL TEST [--runs N]          one test with one model
  bench.py suite [--models A,B] [--tests B0,B1] [--runs N]
                                              every applicable test of every model
  bench.py reference [--runs N]               B12: baseline on the RDK lab's 2.10 build

MODEL is a nickname with optional behaviours (pixel+btm-refuser). Each run
writes OUT/MODEL/TEST/run-N/ (timeline.jsonl, the configurations, the logs,
result.json) and appends its result to OUT/results.jsonl. Runs as root on a
host or VM that can load mac80211_hwsim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from clientmodel import iwd_conf, list_models, load, resolve, wpa_conf  # noqa: E402
from clientmodel.resolve import MODELS  # noqa: E402
import cases  # noqa: E402
from rig import PSK, RUN, SSID, Rig  # noqa: E402

BEHAVIOURS = ["pixel+btm-refuser", "pixel+btm-ignorer", "pixel+no-11v", "iphone+btm-refuser"]
BEHAVIOUR_TESTS = ["B0", "B5"]
REFERENCE_TESTS = ["B0", "B1", "B2", "B3", "B5"]
# The bench's own global options: its scans cover its two channels (5180 and
# 2412 MHz) and so take well under a second, as a phone's full scan takes a few
# seconds; without this a scan of every channel on mac80211_hwsim takes 15 to
# 30 s while associated, during which a walk moves 7 to 15 dB.
ENVIRONMENT = {"freq_list": "5180 2412"}


def model_file_hash(name: str) -> str:
    nickname, *behaviours = name.split("+")
    h = hashlib.sha256()
    paths = [MODELS / f"{nickname}.json"] + [MODELS / "behaviours" / f"{b}.json" for b in behaviours]
    base = json.loads(paths[0].read_text()).get("base")
    while base:
        paths.append(MODELS / f"{base}.json")
        base = json.loads((MODELS / f"{base}.json").read_text()).get("base")
    for p in paths:
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def run_one(args, model_name: str, case: cases.Case, run_dir: Path, binary: str) -> dict:
    model = load(model_name)
    resolved = resolve(model)
    bands = case.bands(model)
    ap1, ap2 = f"ap1-{bands[0]}", f"ap2-{bands[0]}"
    initial = {({"ap1": ap1, "ap2": ap2}.get(k, k)): v for k, v in case.initial.items()}
    load_ = {({"ap1": ap1, "ap2": ap2}.get(k, k)): v for k, v in case.load(model).items()}
    if model.get("implementation") == "iwd":
        binary = "iwd"
    result = {"model": model_name, "test": case.id, "title": case.title, "kind": case.kind,
              "binary": binary, "model_hash": model_file_hash(model_name),
              "run": run_dir.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    build_env = args.build / "build.env"
    if build_env.exists():
        result["build"] = dict(line.split("=", 1) for line in build_env.read_text().splitlines()
                               if "=" in line)
    rig = None
    try:
        rig = Rig(args.build, args.wmediumd, args.medium, run_dir, bands=bands, load=load_,
                  levels=initial)
        if model.get("implementation") == "iwd":
            rig.start_iwd(iwd_conf(resolved), args.iwd)
        else:
            rig.start_wpa(wpa_conf(resolved, SSID, PSK, ctrl_interface=str(RUN / "wpa"),
                                   environment=ENVIRONMENT), binary)
        if case.dual_band:  # which band it chooses is what the test records
            first = "either access point"
            c = cases.wait_for(lambda: next(iter(cases.connections(rig)), None), cases.CONNECT_S)
        else:
            first = max(initial, key=lambda k: initial[k])
            c = cases.wait_connected(rig, first)
        if not c:
            result.update(verdict="error", error=f"no association to {first} in {cases.CONNECT_S} s")
        else:
            rig.associated_at = c[0]
            result.update(case.execute(rig, model))
    except Exception as e:
        result.update(verdict="error", error=f"{type(e).__name__}: {e}",
                      traceback=traceback.format_exc()[-2000:])
    finally:
        if rig:
            try:
                rig.close()
            except Exception as e:
                result.setdefault("cleanup_error", str(e))
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (run_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def record(args, result: dict) -> None:
    with (args.out / "results.jsonl").open("a") as f:
        f.write(json.dumps(result) + "\n")
    print(f"{result['model']:<24} {result['test']:<4} {result['run']:<6} {result['verdict']:<9}"
          f" {result.get('error', '')}", flush=True)


def runs(args, model_name: str, case: cases.Case, binary: str = "wpa_supplicant",
         label: str | None = None) -> list[dict]:
    out = []
    for n in range(1, args.runs + 1):
        run_dir = args.out / (label or model_name) / case.id / f"run-{n}"
        if args.resume and (run_dir / "result.json").exists():
            continue
        result = run_one(args, model_name, case, run_dir, binary)
        if label:
            result["label"] = label
        record(args, result)
        out.append(result)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--build", type=Path, default=Path("/root/build"))
    p.add_argument("--wmediumd", type=Path, default=Path("/root/wmediumd/wmediumd"))
    p.add_argument("--medium", type=Path, default=Path("/root/medium"),
                   help="an easymesh-medium checkout (its configurator's control client)")
    p.add_argument("--iwd", type=Path, default=Path("/root/build/iwd"))
    p.add_argument("--out", type=Path, default=Path("/root/bench-runs"))
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--resume", action="store_true", help="skip runs that already have a result")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("model")
    r.add_argument("test")
    s = sub.add_parser("suite")
    s.add_argument("--models")
    s.add_argument("--tests")
    sub.add_parser("reference")
    args = p.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)

    if args.command == "run":
        runs(args, args.model, cases.BY_ID[args.test])
    elif args.command == "suite":
        names = args.models.split(",") if args.models else list_models()["models"] + BEHAVIOURS
        tests = args.tests.split(",") if args.tests else list(cases.BY_ID)
        for name in names:
            model = load(name)
            for test in tests:
                case = cases.BY_ID[test]
                # a behaviour changes the BTM answer only: B0 and B5 are its tests
                if "+" in name and test not in BEHAVIOUR_TESTS:
                    continue
                if case.applies(model):
                    runs(args, name, case)
    elif args.command == "reference":
        for test in REFERENCE_TESTS:
            runs(args, "baseline", cases.BY_ID[test], binary="wpa_supplicant-2.10",
                 label="baseline@2.10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
