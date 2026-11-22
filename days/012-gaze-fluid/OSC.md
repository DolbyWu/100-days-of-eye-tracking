# OSC contract

One OSC UDP bundle at about 60 Hz, immediate timetag, one float32 per address. Default destination is `127.0.0.1:9012`. Configure the bridge and Day 12 `Port` parameter together. The primary clocks and states travel in every packet once available. Optional channels appear after their first sample.

| Addresses | Unit and meaning |
| --- | --- |
| `/gx /gy` | EMA-smoothed binocular scene UV, lower-left origin. Last position held on invalid data. |
| `/worn /valid` | Binary worn and usable gaze flags. Gaze must be finite and inside the scene image. Stale telemetry clears the flags. |
| `/vx /vy /speed` | Smoothed velocity and magnitude in UV/s. |
| `/dwell` | Seconds within a 0.023 UV radius of a raw-gaze anchor. Position changes, invalid gaze and sample gaps reset it. This feature is a spatial estimate, independent of vendor-classified fixation events. |
| `/pupil_l /pupil_r /pupil_delta` | Left and right pupil diameter in mm. Missing eye values are −1. Delta is the mean of available positive diameters relative to an 8 s baseline. Delta is 0 when both are missing. |
| `/aperture_l /aperture_r` | Optional eyelid aperture in mm. Missing values are −1. |
| `/blink /fixation /saccade /fixation_onset /saccade_onset` | Cumulative counters scoped to `/session`. The renderer triggers a shockwave on a counter increase. A burst arriving in a single render frame produces one wave. |
| `/session /clock /gaze_t /imu_t` | Sender generation ID, heartbeat/playhead in seconds, and sample timestamps relative to the source epoch. Live heartbeat is on the host monotonic clock and sample times are on the device epoch. |
| `/epoch0` through `/epoch3` | Source epoch UNIX ns as four exact unsigned 16-bit words, low word first. Combine with `sum(epoch[i] << (16*i) for i in range(4))`. The telemetry CSV retains full sample timestamps. |
| `/scene_frame` | Replay MP4 zero-based index. −1 before the first timestamp or in live mode. |
| `/accel_data_*`, `/gyro_data_*`, `/quaternion_*` | Optional IMU components, in the source's units. |

The listener gates gaze injection after 300 ms without a fresh bridge heartbeat. The bridge independently expires gaze after 300 ms without a sample. In replay this timeout uses the source timeline. Velocity uses timestamp-aware EMA smoothing with 35 ms position and 55 ms velocity constants. Logging occurs before OSC decimation and retains optional fields as JSON in the raw CSV.
