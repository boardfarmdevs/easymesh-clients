# Client models for the lab's Wi-Fi clients

[Documents](../README.md)

**Status:** Proposal. Nothing here is implemented. The behaviour of every
client in every existing room must stay exactly as it is: a client without a
model is today's client.

**Prepared:** 29 September 2026, from the user's question of the same day
(can the lab's clients behave like different kinds of real devices).

**Moved here** on 2 October 2026 from the umbrella repository (easymesh-labs),
unchanged but for this note and the answer to open question 1. The models are step 3
of [more capable clients](more-capable-clients.md); [the clients of each
lab](../reference/lab-clients.md) has what the labs' clients are today.

## 1. Goal

Every Wi-Fi client in the RDK and prplMesh labs is the same Linux client:
wpa_supplicant on a mac80211_hwsim radio. Real networks are hard for an
optimizer because their clients are not the same: some roam early, some hold
on to a weak AP, some refuse or ignore steering, some support only 2.4 GHz.

A **client model** is a named, documented set of behaviours that one lab client
takes on when a room loads:

- when it starts looking for a better AP, and how often it scans;
- how much better another AP must be before it moves by itself;
- which bands it may use and which it prefers;
- how it answers a BSS Transition Management (BTM) request;
- what it supports (802.11k, v, r, PMF, PHY);
- what it does after it has been pushed off an AP.

Rooms assign models to their station roles, so an optimizer meets a realistic
mix of clients and the lab can check how it copes with each kind.

Not the goal: emulating one phone's firmware, modelling traffic, screen, motion
or battery states, or replacing the Linux client. A model is an **archetype**
that resembles a class of devices, and it says so.

## 2. What exists today

| Piece | Where | What it is now |
| --- | --- | --- |
| RDK client software | meta-cmf `gen/wpa_supplicant/` | `wpa_supplicant-wnm`: wpa_supplicant 2.10 (w1.fi tarball) built with nl80211, WNM, 802.11r, 802.11ac/ax, PMF and SAE, plus the lab patch `0001-wnm-select-hidden-bss-by-current-ssid.patch`. Not built: the bgscan modules, MBO, testing options. Baked into the `wlan-client-base` image by `gen/wlan-client.sh` |
| prplMesh client software | prplmesh-lab `scripts/container/build-hostap-inside.sh` | wpa_supplicant from hostap 2.10 at a pinned `HOSTAP_COMMIT` with `hostap-patches`, defconfig plus WNM and MBO; configured from `manifests/wpa_supplicant.conf` |
| Client configuration | `gen/wlan-client.sh` | One network per client (`private_ssid`, `iot_ssid`, guest), PSK or SAE with `ieee80211w=2`, `scan_ssid` for the IoT SSID, `freq_list` and `scan_freq` for band-directed clients. No `bgscan` |
| Per-world client settings | world files (`band_steering`, `band_steering_expectations`); meta-cmf `gen/demo/room_demo/band_profiles.py` | At most four clients per world get `allowed_bands`, `initial_band` and `measurement_mode`. `ClientBandSettings` captures the client's current settings through `wpa_cli` in its namespace, writes the profile's (`freq_list`, `scan_freq`, `key_mgmt`, `ieee80211w`, `sae_pwe`) and restores them after the world. This is the mechanism a client model extends |
| Client pool and bindings | worlds (`roles`), the compiler `gen/wmediumd/configurator/wmdcfg`, the room's `client_bindings` | 100 client containers, bound to station roles (`sta_static_NN`, `sta_mobile_NN`); a room uses 10 to 50 |
| Room assists | `room_demo/conductor.py`, `room_demo/cli.py` | The interactive room helps steering (an RF steering boost, forced scans, escalation, an RF-stability gate). `--profiling` runs unassisted native BTM |
| Checks | meta-cmf `gen/tests/room-feature-acceptance.js`, `room-backhaul-features.js`; prplmesh-lab `tests` | Convergence to the configured steering policy (strongest AP, same band best), band steering transitions expected against observed |

### How today's client behaves (wpa_supplicant 2.10 source)

1. **It never looks for a better AP by itself.** No `bgscan` is configured
   (and the RDK build has no bgscan module), so while associated it only
   reconsiders its AP when something else causes a scan: the room's forced
   scans, a BTM request, a disconnect.
2. **When it does reconsider, the rule is fixed**
   (`wpa_supplicant_need_to_roam_within_ess()` in `wpa_supplicant/events.c`):
   - a candidate whose estimated throughput is more than 5 Mb/s higher is taken at once;
   - otherwise there is no roam while the current SNR is above 25 dB (`GREAT_SNR`);
   - otherwise the candidate must be stronger by 1 dB (current signal below -85 dBm) up to 5 dB (-70 dBm or better);
   - that margin moves by up to 10 dB either way with the two APs' estimated throughput;
   - it is 2 dB smaller for a move from 2.4 GHz to 5 GHz.
3. **It follows every BTM request it can** (`wnm_sta.c`). It compares the
   request's candidates with its own scan results
   (`compare_scan_neighbor_results()`), skips candidates with preference 0, and
   refuses only when no candidate is usable. The one way to make it refuse
   (`reject_btm_req_reason`) is a test knob that needs `CONFIG_MBO` and
   `CONFIG_TESTING_OPTIONS`. `disable_btm=1`, a plain option, turns 802.11v
   off entirely: the capability is not advertised and requests are ignored.

Today's client is therefore an **obedient client that never moves on its
own**, the easiest case an optimizer can meet, and all 100 clients behave
alike.

## 3. Why it is worth doing

- **Optimizer realism.** The questions that matter in the field need a mix:
  - does the optimizer stop steering a client that keeps refusing, and how many actions does it waste first;
  - does it fight a client that roams by itself (ping-pong);
  - does it leave a 2.4 GHz-only device alone;
  - does it escalate on a sticky client only as far as its policy allows;
  - does it avoid BTM towards a client without 802.11v.
- **EMOSA.** Clients also associate to the OpenSync pods. A refused or ignored
  BTM through a pod must come back to the controller as a failed steer; client
  models exercise that path.
- **Comparable labs.** The same catalog in the RDK and prplMesh labs keeps
  optimizer results comparable.

Identical clients stay the default and the reference for every existing room
and regression.

## 4. What a model covers

Every parameter's default is today's behaviour. A model lists only what it
changes.

| Group | Parameter | Meaning | Mechanism |
| --- | --- | --- | --- |
| Capabilities | `bands` | 2.4, 5, 6 GHz allowed | `freq_list`, `scan_freq` (exists) |
| | `phy` | HT, VHT or HE ceiling | `disable_ht`, `disable_vht`, `disable_he` (configuration) |
| | `btm_supported` | advertises 802.11v BSS Transition | `disable_btm` (configuration) |
| | `neighbor_reports` | asks for 802.11k neighbor reports | `wpa_cli neighbor_rep_request` from the patch's roam logic, or not modelled at first |
| | `fast_transition` | 802.11r | `key_mgmt=FT-PSK` or `FT-SAE` (configuration; needs AP support) |
| | `security` | PSK, SAE, PMF | `key_mgmt`, `ieee80211w`, `sae_pwe` (exists) |
| Scanning | `trigger_dbm` | signal below which it starts looking | `bgscan="simple:<short>:<trigger>:<long>"` (needs `CONFIG_BGSCAN_SIMPLE`) |
| | `scan_interval_below_s`, `scan_interval_above_s` | scan cadence under and over the trigger | the bgscan intervals |
| Roaming | `min_improvement_db` | how much better a candidate must be, as a table by current signal or one value | patch: replaces the fixed table in `wpa_supplicant_need_to_roam_within_ess()` |
| | `great_snr_db` | above this SNR it stays unless the candidate's estimated throughput is much higher | patch (today 25 dB) |
| | `band_bonus_db` | extra margin in favour of 5 or 6 GHz, or against | patch |
| BTM | `btm_policy` | `accept`, `reject`, `ignore` | patch in `ieee802_11_rx_bss_trans_mgmt_req()` (`wnm_sta.c`) |
| | `btm_reject_status` | status code of a refusal | patch |
| | `btm_candidate` | the AP's most preferred candidate, or its own best | patch around `compare_scan_neighbor_results()` |
| | `btm_min_improvement_db` | accepts only a candidate this much better | patch |
| | `btm_response_delay_ms` | time before it answers | patch |
| | `disassoc_imminent` | leaves at once, or stays until it is disconnected | patch |
| After a push | `reconnect_delay_s` | pause before it associates again | patch, or the room holds it off |
| | `avoid_bssid_s` | how long it avoids the AP that pushed it off | wpa_supplicant's own temporary ignore list, bounded by the patch |

Not modelled, on purpose:
- roaming held back by traffic (a call, a stream);
- screen, motion and battery states (a "screen off" phone is at most a long scan interval);
- vendor firmware quirks, rate adaptation, per-OS-version differences;
- probe request behaviour;
- MAC address randomization. The room, the optimizer and the journals
  identify clients by MAC, so randomization is a separate question.

## 5. Mechanism options

| Option | What it is | Covers | Against |
| --- | --- | --- | --- |
| A. Configuration only | existing wpa_supplicant options: `bgscan` (once built), `disable_btm`, `freq_list`, `disable_*`, `key_mgmt` | trigger and scan cadence, no 802.11v, bands, PHY, security | cannot change the roam margin, refuse or ignore BTM while advertising it, or prefer a band |
| B. A small lab patch | the fixed decisions above become configuration options whose defaults are 2.10's behaviour; carried like the existing lab patch (RDK) and in `hostap-patches` (prplMesh) | everything in §4 | a patch to keep on two supplicant builds |
| C. A behaviour daemon per client | a process that drives wpa_supplicant over its control interface: pins BSSIDs, triggers scans, forces roams | roaming policy without C | a second control loop in 100 clients, less realistic timing; BTM responses are built inside wpa_supplicant, so refusals cannot be modelled cleanly |
| D. Real operating systems | Android in a virtual device (§8); nothing exists for Apple | whatever the OS does on simulated radios | heavy, few instances, and still not a phone's firmware roaming |

**Recommendation: A plus B.** One supplicant build per lab, carrying the
patch. A model is data: the world compiler resolves it into supplicant
settings, and the same container becomes an eager roamer or an IoT plug when a
room loads. No build variants per model. Option C stays out; D is at most a
spike.

## 6. The first catalog

Six archetypes, named for behaviour. The values are indicative and must come
from the sources in §7, each with its date and confidence.

| Model | Resembles | Indicative behaviour |
| --- | --- | --- |
| `baseline` | today's lab client | no background scan; 2.10 roam margin; follows every BTM; all bands the world allows |
| `eager-roamer` | iPhone and iPad | starts looking around -70 dBm, scans often below it; needs a clear margin (about 8 dB); supports 802.11k, v and r; follows BTM to the AP's preferred candidate; prefers 5 GHz when it is strong enough |
| `sticky` | laptops at default settings, Macs, phones with the screen off | starts looking late (-75 dBm or lower), scans rarely; needs a large margin (12 dB or more); accepts BTM only towards a much better AP, otherwise refuses |
| `btm-refuser` | clients with 802.11v switched off or broken | advertises 802.11v but refuses (or, as a variant, ignores) every request; roams by itself like `baseline`. Variant `no-11v`: does not advertise 802.11v at all (`disable_btm=1`) |
| `iot-2g4` | smart plugs, cameras, sensors | 2.4 GHz only, HT, PSK, no 802.11k/v/r; never roams while associated; after a disconnect joins the strongest AP after a pause |
| `band-loyal` | devices that hold on to 5 or 6 GHz | a large bonus for 5/6 GHz; refuses a BTM towards 2.4 GHz |

## 7. Sources and calibration

| Source | What it gives | How to use it |
| --- | --- | --- |
| Apple Platform Deployment: "Wi-Fi roaming support in Apple devices" (and its macOS notes) | documented roam trigger (on the order of -70 dBm for iOS and iPadOS, -75 dBm for macOS), the candidate margin rule, the 5 GHz preference, 802.11k/v/r support per OS | values for `eager-roamer` and the Mac variant of `sticky`; no Apple stack exists to run |
| AOSP Wi-Fi module (`packages/modules/Wifi`) at a pinned tag | network selection and scoring, per-band RSSI thresholds in the resource overlay, scan scheduling | an Android archetype's selection behaviour. In-network roaming on most shipped phones is done by the Wi-Fi chip's firmware, with vendor thresholds that are neither uniform nor public, so an Android model is labelled **synthesized** |
| Intel Wi-Fi driver "Roaming Aggressiveness" (1 lowest to 5 highest, 3 by default) | documented presets | laptop variants of `sticky` and `eager-roamer` |
| Vendor client guides (Cisco, HPE Aruba, Juniper Mist) and Wi-Fi Alliance Agile Multiband | which client classes support 802.11k/v/r and MBO, and common failure modes | capability sets; secondary |
| Measurement in the physical lab (easymesh-lab) | a real phone or laptop between two APs: the level at which it roams, the margin, its BTM responses and status codes, what it does with a disassociation imminent request, captured over the air | the strongest evidence; records device, OS version and date |

Every value in a model records its source, the date it was read or measured
and a confidence (`documented`, `measured`, `synthesized`). Values are checked
again when a source changes.

## 8. A real Android or Apple client?

- **Apple:** not possible; there is no open stack. A model from Apple's
  published rules is the only option.
- **Android:** possible in principle, not worth it as a client type. AOSP's
  virtual device (Cuttlefish) simulates Wi-Fi with mac80211_hwsim and its own
  wmediumd fork (AOSP `external/wmediumd`), so an Android guest could be
  bridged into the lab's medium. Against it:
  - it needs nested KVM inside the lab VM and several GB and cores per instance;
  - two wmediumd instances would have to be bridged;
  - it runs the AOSP framework on wpa_supplicant, not a phone's firmware roaming.

  It would check Android's network selection and scan scheduling, not a
  phone's roaming. Waydroid and Android-x86 have no usable Wi-Fi stack on
  simulated radios.
- **Recommendation:** at most an optional spike later, one Cuttlefish instance,
  to check the synthesized Android model's selection behaviour.

## 9. Design

### 9.1 Model definitions

One file per model, in a catalog both labs use (where it lives is an open
question, §12). A sketch:

```json
{
  "schema": "client-model/1",
  "id": "eager-roamer",
  "title": "Eager roamer",
  "resembles": ["iPhone and iPad"],
  "capabilities": {"bands": ["2.4", "5", "6"], "phy": "he", "btm_supported": true,
                   "neighbor_reports": true, "fast_transition": false},
  "scanning": {"trigger_dbm": -70, "scan_interval_below_s": 10, "scan_interval_above_s": 300},
  "roaming": {"min_improvement_db": 8, "great_snr_db": 40, "band_bonus_db": {"5": 3, "6": 3}},
  "btm": {"policy": "accept", "candidate": "preferred", "min_improvement_db": 0,
          "response_delay_ms": 0, "disassoc_imminent": "leave"},
  "after_push": {"reconnect_delay_s": 0, "avoid_bssid_s": 10},
  "sources": [
    {"fields": ["scanning.trigger_dbm"], "source": "Apple Platform Deployment, Wi-Fi roaming support in Apple devices",
     "read": "YYYY-MM-DD", "confidence": "documented"}
  ]
}
```

A pure function resolves a model into supplicant settings: global options
(`disable_btm`, the patch's options) and network options (`bgscan`,
`freq_list`, `key_mgmt`, ...). Unit tests hold it to one rule: `baseline`
resolves to no change at all.

### 9.2 Worlds and the compiler

- A world names models per station role (`client_models: {role: model}`) or
  for all its stations (`default_client_model`). Without either field, every
  station is `baseline` and the world's golden stays byte for byte the same.
- `band_steering` stays as it is. A model's bands must agree with a band
  profile on the same role; the validator refuses a conflict.
- The compiler (`wmdcfg`) checks model names against the catalog and writes
  the resolved settings into the compiled bindings, so the room applies
  exactly what was compiled and the golden's hash covers it.

### 9.3 Applying a model when a room loads

- `ClientBandSettings` grows into a client settings stage that captures a
  client's current settings, writes the model's and restores them when the
  world ends, through the same namespace-safe `wpa_cli` path. Global options
  go through `wpa_cli set` (whether `disable_btm` takes effect at runtime is
  spike 2 in §10), network options through `set_network`.
- Models are applied in the world's client reconnect phase, before the client
  associates, so a capability change is in its association request.
- The four-client limit of band profiles does not apply; the cost with 50
  clients is measured (the apply pipeline runs four clients in parallel).

### 9.4 The room's assists

The interactive room's forced scans, RF steering boost and escalation change
what a client does: a forced scan lets any client roam by itself. Rooms with
models run unassisted (`--profiling`), so the model, not the lab, decides.
Whether some assists stay per model is a design decision (§12).

### 9.5 Visibility

- The room state, the topology view and the room view show each client's
  model.
- The trace and the journal record the model with every steer, so a run can be
  analysed per model.
- The optimizer is not told the models: in the field it must learn them. The
  room's checks know them.

### 9.6 Checks and rooms

- **Existing rooms are unchanged**: all their clients are `baseline`.
- **Behaviour probes**, the proof that each model behaves as it says: a
  two-AP world with no optimizer walks a client from one AP to the other. The
  level at which it moves (trigger plus margin) must match the model within a
  tolerance. A lab steer checks its BTM answer (policy, status code,
  candidate choice), and a disassociation imminent request checks what it does
  then. One probe per model, run in both labs.
- **Mixed-fleet rooms**: a few new worlds tagged `client-models`, with
  expectations per model:
  - `baseline` and `eager-roamer` clients end on their strongest AP;
  - `btm-refuser` and `no-11v` clients stay where they chose, and the optimizer's actions towards them stay under a bound (it stops after repeated refusals);
  - an `eager-roamer` is not steered back within a set time after its own roam (no ping-pong);
  - `sticky` clients move only through the escalation the policy allows;
  - `iot-2g4` clients are never steered to 5 GHz;
  - with the pods: a refusal through a pod reaches the controller as a failed steer with its BTM status.
- Per model, each run reports steer attempts, successes, refusals,
  oscillations and time to converge.

### 9.7 Both labs

The same catalog, schema and resolution in the RDK and prplMesh labs. Both
supplicant builds get `CONFIG_BGSCAN_SIMPLE` and the patch; the RDK build also
gets `CONFIG_MBO` if refusals should carry MBO reasons.

## 10. Spikes before the design is final

1. **bgscan on mac80211_hwsim**: does signal monitoring work, so the trigger
   switches between the two scan intervals? If not, the trigger moves into
   the patch (it polls the signal).
2. **`disable_btm` at runtime**: does `wpa_cli set disable_btm 1` take effect
   on the next association (the capability bit)?
3. **The controllers**: do RDK's `em_ctrl` and prplMesh read a station's
   802.11v capability from its association and avoid BTM towards clients
   without it? This decides what the `no-11v` model tests.
4. **Refusal reporting**: how RDK's and prplMesh's agents, and EMOSA through
   the pods, report a refused or ignored BTM to the controller (Client
   Steering BTM Report), and how the optimizer sees it.
5. **Apply cost** at world load with 50 clients.
6. **Interaction with the room's scanning**: the band scanner and forced
   scans, where the band rooms already hit supplicant scan and roam traps.
7. **The values**: Apple, AOSP and Intel values read with their dates.

## 11. Phases

| Step | Done when |
| --- | --- |
| 1 Sources | the catalog's values read from the sources in §7, each with its date and confidence; the spikes in §10 answered |
| 2 Supplicant | both labs' builds carry `CONFIG_BGSCAN_SIMPLE` and the patch, with 2.10's behaviour as the default; **the full existing suites pass unchanged on both labs** |
| 3 Catalog and resolution | the schema, the six models, the resolver and its tests (`baseline` resolves to no change) |
| 4 Worlds | `client_models` in the world format, checked by the compiler, resolved into the bindings; every existing golden unchanged |
| 5 Room | models applied and restored at world load; shown in the room and topology views; recorded in the trace and journal |
| 6 Probes | one behaviour probe per model passes in the RDK lab |
| 7 Mixed-fleet rooms | two or three worlds with per-model expectations; the optimizers' first results recorded (failures here are findings for the optimizer, not for the models) |
| 8 prplMesh | steps 2 to 7 in prplmesh-lab |
| 9 Optional | the pods variant (EMOSA), physical-lab calibration with real devices, the Cuttlefish spike |

**Gate for every step:** the existing suites of both labs still pass
unchanged. The default client must never move.

## 12. Not in scope

- Emulating a specific device or OS version.
- Traffic-, screen-, motion- or battery-dependent behaviour.
- MAC address randomization.
- Replacing the Linux client or running a real phone OS in the lab.
- Changing any existing room's clients.

## 13. Open questions for the user

1. **Where the catalog lives**: in meta-cmf-bananapi-vcpe with a pinned copy in
   prplmesh-lab (like the room engine), or in easymesh-labs for both. *Answered on
   2 October 2026: in easymesh-clients, read by both labs.*
2. **Assists in model rooms**: unassisted only (recommended), or chosen per
   model.
3. **The first catalog**: the six archetypes in §6, or a different set.
4. **Calibration with real devices**: measure a phone and a laptop in the
   physical lab, or rely on published sources first.
5. **Priority**: after the alignment plan's phases 4 and 5, or alongside them
   when the optimizer work needs it (it does not touch EMOSA's phases).
