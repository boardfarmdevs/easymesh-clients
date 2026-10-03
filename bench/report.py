#!/usr/bin/env python3
"""Turn the bench's results into the records kept in this repository.

  report.py RESULTS.jsonl [RESULTS.jsonl ...] --out docs/records/bench-DATE

Writes results.json (every run's measures, without timelines) and cards.md (a
behaviour card per model: what the model says next to what the bench measured).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from clientmodel import load  # noqa: E402

DROP = {"build", "traceback", "started", "finished"}


def read(paths: list[Path]) -> list[dict]:
    runs = {}
    for path in paths:
        for line in path.read_text().splitlines():
            r = json.loads(line)
            key = (r.get("label") or r["model"], r["test"], r["run"])
            runs[key] = r  # a later result of the same run replaces an earlier one
    return [runs[k] for k in sorted(runs)]


def tally(runs: list[dict]) -> str:
    verdicts = [r["verdict"] for r in runs]
    if all(v == "recorded" for v in verdicts):
        return f"recorded ({len(verdicts)})"
    passed, errors = verdicts.count("pass"), verdicts.count("error")
    word = "pass" if passed == len(verdicts) else "**FAIL**" if passed == 0 else "**mixed**"
    text = f"{word} {passed}/{len(verdicts)}"
    return text + (f", {errors} error(s)" if errors else "")


def num(v) -> str:
    """A number as the documents write it: a true minus sign, times to 0.1 s."""
    if isinstance(v, float):
        v = round(v, 1)
    return str(v).replace("-", "\u2212")


def ap(role) -> str:
    """ap1-5 -> AP1; ap2-2.4 -> AP2 (2.4 GHz)."""
    if not role:
        return str(role)
    name, _, band = str(role).partition("-")
    label = name.upper()
    return label if band == "5" else f"{label} ({band} GHz)"


def values(runs: list[dict], key: str, unit: str = "") -> str:
    vals = [r.get(key) for r in runs]
    if all(v is None for v in vals):
        return "none"
    return ", ".join("—" if v is None else f"{num(v)}{unit}" for v in vals)


def btm_text(r: dict) -> str:
    a = r.get("answer")
    target = a.get("target") if a else None
    if target == "00:00:00:00:00:00":
        target = None
    answer = "no answer" if not a else f"status {a['status']}" + (
        f", target {ap(target)}" if target else ", no target")
    moved = f"moved to {ap(r['moved_to'])}" if r.get("moved_to") else "stayed"
    return f"{answer}; {moved}"


def describe(test: str, runs: list[dict], model: dict) -> tuple[str, str]:
    """(what the model says, what the bench measured) for one test."""
    looking = model.get("looking", {})
    moving = model.get("moving", {})
    btm = model.get("btm", {})
    iwd = model.get("implementation") == "iwd"
    if test == "B0":
        pings = {r.get("ping") for r in runs}
        return "associates, passes traffic", (
            "associated in " + values(runs, "associated_at", " s") + "; the server "
            + ("answered" if pings == {True} else "did not always answer"))
    if test == "B1":
        trig = looking.get("trigger_dbm", model.get("iwd", {}).get("RoamThreshold5G"))
        says = f"looks below {num(trig)} dBm" if trig is not None else "no background scanning"
        bounds = runs[0].get("bounds")
        if all(r.get("look_level") is None and r.get("move_t") is None for r in runs):
            return says, "never looked; stayed on AP1 down to \u221290 dBm"
        got = "looked at " + values(runs, "look_level", " dBm")
        if bounds:
            got += f" (bounds {num(bounds[0])} to {num(bounds[1])})"
        got += "; moved with AP1 at " + values(runs, "move_ap1_level", " dBm")
        return says, got
    if test == "B2":
        says = "stays above its trigger" if moving.get("stay_above_trigger") or iwd \
            else "no move by itself"
        return says, values(runs, "moves") + " moves in 120 s" + ("" if iwd else " with three scans")
    if test in ("B3", "B4"):
        m = moving.get("margin_active_db" if test == "B4" else "margin_db")
        says = f"moves for {m} dB" if m is not None else "upstream table"
        if all(r.get("move_t") is None for r in runs):
            # the walk raises AP2 to 27 dB above AP1 when the model names no margin
            return says, "stayed while AP2 rose to 27 dB above AP1 (no scan to act on)" \
                if m is None else "stayed"
        got = "moved at " + values(runs, "margin_seen", " dB")
        if runs[0].get("bounds"):
            got += f" (bounds {runs[0]['bounds'][0]} to {runs[0]['bounds'][1]})"
        return says, got
    if test in ("B5", "B5b", "B6"):
        if iwd:
            policy = "iwd: follows, never answers"
        elif model.get("capabilities", {}).get("btm") is False:
            policy = "no 802.11v"
        else:
            policy = btm.get("policy", "rules")
        if "min_margin_db" in btm:
            policy += f", minimum margin {btm['min_margin_db']} dB"
        got = "; ".join(sorted({btm_text(r) for r in runs}))
        predicted = [r.get("as_predicted") for r in runs if r.get("predicted") is not None]
        if predicted and all(predicted):
            got += " (as its policy predicts)"
        elif predicted:
            got += f" (**differs from its policy's prediction** in {predicted.count(False)} run(s))"
        return policy, got
    if test == "B7":
        def one(r):
            first = btm_text({"answer": r.get("answer"), "moved_to": None}).split(";")[0]
            joined = [ap(role) for _, role in r.get("connections") or []]
            path = ("; then associated to " + ", then ".join(joined)) if joined else "; stayed"
            return f"{first}{path}; {r.get('disconnects')} disconnection(s)"
        return "not documented", "; ".join(sorted({one(r) for r in runs}))
    if test == "B8":
        zone = model.get("load_trigger", {}).get("5")
        says = (f"looks when over {zone['percent']} % busy at {num(zone['rssi_high_dbm'])} to "
                f"{num(zone['rssi_low_dbm'])} dBm" if zone else "no load trigger (the control)")
        if all(r.get("move_after_s") is None for r in runs):
            return says, "stayed for 60 s"
        return says, "looked for load and moved after " + values(runs, "move_after_s", " s")
    if test == "B9":
        bands = model.get("capabilities", {}).get("bands") or ["2.4", "5", "6"]
        return "bands " + ", ".join(bands), "; ".join(sorted({
            "on " + " and ".join(str(f) for f in r.get("frequencies") or []) + " MHz" for r in runs}))
    if test == "B10":
        return f"margin {moving.get('margin_db')} dB", values(runs, "moves") + " moves in 10 min"
    return "", ""


def cards(runs: list[dict]) -> str:
    by_model = defaultdict(lambda: defaultdict(list))
    for r in runs:
        by_model[r.get("label") or r["model"]][r["test"]].append(r)
    order = ["B0", "B1", "B2", "B3", "B4", "B5", "B5b", "B6", "B7", "B8", "B9", "B10"]
    out = []
    for name in by_model:
        model = load(name.split("@")[0])
        first = next(iter(next(iter(by_model[name].values()))))
        out.append(f"## `{name}`: {model.get('title', name)}\n")
        resembles = "; ".join(model.get("resembles", []))
        out.append(f"Resembles {resembles}. Model file hash `{first.get('model_hash')}`, "
                   f"client `{first.get('binary')}`.\n")
        out.append("| Test | The model says | The bench measured | Result |")
        out.append("| --- | --- | --- | --- |")
        for test in order:
            if test not in by_model[name]:
                continue
            rs = by_model[name][test]
            says, got = describe(test, rs, model)
            errors = [r.get("error") for r in rs if r["verdict"] == "error"]
            if errors:
                short = errors[0] if len(errors[0]) <= 90 else errors[0][:87] + "..."
                got += f" (error: {short})"
            out.append(f"| {test} {rs[0]['title']} | {says} | {got} | {tally(rs)} |")
        out.append("")
    return "\n".join(out)


def outcome(r: dict) -> str:
    """The outcome of one run, in the terms B12 compares."""
    test = r["test"]
    if r["verdict"] == "error":
        return "error"
    if test == "B0":
        return "associates, ping " + ("answers" if r.get("ping") else "fails")
    if test == "B1":
        look = "looks" if r.get("look_level") is not None else "never looks"
        if r.get("move_t") is None:
            return f"{look}, stays"
        return f"{look}, moves to AP2 when AP1 is at {r.get('move_ap1_level')} dBm"
    if test == "B2":
        return f"{r.get('moves')} moves"
    if test == "B3":
        return "stays" if r.get("move_t") is None else f"moves at {r.get('margin_seen')} dB"
    if test in ("B5", "B5b", "B6"):
        return btm_text(r)
    return r["verdict"]


def reference(runs: list[dict]) -> tuple[str, bool]:
    """B12: baseline on 2.12 against baseline on the RDK lab's 2.10, test by test."""
    new = defaultdict(list)
    old = defaultdict(list)
    for r in runs:
        if r.get("label") == "baseline@2.10":
            old[r["test"]].append(r)
        elif r["model"] == "baseline" and not r.get("label"):
            new[r["test"]].append(r)
    if not old:
        return "", True
    lines = ["| Test | 2.12, `baseline` | 2.10, the RDK lab's build | The same |",
             "| --- | --- | --- | --- |"]
    same_all = True
    for test in sorted(old, key=lambda x: (len(x), x)):
        a = sorted({outcome(r) for r in new.get(test, [])})
        b = sorted({outcome(r) for r in old[test]})
        same = a == b
        same_all &= same
        lines.append(f"| {test} {old[test][0]['title']} | {'; '.join(a) or 'not run'} | "
                     f"{'; '.join(b)} | {'yes' if same else '**no**'} |")
    return "\n".join(lines), same_all


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("results", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    runs = read(args.results)
    args.out.mkdir(parents=True, exist_ok=True)
    slim = [{k: v for k, v in r.items() if k not in DROP} for r in runs]
    builds = {json.dumps(r.get("build", {}), sort_keys=True) for r in runs}
    (args.out / "results.json").write_text(json.dumps(
        {"builds": [json.loads(b) for b in sorted(builds)], "runs": slim}, indent=1) + "\n")
    text = cards([r for r in runs if r.get("label") != "baseline@2.10"])
    table, same = reference(runs)
    if table:
        text += ("\n## B12: the default did not change\n\n"
                 f"`baseline` on wpa_supplicant 2.12 with the patch series, against the RDK lab's "
                 f"2.10 build, three runs of each. **{'Pass' if same else 'Fail'}:** "
                 f"{'the same outcomes' if same else 'the outcomes differ'}.\n\n" + table + "\n")
    (args.out / "cards.md").write_text(text + "\n")
    print(f"{len(runs)} runs, {len({r.get('label') or r['model'] for r in runs})} models -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
