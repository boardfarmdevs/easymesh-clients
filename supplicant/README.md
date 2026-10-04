# The client build

[Documents](../docs/README.md)

One wpa_supplicant for every wpa_supplicant client model: **wpa_supplicant 2.12** from the
release tarball, with a three-patch series. Every option the series adds is off by default,
so the build with no options set behaves as 2.12 does. Beside it: stock **hostapd 2.12**
for the bench's access points; the RDK lab's **wpa_supplicant 2.10** rebuilt for comparison;
and **iwd 3.12** for the `linux-iwd` model.

```sh
sudo apt-get install build-essential pkg-config libnl-3-dev libnl-genl-3-dev \
    libnl-route-3-dev libssl-dev libdbus-1-dev libreadline-dev
supplicant/build.sh --reference --iwd          # about 4 minutes on 4 cores
```

The programs go to `supplicant/build/` (or `--output DIR`), never into git, with
`build.env`: the tarballs' SHA-256, the patch series' digest, the build options and this
repository's commit. The tarballs are pinned in [sources.env](sources.env) and checked on
every build; their signatures were checked when they were pinned.

## What is built

| Program | Source | Options | For |
| --- | --- | --- | --- |
| `wpa_supplicant`, `wpa_cli` | wpa_supplicant 2.12 and [patches/](patches/) | `defconfig` and `CONFIG_BGSCAN_MODEL=y` ([wpa_supplicant.config](wpa_supplicant.config)) | every wpa_supplicant model |
| `hostapd`, `hostapd_cli` | hostapd 2.12, unchanged | `defconfig`, `CONFIG_WNM=y`, `CONFIG_TESTING_OPTIONS=y` ([hostapd.config](hostapd.config)) | the bench's access points |
| `wpa_supplicant-2.10` | wpa_supplicant 2.10 and the RDK lab's hidden-BSS patch | the RDK lab's configuration ([reference/](reference/)) | bench test B12 |
| `iwd`, `iwctl` | iwd 3.12 (its tarball carries ell) | `--disable-manual-pages` | `linux-iwd` |

2.12's `defconfig` already has the simple background scan (which brings in WNM, so BTM), SAE,
FT, OWE, DPP and 802.11ac/ax/be. It does **not** have MBO.

## The patch series

| Patch | Adds | Where |
| --- | --- | --- |
| [0001](patches/0001-Roaming-by-a-fixed-margin-a-margin-while-active-and-.patch) | network options `roam_margin`, `roam_margin_active`, `roam_active_pps`, `roam_trigger` | `events.c`, `wpa_supplicant_need_to_roam_within_ess()` |
| [0002](patches/0002-bgscan-model-load-trigger-roam-scan-on-beacon-loss-r.patch) | the background scan module `model` | `bgscan_model.c`, beside `bgscan_simple.c` |
| [0003](patches/0003-BTM-policy-rules-accept-reject-or-ignore-a-minimum-m.patch) | global options `btm_policy`, `btm_reject_status`, `btm_min_margin` | `wnm_sta.c` |

### Network options (patch 0001)

| Option | Default | Meaning |
| --- | --- | --- |
| `roam_margin` | 0: the built-in decision | move within the network only to a candidate heard at least this many dB stronger; replaces the level table, the throughput shortcuts and the 25 dB SNR rule |
| `roam_margin_active` | 0: `roam_margin` | the margin while the station is active |
| `roam_active_pps` | 0: never active | active means it **transmitted** this many packets per second on average since the previous decision (received packets include the AP's beacons, about 10 a second, so are not counted) |
| `roam_trigger` | 0: off | while the current AP is heard above this level (dBm), scan results do not move the station, unless the background scan reported a load trigger. A BSS Transition Management request is not affected |

### The background scan module `model` (patch 0002)

`bgscan="model:<short>:<threshold>:<long>[:<percent>:<high>:<low>:<hold>[:<high_2g4>:<low_2g4>]]"`

The simple module's behaviour: scan every `short` seconds below `threshold` dBm and every
`long` seconds above it, with the kernel's signal monitor (4 dB hysteresis) and the simple
module's back-off. Added:

- **A load trigger.** While the current AP is heard between `high` and `low` dBm (on 2.4 GHz
  between `high_2g4` and `low_2g4`, when given), its channel is scanned passively every
  `hold`/2 s, so a beacon refreshes its BSS Load element; channel utilization above `percent`
  for `hold` seconds starts a roam scan and lets the results move the station above
  `roam_trigger`. The beacon's element is read first: the RDK lab's access points leave it
  out of their probe responses.
- **A scan on beacon loss**, which the simple module does not do (its handler is empty).
  mac80211_hwsim reports no beacon loss, so the bench cannot exercise it.
- **Its scans are limited** to the network's `scan_freq`, or else the global `freq_list`, as
  other scans are; the simple module scans every channel.
- **An event per scan** it requests.

### Global options (patch 0003)

| Option | Default | Meaning |
| --- | --- | --- |
| `btm_policy` | 0 | how a BSS Transition Management request is answered: **0 rules** (2.12 as released), **1 accept** (follow the AP: move to its most preferred listed candidate heard in the last 10 s, scanning first when none is; refuse with status 7 when none can be used), **2 reject** (answer with `btm_reject_status`), **3 ignore** (no answer) |
| `btm_reject_status` | 1 | the status of a rejection |
| `btm_min_margin` | −1: off | with `btm_policy=1`, reject (status 7, no suitable candidate) a target heard less than this many dB stronger than the current AP |

Under **rules**, what 2.12 does depends on the request. With the Abridged bit set (the usual
steering request), an AP that is not in the candidate list, the current one included, is no
candidate, so the client follows the request. Without it, the current AP stays a candidate:
the client picks among the candidates and the current AP by its own ranking, from scan
results it re-uses when they are under 10 s old, and then applies its roaming rules; when
that leaves it where it is, it **accepts with the current AP as its target** and does not
move. On the bench, where the levels had changed since its last scan 8 s before, every
client under *rules* did that (test B5b). *Accept* first did the same, which is not what it
promises; patch 0003 now takes the AP's candidate.

### Events (all patches)

| Event | Fields |
| --- | --- |
| `CTRL-EVENT-DO-ROAM`, `CTRL-EVENT-SKIP-ROAM` | upstream's fields, and `reason=margin margin= active= load=` or `reason=above_trigger trigger=` when a model option decided |
| `CTRL-EVENT-ROAM-SCAN reason=… level=…` | why the background scan asked for a scan: `signal` (crossed below the threshold), `below`, `above` (the interval), `load` and `load-scan` (with `load=`), `beacon-loss` and `beacon-loss-scan` |
| `CTRL-EVENT-BTM-POLICY action=…` | `accept target= target_level=`, `reject status= token=`, `reject reason=min_margin target= target_level= cur_level= margin=`, `ignore token=` |

## The bench's access point profile

hostapd 2.12 with its default capability: no 802.11n/ac/ax, so 802.11a at 54 Mb/s on 5 GHz
channel 36 and 802.11g on 2.4 GHz channel 1, WPA2-PSK, no 802.11r, no PMF, no MBO. Only
these lines are added to its defaults, by the bench:

| Setting | Why |
| --- | --- |
| `bss_transition=1` | advertise 802.11v and accept `BSS_TM_REQ` |
| `rrm_neighbor_report=1` | advertise 802.11k neighbor reports (the list stays empty) |
| `bridge=br0` | both APs on one distribution system |
| `country_code=US` | 5 GHz channel 36 may be used to start a network |
| `bss_load_test=1:<utilization>:0` | test B8 only: a fixed BSS Load element (needs `CONFIG_TESTING_OPTIONS`) |

The full configuration of every run is kept with its results (`hostapd-<ap>.conf`).
