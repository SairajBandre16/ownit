# OwnIt roadmap

Ideas for the next rounds of work, kept here so none get lost. Items move to [`progress.md`](progress.md) when they are built. House rules still apply: no AI models, no external APIs, no detector gaming, no em dashes.

## Done (2026-09-29)

- **Offline banner (UX).** When the server can't be reached, the workspace, Voice and Viva pages explain what still works, how to start or reconnect the server, and offer Retry. Failed requests re-run once the server answers.
- **Rewrite button always visible (UX).** "Suggest rewrites" sits in the sticky step toolbar. The settings panel moved up, under the score.
- **Fewer highlights at once (UX).** The layer chips are one "Layers" menu. The editor shows the main suggestions only; picking a category in the Suggestions list shows all of that category's highlights.
- **Punctuation tidy-up (feature).** New `dash_tidy` transform: dashes become the mark that names the relation (full stop, comma, colon or brackets), with a reason for each change. It runs at every intensity and respects a student whose own writing uses dashes. The analyzer flags dashes and "not just X, it's Y" formulas.

## UI and UX

1. **Quieter document title.** The first line of a draft is not detected as a heading, and its words get protected-span underlines. Treat a short first line as the title and hide protected underlines on headings.
2. **Rename from the step rail.** The title in the step rail is cut off ("Design and Testing ..."). Show the full title on hover and make click-to-rename obvious.
3. **First-run guide.** A short checklist through the five steps, and a "Try a sample draft" button on the empty workspace (today it is only inside the New document dialog).
4. **Keyboard.** A Ctrl+K command menu (jump to a step, run a rewrite, toggle layers) and a "?" sheet listing every shortcut.
5. **Save feedback.** An autosave indicator ("Saved in this browser") and an undo toast after accept, reject and bulk actions.
6. **Mobile layout.** Not checked yet. The insight panel stacks under a long editor; tabs in a bottom sheet would keep the score and changes reachable.
7. **Paragraph focus.** An optional mode that highlights only the paragraph the cursor is in.
8. **Local-only port note.** A dev server on a port other than 3000 is blocked by CORS unless `OWNIT_CORS_ORIGINS` includes it. The offline banner could detect this case and say so.

## Features

1. **Source paraphrase check.** The student pastes their sources; OwnIt flags sentences that stay too close to a source (n-gram overlap plus vector similarity), so they either quote and cite or rewrite in their own words. Runs locally.
2. **References doctor.** Check that in-text `[n]` numbers match the reference list (no gaps, none unused), that one citation style is used, and that author-year citations appear in the list.
3. **Lab data import.** Paste a CSV of measurements to get a results table, a chart, unit checks, and prompts to describe each trend in the student's own words.
4. **Version timeline.** Snapshots per session, a diff between any two, and a chart of the Ownership Score over time.
5. **Group projects.** Each student owns sections; ownership and understanding are tracked per author.
6. **Verifiable Understanding Report.** A read-only link or short code that lets a teacher check a report is genuine (a hash of the report contents).
7. **Offline Revision Deck.** Make the app installable (PWA) so deck review works without a connection.
8. **LaTeX export.** Export alongside .docx, keeping equations, figure references and citations.
9. **Always-on free backend.** Oracle Cloud Always Free VM with Docker and a free HTTPS domain, so the site works without the home PC.
10. **More stock patterns.** Extend the flags beyond dashes: overused lists of three, "In conclusion" wrap-ups that repeat the introduction, and sentence-final "-ing" add-ons ("..., highlighting the importance of X").

## Known issues

- **Synonym swaps can change meaning in technical text.** Seen in an eval run: "deflected" to "avoided" (beam deflection) and "transmit" to "carry" (sensor node). The meaning gate passed both. Options: skip verbs that have a technical sense in `eng_abbreviations.json`-style term lists, raise the vector-similarity floor for verbs, or protect domain verbs listed per subject.
- **Comma splices after phrase deletion.** Removing "just" from "It is not just a cost issue, it is a safety issue" leaves a comma splice. The contrast-formula flag points at it, but the rewrite could split the sentence instead.
