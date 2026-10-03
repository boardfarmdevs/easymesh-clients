# Roaming test plan: checking each client model on a bench

[Documents](../README.md)

**Kind:** project (a test plan). **Prepared:** 3 October 2026, with the
[client models design](../proposals/client-models.md). **Implemented:** 3 October 2026, as
[bench/](../../bench/README.md); the results of every model are in
[the records](../records/bench-2026-10-03/README.md). Where building the bench changed the
plan, this text says so.

The question each test answers: **does a client running a model roam the way the model
says?** At what level it starts looking, how much better the new access point is when it
moves, what makes it look besides signal, and how it answers a BSS Transition Management
(BTM) request. The tests run on a bench without a lab, controller or room.

## 1. The bench

### Parts

| Part | What | From |
| --- | --- | --- |
| Radios | `mac80211_hwsim`, three radios (five for the dual-band test), loaded afresh for every run | the kernel of the bench VM |
| Medium | the labs' patched wmediumd, with its control socket (`-C`) | easymesh-medium's `wmediumd/build-wmediumd.sh`, at the commit the umbrella's manifest pins |
| Signal control | the medium's control client, `configurator/wmdcfg/actuator.py` (standard library only) | the same medium checkout |
| Access points | stock hostapd 2.12, one per AP radio | [the client build](../../supplicant/README.md) |
| Client | wpa_supplicant 2.12 with the client-model patches; iwd 3.12 for `linux-iwd`; the RDK lab's 2.10 for B12 | the same build |
| Driver and recorder | one Python program, standard library only | [bench/](../../bench/README.md) |
| Traffic | `ping` | the VM's packages |

Nothing of a lab is needed: no controller, no room service, no containers. The bench runs as
root in a small VM (Ubuntu 24.04, 2 to 4 vCPUs, 4 to 6 GiB), or on any Linux host where
`mac80211_hwsim` can be loaded. GitHub's runners cannot load kernel modules, so the bench
runs on a lab host's VM, not in CI.

### Layout

```
   netns ap1                      netns ap2                    netns sta
 ┌──────────────────┐          ┌──────────────────┐         ┌──────────────────┐
 │ hostapd  wlan(1) │          │ hostapd  wlan(2) │         │ wpa_supplicant   │
 │   br0 ── veth ───┼──┐   ┌───┼── veth ── br0    │         │ or iwd   wlan(s) │
 └──────────────────┘  │   │   └──────────────────┘         │ 10.99.0.2        │
                       ▼   ▼                                 └──────────────────┘
                  netns ds: bridge br-ds, server 10.99.0.1
        radios ◄──────── wmediumd: every frame, SNR per directed pair ──────────►
```

- Each radio is moved into its namespace (`iw phy <phy> set netns name <ns>`).
- Both APs share one SSID, one passphrase and one distribution system (`ds`), so the
  client keeps its address and its traffic to the server across a roam.
- **The access points** are hostapd 2.12 with its default capability (802.11a at 54 Mb/s on
  5 GHz channel 36, 802.11g on 2.4 GHz channel 1, WPA2-PSK) and: `bss_transition=1`,
  `rrm_neighbor_report=1` with each AP listing the other in its neighbor report, and, for
  B8 only, `bss_load_test` for a fixed channel utilization. Built with `CONFIG_WNM` and
  `CONFIG_TESTING_OPTIONS` (for `bss_load_test` only). Changed from the plan: no `mbo=1`
  (MBO is not in hostapd's default build), no PMF and no FT variant, which no test needed.
  [The profile](../../supplicant/README.md#the-benchs-access-point-profile) lists every line.
- Channels: both APs on 5 GHz channel 36 (one channel, so a scan sees both at once); a
  dual-band variant (2.4 GHz channel 1 and 5 GHz channel 36 on each AP) for B9.

### The bench's environment

**A scan on the bench covers its two channels.** The client gets one global option from the
bench, not from its model: `freq_list=5180 2412`. iwd gets the same through its own record
of where it has seen the network (`.known_network.freq`), and the APs' neighbor reports name
each other. Without these, a scan of every channel on `mac80211_hwsim` takes about 15 s
unassociated; associated, wpa_supplicant's scan hits its 30 s timeout and its results are
thrown away, and iwd's takes 27 s. A phone scans every channel in a few seconds, so on the
bench a scan takes about 0.15 s instead. The `model` background scan module honours
`freq_list` for this reason (the simple module scans every channel whatever is set).

### Setting a signal level

The medium reports every received frame at `signal = SNR − 91 dBm`. To put the client at
−72 dBm from AP1, the driver applies SNR 19 to both directions of the AP1–client pair, in one
generation over the control socket. A walk is a list of such generations at set times:
ramps, holds and crossovers. Moving AP1 down while AP2 rises is one generation per step, so
the client never sees half a change. Levels are exact: the client's signal poll reads the set
level, and its average follows within 1 dB in a few seconds.

### What is recorded

| Source | Records |
| --- | --- |
| The driver | every generation it applied, with the level it set for each AP; every scan it asked for and BTM request it sent |
| The client | its control interface events, attached with `ATTACH`: `CTRL-EVENT-SIGNAL-CHANGE`, `CTRL-EVENT-SCAN-STARTED`, `CTRL-EVENT-SCAN-RESULTS`, `CTRL-EVENT-DO-ROAM`, `CTRL-EVENT-SKIP-ROAM`, `CTRL-EVENT-CONNECTED`, and the patch series' `CTRL-EVENT-ROAM-SCAN` and `CTRL-EVENT-BTM-POLICY`; for iwd, which has no control socket, its debug log's roaming lines |
| The client, polled | `STATUS` and `SIGNAL_POLL` every second: state, BSSID, frequency, levels (for iwd: `iw dev … link`) |
| Each AP | `AP-STA-CONNECTED`, `AP-STA-DISCONNECTED`, `BSS-TM-RESP` with status and target |
| Traffic | the ping summary, when a test runs traffic |

Everything goes into one timeline (`timeline.jsonl`) on one clock, from which each test
derives its result.

### Derived measures

| Measure | How |
| --- | --- |
| Look level | the level the driver had set for AP1 at the client's first roam scan of the walk: `CTRL-EVENT-ROAM-SCAN reason=signal` (or `below`, `beacon-loss`); for iwd, its line "Arming new roam timer" |
| Move level and margin | at the association to the other AP: the levels the driver had set for both, and their difference |
| Decision trail | the `DO-ROAM` and `SKIP-ROAM` events with the levels the client used, and the margin, activity and load the patches add |
| BTM answer | the status in `BSS-TM-RESP` and its target, or no answer within 10 s |
| Moves | the associations to an AP during the test (for iwd, the changes of the polled BSSID) |

## 2. Tolerances

The medium is exact, the client is not instant. A test passes within these bounds:

| Effect | Size | Where it applies |
| --- | --- | --- |
| Levels are whole dB | ±1 dB | every level |
| The kernel averages beacon signal | about 1 dB of lag at a ramp of 1 dB per 2 s | look and move levels |
| The signal monitor fires below the threshold, not at it | 1 to 2 dB | look level |
| Scan cadence below the trigger | up to `scan_below_s` × ramp rate: 5 dB at 10 s | move level, margin |
| A scan takes time | about 0.15 s on the bench's two channels | time to move |

So, with a ramp of 1 dB per 2 s and a 10 s cadence: **look level within [trigger − 10 dB,
trigger + 1 dB]**, **margin within [model margin, model margin + 6 dB]**. Each bound is
recorded with the result.

## 3. The tests

**Conformance** tests have a pass and a fail; a model is accepted when all that apply to it
pass. **Characterisation** tests record behaviour the model does not specify. What a model
should do is derived from the model file, so one test serves every model.

| # | Test | Walk | Expected | Kind | Applies to |
| --- | --- | --- | --- | --- | --- |
| B0 | Bench sanity | AP1 at −50 dBm, AP2 absent | associates to AP1 within 30 s; events arrive; the server answers pings | conformance | all, on 2.4 GHz for a 2.4 GHz-only model |
| B1 | Look level | AP1 from −50 to −90 dBm at 1 dB per 2 s; AP2 held at −55 | first roam scan at the trigger (bounds in section 2); moves to AP2 | conformance; recorded for `baseline` | models with a trigger, `linux-iwd` (its 5 GHz threshold), `baseline` |
| B2 | Stays above the trigger | AP1 at −60, AP2 at −40, for 120 s; the driver asks the client to scan at 10, 50 and 90 s | no move | conformance | models with `stay_above_trigger`; `baseline`; `linux-iwd` |
| B3 | Margin, idle | AP1 held 5 dB below the trigger (−75 dBm for `baseline`); AP2 from −90 rising 1 dB per 2 s | moves when AP2 − AP1 reaches the margin | conformance; recorded for `baseline` | models with a margin, `baseline` |
| B4 | Margin, with traffic | B3, with the client pinging the server every 20 ms | moves at the active margin (8 dB for `iphone`) | conformance | models whose two margins differ |
| B5 | BTM answer | AP1 −65, AP2 −60; AP1 sends `BSS_TM_REQ` with AP2 as preferred candidate and the Abridged bit set | by policy: *rules* and *accept*: status 0 and a move to AP2; *reject*: the configured status, no move; *ignore*: no answer, no move; no 802.11v: no answer, no move, and AP1 sees no BSS Transition capability; `linux-iwd`: a move, no answer | conformance | all |
| B5b | BTM answer without the Abridged bit | as B5, Abridged bit clear | recorded: under *rules* the current AP stays a candidate and the client chooses; *accept* follows | characterisation | wpa_supplicant models (added while building the bench) |
| B6 | BTM to a weaker AP | as B5 with AP2 at −75 (10 dB weaker) | `pixel` (minimum margin 0) refuses with status 7; the rest recorded against the prediction of their policy | conformance for `pixel`, characterisation for the rest | wpa_supplicant models |
| B7 | Disassociation imminent, no better AP | AP1 −68, AP2 −80; BTM with Disassociation Imminent and a timer of 100 beacon intervals | recorded: leaves, stays until disconnected, or moves | characterisation | wpa_supplicant models |
| B8 | Load trigger | AP1 at −72 dBm advertising 80 % channel utilization (`bss_load_test`); AP2 at −55 | `pixel` and `galaxy` look (`reason=load`) and move within 60 s; `mac`, whose −75 dBm trigger is below −72, stays | conformance | `pixel`, `galaxy`, and `mac` as the control |
| B9 | Bands | dual-band APs; AP1's 2.4 GHz radio at −57, its 5 GHz radio at −60; a scan at 20 s | `iot-2g4` only ever on 2.4 GHz; the others' choice recorded | conformance for `iot-2g4`, characterisation for the rest | wpa_supplicant models |
| B10 | No ping-pong | AP1 and AP2 alternate between −68 and −76 dBm every 10 s for 10 min | at most one move | conformance | models with a margin of 8 dB or more |
| B11 | iwd | B1, B2, B5 with `linux-iwd` | look at −76 dBm on 5 GHz; no move above it; follows BTM | conformance | `linux-iwd` |
| B12 | The default did not change | B0, B1, B2, B3, B5 with `baseline` on the RDK lab's 2.10 build | the same outcomes as 2.12's `baseline` | conformance | `baseline` |

Each test runs three times; the result records all three. The behaviour variants run B0 and
B5 (`pixel+btm-refuser`, `pixel+btm-ignorer`, `pixel+no-11v`, `iphone+btm-refuser`).

## 4. Results

For every run, in the bench VM: the timeline, the client's and the access points'
configurations and logs, wmediumd's configuration and log, and `result.json` with the model
file's hash, the build's provenance (`build.env`: tarballs, patch series digest, options),
the derived measures and the bounds they were held to.

Kept in this repository ([records](../records/bench-2026-10-03/README.md)): every run's
result without its timeline (`results.json`), and a behaviour card per model
(`cards.md`): what the model says next to what the bench measured, and whether it passed.

## 5. Order of work

| Step | Done when | State |
| --- | --- | --- |
| E1 The bench | B0 passes with 2.12 and with the labs' 2.10 build | done, 3 Oct |
| E2 The default | B12 passes: 2.12's `baseline` behaves as the labs' client does today | done, 3 Oct; see the records |
| E3 The patch series | built; B12 still passes with every new option at its default; hostap's own hwsim tests of BTM, background scanning, roaming and scanning still pass | done, 3 Oct; see the records |
| E4 The models | B1 to B10 pass for each model, within section 2's bounds; cards written | done, 3 Oct; see the records |
| E5 iwd | B11 passes | done, 3 Oct |
| E6 The labs | the shared build in a lab; one model applied by hand to one client in a room; its events in the room's journal | not started (this step changes the labs) |
| E7 Real devices (optional) | the Protocol lab's phones and laptops between its two extenders, walked by hand, the same measures taken from captures; the cards gain a measured column | not started |

## 6. Questions for the implementation lab

1. Does the kernel's signal monitor (CQM) behave on hwsim with wmediumd as on real drivers?
   **Found on the bench:** yes for the crossings the tests make: one event per crossing,
   fired 1 to 2 dB below the threshold (set −72, reported −71, for a −70 trigger).
2. Is a ping every 20 ms enough for the client to count as "active"? **Found:** yes, once
   "active" counts transmitted packets only; counting received packets too made every client
   active, because the AP's beacons alone are about ten a second. Patch 0001 counts
   transmitted packets.
3. Do the RDK and prplMesh access points advertise BSS Load, so B8's behaviour can appear in
   a room at all? **Open:** it needs the labs (step E6).
4. Run the bench in a VM per run, or keep one VM and reload `mac80211_hwsim` between runs?
   **Done so:** one VM, `mac80211_hwsim` reloaded and every namespace rebuilt for each run;
   the full suite ran in three copies of the VM side by side.
