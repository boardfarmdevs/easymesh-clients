## `baseline`: Baseline

Resembles the labs' client today: wpa_supplicant with no roaming configuration. Model file hash `b20400f2710c972a`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.4 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | no background scanning | never looked; stayed on AP1 down to −90 dBm | recorded (3) |
| B2 Stays above the trigger | no move by itself | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | upstream table | stayed while AP2 rose to 27 dB above AP1 (no scan to act on) | recorded (3) |
| B5 BTM answer | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | rules | status 0, target AP1; stayed | recorded (3) |
| B6 BTM to a weaker AP | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |

## `galaxy`: Galaxy

Resembles Samsung Galaxy S and Note since the S8, Android. Model file hash `a20ae383264ef0ce`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −75 dBm | looked at −77 dBm, −77 dBm, −77 dBm (bounds −85 to −74); moved with AP1 at −77 dBm, −77 dBm, −77 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 10 dB | moved at 13 dB, 13 dB, 13 dB (bounds 10 to 16) | pass 3/3 |
| B5 BTM answer | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s) | recorded (3) |
| B8 Load trigger | looks when over 70 % busy at −65 to −75 dBm | looked for load and moved after 10.9 s, 10.9 s, 10.9 s | pass 3/3 |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 10 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `iot-2g4`: 2.4 GHz device

Resembles a 2.4 GHz-only device: camera, plug, speaker. Model file hash `be619651f4f5fa11`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.9 s, 0.9 s, 0.9 s; the server answered | pass 3/3 |
| B5 BTM answer | no 802.11v | no answer; stayed (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | no 802.11v | no answer; stayed (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | no 802.11v | no answer; stayed (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | no answer; then associated to AP2 (2.4 GHz); 1 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4 | on 2412 MHz | pass 3/3 |

## `ipad`: iPad

Resembles iPad, iPadOS. Model file hash `f28f2df29415c45f`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −70 dBm | looked at −72 dBm, −72 dBm, −72 dBm (bounds −80 to −69); moved with AP1 at −72 dBm, −72 dBm, −72 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 12 dB | moved at 13 dB, 13 dB, 13 dB (bounds 12 to 18) | pass 3/3 |
| B4 Margin, with traffic | moves for 8 dB | moved at 13 dB, 13 dB, 13 dB (bounds 8 to 14) | pass 3/3 |
| B5 BTM answer | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | rules | status 0, target AP1; stayed | recorded (3) |
| B6 BTM to a weaker AP | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 12 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `iphone`: iPhone

Resembles iPhone, iOS. Model file hash `22f3ccda23b86cff`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.4 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −70 dBm | looked at −72 dBm, −72 dBm, −72 dBm (bounds −80 to −69); moved with AP1 at −72 dBm, −72 dBm, −72 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 12 dB | moved at 13 dB, 13 dB, 13 dB (bounds 12 to 18) | pass 3/3 |
| B4 Margin, with traffic | moves for 8 dB | moved at 13 dB, 13 dB, 13 dB (bounds 8 to 14) | pass 3/3 |
| B5 BTM answer | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | rules | status 0, target AP1; stayed | recorded (3) |
| B6 BTM to a weaker AP | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s); status 0, target AP2; then associated to AP2, then AP2, then AP1; 1 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 12 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `iphone+btm-refuser`: iPhone, refuses BTM

Resembles iPhone, iOS. Model file hash `6347a9ef64efde69`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B5 BTM answer | reject | status 1, no target; stayed (as its policy predicts) | pass 3/3 |

## `linux-iwd`: Linux with iwd

Resembles a Linux device running iwd 3.12. Model file hash `c1f56be54bd29550`, client `iwd`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 1.2 s, 1.2 s, 1.2 s; the server answered | pass 3/3 |
| B1 Look level | looks below −76 dBm | looked at −78 dBm, −78 dBm, −78 dBm (bounds −86 to −75); moved with AP1 at −80 dBm, −81 dBm, −80 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s | pass 3/3 |
| B5 BTM answer | iwd: follows, never answers | no answer; moved to AP2 (as its policy predicts) | pass 3/3 |

## `mac`: Mac

Resembles Mac with Apple silicon, macOS. Model file hash `92f9e6f45744dfa5`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −75 dBm | looked at −77 dBm, −77 dBm, −77 dBm (bounds −85 to −74); moved with AP1 at −77 dBm, −77 dBm, −77 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 12 dB | moved at 13 dB, 13 dB, 13 dB (bounds 12 to 18) | pass 3/3 |
| B5 BTM answer | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | rules | status 0, target AP1; stayed | recorded (3) |
| B6 BTM to a weaker AP | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s) | recorded (3) |
| B8 Load trigger | no load trigger (the control) | stayed for 60 s | pass 3/3 |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 12 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `mac-intel`: Mac with Intel

Resembles Mac with an Intel processor, macOS. Model file hash `2675413a23d32bdb`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −75 dBm | looked at −77 dBm, −77 dBm, −77 dBm (bounds −85 to −74); moved with AP1 at −77 dBm, −77 dBm, −77 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 12 dB | moved at 13 dB, 13 dB, 13 dB (bounds 12 to 18) | pass 3/3 |
| B5 BTM answer | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | rules | status 0, target AP1; stayed | recorded (3) |
| B6 BTM to a weaker AP | rules | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 12 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `pixel`: Pixel

Resembles Google Pixel 6 to 9, Android. Model file hash `ff47fd3072813c5e`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.4 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −75 dBm | looked at −77 dBm, −77 dBm, −77 dBm (bounds −85 to −74); moved with AP1 at −77 dBm, −77 dBm, −77 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 10 dB | moved at 13 dB, 13 dB, 13 dB (bounds 10 to 16) | pass 3/3 |
| B5 BTM answer | accept, minimum margin 0 dB | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | accept, minimum margin 0 dB | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | accept, minimum margin 0 dB | status 7, no target; stayed (as its policy predicts) | pass 3/3 |
| B7 Disassociation imminent, no better AP | not documented | status 0, no target; then associated to AP2, then AP1; 1 disconnection(s) | recorded (3) |
| B8 Load trigger | looks when over 70 % busy at −70 to −75 dBm | looked for load and moved after 15.9 s, 15.9 s, 15.9 s | pass 3/3 |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 10 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `pixel+btm-ignorer`: Pixel, ignores BTM

Resembles Google Pixel 6 to 9, Android. Model file hash `758af5721fa361e6`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B5 BTM answer | ignore | no answer; stayed (as its policy predicts) | pass 3/3 |

## `pixel+btm-refuser`: Pixel, refuses BTM

Resembles Google Pixel 6 to 9, Android. Model file hash `b746d074c22ff6c4`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B5 BTM answer | reject | status 1, no target; stayed (as its policy predicts) | pass 3/3 |

## `pixel+no-11v`: Pixel, no 802.11v

Resembles Google Pixel 6 to 9, Android. Model file hash `4f898e7cc8d42961`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B5 BTM answer | no 802.11v, minimum margin 0 dB | no answer; stayed (as its policy predicts) | pass 3/3 |

## `windows-intel`: Windows with Intel

Resembles Windows laptop with Intel Wi-Fi, Roaming Aggressiveness Medium. Model file hash `ef285c303aef3d58`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.4 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −75 dBm | looked at −77 dBm, −77 dBm, −77 dBm (bounds −85 to −74); moved with AP1 at −77 dBm, −77 dBm, −77 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 10 dB | moved at 13 dB, 13 dB, 13 dB (bounds 10 to 16) | pass 3/3 |
| B5 BTM answer | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 10 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `windows-intel-highest`: Windows with Intel, highest

Resembles Windows laptop with Intel Wi-Fi, Roaming Aggressiveness Highest. Model file hash `388ed68b7b039596`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −65 dBm | looked at −67 dBm, −67 dBm, −67 dBm (bounds −75 to −64); moved with AP1 at −67 dBm, −67 dBm, −67 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 10 dB | moved at 13 dB, 13 dB, 13 dB (bounds 10 to 16) | pass 3/3 |
| B5 BTM answer | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 10 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `windows-intel-lowest`: Windows with Intel, lowest

Resembles Windows laptop with Intel Wi-Fi, Roaming Aggressiveness Lowest. Model file hash `c43fdcfbec89f07a`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −85 dBm | looked at −87 dBm, −87 dBm, −87 dBm (bounds −95 to −84); moved with AP1 at −87 dBm, −87 dBm, −87 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 10 dB | moved at 12 dB, 11 dB, 15 dB (bounds 10 to 16) | pass 3/3 |
| B5 BTM answer | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 10 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `windows-intel-medium-high`: Windows with Intel, medium-high

Resembles Windows laptop with Intel Wi-Fi, Roaming Aggressiveness Medium High. Model file hash `f70155d5d34c545a`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −70 dBm | looked at −72 dBm, −72 dBm, −72 dBm (bounds −80 to −69); moved with AP1 at −72 dBm, −72 dBm, −72 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 10 dB | moved at 13 dB, 13 dB, 13 dB (bounds 10 to 16) | pass 3/3 |
| B5 BTM answer | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2, then AP1; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 10 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## `windows-intel-medium-low`: Windows with Intel, medium-low

Resembles Windows laptop with Intel Wi-Fi, Roaming Aggressiveness Medium Low. Model file hash `587c92de3b5fed00`, client `wpa_supplicant`.

| Test | The model says | The bench measured | Result |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, passes traffic | associated in 0.3 s, 0.3 s, 0.3 s; the server answered | pass 3/3 |
| B1 Look level | looks below −80 dBm | looked at −82 dBm, −82 dBm, −82 dBm (bounds −90 to −79); moved with AP1 at −82 dBm, −82 dBm, −82 dBm | pass 3/3 |
| B2 Stays above the trigger | stays above its trigger | 0, 0, 0 moves in 120 s with three scans | pass 3/3 |
| B3 Margin, idle | moves for 10 dB | moved at 13 dB, 13 dB, 13 dB (bounds 10 to 16) | pass 3/3 |
| B5 BTM answer | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | pass 3/3 |
| B5b BTM answer, without the abridged bit | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B6 BTM to a weaker AP | accept | status 0, target AP2; moved to AP2 (as its policy predicts) | recorded (3) |
| B7 Disassociation imminent, no better AP | not documented | status 0, target AP2; then associated to AP2; 0 disconnection(s) | recorded (3) |
| B9 Bands | bands 2.4, 5, 6 | on 5180 MHz | recorded (3) |
| B10 No ping-pong | margin 10 dB | 0, 0, 0 moves in 10 min | pass 3/3 |

## B12: the default did not change

`baseline` on wpa_supplicant 2.12 with the patch series, against the RDK lab's 2.10 build, three runs of each. **Pass:** the same outcomes.

| Test | 2.12, `baseline` | 2.10, the RDK lab's build | The same |
| --- | --- | --- | --- |
| B0 Bench sanity | associates, ping answers | associates, ping answers | yes |
| B1 Look level | never looks, stays | never looks, stays | yes |
| B2 Stays above the trigger | 0 moves | 0 moves | yes |
| B3 Margin, idle | stays | stays | yes |
| B5 BTM answer | status 0, target AP2; moved to AP2 | status 0, target AP2; moved to AP2 | yes |

