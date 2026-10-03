"""The tests of the roaming test plan (docs/project/roaming-test-plan.md).

Each test has a walk (the levels the driver sets, and when), its actions (a
scan requested, a BTM request sent, traffic) and a judgement. What a model
should do is derived from the model itself, so one test serves every model.
A test returns its measures and a verdict: pass, fail, recorded (a
characterisation test) or not-applicable.
"""

from __future__ import annotations

import re
import time

from rig import ABSENT_DBM, CHANNELS, Rig, kv

RAMP_S_PER_DB = 2          # a ramp moves 1 dB every 2 s
LOOK_BELOW = 10            # look level within [trigger - 10, trigger + 1]
LOOK_ABOVE = 1
MARGIN_OVER = 6            # margin within [margin, margin + 6]
BTM_WAIT_S = 10
CONNECT_S = 30



# --- reading the timeline

def events(rig: Rig, source: str, name: str, since: float = 0) -> list[dict]:
    return [r for r in rig.timeline.since(since)
            if r["source"] == source and r["kind"] == "event" and r["name"] == name]


def connections(rig: Rig, since: float = 0) -> list[tuple[float, str]]:
    """(time, role) of each association the client completed after since:
    wpa_supplicant's CTRL-EVENT-CONNECTED, or for iwd (which has no control
    socket) each change of the polled BSSID."""
    roles = {addr: role for role, addr in rig.addr.items()}
    result = []
    if rig.client_kind == "wpa_supplicant":
        for r in rig.timeline.since(since):
            if r["source"] == "client" and r["kind"] == "event" and r["name"] == "CTRL-EVENT-CONNECTED":
                m = re.search(r"Connection to (\S+)", r["text"])
                result.append((r["t"], roles.get(m.group(1), m.group(1))))
        return result
    previous = None
    for r in rig.timeline.records:
        if r["kind"] != "poll":
            continue
        bssid = r.get("bssid")
        if r["t"] >= since and bssid and bssid != previous:
            result.append((r["t"], roles.get(bssid, bssid)))
        if bssid:
            previous = bssid
    return result


def current_role(rig: Rig) -> str | None:
    polls = [r for r in rig.timeline.records if r["kind"] == "poll"]
    if not polls or not polls[-1].get("bssid"):
        return None
    roles = {addr: role for role, addr in rig.addr.items()}
    return roles.get(polls[-1]["bssid"])


def wait_for(predicate, timeout: float, step: float = 0.2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(step)
    return None


def wait_connected(rig: Rig, role: str, since: float = 0, timeout: float = CONNECT_S):
    return wait_for(lambda: next((c for c in connections(rig, since) if c[1] == role), None), timeout)


def moves(rig: Rig, since: float) -> list[tuple[float, str]]:
    return connections(rig, since)


def hold(seconds: float) -> None:
    time.sleep(seconds)


def ramp(rig: Rig, role: str, start: int, end: int, others: dict | None = None,
         stop=None) -> None:
    """Set role from start to end, 1 dB every RAMP_S_PER_DB; stop() ends it early."""
    step = -1 if end < start else 1
    for level in range(start, end + step, step):
        rig.set_levels({role: level, **(others or {})})
        others = None
        if stop and stop():
            return
        time.sleep(RAMP_S_PER_DB)


def disconnects(rig: Rig, since: float) -> int:
    return len(events(rig, "client", "CTRL-EVENT-DISCONNECTED", since))


def btm_request(rig: Rig, target: str, abridged: bool = True, disassoc_timer: int = 0) -> str:
    sta = rig.addr["sta"]
    channel, _, _, op_class = CHANNELS[target.split("-")[1]]
    phy_type = 4 if channel > 14 else 6  # OFDM (802.11a) or ERP (802.11g)
    # BSSID, BSSID Information, Operating Class, Channel, PHY type, and a BSS
    # Transition Candidate Preference subelement of 255
    neighbor = f"{rig.addr[target]},0x0000,{op_class},{channel},{phy_type},0301ff"
    command = f"BSS_TM_REQ {sta} pref=1 abridged={1 if abridged else 0} valid_int=255 neighbor={neighbor}"
    if disassoc_timer:
        command += f" disassoc_imminent=1 disassoc_timer={disassoc_timer}"
    c = rig.ap_ctrl(rig.ap1)
    try:
        reply = c.request(command).strip()
    finally:
        c.close()
    rig.timeline.add("driver", "btm-request", command=command, reply=reply)
    return reply


def btm_answer(rig: Rig, since: float) -> dict | None:
    for r in events(rig, rig.ap1, "BSS-TM-RESP", since):
        fields = dict(re.findall(r"(\w+)=(\S+)", r["text"]))
        roles = {addr: role for role, addr in rig.addr.items()}
        target = fields.get("target_bssid")
        return {"t": r["t"], "status": int(fields.get("status_code", -1)),
                "target": roles.get(target, target)}
    return None


def sta_btm_capable(rig: Rig) -> bool | None:
    c = rig.ap_ctrl(rig.ap1)
    try:
        info = kv(c.request(f"STA {rig.addr['sta']}"))
    finally:
        c.close()
    capab = info.get("ext_capab")
    if capab is None:
        return False
    raw = bytes.fromhex(capab)
    return len(raw) > 2 and bool(raw[2] & 0x08)  # bit 19: BSS Transition


# --- what a model asks for

def trigger(model: dict) -> int | None:
    return model.get("looking", {}).get("trigger_dbm")


def margin(model: dict, active: bool = False) -> int | None:
    moving = model.get("moving", {})
    if active and "margin_active_db" in moving:
        return moving["margin_active_db"]
    return moving.get("margin_db")


def btm_mode(model: dict) -> str:
    if model.get("capabilities", {}).get("btm") is False:
        return "none"
    return model.get("btm", {}).get("policy", "rules")


# --- the tests
#
# Levels are given for "ap1" and "ap2": the two access points of the band the
# test runs on (5 GHz, or 2.4 GHz for a model without 5 GHz).

def model_bands(model: dict) -> list[str]:
    return model.get("capabilities", {}).get("bands") or ["2.4", "5", "6"]


class Case:
    id = ""
    title = ""
    kind = "conformance"
    initial = {"ap1": -50, "ap2": ABSENT_DBM}
    dual_band = False

    def applies(self, model: dict) -> bool:
        return model.get("implementation") == "wpa_supplicant" and "5" in model_bands(model)

    def bands(self, model: dict) -> tuple[str, ...]:
        if self.dual_band:
            return ("5", "2.4")
        return ("5",) if "5" in model_bands(model) else ("2.4",)

    def load(self, model: dict) -> dict:
        return {}

    def levels(self, rig: Rig, levels: dict) -> dict:
        return {getattr(rig, k) if k in ("ap1", "ap2") else k: v for k, v in levels.items()}

    def execute(self, rig: Rig, model: dict) -> dict:
        raise NotImplementedError


class B0(Case):
    id, title = "B0", "Bench sanity"

    def applies(self, model):
        return True

    def execute(self, rig, model):
        ok = rig.ping(3)
        n = len([r for r in rig.timeline.records if r["source"] == "client"])
        return {"verdict": "pass" if ok and n > 0 else "fail", "ping": ok, "client_records": n,
                "associated_at": rig.associated_at}


def is_look(r: dict) -> bool:
    if r["source"] != "client":
        return False
    if r["kind"] == "event":
        return r["name"] == "CTRL-EVENT-ROAM-SCAN" and bool(
            re.search(r"reason=(signal|below|beacon-loss)", r["text"]))
    # iwd arms a 5 s roam timer on the low-signal event, then scans
    return r["kind"] == "iwd" and "Arming new roam timer" in r["text"]


class B1(Case):
    id, title = "B1", "Look level"
    initial = {"ap1": -50, "ap2": -55}

    def applies(self, model):
        return model.get("implementation") == "iwd" or super().applies(model)

    def execute(self, rig, model):
        t0 = rig.timeline.now()
        moved = lambda: any(role == rig.ap2 for _, role in moves(rig, t0))
        ramp(rig, rig.ap1, -50, -90, stop=moved)
        wait_for(moved, 20)
        look = next((r for r in rig.timeline.since(t0) if is_look(r)), None)
        to_ap2 = next((c for c in moves(rig, t0) if c[1] == rig.ap2), None)
        measures = {
            "look_t": look["t"] if look else None,
            "look_level": rig.level_at(rig.ap1, look["t"]) if look else None,
            "look_event": look["text"] if look else None,
            "move_t": to_ap2[0] if to_ap2 else None,
            "move_ap1_level": rig.level_at(rig.ap1, to_ap2[0]) if to_ap2 else None,
            "disconnects": disconnects(rig, t0),
        }
        trig = trigger(model)
        if model.get("implementation") == "iwd":
            trig = model.get("iwd", {}).get("RoamThreshold5G")
        if trig is None:
            measures["verdict"] = "recorded"
            return measures
        measures["bounds"] = [trig - LOOK_BELOW, trig + LOOK_ABOVE]
        ok = (look is not None and trig - LOOK_BELOW <= measures["look_level"] <= trig + LOOK_ABOVE
              and to_ap2 is not None)
        measures["verdict"] = "pass" if ok else "fail"
        return measures


class B2(Case):
    id, title = "B2", "Stays above the trigger"

    def applies(self, model):
        if model.get("implementation") == "iwd":
            return True
        return super().applies(model) and bool(model.get("moving", {}).get("stay_above_trigger")
                                               or model["id"].split("+")[0] == "baseline")

    def execute(self, rig, model):
        rig.set_levels({rig.ap1: -60, rig.ap2: -40})
        t0 = rig.timeline.now()
        for at in (10, 50, 90):
            hold(at - (rig.timeline.now() - t0))
            if model.get("implementation") == "wpa_supplicant":
                rig.client_request("SCAN")  # a scan caused by something else
                rig.timeline.add("driver", "scan-request")
        hold(120 - (rig.timeline.now() - t0))
        m = moves(rig, t0)
        skips = [r["text"] for r in events(rig, "client", "CTRL-EVENT-SKIP-ROAM", t0)]
        return {"moves": len(m), "skip_roam": skips[:3], "verdict": "pass" if not m else "fail"}


class B3(Case):
    id, title = "B3", "Margin, idle"
    active = False

    def applies(self, model):
        return super().applies(model) and (margin(model) is not None
                                           or model["id"].split("+")[0] == "baseline")

    def execute(self, rig, model):
        trig = trigger(model)
        held = trig - 5 if trig is not None else -75
        traffic = rig.start_traffic() if self.active else None
        rig.set_levels({rig.ap1: held, rig.ap2: -90})
        t0 = rig.timeline.now()
        hold(5)
        expected = margin(model, self.active)
        top = min(held + (expected or 15) + MARGIN_OVER + 6, -40)
        moved = lambda: any(role == rig.ap2 for _, role in moves(rig, t0))
        ramp(rig, rig.ap2, -90, top, stop=moved)
        wait_for(moved, 20)
        ping_summary = rig.stop_traffic(traffic) if traffic else None
        to_ap2 = next((c for c in moves(rig, t0) if c[1] == rig.ap2), None)
        decisions = [r["text"] for r in rig.timeline.since(t0) if r["kind"] == "event"
                     and r["name"] in ("CTRL-EVENT-DO-ROAM", "CTRL-EVENT-SKIP-ROAM")]
        measures = {"ap1_level": held, "move_t": to_ap2[0] if to_ap2 else None,
                    "decisions": decisions[-3:], "traffic": ping_summary,
                    "disconnects": disconnects(rig, t0)}
        if to_ap2:
            measures["ap2_level"] = rig.level_at(rig.ap2, to_ap2[0])
            measures["margin_seen"] = measures["ap2_level"] - held
        if expected is None:
            measures["verdict"] = "recorded"
            return measures
        measures["expected_margin"] = expected
        measures["bounds"] = [expected, expected + MARGIN_OVER]
        ok = to_ap2 is not None and expected <= measures["margin_seen"] <= expected + MARGIN_OVER
        measures["verdict"] = "pass" if ok else "fail"
        return measures


class B4(B3):
    id, title = "B4", "Margin, with traffic"
    active = True

    def applies(self, model):
        return (Case.applies(self, model) and margin(model) is not None
                and margin(model, True) != margin(model))


class B5(Case):
    id, title = "B5", "BTM answer"
    abridged = True
    at = {"ap1": -65, "ap2": -60}

    def applies(self, model):
        return model.get("implementation") == "iwd" or \
            model.get("implementation") == "wpa_supplicant"

    def predict(self, model) -> dict | None:
        if model.get("implementation") == "iwd":
            # iwd 3.12 follows a request but has no code to answer one
            return {"answer": None, "moves": True}
        mode = btm_mode(model)
        if mode in ("none", "ignore"):
            return {"answer": None, "moves": False}
        if mode == "reject":
            return {"answer": model.get("btm", {}).get("reject_status", 1), "moves": False}
        if mode == "accept":
            mm = model.get("btm", {}).get("min_margin_db")
            if mm is not None and self.at["ap2"] < self.at["ap1"] + mm:
                return {"answer": 7, "moves": False}
            return {"answer": 0, "moves": True}
        # rules: with the abridged bit the current AP is no candidate, so 2.12 follows
        if self.abridged:
            return {"answer": 0, "moves": True}
        return None  # without it, the client's own rules decide

    def execute(self, rig, model):
        rig.set_levels(self.levels(rig, self.at))
        hold(8)
        capable = sta_btm_capable(rig)
        t0 = rig.timeline.now()
        reply = btm_request(rig, rig.ap2, abridged=self.abridged)
        wait_for(lambda: btm_answer(rig, t0) and any(r == rig.ap2 for _, r in moves(rig, t0)),
                 BTM_WAIT_S)
        hold(2)
        answer = btm_answer(rig, t0)
        m = moves(rig, t0)
        policy_events = [r["text"] for r in rig.timeline.since(t0) if r["kind"] == "event"
                         and r["name"] in ("CTRL-EVENT-BTM-POLICY", "CTRL-EVENT-DO-ROAM",
                                           "CTRL-EVENT-SKIP-ROAM")]
        predicted = self.predict(model)
        measures = {"btm_capable": capable, "request_reply": reply, "answer": answer,
                    "moved_to": m[0][1] if m else None, "events": policy_events[:4],
                    "predicted": predicted}
        if predicted is None:
            measures["verdict"] = "recorded"
            return measures
        status = answer["status"] if answer else None
        ok = status == predicted["answer"] and bool(m and m[0][1] == rig.ap2) == predicted["moves"]
        if model.get("implementation") == "wpa_supplicant" and btm_mode(model) == "none":
            ok = ok and capable is False
        measures["as_predicted"] = ok
        measures["verdict"] = ("pass" if ok else "fail") if self.kind == "conformance" else "recorded"
        return measures


class B5b(B5):
    id, title = "B5b", "BTM answer, without the abridged bit"
    kind = "characterisation"
    abridged = False

    def applies(self, model):
        return model.get("implementation") == "wpa_supplicant" and "+" not in model["id"]


class B6(B5):
    id, title = "B6", "BTM to a weaker AP"
    at = {"ap1": -65, "ap2": -75}

    def applies(self, model):
        return model.get("implementation") == "wpa_supplicant" and "+" not in model["id"]

    def execute(self, rig, model):
        measures = super().execute(rig, model)
        # conformance for a model with a minimum margin; recorded for the rest
        if model.get("btm", {}).get("min_margin_db") is None:
            measures["verdict"] = "recorded"
        return measures


class B7(Case):
    id, title = "B7", "Disassociation imminent, no better AP"
    kind = "characterisation"

    def applies(self, model):
        return model.get("implementation") == "wpa_supplicant" and "+" not in model["id"]

    def execute(self, rig, model):
        rig.set_levels({rig.ap1: -68, rig.ap2: -80})
        hold(8)
        t0 = rig.timeline.now()
        reply = btm_request(rig, rig.ap2, disassoc_timer=100)
        hold(25)
        return {"request_reply": reply, "answer": btm_answer(rig, t0),
                "connections": moves(rig, t0), "disconnects": disconnects(rig, t0),
                "verdict": "recorded"}


class B8(Case):
    id, title = "B8", "Load trigger"

    def applies(self, model):
        base = model["id"].split("+")[0]
        return super().applies(model) and ("load_trigger" in model or base == "mac")

    def load(self, model):
        return {"ap1": 80}

    def execute(self, rig, model):
        rig.set_levels({rig.ap1: -72, rig.ap2: -55})
        t0 = rig.timeline.now()
        moved = lambda: any(role == rig.ap2 for _, role in moves(rig, t0))
        wait_for(moved, 60)
        loads = [r["text"] for r in events(rig, "client", "CTRL-EVENT-ROAM-SCAN", t0)
                 if "reason=load" in r["text"]]
        to_ap2 = next((c for c in moves(rig, t0) if c[1] == rig.ap2), None)
        zone = model.get("load_trigger", {}).get("5")
        expects_move = bool(zone and zone["rssi_low_dbm"] <= -72 <= zone["rssi_high_dbm"])
        measures = {"load_scans": loads[:2], "move_after_s": round(to_ap2[0] - t0, 1) if to_ap2 else None,
                    "expects_move": expects_move}
        ok = (to_ap2 is not None and bool(loads)) if expects_move else to_ap2 is None
        measures["verdict"] = "pass" if ok else "fail"
        return measures


class B9(Case):
    id, title = "B9", "Bands"
    dual_band = True
    initial = {"ap1-5": -60, "ap1-2.4": -57}

    def applies(self, model):
        return model.get("implementation") == "wpa_supplicant" and "+" not in model["id"]

    def execute(self, rig, model):
        hold(20)
        rig.client_request("SCAN")
        rig.timeline.add("driver", "scan-request")
        hold(30)
        freqs = sorted({r["freq"] for r in rig.timeline.records if r["kind"] == "poll" and r.get("freq")})
        measures = {"frequencies": freqs, "connections": moves(rig, 0)}
        if model_bands(model) == ["2.4"]:
            measures["verdict"] = "pass" if freqs and all(f < 3000 for f in freqs) else "fail"
        else:
            measures["verdict"] = "recorded"
        return measures


class B10(Case):
    id, title = "B10", "No ping-pong"
    duration_s = 600
    period_s = 10

    def applies(self, model):
        m = margin(model)
        return super().applies(model) and m is not None and m >= 8

    def execute(self, rig, model):
        t0 = rig.timeline.now()
        phase = 0
        while rig.timeline.now() - t0 < self.duration_s:
            a, b = (-68, -76) if phase % 2 == 0 else (-76, -68)
            rig.set_levels({rig.ap1: a, rig.ap2: b})
            phase += 1
            hold(self.period_s)
        m = moves(rig, t0)
        return {"moves": len(m), "phases": phase, "verdict": "pass" if len(m) <= 1 else "fail"}


ALL = [B0(), B1(), B2(), B3(), B4(), B5(), B5b(), B6(), B7(), B8(), B9(), B10()]
BY_ID = {c.id: c for c in ALL}
