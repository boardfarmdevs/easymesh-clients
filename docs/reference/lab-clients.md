# The clients of each lab

[Documents](../README.md)

**Kind:** reference. **Read from the labs' sources on:** 2 October 2026. No lab was running
when this was written, so nothing here was measured on a live client; the two facts that
need a live check are marked *to verify*.

Every lab has Wi-Fi clients, and every lab creates them with its own scripts. This document
records what each lab's client is, exactly, so the differences are known before anything is
shared. The proposal that builds on it is [More capable clients](../proposals/more-capable-clients.md).

## 1. What every client has in common

- **One simulated radio.** A `mac80211_hwsim` radio from the lab VM's pool, handed to the
  client as its `wlan0`. What the radio hears is decided by the RF medium
  ([easymesh-medium](https://vcpe.dev/easymesh-medium/)). The Protocol lab is the
  exception: its clients are real USB adapters.
- **wpa_supplicant** on that radio, with one network configured, and a control socket for
  `wpa_cli`.
- **An address on `wlan0`**, from the gateway's DHCP server or set by the lab.
- **Nothing running that waits for commands.** A client has no agent and no API. The lab
  reaches it from the VM host, with `lxc exec` or `nsenter`.
- **A name that follows a pattern.** Tools recognize a client by its container name.

## 2. The four implementations

| | RDK EasyMesh | prplMesh | OpenSync lab | Protocol lab |
| --- | --- | --- | --- | --- |
| Repository | meta-cmf-bananapi-vcpe | prplmesh-lab | opensync-lab | easymesh-lab |
| Entry point | `gen/wlan-client.sh`, `gen/wlan-client-pool.sh` | `scripts/radio-lab.sh` (`deploy`, `clients`) | `guest/80-client.sh <name> <pod>` | `tools/wifi_clients.py` (a systemd service) |
| What a client is | an LXD container | an LXD container | an LXD container | a network namespace |
| Name | `wlan-client`, `wlan-client-NNN` | `prpl-client-NN` | free; default `pod-1-wc1` | from the configuration, such as `wifi-client-a` |
| Image | `wlan-client-base`, built from Alpine | `prpl-client-local`, built from Ubuntu 22.04 | `mvx-wclient`, built from Alpine 3.22 | none: the VM's own tools |
| Supplicant | wpa_supplicant 2.10, the lab's own build | wpa_supplicant from hostap 2.10 at a pinned commit, the lab's own build | Alpine's package | Ubuntu's package |
| 802.11v (BTM) | built in (`CONFIG_WNM`) | built in (`CONFIG_WNM`, `CONFIG_MBO`) | not built in | not recorded |
| Radio | one hwsim radio | one hwsim radio | one hwsim radio | one USB Wi-Fi adapter |
| Wired interface | `eth0` on the VM's LXD bridge | not set by the lab's scripts (*to verify*) | none | none |
| Address | DHCP from the gateway, asked once | static, `192.168.77.x/24` | DHCP from the gateway, kept and renewed | static, from the configuration |
| How many | 100 (50 private, 50 IoT) | 100 (50 private, 50 IoT) | one per call | the enrolled adapters (two) |
| Limits | 128 MB, 1 CPU | none set by the lab's scripts | 128 MiB | none |
| Starts with the VM | no (`boot.autostart=false`); the lab starts it | no; the lab starts it | no | yes, the service |

In the RDK lab's EMOSA option the same RDK clients also associate to OpenSync pods.

## 3. The RDK lab's client

### Image

`gen/wlan-client.sh build-image` builds `wlan-client-base` once from the VM's `alpine`
image:

- `iw` and Alpine's `wpa_supplicant` package (for its runtime libraries and `wpa_cli`);
- `/usr/local/sbin/wpa_supplicant-wnm`, a binary committed in `gen/wpa_supplicant/`;
- `/etc/local.d/wlan.start`, an OpenRC `local` hook that connects from `/etc/wpa.conf`
  whenever the container starts.

The image holds no `iperf3`, `tcpdump` or `python3`.

### Supplicant

`gen/wpa_supplicant/build-wnm-supplicant.sh` builds wpa_supplicant 2.10 from the w1.fi
tarball (its checksum is pinned) with this configuration:

```
CONFIG_DRIVER_NL80211=y   CONFIG_LIBNL32=y      CONFIG_CTRL_IFACE=y
CONFIG_BACKEND=file       CONFIG_TLS=openssl    CONFIG_WNM=y
CONFIG_IEEE80211R=y       CONFIG_IEEE80211AC=y  CONFIG_IEEE80211AX=y
CONFIG_IEEE80211W=y       CONFIG_SAE=y
```

- `CONFIG_WNM` is why the lab builds its own: Alpine's build has no BSS Transition
  Management handler, so it drops a steering request without answering.
- One patch, `0001-wnm-select-hidden-bss-by-current-ssid.patch`: when a hidden BSS has
  both an empty-SSID and a full-SSID entry in the scan table, a steer picks the entry of
  the current network.
- Not built: background scanning (`bgscan`), MBO, the testing options.

### Configuration

`wlan-client.sh [-i NNN] [--cohort NAME] [--security MODE] [--band BAND] up [ssid] [psk]`
writes `/etc/wpa.conf` with one network:

| Option | Values | What it writes |
| --- | --- | --- |
| `ssid` | the lab uses `private_ssid` and `iot_ssid` | `ssid=`; `scan_ssid=1` for `iot_ssid`, which is not broadcast |
| `--security` | `auto`, `open`, `wpa2`, `sae` | `key_mgmt=NONE`, `WPA-PSK`, or `SAE` with `ieee80211w=2` (and `sae_pwe=1` on 6 GHz) |
| `--band` | `auto`, `2.4`, `5`, `6` | `scan_freq=` and `freq_list=`, the frequencies the lab's access points support in that band |
| `--cohort` | `private`, `iot` | nothing in the supplicant; recorded on the container |

The control socket is `ctrl_interface=/run/wpa_supplicant`.

Each client has an LXD profile of its own name: `boot.autostart=false`,
`limits.memory=128MB`, `limits.cpu=1`, a root disk, `eth0` on `lxdbr0` and the radio as
`wlan0`. What was asked for is recorded on the container, so tools can tell clients apart
without reading their MAC addresses:

```
user.easymesh.cohort   user.easymesh.ssid   user.easymesh.security
user.easymesh.band     user.easymesh.band-scope   user.easymesh.ordinal
```

### Start, and the gates it must pass

`wlan.start` waits for `wlan0`, starts the supplicant, waits up to 20 seconds for an
association, clears old addresses and runs `udhcpc -i wlan0 -n -q`: one lease, then the DHCP
client exits. Nothing renews the lease afterwards.

`up` then accepts the client only when all of these hold:

1. it is associated (20 seconds, then two retries of 30 seconds with a fresh supplicant);
2. with `--band`, the frequency it associated on is in that band;
3. `wlan0` has an IPv4 address;
4. the controller lists it: its MAC is in the controller's station list as associated,
   within 30 seconds (skipped with `WAIT_EASYMESH_EXPORT=0`, and when no controller runs).

Creating one client refreshes wmediumd, because wmediumd registers a fixed set of radios.

### The pool

`wlan-client-pool.sh plan|up|down|status` always provisions the same 100 clients.

| Index | Container | Cohort and ordinal | SSID |
| --- | --- | --- | --- |
| 0 to 9 | `wlan-client`, `wlan-client-001` to `-009` | private 1 to 10 | `private_ssid` |
| 10 to 19 | `wlan-client-010` to `-019` | IoT 1 to 10 | `iot_ssid` |
| 20 to 99 | `wlan-client-020` to `-099` | alternating: even private, odd IoT; ordinals 11 to 50 | by cohort |

- Every client is WPA2 with `--band auto`, with two exceptions: private ordinal 9 is
  2.4 GHz only, and private ordinal 10 is 6 GHz with SAE.
- The pool needs 105 radios (100 clients and five mesh nodes); the hwsim pool holds at
  most 128.
- `up` keeps a client that is already healthy, with its radio and identity, and creates
  only the others. It takes wmediumd down while it provisions and registers all radios
  once at the end.
- It finishes when the controller's topology shows 50 private and 50 IoT stations, then
  switches on the controller's metrics reporting.

## 4. The prplMesh lab's client

### Image

`scripts/build-runtime-image.sh client` builds `prpl-client-local` from a cached Ubuntu
22.04 image with `scripts/container/setup-client-base.sh`:

- packages: `iw`, `iproute2`, `iputils-ping`, `iperf3`, `tcpdump`, `python3`, `curl`,
  `procps`, `psmisc`;
- `wpa_supplicant` and `wpa_cli` from the lab's hostap build
  (`artifacts/hostap-runtime-2.10.tar.gz`).

### Supplicant

`scripts/container/build-hostap-inside.sh` builds hostapd and wpa_supplicant from hostap
2.10 at the commit pinned as `HOSTAP_COMMIT` in `manifests/lab.env`, with the lab's
`hostap-patches`. The supplicant is the default configuration plus `CONFIG_WNM` and
`CONFIG_MBO`, without D-Bus.

### Configuration and start

`radio-lab.sh deploy` creates the containers (`security.privileged=true`, the project
mounted at `/mnt/project`, one radio as `wlan0`, no autostart). `radio-lab.sh clients`
starts the active ones, several at a time. For each, `setup-client.sh <ordinal> <cohort>
<band>`:

1. sets the MAC address: `02:00:00:10:NN:00` for private, `02:00:00:20:NN:00` for IoT;
2. writes the configuration from `manifests/wpa_supplicant.conf`:
   `ctrl_interface=/var/run/wpa_supplicant`, the cohort's SSID, `ieee80211w=1`, and one
   frequency as `frequency`, `scan_freq` and `freq_list`:

   | Band | Frequency | `key_mgmt` |
   | --- | --- | --- |
   | 2.4 | 2437 MHz | `WPA-PSK` |
   | 5 | 5180 MHz | `WPA-PSK` |
   | 6 | 5975 MHz | `SAE` |

3. starts the supplicant and waits up to 30 seconds for `wpa_state=COMPLETED`;
4. sets a static address, `192.168.77.(100 + n)/24`. There is no DHCP.

The whole setup is retried once. The lab then waits up to 30 seconds for the station to
appear in the controller's model; if it does not, it reconnects the client once and waits
up to 90 seconds.

### The pool

`manifests/lab.env`: 100 clients provisioned and 100 active, on 120 hwsim radios. Odd
ordinals are private, even ones IoT. The band follows the cohort ordinal, in a pattern of
ten: two on 2.4 GHz, five on 5 GHz, three on 6 GHz.

## 5. The OpenSync lab's client

`guest/80-client.sh <name> <pod>` creates one client behind one pod.

- **Image:** `mvx-wclient`, Alpine 3.22 with Alpine's `wpa_supplicant` and `iw`.
- **Container:** privileged, 128 MiB, no autostart, one hwsim radio as `wlan0` and **no
  other interface**.
- **Configuration:** the home SSID, WPA2-PSK, `scan_ssid=1`, and `bssid=` set to the pod's
  fronthaul. Every pod has the same SSID on the one medium, so the client is pinned to its
  pod.
- **Start:** an OpenRC `local` script starts the supplicant and a `udhcpc` that stays
  running: it keeps and renews the lease from the gateway. IPv6 is off on `wlan0`.
- **Checks, as it is created:** associated to the pod's BSSID; listed by the pod; a lease
  from the gateway, across the pod's backhaul; the gateway's DHCP server lists it; ping,
  DNS and an HTTP request to the internet.

This is the only client that is checked as a device on a home network: lease, DNS,
internet.

## 6. The Protocol lab's clients

Real radios. `tools/wifi_clients.py` runs as `easymesh-wifi-clients.service` in the lab VM.

- Each enrolled USB Wi-Fi adapter (by MAC, from `/etc/easymesh-wifi-clients.json`) is moved
  into its own network namespace and renamed `wlan0`. No veth, bridge, default route or NAT
  connects the namespaces: traffic between two clients goes over the air.
- Per client: a static address, WPA2 or WPA3 (SAE with protected management frames),
  optionally one `bssid` and one `scan_freq`. Power save is off.
- Every five seconds the service writes each client's link, radio and station information
  to `run/wifi-clients/status.json`.
- Traffic is run by hand: `iperf3` in one namespace as server, in the other as client,
  each bound to its own address.

## 7. Clients in a room

A room does not name containers. The world file (the medium's configurator, `wmdcfg`)
names **roles**; each lab's bindings file maps roles to its own containers.

| Piece | Where | What it does |
| --- | --- | --- |
| Roles | the world: `sta_static_NN`, `sta_mobile_NN` | per generation, each role is present or not and has a position |
| Bindings | each lab, `rooms/bindings/*.json` (`optimizer.lab-bindings.v1`) | role to container; the two labs bind different containers to the same role |
| Pool roles | the room service, `room_service/pool.py` | clients no world role uses are bound as `sta_pool_021` to `sta_pool_100` and are absent |
| Capacity | `room_service/pool.py` | at most 100 clients, in equal private and IoT halves |
| Name patterns | the medium, `wmdcfg/stacks.py` | `^wlan-client(?:-\d{3})?$` and `^prpl-client-\d{2,}$` |

- **Movement is the medium's.** A world moves a role's position and the medium changes
  what that radio hears. The client is not told and runs nothing.
- **Presence.** The interactive room's baseline is every client online. A client a world
  does not use is disconnected (`wpa_cli disconnect`) and noted as paused in the room's
  recovery record, so it is reconnected when the room ends or is interrupted. The default
  room keeps 20 clients online.
- **Band profiles.** A world may give at most four clients `allowed_bands`, `initial_band`
  and `measurement_mode`. The room captures the client's current network settings
  (`freq_list`, `scan_freq`, `key_mgmt`, `ieee80211w`, `sae_pwe`), writes the profile's and
  restores them after the world (`room_service/band_profiles.py`).

## 8. What reaches into a client

All of it runs on the VM host and enters the client with `lxc exec` or `nsenter`.

| Operation | Command in the client | Who uses it |
| --- | --- | --- |
| Link: BSSID, frequency, signal | `iw dev wlan0 link` | the room service, the labs' scripts and tests, the medium's RF qualification |
| Supplicant state | `wpa_cli -i wlan0 status` | the labs' start scripts, the medium's RF validation |
| Disconnect and reconnect | `wpa_cli -i wlan0 disconnect`, `reconnect` | the room service (presence), the prplMesh lab's start |
| Network settings | `wpa_cli set_network`, `get_network` | the room service's band profiles |
| Scan results | a scan on `wlan0`, read back with each result's age | the optimizer's band scanner (`optimizer/band_scan.py`, with a worker the VM runs in the client's network namespace), the medium's RF validation |
| What the radio supports | `iw dev wlan0 info`, `iw phy info`, `wpa_cli get_capability key_mgmt` | the optimizer's band scanner |
| One ping over Wi-Fi | `ping -I wlan0 -c 1` | the room service, before it trusts a link reading |
| Traffic | `ping`, `iperf3` | the room service's traffic phases; the optimizer's scenario suite; the medium's RF qualification |

Two ways in are in use, and they differ in what the client must contain:

- **`lxc exec <container> -- <tool>`** runs the client's own tool. `iperf3` this way works
  in a prplMesh client and not in an RDK client, whose image has none.
- **`nsenter` into the client's namespaces.** The band profiles enter the client's mount
  and network namespaces and run the client's own `wpa_cli`. The traffic phases and the band
  scanner enter only the network namespace and run the VM's own `ping`, `iperf3` and
  Python, so the client needs none of them.

A lock per client (`client_radio_lock` in `optimizer/band_scan.py`) keeps a scan and a
settings change from using one radio at the same time.

## 9. How a client behaves

The RDK and prplMesh clients behave alike, and all 100 of each behave the same. The
reading of wpa_supplicant 2.10 behind these statements is in the
[client models proposal](../proposals/client-models.md).

| Behaviour | Today |
| --- | --- |
| Associates to its one network and keeps trying | yes |
| Answers ARP and ping on `wlan0` | yes (the kernel does) |
| Follows a BTM request to a candidate it can see | always |
| Refuses or ignores a BTM request | never, unless no candidate is usable |
| Looks for a better access point by itself | never: no background scanning is configured |
| Roams when something else causes a scan | by wpa_supplicant's fixed rule |
| Differs from the other clients | only in SSID, security and band |
| Sends traffic by itself | never |

The OpenSync lab's client is pinned to one BSSID and has no BTM handler, so it does not
move at all.

## 10. Differences that matter when sharing

| Difference | RDK | prplMesh | Why it matters |
| --- | --- | --- | --- |
| Tools in the image | `iw`, `wpa_cli` | also `iperf3`, `tcpdump`, `python3` | a tool run with `lxc exec` works in one lab only |
| Supplicant source | w1.fi 2.10 tarball, one patch | hostap git at a pinned commit, the lab's patches | one behaviour patch must be carried twice |
| Supplicant options | WNM, 802.11r, no MBO | WNM, MBO, the defaults | a refusal with an MBO reason exists in one lab only |
| Address | DHCP, once | static | an address is found differently; a DHCP lease is never renewed |
| Band | a list of the band's frequencies | one frequency | a prplMesh client cannot move to another channel of its band |
| Control socket | `/run/wpa_supplicant` | `/var/run/wpa_supplicant` | the same directory if `/var/run` links to `/run` (*to verify*) |
| MAC address | the radio's | set from cohort and ordinal | only one lab can derive a client's MAC from its name |
| Record of intent | `user.easymesh.*` on the container | the ordinal's arithmetic | only one lab can be asked what a client was created as |
| Privilege | unprivileged (LXD's default) | privileged | what a tool inside the client may do |
| Start gate | the controller's station list | the controller's model | each is tied to its stack |

## 11. Not checked

- Whether an RDK client's `eth0` holds an address while the lab runs, and whether a
  prplMesh client has a wired interface from LXD's default profile.
- Whether `/var/run` is a link to `/run` in both images.
- The memory a running client uses. The limit (128 MB) is from the profile, not a
  measurement.
- Whether the labs' access points forward frames between two associated clients.
