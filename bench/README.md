# The roaming bench

[Documents](../docs/README.md)

A client running a model between two access points, on `mac80211_hwsim` and the labs'
wmediumd, with the signal levels walked by script and everything recorded on one clock. It
runs the [roaming test plan](../docs/project/roaming-test-plan.md); no lab, controller or
room is involved. Python standard library only.

## What it needs

A Linux host or VM where `mac80211_hwsim` can be loaded (Ubuntu 24.04 with
`linux-modules-extra`), run as root:

| Part | Where from |
| --- | --- |
| `wpa_supplicant`, `hostapd`, and for B11/B12 `iwd`, `wpa_supplicant-2.10` | [supplicant/build.sh](../supplicant/README.md) `--reference --iwd`, into `/root/build` |
| wmediumd with its control socket | an easymesh-medium checkout at the commit the labs' manifest pins, `wmediumd/build-wmediumd.sh`, into `/root/wmediumd` |
| the medium's control client | the same checkout (`configurator/wmdcfg/actuator.py`), at `/root/medium` |
| `iw`, `iproute2`, `ping`, `dbus-daemon` | the distribution |

The paths are the defaults; `--build`, `--wmediumd`, `--medium` and `--iwd` change them.

## Running it

```sh
python3 bench/bench.py run iphone B1 --runs 1        # one test, one model
python3 bench/bench.py suite                         # every applicable test, every model, 3 runs
python3 bench/bench.py suite --models pixel,galaxy --tests B5,B8
python3 bench/bench.py reference                     # B12: baseline on the 2.10 build
python3 bench/report.py /root/bench-runs/results.jsonl --out docs/records/bench-<date>
```

Each run builds the bench from nothing and removes it afterwards: a few seconds of set-up
(the client associates within about a second), then the test's walk. The full suite is 441
runs, about ten hours of run time, most of it the ten-minute B10 runs; on five copies of the
VM side by side, each model on one of them, it took 2 hours 43 minutes. A run's directory (`/root/bench-runs/<model>/<test>/run-<n>/`) holds
`timeline.jsonl`, the client's and the access points' configurations and logs, wmediumd's
configuration and log, and `result.json`; `results.jsonl` collects every result.
`--resume` skips runs that already have one.

## How it is built

| Part | Detail |
| --- | --- |
| Radios | `mac80211_hwsim` loaded per run with three radios (five for the dual-band test), each moved into its network namespace: `ap1`, `ap2`, `sta` |
| Distribution system | namespace `ds`: bridge `br-ds` with the server at 10.99.0.1; each AP's `br0` joins it through a veth pair; the client is 10.99.0.2 |
| Medium | wmediumd with its control socket; a level is set as SNR = level + 91 dB on both directions of the AP–client pair, one generation per step |
| Access points | hostapd per radio, [the profile in the client build's README](../supplicant/README.md#the-benchs-access-point-profile) |
| Client | the model resolved by [clientmodel](../clientmodel/) into `client.conf`, plus the bench's one global option, `freq_list=5180 2412`: the bench's scans cover its two channels |
| Recorder | the client's and each AP's control interface events (`ATTACH`), the client's state and signal every second (`STATUS`, `SIGNAL_POLL`), and every level the driver set; for iwd, its debug log and `iw` |

Why `freq_list`: a scan of every channel on `mac80211_hwsim` takes 15 s unassociated and hits
wpa_supplicant's 30 s scan timeout while associated (mac80211 scans in software, returning
to the operating channel between channels), so its results are thrown away. A phone scans
every channel in a few seconds. Two channels take about 0.15 s.

## Files

| File | What |
| --- | --- |
| [bench.py](bench.py) | the command line: one test, the suite, the reference |
| [rig.py](rig.py) | radios, namespaces, medium, access points, client, recorder |
| [cases.py](cases.py) | the tests: walks, actions and judgements, each derived from the model |
| [report.py](report.py) | results into records: `results.json` and the behaviour cards |
