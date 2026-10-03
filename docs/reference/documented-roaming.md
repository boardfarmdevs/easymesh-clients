# What devices document about roaming

[Documents](../README.md)

**Kind:** reference. **Read on:** 3 October 2026. The sources a client model takes its values
from: what each kind of device, and each candidate implementation, documents about when it
roams and where to. The models built on it are in [client models](../proposals/client-models.md).

Every value carries one of five confidences:

| Confidence | Meaning |
| --- | --- |
| **documented** | stated by the vendor in its own published documentation |
| **documented, secondary** | attributed to the vendor and quoted consistently, but the vendor's original page was not retrieved |
| **configured in source** | set in the vendor's published source code (a driver's build settings); the firmware that applies it is closed |
| **measured** | observed by a third party with a stated method |
| **synthesized** | not documented; chosen for the model and marked so, to be measured later |

## 1. Summary

| Device | Roam trigger | Margin for the new AP | Other triggers | 802.11k / v / r | Confidence |
| --- | --- | --- | --- | --- | --- |
| iPhone (iOS) | −70 dBm | 8 dB with traffic, 12 dB idle | none documented | yes / yes / yes | documented |
| iPad (iPadOS) | −70 dBm | 8 dB with traffic, 12 dB idle | none documented | yes / yes / yes | documented |
| Mac, Apple silicon | −75 dBm | 12 dB | none documented | yes / yes / yes | documented |
| Mac, Intel | −75 dBm | 12 dB | none documented | no / yes / no (interoperates with FT networks) | documented |
| Google Pixel | −75 dBm, all bands | 10 dB | channel utilization over 70 % for 10 s at −70 to −75 dBm (5 GHz), −60 to −75 dBm (2.4 GHz) | yes / yes / yes | configured in source |
| Samsung Galaxy (S and Note since S8) | −75 dBm | 10 dB | beacon loss of 2 s (6 s with the display off); channel utilization over 70 % at −65 to −75 dBm | k and v since S8; r since S6 | documented, secondary |
| Windows laptop, Intel Wi-Fi | Medium aggressiveness by default; Intel gives no dBm. Widely cited: −75 dBm for Medium | not documented | not documented | v on recent adapters (not confirmed by Intel) | documented (levels only); the dBm values synthesized |
| Linux with iwd 3.12 | −70 dBm on 2.4 GHz, −76 dBm on 5 GHz | ranks candidates; no fixed margin | critical −80 / −82 dBm (roam whatever the affinity); retry after 60 s | yes / yes / yes | documented |
| Today's lab client (wpa_supplicant) | none: no background scanning configured | a table from 1 to 5 dB by level, adjusted by estimated throughput and band | a scan caused by something else | yes / yes / per network | source |

## 2. Apple: iPhone, iPad, Mac

**Source:** Apple Platform Deployment, "Wi-Fi roaming support in Apple devices"
(<https://support.apple.com/guide/deployment/wi-fi-roaming-support-dep98f116c0f/web>, last
updated 25 September 2024). Corroborated by Cisco's "Enterprise Best Practices for iOS,
iPadOS, and macOS Devices on Cisco Wireless LAN" (updated 13 April 2022), which gives the
same thresholds.

| Behaviour | iPhone, iPad | Mac |
| --- | --- | --- |
| Roam trigger | keeps the current BSS until its RSSI drops below **−70 dBm** | **−75 dBm**, Apple silicon and Intel alike |
| After the trigger | scans for candidates of the same ESS: all channels in 2.4 and 5 GHz and the preferred scanning channels in 6 GHz; with 802.11k, the first **six** Neighbor Report entries set which channels are scanned first | the same |
| Margin | the candidate must be **8 dB** stronger when the device is transmitting data, **12 dB** when idle | **12 dB**, transmitting or idle |
| Among candidates | Wi-Fi 7 over 6 over 5; wider channels over narrower (160 over 80, 40, 20 MHz); channel utilization and number of associated clients advertised by the network are used | the same |
| 802.11k, v, r | all supported; 802.11v BSS transition data is reviewed when the device needs to roam | Apple silicon: all; Intel Macs: no 802.11k or 802.11r |
| 6 GHz | found out of band, from 2.4 and 5 GHz beacons | the same |

**Not documented by Apple:** the scan cadence below the trigger, whether and when a BTM
request is refused, what happens on a Disassociation Imminent request, and how long the
device waits before roaming again.

## 3. Google Pixel

In-network roaming on a Pixel is done by the Wi-Fi chip's firmware, not by Android. The
firmware is closed; the driver that configures it is open source, published by Google for
each Pixel Wi-Fi chip.

**Source:** the Broadcom `bcmdhd` driver for Pixel phones, Google's kernel modules
(`kernel/google-modules/wlan/bcmdhd/...`), read in the GrapheneOS mirrors of three chips:
`bcm4389` (Pixel 6 and 7), `bcm4398` and `bcm4390` (later Pixels; the `bcm4390` snapshot is
dated 6 December 2024). The three agree.

| Setting | Value | Where |
| --- | --- | --- |
| Roam trigger | **−75 dBm** | `Kbuild`: `CUSTOM_ROAM_TRIGGER_SETTING=-75` |
| Roam delta | **10 dB** | `Kbuild`: `CUSTOM_ROAM_DELTA_SETTING=10` |
| Roam scan period | **10 s** | `wl_cfg80211.h`: `DEFAULT_ROAM_SCAN_PRD 10` |
| Full roam scan period | **120 s** | `wl_cfg80211.h`: `DEFAULT_FULL_ROAM_PRD 0x78` |
| Load-aware roaming (WBTEXT) | 5 GHz: between −70 and −75 dBm, a roam scan when channel utilization is over **70 %** for **10 s**; below −75 dBm, always. 2.4 GHz: the same between −60 and −75 dBm | `wl_android.c`: `DEFAULT_WBTEXT_PROFILE_A_V3 "a -70 -75 70 10 -75 -128 0 10"`, `..._B_V3 "b -60 -75 70 10 -75 -128 0 10"` |
| Candidate score | RSSI weight 65, channel utilization weight 35 | `DEFAULT_WBTEXT_WEIGHT_RSSI_A "RSSI a 65"`, `..._CU_A "CU a 35"` |
| BTM delta | **0** | `Kbuild`: `WBTEXT_BTMDELTA=0`, set as the firmware's `wnm_btmdelta` |

The meaning of the BTM delta is inferred from its name: the improvement a BSS Transition
target needs over the current AP. Zero means a requested target is not refused for being
no stronger.

**Android itself** (source.android.com, "Wi-Fi network selection", describing Android 12)
chooses networks, not access points within one: with the screen on it scans at 20, 40, 80,
then 160 s intervals, and treats a connection as sufficient above −73 dBm (2.4 GHz) and
−70 dBm (5 and 6 GHz). With the screen off, the firmware alone evaluates the link and may
roam.

## 4. Samsung Galaxy

**Source, documented, secondary:** Samsung's description of how its mobile devices roam is
quoted in identical words across forums and write-ups (among them the Ubiquiti community
thread "ROAMING PROBLEM SAMSUNG" and secondary summaries); the original Samsung page was not
retrieved. Its content:

- **Weak signal:** a roaming scan when the current RSSI is below **−75 dBm**; the new AP must
  be **10 dB** stronger.
- **Beacon loss:** no beacon from the current AP for **2 s** (**6 s** with the display off)
  starts a roaming scan.
- **Channel utilization:** a roaming scan when the AP's advertised channel utilization is
  over **70 %** and the RSSI is between **−65 and −75 dBm**; Galaxy S and Note series since
  the S8.
- **Standards:** 802.11r since the Galaxy S6; 802.11k and v since the S8.

**Source, documented:** Samsung Knox Service Plugin, "Device controls" (docs.samsungknox.com):
an enterprise can set **Wi-Fi Roam Trigger** (−100 to −50 dBm), **Wi-Fi Roam Delta**, **Wi-Fi
Roam Scan Period** (0 to 60 s) and the roam bands. Defaults are not given there.

The numbers match the Pixel driver's (−75 dBm, 10 dB), which are also the Broadcom driver's
own built-in defaults (`DEFAULT_ROAM_TRIGGER_VALUE -75`, `DEFAULT_ROAM_DELTA_VALUE 10` in
`dhd.h`); the Samsung and Pixel figures may share that origin. Galaxy phones with Qualcomm
Wi-Fi were not examined.

## 5. Windows laptops with Intel Wi-Fi

**Source, documented:** Intel, "Wi-Fi Roaming Aggressiveness Setting" (article 000005546,
last reviewed 6 February 2025). Five levels: **Lowest** ("will trigger roaming scan for
another candidate AP when the signal strength with the current AP is very low"),
Medium-Low, **Medium** ("Recommended value"; the default), Medium-High, **Highest** ("when
the signal strength with the current AP is still good"). Intel gives no dBm values and no
margin.

**Synthesized from secondary sources:** a mapping of the five levels to −85, −80, −75, −70
and −65 dBm is widely repeated (for example in an Intune write-up of 29 September 2026),
without a citation to Intel. **Measured:** SmallNetBuilder's "Wi-Fi Roaming Secrets
Revealed, Part 3" (Tim Higgins) saw an Intel Windows client roam between −65 and −70 dBm.
The default level is therefore modelled at −75 dBm and marked synthesized, to be calibrated
on real hardware.

## 6. iwd

iwd (Intel's wireless daemon for Linux), release **3.12** of 13 March 2026, documents its
roaming in `iwd.config(5)`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `RoamThreshold` | −70 dBm | how aggressively it roams on 2.4 GHz |
| `RoamThreshold5G` | −76 dBm | the same on 5 GHz |
| `CriticalRoamThreshold` | −80 dBm | roams regardless of the current BSS's affinity (2.4 GHz) |
| `CriticalRoamThreshold5G` | −82 dBm | the same on 5 GHz |
| `RoamRetryInterval` | 60 s | wait after a failed roam attempt |
| `BandModifier2_4GHz`, `5GHz`, `6GHz` | 1.0 | weight of each band in ranking; 0 disables a band |
| `DisableRoamingScan` | false | no scans for roaming decisions |

Its source (`src/station.c`) requests an 802.11k neighbor report before a roam scan when the
AP supports it, and follows AP-directed roaming (802.11v BSS Transition Management). On the
low-signal event it arms a 5 s timer and roams when it fires. It **sends no BSS Transition
Management Response**: 3.12's source has no code for one, and on the bench it moved on a
request without answering it. Without a neighbor report naming another channel it scans
every channel it may use, and it has no scan timeout.

## 7. wpa_supplicant, the lab's client today

The labs run wpa_supplicant 2.10. The current release is **2.12** (7 August 2026); its
ChangeLog lists "improve BSS transition management support". In 2.12:

- **When it roams within an ESS** (`wpa_supplicant_need_to_roam_within_ess()` in
  `wpa_supplicant/events.c`): a candidate with an estimated throughput more than 5 Mb/s
  higher wins at once; no roam while the current SNR is above 25 dB (`GREAT_SNR`); otherwise
  the candidate must be stronger by 1 dB (current below −85 dBm) up to 5 dB (−70 dBm or
  better), a margin moved by up to 10 dB either way with the estimated throughputs and by
  2 dB per band step. Every decision is reported as `CTRL-EVENT-DO-ROAM` or
  `CTRL-EVENT-SKIP-ROAM`, with both levels.
- **When it looks:** only when something causes a scan, unless background scanning is
  configured. `bgscan="simple:<short>:<threshold>:<long>[:<btm_query>]"` scans every
  `<short>` seconds below the threshold (with a 4 dB hysteresis on the kernel's signal
  monitor) and every `<long>` seconds above it; the optional fourth field sends a BSS
  Transition Management query to the AP instead of a plain scan.
- **BTM** (`wnm_scan_process()` in `wpa_supplicant/wnm_sta.c`, seen on the bench): with the
  Abridged bit set, the usual steering request, an AP not in the candidate list is no
  candidate, the current one included, so the client follows the request. Without it, the
  current AP stays a candidate: the client picks among the candidates and the current AP by
  its own ranking, from scan results it re-uses when they are under 10 s old, then applies
  its roaming rules, and when that leaves it where it is, **accepts with the current AP as its
  target** and stays. With Disassociation
  Imminent it never refuses, and it leaves even for a weaker AP. A refusal on demand
  (`reject_btm_req_reason`) exists only in a build with `CONFIG_TESTING_OPTIONS` and MBO.
  `disable_btm=1` stops advertising 802.11v and ignores requests.
- **Defaults in its build configuration:** 2.12's `defconfig` has `CONFIG_BGSCAN_SIMPLE`,
  which brings in `CONFIG_WNM`; it does **not** have `CONFIG_MBO` (corrected 3 October 2026;
  this text first said it had). The RDK lab's own build has WNM but neither MBO nor
  background scanning.
- **The simple background scan on beacon loss** does nothing: its handler is empty.
- **Signal poll** returns the station's transmitted and received packet counts, enough to
  tell a client that is passing traffic from an idle one.

## 8. A real Android in the lab

Android's emulator for devices, Cuttlefish, can run its Wi-Fi on `mac80211_hwsim` with its
own wmediumd (source.android.com, "Test connectivity of multiple devices"). It needs its own
virtual machine per device, not a container. In it there is no phone firmware to roam, so
moving between access points falls to the Android framework's network selection and AOSP's
wpa_supplicant: open-source code, but not what a phone does, whose roaming within a network
is the firmware's (section 3).

## 9. Not documented anywhere examined

- How long any device waits after a roam before it will roam again.
- Refusal rules for BTM requests on Apple, Samsung and Intel devices.
- Behaviour on a Disassociation Imminent request without a better candidate.
- Scan cadence below the trigger for Apple and Intel devices.
- Anything specific to Wi-Fi 7 multi-link roaming.

These stay synthesized in the models until measured on real devices.
