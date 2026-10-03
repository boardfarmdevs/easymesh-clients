# Client models: requirements and design

[Documents](../README.md)

**Status:** Implemented on the bench, 3 October 2026: the client build
([supplicant/](../../supplicant/README.md)), the catalog and its resolver
([models/](../../models/README.md)), and the bench ([bench/](../../bench/README.md)) with its
[results](../records/bench-2026-10-03/README.md). Steps 1 to 6 of section 11 are done on the
bench; the labs (step 7) are not touched yet. The four questions of section 12 are still
open; the models use the assumption each names. **Prepared:** 29 September 2026.
**Revised:** 3 October 2026: models are named after kinds of devices, with values from what
those devices document ([documented roaming](../reference/documented-roaming.md)); the
behaviour archetypes of the first version survive as behaviour variants. The first version is
in this repository's history. Where the implementation changed the design, this text says
so.

## 1. The goal

Every Wi-Fi client in the RDK and prplMesh labs is the same: wpa_supplicant on a simulated
radio, which never looks for a better access point by itself and follows every steering
request. An optimizer tested only against that client has met the easiest case there is.

A **client model** makes one lab client roam the way a kind of real device documents that it
roams: when it starts looking (the trigger), how much better another access point must be
(the margin), what else makes it look (load, beacon loss), how it answers a BSS Transition
Management (BTM) request, and what it supports. A room assigns models to its clients, so an
optimizer meets a realistic mix.

## 2. Requirements

| # | Requirement |
| --- | --- |
| R1 | **The default is today's client, on the current supplicant.** A client without a model runs wpa_supplicant 2.12, built with its default options (background scanning, which brings in WNM; SAE, FT, 802.11ac/ax/be; not MBO), configured as today: no background scanning, every option at its upstream default. Moving the labs from 2.10 to 2.12 is qualified on its own, before any model is used. |
| R2 | **Each model resembles a kind of device and says which.** Every value comes from a source with its date and a confidence (documented, documented secondary, configured in source, measured, synthesized). A synthesized value is marked so, and replaced when measured. |
| R3 | **A model is data.** One supplicant build serves every wpa_supplicant model; a model is chosen per client when a room loads, without a new image. The one exception is a model whose point is a different implementation (iwd). |
| R4 | **Nothing changes unless asked.** Every new supplicant option defaults to upstream behaviour; a model lists only what it changes; a room without models compiles and runs as before. |
| R5 | **Observable.** Every roam decision, every reason to look, every BTM answer is an event with the levels involved, so the bench and the lab's journal can tell which rule acted. |
| R6 | **Verifiable without a lab.** A bench of two or three simulated access points, one client and the medium's wmediumd checks each model's trigger, margin, load trigger and BTM answers, within stated tolerances ([the test plan](../project/roaming-test-plan.md)). |
| R7 | **Both labs, one build.** The RDK and prplMesh labs use the same supplicant build and the same model catalog. |
| R8 | **Fits the containers as they are.** A client container gains one binary (and, for the iwd model, an alternative image); its radio, address and naming stay the lab's. |
| R9 | **The optimizer is not told.** Models are known to the room and its checks, not to the optimizer, as in the field. |
| R10 | **Ready for the configurator later.** A model has a stable name a world can use; the compiler can check it; nothing about worlds changes in this step. |

## 3. The catalog

### Models

| Nickname | Resembles | Implementation | In short | Confidence |
| --- | --- | --- | --- | --- |
| `baseline` | today's lab client | wpa_supplicant 2.12 | no background scanning; upstream margin table; follows BTM | source |
| `iphone` | iPhone (iOS) | wpa_supplicant 2.12 + patches | looks below −70 dBm; moves for 8 dB (transmitting) or 12 dB (idle); stays put above −70 dBm | documented |
| `ipad` | iPad (iPadOS) | as `iphone` | Apple documents the same behaviour; a separate name so a room can say iPad and so it can diverge once measured | documented |
| `mac` | Mac with Apple silicon | wpa_supplicant 2.12 + patches | looks below −75 dBm; moves for 12 dB | documented |
| `pixel` | Google Pixel 6 to 9 | wpa_supplicant 2.12 + patches | looks below −75 dBm, or at −70 to −75 dBm when the AP is over 70 % busy; moves for 10 dB; accepts a BTM target that is not stronger | configured in source |
| `galaxy` | Samsung Galaxy S and Note | wpa_supplicant 2.12 + patches | looks below −75 dBm, or at −65 to −75 dBm when the AP is over 70 % busy; moves for 10 dB | documented, secondary |
| `windows-intel` | a Windows laptop with Intel Wi-Fi at its default Roaming Aggressiveness | wpa_supplicant 2.12 + patches | looks below −75 dBm; moves for 10 dB | synthesized (Intel documents levels, not values) |
| `linux-iwd` | a Linux device running iwd | **iwd 3.12** | iwd's own algorithm: −70 dBm on 2.4 GHz, −76 dBm on 5 GHz, critical −80 / −82 dBm | documented |

### Variants

| Variant | Of | What changes | Confidence |
| --- | --- | --- | --- |
| `mac-intel` | `mac` | no 802.11k, no 802.11r | documented |
| `windows-intel-lowest` … `-highest` | `windows-intel` | the trigger at the five Roaming Aggressiveness levels: −85, −80, −75 (default), −70, −65 dBm | synthesized |
| `iot-2g4` | `baseline` | 2.4 GHz only, HT, no 802.11k/v/r, never looks while associated | synthesized from the device class |
| `+btm-refuser` | any wpa_supplicant model | advertises 802.11v but refuses every BTM request (or, as `+btm-ignorer`, never answers) | synthesized |
| `+no-11v` | any wpa_supplicant model | does not advertise 802.11v (`disable_btm=1`) | configuration |

### Why this set is enough

| Dimension | Covered by |
| --- | --- |
| Trigger | −70 (`iphone`, `ipad`, `linux-iwd` on 2.4 GHz), −75 (`mac`, `pixel`, `galaxy`, `windows-intel`), −76 (`linux-iwd` on 5 GHz), −65 to −85 (`windows-intel` levels), none (`baseline`, `iot-2g4`) |
| Margin | 8 / 12 dB by traffic (`iphone`), 12 dB (`mac`), 10 dB (`pixel`, `galaxy`, `windows-intel`), throughput-weighted table (`baseline`), ranking (`linux-iwd`) |
| Other reasons to look | channel utilization (`pixel`, `galaxy`), critical threshold (`linux-iwd`) |
| BTM | its own rules (`baseline`, the Apple models), accepts (`galaxy`, `windows-intel`), accepts but not a weaker target (`pixel`), refuses or ignores (`+btm-refuser`, `+btm-ignorer`), cannot be asked (`+no-11v`, `iot-2g4`), follows without answering (`linux-iwd`) |
| Bands and capabilities | all bands with FT and 802.11k (`iphone`, `mac`, `pixel`), no 11k/11r (`mac-intel`), 2.4 GHz only (`iot-2g4`) |
| Implementation | wpa_supplicant (all but one), iwd (`linux-iwd`) |

## 4. What a model specifies

Every field is optional; an absent field keeps the upstream behaviour.

| Group | Field | Meaning |
| --- | --- | --- |
| Identity | `id`, `title`, `resembles`, `implementation` | the nickname, a label, the devices it resembles, `wpa_supplicant` or `iwd` |
| Capabilities | `bands`, `phy_max`, `btm`, `neighbor_reports`, `fast_transition`, `mbo_cell` | allowed bands; the highest PHY (HT … EHT); whether 802.11v, 802.11k and 802.11r are offered; MBO cellular capability |
| Looking | `trigger_dbm`, `scan_below_s`, `scan_above_s`, `btm_query` | below the trigger, scan every `scan_below_s`; above it, every `scan_above_s`; ask the AP with a BTM query instead of a plain scan |
| Load | `load_trigger`: per band (`"5"`, `"2.4"`), `percent`, `rssi_high_dbm`, `rssi_low_dbm`, `hold_s` | between the two levels, look when the AP's advertised channel utilization stays over `percent` for `hold_s`; `percent` and `hold_s` are the same in every band |
| Moving | `margin_db`, `margin_active_db`, `active_pps`, `stay_above_trigger` | the candidate must be stronger by the margin (the active margin while transmitting more than `active_pps` packets per second); no move while the current AP is above the trigger, except when asked by BTM |
| BTM | `btm`: `policy` (`rules`, `accept`, `reject`, `ignore`), `reject_status`, `min_margin_db` | how a request is answered: by the client's own roaming rules (2.12 as released), by following it, by refusing it, or not at all; with `accept`, refuse a target less than `min_margin_db` stronger (0: not weaker). A variant or behaviour replaces this section as a whole |
| iwd | `iwd`: the `[General]` settings | the thresholds of section 6.4 |
| Provenance | `sources[]`: field list, source, date read, confidence | R2 |

## 5. The models' values

| Field | `iphone` / `ipad` | `mac` | `pixel` | `galaxy` | `windows-intel` |
| --- | --- | --- | --- | --- | --- |
| `trigger_dbm` | −70 | −75 | −75 | −75 | −75 (s) |
| `scan_below_s` | 10 (s) | 10 (s) | 10 | 10 (s) | 10 (s) |
| `scan_above_s` | 300 (s) | 300 (s) | 120 | 120 (s) | 120 (s) |
| `margin_db` | 12 | 12 | 10 | 10 | 10 (s) |
| `margin_active_db` | 8 | 12 | 10 | 10 | 10 (s) |
| `stay_above_trigger` | yes | yes | yes | yes | yes (s) |
| `load_trigger` | — | — | 5 GHz: 70 %, −70 to −75 dBm, 10 s; 2.4 GHz: 70 %, −60 to −75 dBm, 10 s | 70 %, −65 to −75 dBm, 10 s (s) | — |
| `btm.policy` | rules | rules | accept | accept (s) | accept (s) |
| `btm.min_margin_db` | — | — | 0 | — | — |
| `neighbor_reports` | yes | yes | yes | yes | — |
| `fast_transition` | yes | yes | yes | yes | — |
| Bands | 2.4, 5, 6 | 2.4, 5, 6 | 2.4, 5, 6 | 2.4, 5, 6 | 2.4, 5, 6 |

(s): synthesized. Everything else traces to [documented roaming](../reference/documented-roaming.md).
The Apple models keep the client's own rules for a BTM request because Apple documents that
802.11v data "is reviewed when the device needs to roam"; the first version of this design had
them accept every request.

## 6. How a model becomes a client

### 6.1 One supplicant build

wpa_supplicant **2.12** from the release tarball (or the `hostap_2_12` tag) with its
`defconfig` (which enables simple background scanning, and through it WNM, with SAE, FT, OWE
and 802.11ac/ax/be; **not MBO**), plus `CONFIG_BGSCAN_MODEL` from the patch series below and
`CONFIG_HT_OVERRIDES`, `CONFIG_VHT_OVERRIDES`, `CONFIG_HE_OVERRIDES`, without which a model's
PHY ceiling cannot be set. No `CONFIG_TESTING_OPTIONS`: refusing a BTM request becomes an
ordinary option instead. Built by [supplicant/build.sh](../../supplicant/README.md). One
build for both labs replaces the RDK lab's own 2.10 build and the prplMesh lab's hostap
build; it is the first piece of client code worth sharing
([more capable clients](more-capable-clients.md), section 10).

### 6.2 What configuration alone does

| Need | 2.12 option, no patch |
| --- | --- |
| Look below a trigger, at a cadence | `bgscan="simple:<below>:<trigger>:<above>"`; the kernel's signal monitor adds a 4 dB hysteresis |
| Ask the AP instead of scanning | `bgscan` simple's fourth field (`:1`, a BTM query) |
| Not offer 802.11v | `disable_btm=1` (global) |
| Bands | `freq_list`, `scan_freq` |
| PHY ceiling | `disable_eht`, `disable_he`, `disable_vht`, `disable_ht` (all but the first need the `*_OVERRIDES` build options) |
| 802.11r | `key_mgmt=FT-PSK` or `FT-SAE` (needs the AP to offer it) |
| MBO cellular capability | `mbo_cell_capa` |

That covers `baseline`, `iot-2g4`, `+no-11v`, the triggers and cadences. It cannot set a
fixed margin, stay put above the trigger, react to load, or refuse BTM without a testing
build.

### 6.3 The patch series

Three patches against 2.12, each option defaulting to upstream behaviour (R4), written so
they could be offered upstream. The design's P1 and P2 became one patch, and P5's events are
part of each. The options, their defaults and the events are listed in the
[client build's README](../../supplicant/README.md#the-patch-series).

| Patch | Options | Where | Behaviour |
| --- | --- | --- | --- |
| 0001 margin and trigger (P1, P2) | `roam_margin`, `roam_margin_active`, `roam_active_pps`, `roam_trigger` (network) | `events.c`, `wpa_supplicant_need_to_roam_within_ess()` | when `roam_margin` is set, it replaces the level table, the throughput shortcuts and the 25 dB SNR rule: move if and only if the candidate is stronger by the margin. "Active" counts the **transmitted** packets the signal poll returns since the previous decision (received packets include about ten beacons a second, which made every client active: found on the bench). No scan-result-driven move while the current level is above `roam_trigger`, unless a load trigger fired; a BTM request is not affected |
| 0002 the `model` background scan (P3) | `bgscan="model:<below>:<trigger>:<above>[:<percent>:<high>:<low>:<hold>[:<high_2g4>:<low_2g4>]]"` (`CONFIG_BGSCAN_MODEL`) | `bgscan_model.c`, beside `bgscan_simple.c` | the simple module's behaviour, plus: between `high` and `low` dBm (other levels on 2.4 GHz when given), a scan of the current channel every `hold`/2 s refreshes the current AP's BSS Load element, and channel utilization over `percent` for `hold` seconds starts a roam scan; a roam scan on beacon loss; its scans limited to the network's `scan_freq` or the global `freq_list` |
| 0003 BTM policy (P4) | `btm_policy` (0 rules, 1 accept, 2 reject, 3 ignore), `btm_reject_status` (default 1), `btm_min_margin` (global) | `wnm_sta.c` | *rules* is 2.12 as released; *accept* follows the AP, to its most preferred listed candidate heard in the last 10 s (scanning first when none is, refusing with status 7 when none can be used), without the roaming rules; *reject* answers with the status; *ignore* sends nothing; with *accept*, a minimum margin rejects (status 7, no suitable candidates) a target that is not that much stronger |
| events (P5) | — | the three above | `CTRL-EVENT-DO-ROAM` and `CTRL-EVENT-SKIP-ROAM` gain `reason=margin margin= active= load=` or `reason=above_trigger trigger=`; a new `CTRL-EVENT-ROAM-SCAN reason=signal|below|above|load|load-scan|beacon-loss|beacon-loss-scan`; `CTRL-EVENT-BTM-POLICY action=accept|reject|ignore` (R5) |

**What 2.12 does with a BTM request under *rules*,** read in its source and seen on the bench:
with the Abridged bit set, the usual steering request, an AP not in the candidate list (the
current one included) is no candidate, so the client follows; without it, the current AP
stays a candidate: the client picks among the candidates and the current AP by its own
ranking, from scan results it re-uses when under 10 s old, then applies its roaming rules (a
model's margin included) and, when that leaves it where it is, **accepts with the current AP
as its target** and does not move. On the bench every *rules* client did that (B5b), and so
did *accept* until patch 0003 was changed to take the AP's candidate.

**Not in v1, kept for v2:** ranking candidates by RSSI and load weights (the Pixel's 65/35),
scanning the channels of a neighbor report first (Apple's first six entries), a pause after a
roam before the next. In the lab's few channels the second matters little; the first and
third need measurements to be worth modelling.

### 6.4 iwd for `linux-iwd`

iwd 3.12, built from its release (it needs the ell library) or taken from the distribution
package, with `/etc/iwd/main.conf`:

```ini
[General]
EnableNetworkConfiguration=false     # the lab assigns the address, as today
RoamThreshold=-70
RoamThreshold5G=-76
CriticalRoamThreshold=-80
CriticalRoamThreshold5G=-82
RoamRetryInterval=60
```

The values are iwd's defaults; the model only makes them explicit. iwd needs a D-Bus system
bus, so its container image (`wlan-client-iwd`) runs `dbus-daemon` beside it. It is
controlled with `iwctl` instead of `wpa_cli`, so the lab's tools that run `wpa_cli` in a
client need an iwd path for this model, or skip it.

### 6.5 Not used: AOSP

A real Android (Cuttlefish) needs a virtual machine per device, nested virtualization and a
second wmediumd, and in it roaming falls to the Android framework and AOSP's wpa_supplicant,
not to a phone's firmware ([documented roaming](../reference/documented-roaming.md),
section 8). The Pixel's documented firmware settings, applied to wpa_supplicant, are closer
to a Pixel than an emulated Android would be. AOSP stays a reference for the framework's
scan schedule and thresholds only.

### 6.6 From a model to a client

A pure function ([clientmodel/](../../clientmodel/), `python3 -m clientmodel`) turns a model
file into:

- **global options**, set with `wpa_cli set` where 2.12 accepts them at run time
  (`disable_btm`, `btm_policy`, `btm_reject_status`, `btm_min_margin`, `mbo_cell_capa`), else
  written to the configuration before the supplicant starts;
- **network options** (`bgscan`, `roam_margin`, `roam_margin_active`, `roam_active_pps`,
  `roam_trigger`, `freq_list`, `scan_freq`, `key_mgmt`, `disable_*`), set with
  `wpa_cli set_network`, followed by a reconnect so the association carries the
  capabilities;
- for `linux-iwd`, a `main.conf` and the iwd image.

Unit tests hold it to one rule: `baseline` resolves to no change at all (R1, R4). Options
that belong to where the client runs, not to the model (the bench limits scans to its two
channels with `freq_list`), are passed apart and may not collide with the model's.

### 6.7 In the containers

| Lab | Today | With models |
| --- | --- | --- |
| RDK | Alpine image, the lab's 2.10 build as `/usr/local/sbin/wpa_supplicant-wnm`, configuration in `/etc/wpa.conf` | the shared 2.12 build in its place; the model's options in `/etc/wpa.conf` and through `wpa_cli` |
| prplMesh | Ubuntu image, the lab's hostap 2.10 build in `/usr/local/sbin` | the same shared build |
| `linux-iwd` | — | `wlan-client-iwd`: the lab's base image with iwd and dbus instead of wpa_supplicant |

The model in force is written on the container (`user.easymesh.model`), next to the keys
each lab already records.

## 7. The model file

One JSON file per model, in `models/` of this repository:

```json
{
  "schema": "client-model/2",
  "id": "iphone",
  "title": "iPhone",
  "resembles": ["iPhone, iOS"],
  "implementation": "wpa_supplicant",
  "capabilities": {"bands": ["2.4", "5", "6"], "btm": true, "neighbor_reports": true,
                   "fast_transition": true},
  "looking": {"trigger_dbm": -70, "scan_below_s": 10, "scan_above_s": 300},
  "moving": {"margin_db": 12, "margin_active_db": 8, "active_pps": 10,
             "stay_above_trigger": true},
  "btm": {"policy": "rules"},
  "sources": [
    {"fields": ["looking.trigger_dbm", "moving.margin_db", "moving.margin_active_db", "btm.policy"],
     "source": "Apple Platform Deployment, Wi-Fi roaming support in Apple devices (updated 2024-09-25)",
     "read": "2026-10-03", "confidence": "documented"},
    {"fields": ["looking.scan_below_s", "looking.scan_above_s", "moving.active_pps"],
     "source": "not documented", "read": "2026-10-03", "confidence": "synthesized"}
  ]
}
```

(Shortened; [models/iphone.json](../../models/iphone.json) is the file itself.) Variants name
their base and list only their differences (`"base": "mac"`, `"capabilities":
{"neighbor_reports": false, "fast_transition": false}`); behaviour variants, in
`models/behaviours/`, combine with a model (`"pixel+btm-refuser"`).

## 8. Later: rooms and the configurator

Not part of this step (R10), recorded so the design fits it:

- A world names models per station role (`client_models: {"sta_mobile_01": "iphone"}`) or for
  all its stations; without the field every client is `baseline` and the golden is
  unchanged.
- The compiler checks names against the catalog and writes the resolved settings into the
  compiled bindings, so a run applies exactly what was compiled.
- The room shows each client's model; the journal records it with every steer.
- Rooms with models run without the room's steering assists, so the model decides, not the
  lab.
- Mixed-fleet rooms check, per model: no steering ping-pong with a client that roams by
  itself, bounded attempts on a client that refuses, no 5 GHz steer of a 2.4 GHz-only
  client.

## 9. Not modelled

- Beacon-loss timing (Galaxy's 2 s, 6 s with the display off): the kernel detects beacon
  loss for every client alike. The simple background scan does nothing on it (its handler is
  empty); the `model` module scans, but mac80211_hwsim reports no beacon loss, so the bench
  cannot check it.
- Screen, motion and battery states, beyond what a cadence expresses.
- Ranking by load weights, neighbor-report channel order, a pause after a roam (v2).
- Wi-Fi 7 multi-link roaming, rate adaptation, vendor firmware quirks.
- MAC address randomization: the room, the optimizer and the journals identify clients by
  MAC.

## 10. Risks

| Risk | Fallback |
| --- | --- |
| Signal in the simulated medium is SNR − 91 dBm, without fading; triggers fire cleanly where real devices hesitate | the bench reports the margins it measures; a model's tolerance absorbs the kernel's averaging and the 4 dB hysteresis |
| The lab's access points do not advertise BSS Load, so load triggers never fire in rooms | checked in the implementation lab; the RDK and prplMesh APs' hostapd settings decide it |
| 2.12 changes the default client's behaviour against 2.10 | R1: the upgrade is qualified on its own, with every suite, before models |
| A synthesized value is wrong | it is marked; the Protocol lab's real phones and laptops can measure it |
| iwd differs in control (no `wpa_cli`) | `linux-iwd` only in rooms whose tools support it, until they do |

## 11. Steps

| Step | Done when | State |
| --- | --- | --- |
| 1 The bench | two APs and a client on hwsim with the medium's wmediumd, a scripted signal walk and the event recorder ([test plan](../project/roaming-test-plan.md), B0) | done, 3 Oct ([bench/](../../bench/README.md)) |
| 2 2.12 as `baseline` | the default build passes B0 to B2 like 2.10; then both labs' full suites pass on it (R1) | the bench part done, 3 Oct (B12: the same outcomes as 2.10); the labs' suites not run |
| 3 The patch series | P1 to P5 against 2.12, each option off by default; hostap's own hwsim tests still pass | done, 3 Oct: three patches; hostap's tests of BTM, background scanning, roaming, scanning and configuration the same with and without them |
| 4 The catalog and its resolver | the model files, their schema and the resolver, with `baseline` resolving to no change | done, 3 Oct ([models/](../../models/README.md), with unit tests) |
| 5 Each model on the bench | B1 to B10 pass for every model within its tolerances; the results recorded per model | done, 3 Oct: every conformance test of every model passed in all three runs ([results](../records/bench-2026-10-03/README.md)) |
| 6 `linux-iwd` | the iwd image passes B1, B2, B5 | on the bench, done, 3 Oct; the container image not built (it belongs to the labs) |
| 7 The labs | the shared build in both labs; models applied by hand to a few clients in a room | not started |
| 8 The configurator | world field, compiler check, room view, journal (section 8) | not started |
| 9 Calibration (optional) | the Protocol lab's real devices measured on the same tests | not started |

## 12. Open questions

1. **Scan cadence for Apple and Intel models:** 10 s below the trigger is synthesized;
   measure on real devices first, or accept it for now?
2. **Galaxy's load trigger hold time:** Samsung documents the threshold, not the time; reuse
   the Pixel's 10 s?
3. **`windows-intel` margin:** nothing is published; 10 dB like the phones, or the upstream
   table?
4. **`linux-iwd` in the labs:** worth an iwd path in the lab's tools now, or bench only?
