# Day 011 — Semantic Transfer / Paper Song

A glass crawler follows your gaze across a PDF. Step on a word and watch it fly toward a counter. The counter grows on arrival. With sound enabled, each reading path produces a different song.

[Try the mouse demo](https://dolbywu.github.io/100-days-of-eye-tracking/days/011-semantic-transfer/demo/) · [Get the Eye5.js sketch](sketch.js)

- Open a PDF and move the pointer over the page. Scroll to read or use the page arrows.
- Click **Enable Paper Song**. Nouns, prepositions, technical terms, theory words, and citations have distinct sounds. Citations play an ascending chime and can reveal the corresponding bibliography entry. Paper sections change the harmony in A minor at 104 BPM.
- The upper bars count word categories. The lower bars count contacts by paper section. A contact can count in both. The reader maps common headings locally. Use **Section on this page** to assign an unrecognized page manually.
- For live gaze, paste the full sketch into the [Eye5.js Workshop Editor](https://sharkburger.github.io/donut-midi/library/editor.html), run it, and connect Neon. Keep all four AprilTags visible.

## Optional OpenAI analysis

Run `node day011-semantic-transfer-server.cjs` from this directory and open [the local reader](http://127.0.0.1:8793/). Open a PDF, enter your own key, and select **Analyze headings + theories**. This sends heading candidates, then up to 2,400 words from Related Work or Background (or the current page when no such section is detected). **Analyze text + resolve references** sends the selected reading and bibliography text. The key stays in memory. The local heading map and mouse demo work without a key.

Based on [Day 010](../010-reading-observatory/). See [third-party notices](demo/THIRD_PARTY_NOTICES.md).
