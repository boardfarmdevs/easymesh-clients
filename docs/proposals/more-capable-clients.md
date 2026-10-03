# More capable clients

[Documents](../README.md)

**Status:** Proposal. Step 3 (models) is implemented in this repository and checked on a
bench, 3 October 2026; no lab uses it yet. Nothing else here is implemented, and nothing
here needs to be decided at once. **Prepared:** 2 October 2026.

What the clients are today is in [The clients of each lab](../reference/lab-clients.md).

## 1. The goal and the rule

The lab's clients associate, hold an address, answer pings and obey steering. The goal is
clients that can do more, in two directions:

- **Do something when asked.** Run traffic between two clients, roam to a named access
  point, scan, drop off and come back. Asked for by one short command, independent of the
  room that is loaded.
- **Behave like a kind of device.** A phone that roams early, a laptop that holds on, an
  IoT device that knows only 2.4 GHz, a client that refuses steering.

**The rule: a client nobody asks anything of is today's client.** No existing room, golden
world, suite or lab script changes because of anything here. Every step adds; a lab takes
a step when it wants it.

## 2. What is missing today

1. **No vocabulary.** Every tool that needs a client writes its own commands: the medium's
   RF validation, qualification and spatial tools; the optimizer's band scanner; the room
   service's presence, band-profile and traffic modules; both labs' scripts and tests.
   Traffic between two endpoints is written three times (the medium's `rf_spatial.py`, the
   room service's `traffic_experiment.py`, the Protocol lab's guide).
2. **No contract.** What a client must provide is nowhere stated, so the two labs' clients
   have drifted: one has `iperf3` inside and the other has not; one records what it was
   created as and the other does not.
3. **One behaviour.** All 100 clients are the same obedient client that never moves by
   itself, the easiest case an optimizer can meet.

## 3. Four steps

Each step works without the next one.

| Step | Adds | Changes in a client | Changes in rooms and worlds |
| --- | --- | --- | --- |
| 1. Contract | what every client provides, written down, and a read-only check | none (one lab records a few container keys) | none |
| 2. Actions | one command that asks a client to do something | none | none |
| 3. Models | clients that behave like kinds of devices | the supplicant build gains options whose defaults are today's behaviour | one optional field in a world |
| 4. Behaviours | clients that send traffic by themselves, on a schedule | none | one optional field in a world |

## 4. Step 1: the contract

What a virtual lab client must provide for one tool to work on it, in either lab.

| Item | Contract | RDK today | prplMesh today |
| --- | --- | --- | --- |
| Name | matches its stack's pattern in the medium's `wmdcfg/stacks.py` | yes | yes |
| Radio | the client's one radio is `wlan0` | yes | yes |
| Supplicant control | `wpa_cli -i wlan0` works inside the client | yes | yes |
| Tools inside | `wpa_cli` and `iw`, nothing else | yes | yes, and more |
| Address | one IPv4 address on `wlan0`, in the mesh's LAN | yes (DHCP) | yes (static) |
| Record of intent | `user.easymesh.cohort`, `.ssid`, `.security`, `.band` on the container | yes | **no** |
| BTM | the supplicant answers a BSS Transition Management request | yes | yes |

- **Everything else runs from the VM host**, in the client's network namespace: `ping`,
  `iperf3`, packet capture, Python. The room service already runs traffic and scans this
  way. A client image then never needs a tool added, and both labs' clients can do the
  same things although their images differ.
- **The one gap** is the record of intent in the prplMesh lab. Closing it is four
  `lxc config set` calls when a client is deployed; nothing reads them today, so nothing
  breaks.
- **A check**, read-only, that reports for each client of a running lab whether it meets
  the contract. It is the first piece of code this repository would hold.
- The OpenSync lab's client and the Protocol lab's clients are outside the contract for
  now (section 12).

## 5. Step 2: actions

One command on the VM host, here called `em-clients`. It finds clients by their stack's
name pattern, or by room role when a room is loaded (`sta_mobile_03`, through the room's
bindings), and prints one JSON document per action.

| Action | Class | What it does |
| --- | --- | --- |
| `list` | read | every client: container, cohort, band, state |
| `status <client>` | read | supplicant state, BSSID, frequency, signal, address |
| `scan <client>` | read | the access points the client hears, with signal and age |
| `ping <client> [target]` | traffic | ping over `wlan0`, to the gateway by default |
| `iperf <client> <target>` | traffic | `iperf3` from a client to the gateway or **to another client** |
| `disconnect`, `reconnect <client>` | state | leave and rejoin |
| `roam <client> <bssid>` | state | the client moves by itself to a named access point (`wpa_cli roam`) |
| `query <client>` | state | the client asks its access point for better candidates (a BSS Transition Management query) |
| `band <client> <bands>` | state | limit the client to bands, as the room's band profiles do |
| `model <client> <name>` | state | step 3 |

The three classes matter for what an action may disturb (section 9).

### Traffic between two clients

```sh
em-clients iperf sta_mobile_01 sta_static_03 --seconds 10 --udp 20M
```

1. Resolve both names to containers and read each one's `wlan0` address.
2. Start `iperf3 -s -1 -B <address of B>` in B's network namespace.
3. Start `iperf3 -c <address of B> -B <address of A>` in A's network namespace.
4. Report both ends' results, and each client's BSSID, frequency and signal before and
   after.

- Binding both ends to their `wlan0` addresses keeps the traffic on Wi-Fi even where a
  client has a wired interface.
- The path is client, access point, backhaul if the two are on different nodes, access
  point, client. Two clients on one radio use its airtime twice; the result is not
  comparable with a client-to-gateway test.
- It needs the access points to forward between clients. Whether both labs' access points
  do is experiment E1.
- Addresses differ per lab (DHCP in one, static in the other); the action reads them
  rather than computing them.

### Form

A Python package without dependencies, like the optimizer. It uses `lxc exec` and
`nsenter`, the client lock that exists (`client_radio_lock`), and the stack description
the medium already keeps. It would replace nothing at first: the room service and the
medium's tools keep their own code until someone chooses to move them onto it.

## 6. The control channel

How a command reaches a client.

| Option | What it is | For | Against |
| --- | --- | --- | --- |
| A. From the VM host | `lxc exec` and `nsenter`, as today | nothing runs in the client; works on every existing client; no network needed | only for someone on the VM host |
| B. An agent in each client | a small service on the client's wired interface | reachable from anywhere on the lab's bridge | a hundred more processes; a wired route in a device that should have only Wi-Fi; a listening service to secure and to version with the image |
| C. Through the room service | the same actions, behind the room's API | reachable from a browser and for remote developers; the room knows what was done | only while a room service runs |

**Recommendation: A, and C on top of it.** The agent can do nothing the host cannot, and
the wired interface it would listen on is a hazard: the OpenSync lab's client and the
Protocol lab's clients have none on purpose, so that traffic cannot leave except over the
air. Option B becomes right only for a client the host cannot enter, such as a real phone;
it would then carry the same actions over another transport.

## 7. Step 3: models

The [client models proposal](client-models.md) (29 September 2026, revised 3 October as
requirements and design) names models after kinds of devices, with the values those devices
document ([documented roaming](../reference/documented-roaming.md)), and a
[bench test plan](../project/roaming-test-plan.md) checks each one.

| Model | Resembles | In short |
| --- | --- | --- |
| `baseline` | today's lab client | wpa_supplicant 2.12; never scans by itself; follows a steering request (one with the Abridged bit) |
| `iphone`, `ipad` | iPhone, iPad | look below −70 dBm; move for 8 dB with traffic, 12 dB idle |
| `mac` | Mac with Apple silicon | look below −75 dBm; move for 12 dB |
| `pixel` | Google Pixel | look below −75 dBm or on a busy AP; move for 10 dB |
| `galaxy` | Samsung Galaxy | look below −75 dBm or on a busy AP; move for 10 dB |
| `windows-intel` | a Windows laptop with Intel Wi-Fi | look below −75 dBm (synthesized); move for 10 dB |
| `linux-iwd` | a Linux device running iwd | iwd 3.12's own algorithm |

Variants add a 2.4 GHz-only IoT device and clients that refuse, ignore or cannot receive BTM
requests.

How it fits here:

- A model is data, and the same container takes one on when a room loads. A world names
  models per role; without that field every client is `baseline` and the world's golden is
  unchanged.
- `em-clients model <client> <name>` is the same resolution, applied by hand.
- The catalog would live in this repository. That answers the proposal's first open
  question, and both labs then read one catalog.
- The models need a small patch series against wpa_supplicant 2.12, in one build both labs
  use. That build is the first code worth sharing (section 10).
- **Built, 3 October 2026:** the build ([supplicant/](../../supplicant/README.md)), the
  catalog and its resolver ([models/](../../models/README.md)) and the bench
  ([bench/](../../bench/README.md)) are in this repository, with every model's
  [results](../records/bench-2026-10-03/README.md). Orders 3 and 4 of section 10 exist here;
  no lab has taken them yet.

## 8. Step 4: behaviours

What a client does without being asked: an IoT device that sends a few packets a minute, a
video call, a download, a stream. Worlds already describe traffic in phases (the medium's
`wmdcfg/traffic_profile.py`), and the room service runs them from the VM host. A behaviour
would be a named traffic pattern attached to a role, run the same way, with no process
added to the client. It is the farthest step and the least defined.

## 9. Rooms and the configurator

A room owns its clients while it runs: which are online, their bands, and the checks that
say whether the optimizer did well. An action by hand can make a check meaningless.

1. **Read actions** are always allowed.
2. **Traffic actions** are allowed, and refused for a client a room's traffic phase is
   using at that moment.
3. **State actions** take the client's lock. While a room runs they go through the room
   service, which records them in the room's journal and marks the run **touched by hand**:
   its checks are still reported and no longer count as a pass. With no room running, they
   are free.
4. **Whatever an action changes is restored or recorded**, as the room does today: a
   disconnect is noted as paused so recovery reconnects it; band and model settings are
   captured first and written back.
5. **The configurator is not involved before step 3.** Steps 1 and 2 add no field to a
   world. Step 3 adds an optional one, and a world without it compiles to the same bytes.

## 10. Sharing the code: what, and when

The medium and the optimizer were split out of the labs when both labs already ran the
same code. The clients are three implementations that differ in image, supplicant,
address, naming and pool logic. Moving them now would be a convergence and a move at once,
with every suite of both labs to run again, days after the labs were rebuilt and qualified
following the last splits (30 September 2026).

Some of the client code is tied to its lab and should stay there: allocating radios from
the hwsim pool and registering them with the medium, the gate that waits for the lab's own
controller, the pool plan and the names.

| Order | What is shared | When | What it disturbs |
| --- | --- | --- | --- |
| 1 | the documents | now | nothing |
| 2 | the contract check and the actions | when first wanted | nothing: new code, and a lab opts in by pinning this repository |
| 3 | the model catalog and its resolver | with client models | nothing in existing rooms |
| 4 | the supplicant: one source, one patch set, one configuration | with the client-model patch | both labs rebuild their client image and run their suites; the patch requires that anyway |
| 5 | the client image and its creation | after 4, one lab at a time, behind the labs' current entry points | one full qualification per lab |

A lab would use this repository as it uses the medium and the optimizer: a pinned
submodule (`clients`) next to them.

**Now is the time for order 1, not for 4 and 5.** The patch for client models changes
both client builds whatever is decided here; that is the moment one shared build costs
nothing extra.

## 11. Experiments, before deciding

| | Question | How |
| --- | --- | --- |
| E1 | Do the labs' access points forward between two clients, on one node and across nodes? | `iperf3` between two clients by hand, in both labs, from the VM host |
| E2 | What does the contract check find on a running lab? | read `/var/run`, the wired interface and its address, the tools, in one client of each lab |
| E3 | Do `wpa_cli roam` and a BSS Transition Management query work on hwsim clients? | one client between two access points, in both labs |
| E4 | What does a running client cost? | its proportional memory, times 100; the cost an agent would add |
| E5 | Does a room notice an action by hand? | disconnect a client during a room's check and read the verdict |

## 12. Open questions

1. **The first actions.** All of section 5, or only `list`, `status`, `ping` and `iperf`.
2. **The client models proposal.** *Answered on 2 October 2026: moved into this
   repository.*
3. **The record of intent** in the prplMesh lab: add the container keys now, or with
   step 2.
4. **The Protocol lab's clients.** They are namespaces around real radios. The same
   actions would work with `ip netns exec` in place of `lxc exec`; whether that is wanted.
5. **The OpenSync lab's client.** Its supplicant has no BTM handler and it is pinned to
   one pod. Bring it under the contract, or keep it as the client that checks a home
   network end to end.
6. **The command's name**, and whether the room viewer gets buttons for the actions.
