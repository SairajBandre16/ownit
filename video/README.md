# OwnIt intro video

A 37-second, 1920x1080 intro for OwnIt, built with [Remotion](https://www.remotion.dev) (React to
video). Every cut and animation lands on a beat of a soundtrack that is synthesized from scratch
(oscillators and filtered noise, no samples), so the whole thing is license-free.

## Storyboard

100 BPM, one beat = 18 frames at 30 fps (0.6 s). Feature scenes get 6 beats (3.6 s) so captions can be read;
the chord changes on every scene cut.

| Time | Beats | Scene | Sound |
|---|---|---|---|
| 0:00 | 0-7 | Hook: an AI draft, stock phrases flagged; "AI wrote the draft." "Can you defend it?" | pad, pops, thuds, riser, silence |
| 0:04.8 | 8-11 | Brand: logo draws on, "Five steps from AI draft to defensible." | impact, drums and bass enter |
| 0:07.2 | 12-19 | 01 Humanize: changes strike and swap, reason cards, score 54 to 82 | orange wipe + whoosh, full groove |
| 0:12.0 | 20-25 | 02 Walkthrough: gist, concept map nodes pop in | whip pan + whoosh, pops |
| 0:15.6 | 26-31 | 03 Make it yours: generic spot, prompt, typed insertion, ownership heatmap | ticks, typing, shimmer |
| 0:19.2 | 32-37 | 04 Prove it: Viva Simulator in exam hall mode | iris + whoosh, half-time drums |
| 0:22.8 | 38-42 | Report Doctor: units, abbreviations, claims | crash, a tick per fix |
| 0:25.8 | 43-48 | 05 Export: understanding gate, lock opens, .docx files | pops, unlock |
| 0:29.4 | 49-54 | Kinetic cards: 0 AI models, 0 external APIs, Every change explained, Yours. | chord stabs, snare roll |
| 0:33.0 | 55-60 | End card: logo, "Humanize it. Understand it. Own it.", URL | silence, big hit, bells, fade |

## Run

Needs Node 18+ and Python 3 with `numpy` and `scipy`.

```bash
cd video
npm install
npm run soundtrack   # writes public/soundtrack.wav from src/timeline.json
npm run studio       # live preview in the browser, scrub the timeline
npm run render       # out/ownit-intro.mp4 (master, CRF 18, AAC 256k)
npm run render:web   # media/: 1080p + 720p MP4, VP9 WebM, poster JPG (committed)
npm run stills       # out/stills/*.png at half size, for a quick look
```

`npm run build` runs soundtrack, render and render:web in order. Rendering downloads Chrome
Headless Shell once (about 110 MB). On a low-memory machine keep `--concurrency 2`.

## Editing

- **Timing** lives in `src/timeline.json`. Each scene has a start, a length in beats and its chords; each cue
  is `[beat relative to the scene's cut, sound]`. The video (`cue()` in `src/timeline.ts`) and the
  soundtrack script both read it, so moving a cue moves its animation and its sound together.
  Re-run `npm run soundtrack` after any change there.
- **Mix levels** are the `LEVEL` and `SFX_GAIN` tables at the top of `scripts/make_soundtrack.py`.
- **Scenes** are in `src/scenes/`, one file each. Transitions (orange wipe, whip pan, iris) are in
  `src/Intro.tsx`; the notebook chrome (crop marks, timecode, step rail) is `src/Overlay.tsx`.
- **Colors and fonts** come from the app's design tokens (`src/theme.ts`): Newsreader, Schibsted
  Grotesk, IBM Plex Mono, paper `#F7F5F0`, ink `#1A1A1A`, signal orange `#FF5A1F`.

## Portfolio embed

Browsers only autoplay muted video, so autoplay it muted and let visitors turn the sound on.

```html
<video
  autoplay muted loop playsinline controls preload="metadata"
  poster="/media/ownit-intro-poster.jpg"
  width="1920" height="1080" style="width: 100%; height: auto; border-radius: 12px;">
  <source src="/media/ownit-intro-1080p.webm" type="video/webm" />
  <source src="/media/ownit-intro-1080p.mp4" type="video/mp4" />
</video>
```

For phones, swap the MP4 source for the 720p file with a media query, or serve only the 720p file
if page weight matters more than sharpness.

## License note

Remotion is free for individuals and small teams; companies above its size limit need a license
(see remotion.dev/license). The soundtrack and all visuals are original to this repo.
