# OSC contract

One OSC UDP bundle at about 60 Hz, immediate timetag, one float32 per address. Default destination is `127.0.0.1:9012`. Configure the bridge and Day 12 `Port` parameter together. The primary clocks and states travel in every packet once available. Optional channels appear after their first sample.

| Addresses | Unit and meaning |
| --- | --- |
| `/gx /gy` | EMA-smoothed binocular UV, lower-left origin. In AprilTag mode these are artwork-surface coordinates; otherwise scene-camera coordinates. Last position held on invalid data. |
| `/worn /valid` | Binary worn and usable gaze flags. Gaze must be finite and inside the active coordinate surface. In AprilTag mode, the marker surface must be visible and gaze must fall inside it. Stale telemetry clears the flags. |
| `/vx /vy /speed` | Smoothed velocity and magnitude in UV/s. |
| `/dwell` | Seconds within a 0.023 UV radius of a raw-gaze anchor. Position changes, invalid gaze and sample gaps reset it. This feature is a spatial estimate, independent of vendor-classified fixation events. |
| `/pupil_l /pupil_r /pupil_delta` | Left and right pupil diameter in mm. Missing eye values are −1. Delta is the mean of available positive diameters relative to an 8 s baseline. Delta is 0 when both are missing. |
| `/aperture_l /aperture_r` | Optional eyelid aperture in mm. While the device is worn, available readings are sent even when gaze is invalid, so a sustained eye closure can still be detected. Missing values are −1. |
| `/blink /fixation /saccade /fixation_onset /saccade_onset` | Cumulative counters scoped to `/session`. The renderer triggers a shockwave on a counter increase. A burst arriving in a single render frame produces one wave. |
| `/session /clock /gaze_t /imu_t` | Sender generation ID, heartbeat/playhead in seconds, and sample timestamps relative to the source epoch. Live heartbeat is on the host monotonic clock and sample times are on the device epoch. |
| `/epoch0` through `/epoch3` | Source epoch UNIX ns as four exact unsigned 16-bit words, low word first. Combine with `sum(epoch[i] << (16*i) for i in range(4))`. The telemetry CSV retains full sample timestamps. |
| `/scene_frame` | Replay MP4 zero-based index. −1 before the first timestamp or in live mode. |
| `/raw_gx /raw_gy` | Unsmoothed scene-camera gaze normalized by its 1600×1200 frame, top-left origin. Available before AprilTag mapping. |
| `/surface_visible /surface_on /marker_count` | Marker surface localized, current gaze inside it, and recognized configured tag count. These are 0 in ordinary live mode. |
| `/eye_video_valid /eye_video_w /eye_video_h` | Eye video analysis status and video frame size in pixels. |
| `/eye_url_n /eye_url0 …` | Length and packed UTF-8 bytes of the current eye-video RTSP URL. Each float carries up to three bytes as an exact integer. Zero length indicates no eye-video endpoint, as in the offline demo. |
| `/eye_l_* /eye_r_*` | Per video-half pupil candidate: `x`, `y` top-left normalized, `radius` normalized by full video width, `confidence`, `valid`. Video half names do not assert anatomical laterality. |
| `/eye_change0_*` through `/eye_change2_*` | Largest frame-change regions: top-left normalized center `x/y`, normalized box `w/h`, intensity `value` in 0–1, and `valid`. These are visual change cues, not neurotransmitter events. |
| `/accel_data_*`, `/gyro_data_*`, `/quaternion_*` | Optional IMU components, in the source's units. |

The listener gates gaze injection after 300 ms without a fresh bridge heartbeat. The bridge independently expires gaze after 300 ms without a sample. In replay this timeout uses the source timeline. Velocity uses timestamp-aware EMA smoothing with 35 ms position and 55 ms velocity constants. Logging occurs before OSC decimation and retains optional fields as JSON in the raw CSV.
