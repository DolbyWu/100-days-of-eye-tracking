# Day 010 — Reading Observatory

A live dashboard for reading with your eyes, built in our Eye5.js / Donut MIDI Workshop Editor. The glass crawler from Day 009 follows your gaze across a PDF. Its footfalls turn words into effects and feed a live radar and vertical bar chart.

[Try the mouse demo](https://dolbywu.github.io/100-days-of-eye-tracking/days/010-reading-observatory/demo/) · [Get the Eye5.js sketch](sketch.js) · [Watch the Day 010 Short on YouTube](https://www.youtube.com/shorts/KJUBxSQt9Os)

## Read and explore

- Open **PDF & analysis settings**, choose a PDF, and move your mouse across the page to guide the crawler. Scroll to read, or use the arrows below the PDF to turn pages.
- The gaze heatmap builds on each PDF page. Blue, yellow, and red indicate increasing exposure. Unvisited areas show the original page.
- The radar and bars count foot contacts with nouns, prepositions, technical terms, theories, and citations. Categories can overlap. Stepping on a numbered citation can reveal its matching bibliography entry in a green ribbon.
- Use **Visible seconds** to set the time window for the live gaze and pupil traces. **Reset session data** clears readings, heatmaps, and contact counts.

## Connect Neon

Paste the entire [sketch.js](sketch.js) into [our Eye5.js Workshop Editor](https://sharkburger.github.io/donut-midi/library/editor.html), press **Run**, and connect Neon through the Workshop. Keep all four AprilTags visible. The PDF stage uses the Workshop's 3:2 reference layout.

With fresh Neon data, the dashboard shows left and right pupil diameters and eye-direction yaw and pitch. The public mouse demo simulates gaze only.

## Optional OpenAI analysis

Run `node day010-dashboard-server.cjs` from this directory, then open [the local reader](http://127.0.0.1:8792). Open a PDF, enter your own API key, select reading and bibliography pages, and click **Analyze text + resolve references**. Only that action sends text from the selected pages to OpenAI through the local relay. Contextual analysis adds technical and theory tags and can supplement local numbered-reference matching. API usage is billed to your key.

Based on [Day 009 · Semantic Spider](../009-semantic-spider/). See [third-party notices](demo/THIRD_PARTY_NOTICES.md).
