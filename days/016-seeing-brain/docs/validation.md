# Mapping and validation

### Anatomical interpretation

| Display channel | Geometry and interpretation |
|---|---|
| V1 | Calcarine sulcus mesh, anatomical landmark proxy. Its surface does not delineate V1. |
| FEF | Middle frontal gyrus mesh used as a broad proxy. It overstates the spatial extent of FEF. |
| IPS | Source intraparietal sulcus, an anatomical landmark for the illustrated parietal response. |
| MT/MST | Middle temporal gyrus, a broad illustrative proxy with no verified functional boundary. |
| LGN, SC, optic chiasm and optic tracts | Named structures in this source atlas. |
| Cerebellum, brainstem | Named component geometry. Motor-related signals illuminate broad structures. |
| SEF, LC, pretectal/EW | No validated functional target used. LC and light-reflex activations are omitted. |
| Optic nerves and optic radiations | Schematic paths between atlas landmarks. The selected source meshes did not include a verified paired optic nerve. The approximated radiation bends laterally toward the calcarine landmark. |

The pathways animate representative same-side temporal and crossing nasal routes from each globe. Their branches use landmark centers and illustrative velocities, without reconstructing retinal hemifields or individual fibers. Two independently transformed eyeball meshes share one combined-gaze signal. The global low-amplitude pupil-linked tissue gain is deliberately nonspecific.

Yamamoto et al. compared fixation, smooth tracking and saccadic tracking blocks with fMRI. The reported tracking-related changes were distributed, with broader cortical involvement for saccadic tracking. These comparisons motivate a qualitative multi-region composition. The chosen colors, weights and time constants belong to the artwork. [Paper](https://doi.org/10.1093/cercor/bhaf242) · [Publisher-supplied metadata and abstract](https://api.crossref.org/works/10.1093/cercor/bhaf242)

### Signals

The adapter reads normalized combined gaze `gx/gy` (Y up), relative source gaze time in seconds, validity, cumulative native blink events, session and left/right pupil diameters in millimeters. Some bridge versions additionally supply four 16-bit epoch words; when present the features CHOP stores an approximate absolute gaze timestamp reconstructed from those words and the OSC float32 relative time. Precision is bounded by that float transport. Coordinate differences use actual source time gaps; render time drives decay. No fixed device sample rate was assumed. The bridge does not supply calibrated 3D rays. The thresholds in `config/activation.json` use normalized image fractions per second and depend on scene geometry and bridge smoothing.

Fixation requires sustained low speed; a saccade uses separate enter/exit speeds. Continuous moderate motion becomes smooth_motion. Target tracking, visual search and cognitive state are not inferred. A native blink count increment triggers a local pulse. Invalid gaze clears motion features, stale timestamps fade activation, and session changes reset the baseline. Valid positive pupil diameters are compared to a slow session baseline, skipping blink intervals. Scene luminance is not corrected. All indications are illustrative.

### Test record

- Verified archive digest before extracting. Verified all 24 generated mesh digests, finite coordinates and left/right landmark ordering. Inspected [frontal](front.png), [lateral](lateral.png), [superior](superior.png) and [oblique](oblique.png) TouchDesigner renders.
- The first render exposed default torus POPs inside Geometry COMPs. The builder removes the defaults before selecting the anatomical File SOPs. Separate passes make inner structures visible even when the skull is face-on.
- Mock and manual triggers produced distinct [fixation](fixation.png) and [saccade](saccade.png) captures. Python tests cover actual timestamps, hysteretic event entry, bounded activation, missing pupils, native blink handling, session reset and stale decay.
- The existing Day 012 demo bridge sent real localhost OSC packets into the project. The installed TD-Neon app subsequently delivered valid physical Neon gaze and bilateral pupil measurements on UDP 9000, with advancing gaze timestamps; the live feature CHOP produced nonzero V1 and FEF animation channels. No participant gaze recording is included.
- The optional [projected history layer](history.png) produced a nonzero trail inside the cortical projection. Camera changes clear it intentionally; trails have no 3D anatomical registration.
- Short frame-start timing windows in the saved quality setting yielded about 58 FPS in the mock scene and 60 FPS with growth at 960 × 540. These runs are too short to compare costs or establish sustained performance. [Raw timing](runtime-check.json). Set Width to 640, reduce Particles/Agents, disable Growth and set the TD project cook rate to 30 FPS for slower hardware. 1080p performance and Windows were not measured.
- Movie File Out produced a readable 960 × 540 Motion JPEG movie. [Preview](demo.mp4). Recording saves the public visualization; the existing bridge separately supports explicit raw telemetry capture. Keep recordings private unless consented.
