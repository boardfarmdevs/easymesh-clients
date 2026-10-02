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

**This repository holds documents only, no client code.** Each lab still creates its own
clients, with its own scripts:

| Lab | Where its clients are created | Client names |
| --- | --- | --- |
| [RDK EasyMesh](https://vcpe.dev/meta-cmf-bananapi-vcpe/) | `gen/wlan-client.sh`, `gen/wlan-client-pool.sh` | `wlan-client`, `wlan-client-001` to `-099` |
| [prplMesh](https://vcpe.dev/prplmesh-lab/) | `scripts/radio-lab.sh`, `scripts/container/setup-client.sh` | `prpl-client-01` to `-100` |
| [OpenSync lab](https://vcpe.dev/opensync-lab/) | `guest/80-client.sh` | one per pod, such as `pod-1-wc1` |
| [Protocol lab](https://vcpe.dev/easymesh-lab/) | `tools/wifi_clients.py` | network namespaces around USB Wi-Fi adapters |

Nothing in a lab depends on this repository, and no lab pins it. It is the place where
what the clients have in common is written down first and, later, shared.

## Components

| Part | What it is |
| --- | --- |
| [site/](site) | the explainer site: the labs' Wi-Fi clients, from one container to a room of a hundred |
| [docs/](docs) | the reference (the clients of each lab, as built) and the proposal (more capable clients, and when to share their code) |
| [pages/](pages) | the site's build and the labs' shared checks |

## Getting started

```sh
git clone git@github.com:boardfarmdevs/easymesh-clients.git
cd easymesh-clients
python3 pages/check-docs.py                    # the documents' layout and links
pages/build && python3 pages/finish-site.py    # the site, into dist/site
```

To see a client, open a shell in a running lab VM and look at one:

```sh
lxc exec wlan-client-001 -- iw dev wlan0 link       # the RDK lab
lxc exec prpl-client-01 -- wpa_cli -i wlan0 status  # the prplMesh lab
```

## Documentation

The [site](https://vcpe.dev/easymesh-clients/) introduces the clients for a newcomer. The
documents are indexed in [docs/README.md](docs/README.md): the reference of every lab's
clients as they are built today, and the proposal for more capable clients.
