# The client models

[Documents](../docs/README.md)

One file per model, in the format `client-model/2` of the
[design](../docs/proposals/client-models.md#7-the-model-file); behaviours that combine with
any wpa_supplicant model are in [behaviours/](behaviours/). Every value names its source and
its confidence ([documented roaming](../docs/reference/documented-roaming.md)).

| Model | Resembles | Looks below | Moves for | Load trigger | BTM |
| --- | --- | --- | --- | --- | --- |
| [baseline](baseline.json) | the labs' client today | never by itself | upstream table | — | rules |
| [iphone](iphone.json), [ipad](ipad.json) | iPhone, iPad | −70 dBm | 12 dB idle, 8 dB transmitting | — | rules |
| [mac](mac.json) | Mac, Apple silicon | −75 dBm | 12 dB | — | rules |
| [mac-intel](mac-intel.json) | Mac, Intel | as `mac` | as `mac` | — | rules; no 802.11k or r |
| [pixel](pixel.json) | Pixel 6 to 9 | −75 dBm | 10 dB | 70 % for 10 s at −70 to −75 dBm (5 GHz), −60 to −75 (2.4 GHz) | accept, not to a weaker AP |
| [galaxy](galaxy.json) | Galaxy S and Note | −75 dBm | 10 dB | 70 % for 10 s at −65 to −75 dBm | accept |
| [windows-intel](windows-intel.json) | Windows, Intel Wi-Fi, Medium | −75 dBm | 10 dB | — | accept |
| `windows-intel-lowest`, `-medium-low`, `-medium-high`, `-highest` | the other Roaming Aggressiveness levels | −85, −80, −70, −65 dBm | 10 dB | — | accept |
| [linux-iwd](linux-iwd.json) | Linux with iwd 3.12 | −76 dBm (5 GHz), −70 (2.4 GHz) | iwd's ranking | — | iwd's |
| [iot-2g4](iot-2g4.json) | 2.4 GHz-only devices | never by itself | upstream table | — | no 802.11v |

| Behaviour | Changes |
| --- | --- |
| [+btm-refuser](behaviours/btm-refuser.json) | refuses every BTM request (status 1) |
| [+btm-ignorer](behaviours/btm-ignorer.json) | never answers a BTM request |
| [+no-11v](behaviours/no-11v.json) | does not offer 802.11v |

**BTM policies:** *rules* is wpa_supplicant 2.12 as released, the client's own roaming rules
deciding when the request leaves it the choice; *accept* follows the AP's candidate. Apple
documents that it reviews 802.11v data "when the device needs to roam", so the Apple models
keep the rules; the Pixel's driver sets a BTM delta of 0, so it accepts unless the target is
weaker.

## Resolving a model

```sh
python3 -m clientmodel list
python3 -m clientmodel show mac-intel                 # with its base merged
python3 -m clientmodel resolve pixel+btm-refuser      # the options, as JSON
python3 -m clientmodel wpa-conf iphone --ssid lab --psk secret
python3 -m clientmodel iwd-conf linux-iwd
```

The rules the resolver keeps, tested in [tests/](../tests/test_clientmodel.py): an absent
field keeps upstream behaviour, so `baseline` resolves to no option at all; a variant lists
only its differences from its `base`; a behaviour is merged on top of a model; the `btm`
section is replaced as a whole; impossible combinations (a load trigger without a trigger,
a minimum margin without `accept`) are refused.
