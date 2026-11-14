# Boundless performance comparison

| run_id | runtime_mod_count | startup_timer_s | menu_signal_s | integrated_server_start_s | presentmon_scenario | mean_fps | fps_1_percent_low | fps_0_1_percent_low | f3_point_fps | f3_point_server_tick_ms | tick_backlog_warning_p95_ms | tick_backlog_warning_max_ms | chunk_generation_events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| historical-in-world-power-outage-20261113 | 492 | 384.251 | 293 | 489 |  |  |  |  | 33 | 207 | 109.631 | 164.633 |  |
| p01-current-20261114 | 505 | 424.132 | 344 |  | startup-transition | 57.687 | 13.204 | 5.847 |  |  |  |  | 0 |

## Match status

| run_id | scenario_matches_reference | mods_match_reference | config_matches_reference |
| --- | --- | --- | --- |
| historical-in-world-power-outage-20261113 | True | unknown | unknown |
| p01-current-20261114 | True | False | unknown |

`false` marks a known scenario or runtime mod-count, JAR-hash, or configuration-fingerprint mismatch; `unknown` means the needed baseline lock was not retained. Startup timers are descriptive because the historical run has no JAR or configuration lock.
