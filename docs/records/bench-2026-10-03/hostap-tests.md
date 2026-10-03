# hostap's own tests on the patched build

[Documents](../../README.md) · [The bench's results](README.md)

**Kind:** record. **Run:** 3 October 2026, in a VM like the bench's (Ubuntu 24.04.5, kernel
6.8.0-142, `mac80211_hwsim`).

The question: do the client-model patches change anything hostap's own tests check, with
every new option at its default? hostap's hwsim test suite is in its git tree, not in the
release tarballs, so it ran from the `hostap_2_12` tag (831364b, the release's version
commit) three times: with the three patches as first written, with the patches as committed
(the *accept* policy fixed; see [the results](README.md)), each with `CONFIG_BGSCAN_MODEL=y`
added to the suite's own build configuration, and unpatched. The patches apply to the tag as
they do to the tarball. Each build used the suite's `build.sh` and example configurations
(which include `CONFIG_TESTING_OPTIONS` and MBO). The modules that cover what the patches
touch:
`test_wnm.py` (BSS Transition Management), `test_bgscan.py`, `test_ap_roam.py`,
`test_scan.py` and `test_wpas_config.py`.

**Result:** 155 passed, 4 skipped, 1 failed, **the same, test by test, with both builds of
the patches and without them**. The one failure, `scan_chan_switch` ("Channel switch
completed event not seen"), fails the same way on the unpatched build: it belongs to the VM,
not to the patches. Two tests were skipped for want of `tshark` (`scan_random_mac`, `scan_dfs`) and two because they run
only in hostap's own test VM (`wnm_bss_keep_alive`, `wnm_bss_protected_keep_alive`).

Setting it up took the build dependencies `binutils-dev`, `libpcap-dev`,
`libsqlite3-dev`, `libxml2-dev`, `libcurl4-openssl-dev`, `zlib1g-dev` and
`python3-pycryptodome`; wpa_supplicant's D-Bus policy installed on the system bus, as the
suite's README describes; and, because the VM's kernel is locked down, one change to the
runner in the test VM's checkout: a permission error tolerated where it writes
`/sys/kernel/debug/clear_warn_once`.

| Module | Passed | Skipped | Failed |
| --- | --- | --- | --- |
| `test_wnm.py` | 63 | 2 | 0 |
| `test_bgscan.py` | 16 | 0 | 0 |
| `test_ap_roam.py` | 11 | 0 | 0 |
| `test_scan.py` | 50 | 2 | 1 |
| `test_wpas_config.py` | 11 | 0 | 0 |
| in those modules, named otherwise (`ap_ignore_bssid_all`, `ap_reconnect_auth_timeout`, `ap_reassociation_to_same_bss`, `connect_mbssid_open_1`) | 4 | 0 | 0 |

## Every test

| Test | Patched (both builds) | Unpatched |
| --- | --- | --- |
| `ap_roam_during_scan` | pass | pass |
| `ap_roam_open` | pass | pass |
| `ap_roam_open_failed` | pass | pass |
| `ap_roam_open_failed_ssid_mismatch` | pass | pass |
| `ap_roam_set_bssid` | pass | pass |
| `ap_roam_signal_level_override` | pass | pass |
| `ap_roam_with_reassoc_auth_timeout` | pass | pass |
| `ap_roam_wpa2_psk` | pass | pass |
| `ap_roam_wpa2_psk_failed` | pass | pass |
| `ap_roam_wpa2_psk_pmf_mismatch` | pass | pass |
| `ap_roam_wpa2_psk_race` | pass | pass |
| `bgscan_learn` | pass | pass |
| `bgscan_learn_beacon_loss` | pass | pass |
| `bgscan_learn_driver_conf_failure` | pass | pass |
| `bgscan_learn_oom` | pass | pass |
| `bgscan_learn_scan_failure` | pass | pass |
| `bgscan_reconfig` | pass | pass |
| `bgscan_simple` | pass | pass |
| `bgscan_simple_beacon_loss` | pass | pass |
| `bgscan_simple_btm_query` | pass | pass |
| `bgscan_simple_btm_query_no_ap_support` | pass | pass |
| `bgscan_simple_driver_conf_failure` | pass | pass |
| `bgscan_simple_oom` | pass | pass |
| `bgscan_simple_same_scan_int` | pass | pass |
| `bgscan_simple_scan_failure` | pass | pass |
| `bgscan_simple_scanning` | pass | pass |
| `bgscan_unknown_module` | pass | pass |
| `ap_ignore_bssid_all` | pass | pass |
| `ap_reassociation_to_same_bss` | pass | pass |
| `ap_reconnect_auth_timeout` | pass | pass |
| `connect_mbssid_open_1` | pass | pass |
| `scan` | pass | pass |
| `scan_abort` | pass | pass |
| `scan_abort_on_connect` | pass | pass |
| `scan_aborted_on_connect_no_reselect` | pass | pass |
| `scan_and_bss_entry_removed` | pass | pass |
| `scan_and_interface_disabled` | pass | pass |
| `scan_ap_scan_2_ap_mode` | pass | pass |
| `scan_bss_expiration_age` | pass | pass |
| `scan_bss_expiration_count` | pass | pass |
| `scan_bss_expiration_on_ssid_change` | pass | pass |
| `scan_bss_limit` | pass | pass |
| `scan_bss_operations` | pass | pass |
| `scan_chan_switch` | fail | fail |
| `scan_dfs` | skip | skip |
| `scan_ext` | pass | pass |
| `scan_external_trigger` | pass | pass |
| `scan_fail` | pass | pass |
| `scan_fail_type_only` | pass | pass |
| `scan_filter` | pass | pass |
| `scan_flush` | pass | pass |
| `scan_for_auth` | pass | pass |
| `scan_for_auth_fail` | pass | pass |
| `scan_for_auth_wep` | pass | pass |
| `scan_freq_list` | pass | pass |
| `scan_freq_network` | pass | pass |
| `scan_hidden` | pass | pass |
| `scan_hidden_many` | pass | pass |
| `scan_ies` | pass | pass |
| `scan_int` | pass | pass |
| `scan_mbssid_hidden_ssid` | pass | pass |
| `scan_multi_bssid` | pass | pass |
| `scan_multi_bssid_2` | pass | pass |
| `scan_multi_bssid_3` | pass | pass |
| `scan_multi_bssid_4` | pass | pass |
| `scan_multi_bssid_check_ie` | pass | pass |
| `scan_multi_bssid_fms` | pass | pass |
| `scan_multiple_mbssid_ie` | pass | pass |
| `scan_new_only` | pass | pass |
| `scan_only` | pass | pass |
| `scan_only_one` | pass | pass |
| `scan_parsing` | pass | pass |
| `scan_probe_req_events` | pass | pass |
| `scan_probe_req_events_with_payload` | pass | pass |
| `scan_random_mac` | skip | skip |
| `scan_random_mac_connected` | pass | pass |
| `scan_reqs_with_non_scan_radio_work` | pass | pass |
| `scan_setband` | pass | pass |
| `scan_short_ssid_list` | pass | pass |
| `scan_specific_bssid` | pass | pass |
| `scan_specify_ssid` | pass | pass |
| `scan_ssid_list` | pass | pass |
| `scan_trigger_failure` | pass | pass |
| `scan_tsf` | pass | pass |
| `wnm_action_proto` | pass | pass |
| `wnm_action_proto_no_pmf` | pass | pass |
| `wnm_action_proto_pmf` | pass | pass |
| `wnm_bss_group_rekey` | pass | pass |
| `wnm_bss_group_rekey_skip` | pass | pass |
| `wnm_bss_keep_alive` | skip | skip |
| `wnm_bss_max_idle_period_management` | pass | pass |
| `wnm_bss_protected_keep_alive` | skip | skip |
| `wnm_bss_tm` | pass | pass |
| `wnm_bss_tm_ap_proto` | pass | pass |
| `wnm_bss_tm_connect_cmd` | pass | pass |
| `wnm_bss_tm_country_cn` | pass | pass |
| `wnm_bss_tm_country_fi` | pass | pass |
| `wnm_bss_tm_country_jp` | pass | pass |
| `wnm_bss_tm_country_us` | pass | pass |
| `wnm_bss_tm_drv_processing` | pass | pass |
| `wnm_bss_tm_errors` | pass | pass |
| `wnm_bss_tm_global` | pass | pass |
| `wnm_bss_tm_global4` | pass | pass |
| `wnm_bss_tm_nei_11a` | pass | pass |
| `wnm_bss_tm_nei_11b` | pass | pass |
| `wnm_bss_tm_nei_11g` | pass | pass |
| `wnm_bss_tm_nei_vht` | pass | pass |
| `wnm_bss_tm_op_class_0` | pass | pass |
| `wnm_bss_tm_reject` | pass | pass |
| `wnm_bss_tm_req` | pass | pass |
| `wnm_bss_tm_req_with_mbo_ie` | pass | pass |
| `wnm_bss_tm_rsn` | pass | pass |
| `wnm_bss_tm_scan_needed` | pass | pass |
| `wnm_bss_tm_scan_needed_e4` | pass | pass |
| `wnm_bss_tm_scan_not_needed` | pass | pass |
| `wnm_bss_tm_security_mismatch` | pass | pass |
| `wnm_bss_tm_steering_timeout` | pass | pass |
| `wnm_bss_tm_termination` | pass | pass |
| `wnm_bss_transition_mgmt` | pass | pass |
| `wnm_bss_transition_mgmt_disabled` | pass | pass |
| `wnm_bss_transition_mgmt_oom` | pass | pass |
| `wnm_bss_transition_mgmt_query` | pass | pass |
| `wnm_bss_transition_mgmt_query_disabled_on_ap` | pass | pass |
| `wnm_bss_transition_mgmt_query_mbo` | pass | pass |
| `wnm_bss_transition_mgmt_query_with_unknown_candidates` | pass | pass |
| `wnm_coloc_intf_reporting` | pass | pass |
| `wnm_coloc_intf_reporting_errors` | pass | pass |
| `wnm_disassoc_imminent` | pass | pass |
| `wnm_disassoc_imminent_bssid_set` | pass | pass |
| `wnm_disassoc_imminent_fail` | pass | pass |
| `wnm_ess_disassoc_imminent` | pass | pass |
| `wnm_ess_disassoc_imminent_fail` | pass | pass |
| `wnm_ess_disassoc_imminent_pmf` | pass | pass |
| `wnm_ess_disassoc_imminent_reject` | pass | pass |
| `wnm_event_report` | pass | pass |
| `wnm_sleep_mode_ap_oom` | pass | pass |
| `wnm_sleep_mode_disabled_on_ap` | pass | pass |
| `wnm_sleep_mode_open` | pass | pass |
| `wnm_sleep_mode_open_fail` | pass | pass |
| `wnm_sleep_mode_proto` | pass | pass |
| `wnm_sleep_mode_rsn` | pass | pass |
| `wnm_sleep_mode_rsn_badocv` | pass | pass |
| `wnm_sleep_mode_rsn_beacon_prot` | pass | pass |
| `wnm_sleep_mode_rsn_ocv` | pass | pass |
| `wnm_sleep_mode_rsn_ocv_failure` | pass | pass |
| `wnm_sleep_mode_rsn_pmf` | pass | pass |
| `wnm_sleep_mode_rsn_pmf_key_workaround` | pass | pass |
| `wnm_time_adv_restart` | pass | pass |
| `wnm_time_adv_without_time_zone` | pass | pass |
| `wpas_config_file` | pass | pass |
| `wpas_config_file_invalid_network` | pass | pass |
| `wpas_config_file_key_mgmt` | pass | pass |
| `wpas_config_file_sae` | pass | pass |
| `wpas_config_file_set_cred` | pass | pass |
| `wpas_config_file_set_global` | pass | pass |
| `wpas_config_file_set_psk` | pass | pass |
| `wpas_config_file_wps` | pass | pass |
| `wpas_config_file_wps2` | pass | pass |
| `wpas_config_range_check` | pass | pass |
| `wpas_config_update_without_file` | pass | pass |
