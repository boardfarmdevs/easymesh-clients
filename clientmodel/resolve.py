"""Resolve a client model into wpa_supplicant or iwd configuration.

The rules (docs/proposals/client-models.md, sections 4 to 7):

- every field is optional, and an absent field keeps the upstream behaviour, so
  ``baseline`` resolves to no option at all;
- a variant names its ``base`` and lists only its differences, merged section by
  section; the ``btm`` section is replaced as a whole;
- a behaviour (``+btm-refuser``) is merged on top of a model the same way;
- the result is the global options, the network options, whether 802.11r
  key management is added or removed, and notes on what has no option.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

SCHEMA = "client-model/2"
MODELS = Path(__file__).resolve().parent.parent / "models"

CONFIDENCE = {"documented", "documented, secondary", "configured in source", "measured",
              "synthesized", "source", "configuration"}
TOP = {"schema", "id", "title", "resembles", "implementation", "base", "applies_to",
       "capabilities", "looking", "load_trigger", "moving", "btm", "iwd", "sources"}
SECTIONS = {
    "capabilities": {"bands", "phy_max", "btm", "neighbor_reports", "fast_transition"},
    "looking": {"trigger_dbm", "scan_below_s", "scan_above_s", "btm_query"},
    "moving": {"margin_db", "margin_active_db", "active_pps", "stay_above_trigger"},
    "btm": {"policy", "reject_status", "min_margin_db"},
}
LOAD_FIELDS = {"percent", "rssi_high_dbm", "rssi_low_dbm", "hold_s"}
IWD_FIELDS = {"RoamThreshold", "RoamThreshold5G", "CriticalRoamThreshold",
              "CriticalRoamThreshold5G", "RoamRetryInterval", "DisableRoamingScan",
              "BandModifier2_4GHz", "BandModifier5GHz", "BandModifier6GHz"}
REPLACED = {"btm"}

BANDS = {
    "2.4": [2412 + 5 * i for i in range(13)],
    "5": [5180 + 20 * i for i in range(8)] + [5500 + 20 * i for i in range(12)]
         + [5745 + 20 * i for i in range(7)],
    "6": [5955 + 20 * i for i in range(59)],
}
PHY = ["HT", "VHT", "HE", "EHT"]
BTM_POLICY = {"rules": 0, "accept": 1, "reject": 2, "ignore": 3}
FT_OF = {"WPA-PSK": "FT-PSK", "SAE": "FT-SAE", "WPA-EAP": "FT-EAP"}
STRING_OPTIONS = {"bgscan"}


class ModelError(ValueError):
    pass


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise ModelError(f"no such model file: {path}") from None
    except json.JSONDecodeError as e:
        raise ModelError(f"{path}: {e}") from None
    if data.get("schema") != SCHEMA:
        raise ModelError(f"{path}: schema is not {SCHEMA}")
    _check(data, path)
    return data


def _check(m: dict, where) -> None:
    unknown = set(m) - TOP
    if unknown:
        raise ModelError(f"{where}: unknown fields {sorted(unknown)}")
    for section, fields in SECTIONS.items():
        extra = set(m.get(section, {})) - fields
        if extra:
            raise ModelError(f"{where}: unknown {section} fields {sorted(extra)}")
    for band, profile in m.get("load_trigger", {}).items():
        if band not in BANDS:
            raise ModelError(f"{where}: load_trigger band {band!r}")
        if set(profile) != LOAD_FIELDS:
            raise ModelError(f"{where}: load_trigger.{band} needs exactly {sorted(LOAD_FIELDS)}")
    extra = set(m.get("iwd", {})) - IWD_FIELDS
    if extra:
        raise ModelError(f"{where}: unknown iwd settings {sorted(extra)}")
    for s in m.get("sources", []):
        if not {"fields", "source", "read", "confidence"} <= set(s):
            raise ModelError(f"{where}: a source needs fields, source, read and confidence")
        if s["confidence"] not in CONFIDENCE:
            raise ModelError(f"{where}: confidence {s['confidence']!r}")


def _merge(base: dict, over: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in over.items():
        if key in ("schema", "base", "applies_to"):
            continue
        if key == "sources":
            result["sources"] = result.get("sources", []) + copy.deepcopy(value)
        elif key in REPLACED:
            result[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_model(name: str, models_dir: Path, seen: frozenset) -> dict:
    if name in seen:
        raise ModelError(f"model {name}: its bases form a cycle")
    path = models_dir / f"{name}.json"
    if not path.exists():
        raise ModelError(f"unknown model {name!r}")
    m = _read(path)
    if m.get("id") != name:
        raise ModelError(f"{path}: id is {m.get('id')!r}, not {name!r}")
    if "base" in m:
        m = _merge(_load_model(m["base"], models_dir, seen | {name}), m)
    return m


def list_models(models_dir: Path = MODELS) -> dict:
    return {
        "models": sorted(p.stem for p in models_dir.glob("*.json")),
        "behaviours": sorted("+" + p.stem for p in (models_dir / "behaviours").glob("*.json")),
    }


def load(name: str, models_dir: Path = MODELS) -> dict:
    """The model ``name`` (``nickname[+behaviour...]``) with its bases merged."""
    nickname, *behaviours = name.split("+")
    m = _load_model(nickname, Path(models_dir), frozenset())
    for b in behaviours:
        path = Path(models_dir) / "behaviours" / f"{b}.json"
        if not path.exists():
            raise ModelError(f"unknown behaviour '+{b}'")
        bm = _read(path)
        if bm.get("applies_to") not in (None, m.get("implementation")):
            raise ModelError(f"+{b} applies to {bm['applies_to']}, {nickname} is {m.get('implementation')}")
        title = m.get("title", nickname)
        m = _merge(m, bm)
        m["title"] = f"{title}, {bm.get('title', b)}"
    m["id"] = name
    m.pop("applies_to", None)
    return m


def _int(m: dict, section: str, field: str) -> int:
    value = m.get(section, {}).get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ModelError(f"{m['id']}: {section}.{field} must be an integer")
    return value


def _bgscan(m: dict) -> str | None:
    looking = m.get("looking", {})
    load = m.get("load_trigger")
    if "trigger_dbm" not in looking:
        if load:
            raise ModelError(f"{m['id']}: load_trigger needs looking.trigger_dbm")
        return None
    trigger = _int(m, "looking", "trigger_dbm")
    below = _int(m, "looking", "scan_below_s")
    above = _int(m, "looking", "scan_above_s")
    head = f"{below}:{trigger}:{above}"
    if load:
        if looking.get("btm_query"):
            raise ModelError(f"{m['id']}: btm_query and load_trigger cannot be combined")
        main = load.get("5") or load.get("6") or load["2.4"]
        g24 = load.get("2.4", main)
        if (g24["percent"], g24["hold_s"]) != (main["percent"], main["hold_s"]):
            raise ModelError(f"{m['id']}: load_trigger percent and hold_s must be the same in every band")
        spec = (f"model:{head}:{main['percent']}:{main['rssi_high_dbm']}:"
                f"{main['rssi_low_dbm']}:{main['hold_s']}")
        if (g24["rssi_high_dbm"], g24["rssi_low_dbm"]) != (main["rssi_high_dbm"], main["rssi_low_dbm"]):
            spec += f":{g24['rssi_high_dbm']}:{g24['rssi_low_dbm']}"
        return spec
    if looking.get("btm_query"):
        return f"simple:{head}:1"
    return f"model:{head}"


def resolve(model: str | dict, models_dir: Path = MODELS) -> dict:
    """The configuration a model asks for.

    Returns ``id``, ``implementation``, ``global`` (wpa_supplicant global
    options), ``network`` (network block options), ``key_mgmt_ft`` (True: add
    802.11r key management, False: remove it, None: leave it), ``iwd`` (the
    [General] settings, for iwd) and ``notes``.
    """
    m = load(model, models_dir) if isinstance(model, str) else model
    result = {"id": m["id"], "implementation": m.get("implementation"), "global": {},
              "network": {}, "key_mgmt_ft": None, "iwd": {}, "notes": []}
    if m.get("implementation") == "iwd":
        for section in ("capabilities", "looking", "load_trigger", "moving", "btm"):
            if section in m:
                raise ModelError(f"{m['id']}: an iwd model sets iwd settings, not {section}")
        result["iwd"] = dict(m.get("iwd", {}))
        return result
    if m.get("implementation") != "wpa_supplicant":
        raise ModelError(f"{m['id']}: implementation must be wpa_supplicant or iwd")

    g, n, notes = result["global"], result["network"], result["notes"]
    caps = m.get("capabilities", {})
    bands = caps.get("bands")
    if bands is not None:
        if not bands or set(bands) - set(BANDS):
            raise ModelError(f"{m['id']}: bands must be a non-empty subset of {sorted(BANDS)}")
        if set(bands) != set(BANDS):
            freqs = " ".join(str(f) for b in sorted(set(bands), key=list(BANDS).index)
                             for f in BANDS[b])
            n["freq_list"] = freqs
            n["scan_freq"] = freqs
    phy = caps.get("phy_max")
    if phy is not None:
        if phy not in PHY:
            raise ModelError(f"{m['id']}: phy_max must be one of {PHY}")
        for higher in PHY[PHY.index(phy) + 1:]:
            n[f"disable_{higher.lower()}"] = 1
    if caps.get("btm") is False:
        g["disable_btm"] = 1
    if "fast_transition" in caps:
        result["key_mgmt_ft"] = bool(caps["fast_transition"])
    if caps.get("neighbor_reports") is False:
        notes.append("capabilities.neighbor_reports=false has no option in wpa_supplicant 2.12: "
                     "it never requests a neighbor report by itself, so the field is informative")

    bgscan = _bgscan(m)
    if bgscan:
        n["bgscan"] = bgscan

    moving = m.get("moving", {})
    if "margin_db" in moving:
        n["roam_margin"] = _int(m, "moving", "margin_db")
    if "margin_active_db" in moving:
        if "margin_db" not in moving:
            raise ModelError(f"{m['id']}: margin_active_db needs margin_db")
        n["roam_margin_active"] = _int(m, "moving", "margin_active_db")
    if "active_pps" in moving:
        n["roam_active_pps"] = _int(m, "moving", "active_pps")
    if moving.get("stay_above_trigger"):
        if "trigger_dbm" not in m.get("looking", {}):
            raise ModelError(f"{m['id']}: stay_above_trigger needs looking.trigger_dbm")
        n["roam_trigger"] = m["looking"]["trigger_dbm"]

    btm = m.get("btm", {})
    policy = btm.get("policy", "rules")
    if policy not in BTM_POLICY:
        raise ModelError(f"{m['id']}: btm.policy must be one of {list(BTM_POLICY)}")
    if BTM_POLICY[policy]:
        g["btm_policy"] = BTM_POLICY[policy]
    if "reject_status" in btm:
        if policy != "reject":
            raise ModelError(f"{m['id']}: btm.reject_status needs policy reject")
        status = _int(m, "btm", "reject_status")
        if not 1 <= status <= 255:
            raise ModelError(f"{m['id']}: btm.reject_status must be 1 to 255")
        if status != 1:
            g["btm_reject_status"] = status
    if "min_margin_db" in btm:
        if policy != "accept":
            raise ModelError(f"{m['id']}: btm.min_margin_db needs policy accept")
        g["btm_min_margin"] = _int(m, "btm", "min_margin_db")
    if caps.get("btm") is False and policy != "rules":
        notes.append(f"btm.policy {policy} has no effect: 802.11v is not offered")
    return result


def key_mgmt(value: str, ft: bool | None) -> str:
    """The network's key management with 802.11r added (True) or removed (False)."""
    items = value.split()
    if ft is True:
        items += [FT_OF[k] for k in items if k in FT_OF]
    elif ft is False:
        items = [k for k in items if not k.startswith("FT-")]
    seen = []
    for k in items:
        if k not in seen:
            seen.append(k)
    if not seen:
        raise ModelError(f"no key management left of {value!r}")
    return " ".join(seen)


def _option(name: str, value) -> str:
    return f'"{value}"' if name in STRING_OPTIONS else str(value)


def wpa_conf(resolved: dict, ssid: str, psk: str | None = None, key_mgmt_value: str = "WPA-PSK",
             ctrl_interface: str = "/var/run/wpa_supplicant", network: dict | None = None,
             environment: dict | None = None) -> str:
    """A wpa_supplicant.conf for one network, with the model's options.

    environment holds global options that belong to the place the client
    runs in, not to the model (the bench limits scans to its channels)."""
    if resolved["implementation"] != "wpa_supplicant":
        raise ModelError(f"{resolved['id']} is not a wpa_supplicant model")
    lines = [f"# client model: {resolved['id']}", f"ctrl_interface={ctrl_interface}"]
    clash = set(environment or {}) & set(resolved["global"])
    if clash:
        raise ModelError(f"the environment and the model both set {sorted(clash)}")
    if environment:
        lines.append("# the environment")
        lines += [f"{k}={v}" for k, v in environment.items()]
        lines.append("# the model")
    lines += [f"{k}={v}" for k, v in resolved["global"].items()]
    lines += ["", "network={", f'\tssid="{ssid}"']
    if psk is None:
        lines.append("\tkey_mgmt=NONE")
    else:
        lines.append(f'\tpsk="{psk}"')
        lines.append(f"\tkey_mgmt={key_mgmt(key_mgmt_value, resolved['key_mgmt_ft'])}")
    for k, v in (network or {}).items():
        lines.append(f"\t{k}={v}")
    for k, v in resolved["network"].items():
        lines.append(f"\t{k}={_option(k, v)}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def wpa_cli_commands(resolved: dict, network_id: int = 0) -> list[list[str]]:
    """The same options as wpa_cli commands, for a running client; a
    ``reassociate`` follows so the association carries the capabilities."""
    if resolved["implementation"] != "wpa_supplicant":
        raise ModelError(f"{resolved['id']} is not a wpa_supplicant model")
    commands = [["set", k, str(v)] for k, v in resolved["global"].items()]
    commands += [["set_network", str(network_id), k, _option(k, v)]
                 for k, v in resolved["network"].items()]
    if commands:
        commands.append(["reassociate"])
    return commands


def iwd_conf(resolved: dict) -> str:
    """iwd's /etc/iwd/main.conf for an iwd model."""
    if resolved["implementation"] != "iwd":
        raise ModelError(f"{resolved['id']} is not an iwd model")
    lines = [f"# client model: {resolved['id']}", "[General]",
             "EnableNetworkConfiguration=false"]
    lines += [f"{k}={str(v).lower() if isinstance(v, bool) else v}"
              for k, v in resolved["iwd"].items()]
    return "\n".join(lines) + "\n"
