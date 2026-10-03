# easymesh-clients: the Wi-Fi clients of the EasyMesh labs

<!-- labs block: the same in every repository of the EasyMesh labs, but for the Site line -->
**Site:** <https://vcpe.dev/easymesh-clients/>
The [EasyMesh labs](https://mesh.vcpe.dev/) serve three
goals: EasyMesh optimizer development
([easymesh-optimizer](https://vcpe.dev/easymesh-optimizer/)) in a rich
virtual lab, on both stacks
([RDK EasyMesh](https://vcpe.dev/meta-cmf-bananapi-vcpe/),
[prplMesh](https://vcpe.dev/prplmesh-lab/)); unchanged OpenSync
pods as EasyMesh agents under a local controller, without the OpenSync cloud
([EMOSA](https://vcpe.dev/emosa-lab/), with the
[OpenSync lab](https://vcpe.dev/opensync-lab/)'s pods); and
EasyMesh on physical hardware
([Protocol lab](https://vcpe.dev/easymesh-lab/)). Two core
components carry them: the RF medium
([easymesh-medium](https://vcpe.dev/easymesh-medium/)) and EMOSA's
OVSDB ⇄ EasyMesh conversion. The rest is infrastructure, tools (the
[room builder](https://vcpe.dev/easymesh-room-builder/)) and learning
around them.
<!-- /labs block -->

The Wi-Fi clients every lab runs: what they are, how they are built, configured and
managed, what they can do, and how they can be made more capable.

It holds the documents, and the **client models** as built so far: one wpa_supplicant 2.12
build with a small patch series, the model files and their resolver, and a bench that
checks every model on simulated radios (results in [docs/records](docs/records/)). **No lab
uses them yet.** Each lab still creates its own clients, with its own scripts:

| Lab | Where its clients are created | Client names |
| --- | --- | --- |
| [RDK EasyMesh](https://vcpe.dev/meta-cmf-bananapi-vcpe/) | `gen/wlan-client.sh`, `gen/wlan-client-pool.sh` | `wlan-client`, `wlan-client-001` to `-099` |
| [prplMesh](https://vcpe.dev/prplmesh-lab/) | `scripts/radio-lab.sh`, `scripts/container/setup-client.sh` | `prpl-client-01` to `-100` |
| [OpenSync lab](https://vcpe.dev/opensync-lab/) | `guest/80-client.sh` | one per pod, such as `pod-1-wc1` |
| [Protocol lab](https://vcpe.dev/easymesh-lab/) | `tools/wifi_clients.py` | network namespaces around USB Wi-Fi adapters |

Nothing in a lab depends on this repository, and no lab pins it. It is the place where
what the clients have in common is written down and built first, and checked on its own,
before a lab takes it.

## Components

| Part | What it is |
| --- | --- |
| [supplicant/](supplicant/README.md) | the client build: wpa_supplicant 2.12 with the client-model patch series, stock hostapd 2.12 for the bench, iwd 3.12, and the RDK lab's 2.10 for comparison; from pinned release tarballs |
| [models/](models/README.md) | the client models, one JSON file each, every value with its source and confidence, and the behaviour variants |
| [clientmodel/](clientmodel/) | the resolver: a model into wpa_supplicant options or iwd's `main.conf` (`python3 -m clientmodel`) |
| [bench/](bench/README.md) | the roaming bench: two access points and a client on `mac80211_hwsim` and the labs' wmediumd, the tests of the [roaming test plan](docs/project/roaming-test-plan.md), and the report |
| [tests/](tests/) | the resolver's unit tests |
| [site/](site) | the explainer site: the labs' Wi-Fi clients, from one container to a room of a hundred |
| [docs/](docs) | the references, the proposals, the roaming test plan and the bench's records |
| [pages/](pages) | the site's build; the rest of the Pages workflow is the labs' shared one |

## Getting started

```sh
git clone git@github.com:boardfarmdevs/easymesh-clients.git
cd easymesh-clients
python3 -m unittest discover -s tests          # the resolver's rules (no root, no radios)
python3 -m clientmodel resolve pixel           # what a model sets
pages/build                                    # the site, into dist/site
```

The client build and the bench need a Linux VM that can load `mac80211_hwsim`, as root
([the bench's README](bench/README.md) has the parts):

```sh
supplicant/build.sh --output /root/build --reference --iwd    # about 4 minutes
python3 bench/bench.py run iphone B1 --runs 1                  # one test, one model
python3 bench/bench.py suite                                   # every model, every test
```

The documentation check and the site's finishing step are the labs' shared ones, kept in
the umbrella ([easymesh-labs](https://mesh.vcpe.dev/)) and run by its Pages workflow. From
this repository's root, with the umbrella checked out next to it:

```sh
python3 ../easymesh-labs/pages/check-docs.py
python3 ../easymesh-labs/pages/finish-site.py dist/site
```

To see a client, open a shell in a running lab VM and look at one:

```sh
lxc exec wlan-client-001 -- iw dev wlan0 link       # the RDK lab
lxc exec prpl-client-01 -- wpa_cli -i wlan0 status  # the prplMesh lab
```

## Documentation

The [site](https://vcpe.dev/easymesh-clients/) introduces the clients for a newcomer. The
documents are indexed in [docs/README.md](docs/README.md): the reference of every lab's
clients as they are built today, what devices document about roaming, the proposals for
more capable clients and for client models, the roaming test plan and the bench's records.
