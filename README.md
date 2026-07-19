# MovieRex

Movie recommendation website — [movierex.github.io](https://movierex.github.io)

## Adding a movie

Add a line to `Movies.txt`:

```
The Substance 2024
```

Format is `Title Year`. That's the whole workflow — push the change and a
GitHub Action scrapes Rotten Tomatoes, downloads the poster, and rebuilds
`index.html`. Removing a line removes the movie from the site.

## How it works

| File | Purpose |
| --- | --- |
| `Movies.txt` | The list. The only file you edit by hand. |
| `movies.json` | Scraped data cache, one entry per movie. Written by the build. |
| `index.html` | Generated. The build rewrites the regions between `<!-- MOVIE_CARDS -->`, `<!-- GENRE_CHIPS -->` and `<!-- STREAMER_CHIPS -->` marker pairs; everything else is hand-edited. |
| `rt_scraper.py` | Fetches one movie from Rotten Tomatoes. |
| `update_html.py` | Reads `Movies.txt`, scrapes anything new, renders the page. |
| `test_scraper.py` | Offline tests. Add `--live` to also hit Rotten Tomatoes. |
| `css/movierex.css`, `js/movierex.js` | The site. No frameworks, no dependencies. |

The build is idempotent — it regenerates the movie grid from scratch each run
rather than appending, so re-running it never duplicates entries.

Because `movies.json` caches scraped **data** rather than rendered markup, you
can change the page template freely without re-scraping. To force a refresh of
one movie, delete its key from `movies.json`; delete the whole file to refetch
everything.

## Running it locally

```bash
pip install -r requirements.txt
python test_scraper.py      # offline checks
python update_html.py       # scrape anything new, rebuild index.html
python -m http.server 4173  # then open http://localhost:4173
```

## Notes

- Posters are downscaled to 400px wide on download; full-resolution originals
  from Rotten Tomatoes run to 15MB each.
- Streaming services without a logo in `img/logos/` render as a text chip, so a
  newly-added service doesn't need an asset to work.
- If a title fails to scrape, the build publishes everything else and exits
  non-zero listing the failures. Check the title and year against the Rotten
  Tomatoes page — the year is used to disambiguate remakes.
