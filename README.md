# Jaden Bachrach portfolio mirror

A static, self-contained copy of [jadenbachrach.framer.website](https://jadenbachrach.framer.website),
served at **https://jbachrach36.github.io** for networks that block Framer.

## How it updates
`.github/workflows/mirror.yml` runs `mirror.py`, which loads the published Framer site,
downloads every page, image, font and script into the copy, and publishes it to GitHub Pages.
It runs every 6 hours, on every push, and on demand:
**Actions → Mirror Framer site → Run workflow** (about a minute). The link never changes.
If a run fails, the previous copy stays live.

## Presentations
`static/decks/` holds the deck pages (slide viewer, PDF, link to the animated Figma version).
Links to those Figma files in the portfolio are pointed at these pages in the mirror
(see `DECK_LINKS` in the workflow). `build_decks.py` regenerates the pages from the slide images.
