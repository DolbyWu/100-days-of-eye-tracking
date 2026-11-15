# Third-party components

The standalone mouse playground bundles these components so it can run without the Workshop:

- p5.js 1.11.11 — LGPL-2.1; full license: [vendor/p5-LICENSE.txt](vendor/p5-LICENSE.txt). Upstream source: https://github.com/processing/p5.js/tree/v1.11.11 . The distributed runtime is unmodified.
- `p5.neon.js` and `p5.neon-effects.js` — MIT, from the Donut MIDI `aoi-cognitive-voices` branch: https://github.com/sharkburger/donut-midi/tree/aoi-cognitive-voices/library . License annotations are retained in the source files.
- `markers.svg` — original Donut MIDI marker layout: https://github.com/sharkburger/donut-midi/blob/aoi-cognitive-voices/markers.svg . Bundled unmodified to preserve the artwork's corner marker appearance.

The playground uses the existing `sketch.js` one directory above. It runs in mouse mode and does not connect to hardware, open a camera, or record eye data.
