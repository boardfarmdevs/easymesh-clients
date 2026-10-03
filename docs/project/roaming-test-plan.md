# Roaming test plan: checking each client model on a bench

[Documents](../README.md)

**Kind:** project (a test plan). **Prepared:** 3 October 2026, with the
[client models design](../proposals/client-models.md). Nothing here is built yet; it is the
plan for the implementation lab.

The question each test answers: **does a client running a model roam the way the model
says?** At what level it starts looking, how much better the new access point is when it
moves, what makes it look besides signal, and how it answers a BSS Transition Management
(BTM) request. The tests run on a bench without a lab, controller or room.

## 1. The bench

### Parts

| Part | What | From |
| --- | --- | --- |
| Radios | `mac80211_hwsim`, four or five radios | the kernel of the bench host or VM |
| Medium | the labs' patched wmediumd, with its control socket (`-C`) | easymesh-medium's `wmediumd/build-wmediumd.sh`, at the commit the umbrella's manifest pins |
| Signal control | the medium's control client, `configurator/wmdcfg/actuator.py` (standard library only) | the same medium checkout |
| Access points | hostapd, one per AP radio | the same hostap source as the client build |
| Client | wpa_supplicant 2.12 with the client-model patches; or iwd 3.12 for `linux-iwd` | this repository's client build |
| Driver and recorder | one Python script, standard library only | this repository, `bench/` |
| Traffic | `ping`, optionally `iperf3` | the host's packages |

Nothing of a lab is needed: no controller, no room service, no containers. The bench runs as
root in a small VM (two vCPUs, 2 GiB), or on any Linux host where `mac80211_hwsim` can be
loaded. GitHub's runners cannot load kernel modules, so the bench runs on a lab host's VM, not
in CI.

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
- AP settings: `bss_transition=1`, `rrm_neighbor_report=1`, `mbo=1`, `ieee80211w=1`; an FT
  variant (`FT-PSK`, `mobility_domain`) for models that use 802.11r; a load variant with
  `bss_load_test=<stations>:<utilization>:<capacity>` to advertise a fixed channel
  utilization.
- Channels: both APs on 5 GHz channel 36 for most tests (one channel, so a scan sees both at
  once); a dual-band variant (2.4 GHz channel 1, 5 GHz channel 36) for band tests.

### Setting a signal level

The medium reports every received frame at `signal = SNR − 91 dBm`. To put the client at
−72 dBm from AP1, the driver applies SNR 19 to both directions of the AP1–client pair, in one
generation over the control socket. A walk is a list of such generations at set times:
ramps, holds and crossovers. Moving AP1 down while AP2 rises is one generation per step, so
the client never sees half a change.

### What is recorded

| Source | Records |
| --- | --- |
| The driver | every generation it applied, with the level it set for each AP |
| The client | its control interface events, attached with `ATTACH`: `CTRL-EVENT-SIGNAL-CHANGE`, `CTRL-EVENT-SCAN-STARTED`, `CTRL-EVENT-SCAN-RESULTS`, `CTRL-EVENT-DO-ROAM`, `CTRL-EVENT-SKIP-ROAM`, `CTRL-EVENT-CONNECTED`, the WNM events, and the patch series' `CTRL-EVENT-ROAM-SCAN reason=…` |
| The client, polled | `SIGNAL_POLL` every second: current level, frequency, BSSID |
| Each AP | `AP-STA-CONNECTED`, `AP-STA-DISCONNECTED`, `BSS-TM-RESP` with status and target |
| Traffic | the ping or iperf3 result, when a test runs traffic |

Everything goes into one timeline (`timeline.jsonl`) on one clock, from which each test
derives its result.

### Derived measures

| Measure | How |
| --- | --- |
| Look level | the level the driver had set for the current AP when the first roam scan after a crossing started |
| Move level and margin | at `CTRL-EVENT-CONNECTED` to the other AP: the current AP's level, the new AP's level, and their difference |
| Decision trail | the `DO-ROAM` and `SKIP-ROAM` events with the levels the client used, and the margin and activity the patches add |
| Time to move | from the crossing of the trigger to the new association |
| BTM answer | the status in `BSS-TM-RESP`, its target, or no answer within 5 s |
| Moves | the number of associations to a different AP during the test |

## 2. Tolerances

The medium is exact, the client is not instant. A test passes within these bounds:

| Effect | Size | Where it applies |
| --- | --- | --- |
| Levels are whole dB | ±1 dB | every level |
| The kernel averages beacon signal | about 1 dB of lag at a ramp of 1 dB per 2 s | look and move levels |
| The signal monitor's hysteresis (4 dB in the simple background scan) | the look may come up to 4 dB below the trigger | look level |
| Scan cadence below the trigger | up to `scan_below_s` × ramp rate | look and move levels |
| A scan takes time | under 1 s on two channels | time to move |

So, with a ramp of 1 dB per 2 s and a 10 s cadence: **look level within [trigger − 10 dB,
trigger + 1 dB]**, **margin within [model margin, model margin + 6 dB]**. Each bound is
recorded with the result, so a tighter ramp gives a tighter check.

## 3. The tests

**Conformance** tests have a pass and a fail; a model is accepted when all that apply to it
pass. **Characterisation** tests record behaviour the model does not specify.

| # | Test | Walk | Expected | Kind | Applies to |
| --- | --- | --- | --- | --- | --- |
| B0 | Bench sanity | AP1 at −50 dBm, AP2 at −90 | associates to AP1 within 10 s; events arrive; the server answers pings | conformance | all |
| B1 | Look level | AP1 from −50 to −90 dBm at 1 dB per 2 s; AP2 held at −55 | first roam scan at the trigger (bounds in section 2); moves to AP2 shortly after | conformance | models with a trigger |
| B2 | Stays above the trigger | AP1 at −60, AP2 at −40, for 120 s | no move | conformance | models with `stay_above_trigger`; `baseline` (no background scan) |
| B3 | Margin, idle | AP1 held 5 dB below the trigger; AP2 from −90 rising 1 dB per 2 s | moves when AP2 − AP1 reaches the margin | conformance | models with a margin |
| B4 | Margin, with traffic | B3, with the client pinging the server every 20 ms | moves at the active margin (8 dB for `iphone`) | conformance | models whose two margins differ |
| B5 | BTM answer | AP1 −65, AP2 −60; AP1 sends `BSS_TM_REQ` with AP2 as preferred candidate | `accept`: status 0 and a move to AP2 within 5 s; `+btm-refuser`: the configured status, no move; `+btm-ignorer`: no answer; `+no-11v`: AP1 sees no BSS Transition capability in the association | conformance | all |
| B6 | BTM to a weaker AP | as B5 with AP2 at −75 (10 dB weaker) | recorded; `pixel` (minimum margin 0) refuses, the others follow upstream | characterisation, conformance for `pixel` | all |
| B7 | Disassociation imminent, no better AP | AP1 −68, AP2 −80; BTM with Disassociation Imminent and a 10 s timer | recorded: leaves, stays until disconnected, or moves | characterisation | all |
| B8 | Load trigger | AP1 at −72 dBm advertising 80 % channel utilization (`bss_load_test`); AP2 at −55 | `pixel` and `galaxy` look and move; models without a load trigger stay (−72 is above their trigger) | conformance | `pixel`, `galaxy`, and one model without a load trigger as the control |
| B9 | Bands | dual-band APs; the 2.4 GHz one stronger by 3 dB | `iot-2g4` only ever on 2.4 GHz; the others' choice recorded | conformance for `iot-2g4`, characterisation for the rest | all |
| B10 | No ping-pong | AP1 and AP2 alternate ±4 dB around −72 dBm every 10 s for 10 min | at most one move for models with a margin of 8 dB or more | conformance | models with a margin |
| B11 | iwd | B1, B2, B5 with `linux-iwd` | look at −76 dBm on 5 GHz (−70 on the 2.4 GHz variant); follows BTM | conformance | `linux-iwd` |
| B12 | The default did not change | B0 to B3 and B5 with `baseline` on 2.12 and with the labs' 2.10 builds | the same outcomes: no move by itself, BTM followed | conformance | `baseline` |

Each test runs three times; the result records all three and their spread.

## 4. Results

For every run: the timeline, the walk, the client's configuration and its build (version,
patch series, build options), the model file and its hash, and the derived measures with the
bounds they were held to.

For every model, a behaviour card: each documented value next to what the bench measured,
and whether it passed. The cards are kept in this repository's records, dated, so a later
change to the build or a model can be compared with them.

## 5. Order of work

| Step | Done when |
| --- | --- |
| E1 The bench | B0 passes with an unmodified 2.12 and with the labs' 2.10 build |
| E2 The default | B12 passes: 2.12's `baseline` behaves as the labs' client does today |
| E3 The patch series | P1 to P5 built; B12 still passes with every new option at its default |
| E4 The models | B1 to B10 pass for each model, within section 2's bounds; cards written |
| E5 iwd | B11 passes |
| E6 The labs | the shared build in a lab; one model applied by hand to one client in a room; its events in the room's journal |
| E7 Real devices (optional) | the Protocol lab's phones and laptops between its two extenders, walked by hand, the same measures taken from captures; the cards gain a measured column |

## 6. Questions for the implementation lab

1. Does the kernel's signal monitor (CQM) behave on hwsim with wmediumd as on real drivers:
   one event per crossing, with the configured hysteresis? hostap's own hwsim tests use the
   simple background scan, which suggests it does.
2. Is a ping every 20 ms enough for the client to count as "active" through the
   signal poll's packet counters, or does it need a higher rate?
3. Do the RDK and prplMesh access points advertise BSS Load, so B8's behaviour can appear in
   a room at all?
4. Run the bench in a VM per run, or keep one VM and reload `mac80211_hwsim` between runs?
