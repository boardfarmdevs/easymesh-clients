# The bench's results, 3 October 2026

[Documents](../../README.md)

**Kind:** record. Every client model on every test of the
[roaming test plan](../../project/roaming-test-plan.md) that applies to it, three runs each,
on the [bench](../../../bench/README.md); and hostap's own tests on the patched build.

**All 441 runs completed. Every conformance test of every model passed, in all three runs
(279 runs); the 162 runs of characterisation tests are recorded. No run failed and none
ended in an error.** 19 clients ran: 14 models, 4 behaviour combinations and, for B12, the
RDK lab's 2.10 build.

## What ran

| Part | What |
| --- | --- |
| Client | wpa_supplicant 2.12 (tarball SHA-256 `08e23937…737ef6`) with the three patches of [supplicant/patches](../../../supplicant/patches/), `defconfig` and `CONFIG_BGSCAN_MODEL`, `CONFIG_HT_OVERRIDES`, `CONFIG_VHT_OVERRIDES`, `CONFIG_HE_OVERRIDES`. Three builds of the series, each run recording which: as first written (SHA-256 `7ab8cd46…e29e`, 315 runs); with *accept* fixed (`05c46e59…9e3e`, 60 runs: B5 to B7 of the five Windows models); and as committed, with the load refresh fixed too (`5ae4f1d5…4227`, 66 runs: every Pixel and Galaxy run). Each fix was followed by a new run of every test that reaches its code |
| Reference | the RDK lab's wpa_supplicant 2.10 (`20df7ae5…7b2f`) with its hidden-BSS patch and its configuration, rebuilt |
| iwd | iwd 3.12 (`d89a5e45…1a49`) |
| Access points | hostapd 2.12 (`f4350256…eabd`), `defconfig`, `CONFIG_WNM`, `CONFIG_TESTING_OPTIONS`; [the profile](../../../supplicant/README.md#the-benchs-access-point-profile) |
| Medium | wmediumd from easymesh-medium at `2de64a5` (the commit the labs' manifest pins): upstream `717e5d7` and the medium's 36 patches (series `270fef1b…61d2`) |
| Bench | Ubuntu 24.04.5, kernel 6.8.0-142, `mac80211_hwsim`; five copies of one VM on rev140, each model on one of them |
| Environment | the client's scans limited to the bench's two channels (`freq_list=5180 2412`; for iwd, its known frequencies), and each AP listing the other in its neighbor report, as the [test plan](../../project/roaming-test-plan.md#the-benchs-environment) explains |

Every run's `result.json` carries the build's provenance (`build.env`) and the model file's
hash; [results.json](results.json) keeps them all, without the timelines. The timelines and
logs of every run stay in the bench VMs (`/root/bench-runs`, about 90 MB in all).

## The models

A model passes when every conformance test that applies to it passes in all three runs;
the characterisation tests are recorded. [cards.md](cards.md) has a behaviour card per
model: each test, what the model says, what the bench measured in each run.

| Model | Resembles | Conformance tests passed | Recorded | Runs | |
| --- | --- | --- | --- | --- | --- |
| `baseline` | Baseline | 3 of 3: B0, B2, B5 | B1, B3, B5b, B6, B7, B9 | 27 | all pass |
| `iphone` | iPhone | 7 of 7: B0, B1, B2, B3, B4, B5, B10 | B5b, B6, B7, B9 | 33 | all pass |
| `ipad` | iPad | 7 of 7: B0, B1, B2, B3, B4, B5, B10 | B5b, B6, B7, B9 | 33 | all pass |
| `mac` | Mac | 7 of 7: B0, B1, B2, B3, B5, B8, B10 | B5b, B6, B7, B9 | 33 | all pass |
| `mac-intel` | Mac with Intel | 6 of 6: B0, B1, B2, B3, B5, B10 | B5b, B6, B7, B9 | 30 | all pass |
| `pixel` | Pixel | 8 of 8: B0, B1, B2, B3, B5, B6, B8, B10 | B5b, B7, B9 | 33 | all pass |
| `galaxy` | Galaxy | 7 of 7: B0, B1, B2, B3, B5, B8, B10 | B5b, B6, B7, B9 | 33 | all pass |
| `windows-intel` | Windows with Intel | 6 of 6: B0, B1, B2, B3, B5, B10 | B5b, B6, B7, B9 | 30 | all pass |
| `windows-intel-lowest` | Windows with Intel, lowest | 6 of 6: B0, B1, B2, B3, B5, B10 | B5b, B6, B7, B9 | 30 | all pass |
| `windows-intel-medium-low` | Windows with Intel, medium-low | 6 of 6: B0, B1, B2, B3, B5, B10 | B5b, B6, B7, B9 | 30 | all pass |
| `windows-intel-medium-high` | Windows with Intel, medium-high | 6 of 6: B0, B1, B2, B3, B5, B10 | B5b, B6, B7, B9 | 30 | all pass |
| `windows-intel-highest` | Windows with Intel, highest | 6 of 6: B0, B1, B2, B3, B5, B10 | B5b, B6, B7, B9 | 30 | all pass |
| `linux-iwd` | Linux with iwd | 4 of 4: B0, B1, B2, B5 | — | 12 | all pass |
| `iot-2g4` | 2.4 GHz device | 3 of 3: B0, B5, B9 | B5b, B6, B7 | 18 | all pass |
| `pixel+btm-refuser` | Pixel, refuses BTM | 2 of 2: B0, B5 | — | 6 | all pass |
| `pixel+btm-ignorer` | Pixel, ignores BTM | 2 of 2: B0, B5 | — | 6 | all pass |
| `pixel+no-11v` | Pixel, no 802.11v | 2 of 2: B0, B5 | — | 6 | all pass |
| `iphone+btm-refuser` | iPhone, refuses BTM | 2 of 2: B0, B5 | — | 6 | all pass |
| `baseline@2.10` | Baseline on the RDK lab's 2.10 | 3 of 3: B0, B2, B5 | B1, B3 | 15 | all pass |

**B12, the default did not change:** `baseline` on 2.12 with the patch series gives the
same outcomes as the RDK lab's 2.10 build in B0, B1, B2, B3 and B5
([the comparison](cards.md#b12-the-default-did-not-change)).

## What the bench found

- **Each model looks where it says, 2 dB below.** In all 36 runs of B1 with a trigger, the
  first roam scan came when the driver had set AP1 2 dB below the model's trigger (−72 dBm
  for −70): the kernel's signal monitor fires once the signal is below the threshold, and
  the averaged beacon signal it uses reads 1 dB above the set level. Every model then moved
  to AP2 at once. iwd looked at −78 dBm for its −76 dBm threshold and moved 5 s later, when
  its roam timer fired.
- **Margins hold within the scan cadence.** In B3 every model moved 1 to 5 dB over its
  margin (33 runs: +1 in 13, +2 in 3, +3 in 16, +5 in 1), the step being the 5 dB AP2 rises
  between two scans 10 s apart. With traffic (B4) the iPhone and iPad models moved at 13 dB
  for their 8 dB margin, their client's view of the gap being 1 dB smaller than the set one
  and the next scan 5 dB later.
- **Above the trigger, nothing moves them.** B2's three requested scans each found AP2
  20 dB stronger, and every model with a trigger logged `SKIP-ROAM reason=above_trigger`;
  `baseline` stayed too, by upstream's rule that keeps a current AP heard at over 25 dB SNR
  ("Skip roam - Current BSS has good SNR (33 > 25)", in its debug log; 2.12 reports no event
  for that rule).
- **No ping-pong:** 0 moves in all 33 ten-minute runs of B10.
- **Load:** `pixel` and `galaxy` started a roam scan for load (`reason=load`, 80 % advertised)
  and moved 11.1, 16.1 and 11.1 s after the walk put them in their load zone, the steps
  being the 10 s hold and the 5 s between two refreshes of the element; `mac`, the control,
  stayed.
- **Steering requests.** With the Abridged bit (B5) every client under *rules* or *accept*
  followed; `+btm-refuser` answered status 1, `+btm-ignorer` and `+no-11v` sent
  nothing, and `linux-iwd` moved without answering: iwd 3.12 sends no response. Without the
  bit (B5b), every client under *rules* answered status 0 naming its current AP and stayed,
  having chosen from a scan 8 s old; the *accept* models followed. To a weaker AP (B6) all
  followed but `pixel`, which refused with status 7 (its minimum margin of 0 dB).
- **Disassociation imminent (B7):** every client with 802.11v accepted and left for the
  weaker AP2 (−80 dBm). Every model whose trigger is above −80 dBm then came back to AP1 on
  its own, AP1 being 12 dB stronger; `baseline` and the Windows lowest and medium-low levels
  stayed on AP2. `pixel` refused the weaker target, which a client may not do then, so it
  answered accept without a target, stayed until AP1 dropped it 10 s later, joined AP2 and
  returned to AP1. `iot-2g4`, which cannot be asked, was dropped and stayed on AP2.
- **Bands (B9):** every model allowed both bands joined 5 GHz although AP1's 2.4 GHz radio
  was 3 dB stronger; `iot-2g4` stayed on 2.4 GHz.
- **The bench's own environment** (both found while building it): a scan of every channel
  takes 15 to 30 s on `mac80211_hwsim`, so scans are limited to the bench's two channels;
  and an idle client receives about ten beacons a second, so activity counts transmitted
  packets only.
- **Two defects of the patch series, found and fixed.** B5b showed *accept* doing what
  *rules* does without the Abridged bit: it skipped the roaming rules but kept 2.12's own
  choice, and so named the current AP. Patch 0003 now takes the AP's most preferred listed
  candidate; the B5 to B7 runs of the seven *accept* models were run again (that code runs
  only under `btm_policy=1` while a request is handled). Then a read-only look at the RDK
  lab showed its access points put the BSS Load element in their beacons only, while the
  `model` module read the probe response's copy, from an active scan: no RDK access point's
  load would ever have been seen. The module now refreshes the element with a passive scan
  of its channel and reads the beacon's copy first; every Pixel and Galaxy run (the only
  models with a load trigger) was run again. The bench's hostapd puts the element in both
  frames, so the beacon-only case is left for a room (the test plan's step E6).

## hostap's own tests

hostap's hwsim tests of BSS Transition Management, background scanning, roaming, scanning
and configuration, with each of the three builds of the series: 155 passed, 4 skipped, 1
failed, **the same, test by test, with and without the patches** ([every test](hostap-tests.md)). The one
failure belongs to the VM.

## How these were made

```sh
python3 bench/bench.py --out /root/bench-runs --resume suite --models <the VM's models>
python3 bench/bench.py --out /root/bench-runs --resume reference
python3 bench/bench.py --out /root/bench-rerun suite --models <models> --tests <tests>   # after each fix
python3 bench/report.py <the suites' results.jsonl> <the reruns' results.jsonl> --out docs/records/bench-2026-10-03
```

The report keeps one result per model, test and run; a rerun's result, given later, replaces
the earlier one.

Two things went wrong while running and are not in these results: on one VM, a stopped
suite's shell started the next command while the new suite ran, so two benches shared one
set of radios for 42 s; every run of that window was deleted and run again alone. And the
2.10 reference first failed to start at all, because the bench passed it `-f`, which its
build lacks; the bench now runs every client in the foreground, and the reference was run
again.
