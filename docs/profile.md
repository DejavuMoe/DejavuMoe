# Maintaining the profile

The README has three generated parts, everything else is handwritten:

- **Projects**: pinned-repository cards that look like GitHub's own pins, two to a row, in light and dark. Any number of them, any repository (yours or someone else's), each one customisable.
- **Writing**: the latest posts from the blog's RSS feed, as plain text links.
- The data snapshot in [`data/profile.json`](../data/profile.json) that both are rendered from.

## Why the cards don't hit rate limits

Services like `github-readme-stats` render a card **every time someone views your profile**, calling the GitHub API with a shared token — so cards break when that token is rate-limited. Here it works the other way round:

1. Once a day, GitHub Actions asks the GitHub GraphQL API about **all pinned repositories in one request**, using the job's built-in `GITHUB_TOKEN` (5,000 points/hour; one run costs about 1).
2. The cards are drawn as static SVG files and committed to [`assets/generated/`](../assets/generated/).
3. Visitors only ever load those committed files. Viewing the profile calls no API and no third-party service.

The trade-off is freshness: star counts are at most a day old (or as fresh as the last push or manual run).

## Customising the cards

Edit `pins` in [`profile.config.json`](../profile.config.json). Order in the list is order on the page. An entry is either a repository name or an object:

```jsonc
"pins": [
  "Pail",                                  // one of your own repositories
  "someone/their-repo",                    // anyone else's public repository
  {
    "repo": "Smoji",                       // required: "name" or "owner/name"
    "title": "Smoji ✨",                   // card heading (default: name, or owner/name for others)
    "description": "Your own wording.",    // replaces the GitHub description
    "badge": "Featured",                   // pill next to the title ("" hides it; default Public / Public archive / Public template)
    "link": "https://smoji.example"        // where the card links (default: the repository); HTTPS only
  }
]
```

Unknown keys, duplicates, invalid names or non-HTTPS links fail the run instead of being ignored. A pinned repository that is renamed, deleted or made private fails the full refresh with its name in the error, and the previous profile stays published until you fix the list.

After changing `pins`, either push (the workflow runs a full refresh on `master`) or run the full refresh locally. `--offline` and `--check` cannot add a new pin, because its numbers are not in the snapshot yet.

What a card shows: repository icon, title, badge, *Forked from …* for forks, the description (up to three lines, then `…`), primary language with GitHub's colour, stars, and forks (when there are any).

On screens narrower than 600px GitHub swaps in a compact variant of each card with larger lettering and a two-line description, so the two-column grid stays readable on phones.

## Files

- [README](../README.md): handwritten intro, navigation, section headings and PGP identity, plus two generated regions (`PINS`, `BLOG-POST-LIST`).
- [Configuration](../profile.config.json): owner, blog and feed URLs, `post_count`, and `pins`.
- [Updater](../scripts/update_profile.py): GraphQL and RSS collection, validation, rendering. Python 3.11+, **standard library only**.
- [Cards](../scripts/profile_art.py): the pin card SVG and the README grid markup.
- [Preview](../scripts/preview.py): renders the README through GitHub's own Markdown API into `.preview/site/`.
- [Tests](../tests/test_profile.py): network-free.
- [Workflow](../.github/workflows/profile.yml): the single writer of the README and generated assets.

## CI/CD

**Test & preview** runs on every relevant push and pull request: compile, unit tests, (on PRs) a byte-exact check that committed output matches its sources, an offline render, and a preview (`light.html`, `dark.html`, `gallery.html`) uploaded as the **profile-preview** artifact.

**Update profile** runs after the tests pass, on `master` only:

| Trigger | What runs | UTC | UTC+8 |
| :--- | :--- | :--- | :--- |
| Schedule | Full refresh: cards and posts | 00:23 daily | 08:23 |
| Schedule | Posts only (keeps the dated card snapshot) | 06:23, 12:23, 18:23 | 14:23, 20:23, 02:23 |
| Push to `master` touching sources | Full refresh | — | — |
| **Actions → Profile → Run workflow** | `full`, `blog-only`, or `offline` | — | — |

Each run writes a summary (cards with stars and forks, latest post, changed files), verifies the exact file inventory, commits only if something changed and pushes without force. No custom secret is required. Scheduled workflows can be paused by GitHub after long inactivity; use **Run workflow** to wake them.

The unrelated exchange-rate release workflow (`releaseRateJSON.yml`) is untouched.

## Updating locally

```powershell
python scripts/update_profile.py              # full refresh (token from GH_TOKEN, GITHUB_TOKEN or `gh auth token`)
python scripts/update_profile.py --blog-only  # posts only
python scripts/update_profile.py --offline    # re-render the committed snapshot, no network
python scripts/update_profile.py --check      # verify bytes and file inventory, no writes
python -m unittest discover -s tests -v
python scripts/preview.py                     # .preview/site/{light,dark,gallery}.html
```

Rendering is byte-for-byte deterministic on Windows and Linux, which is what lets `--check` work.

Linux validation from this Windows workstation:

```powershell
linux-task.ps1 -Mode build -Project 'D:\Forgejo\DejavuMoe' `
  -Command 'python3 -m unittest discover -s tests -v && python3 scripts/update_profile.py --check'
```

## Failure behaviour

- Everything is fetched, validated and rendered in memory **before** any file is written. A GitHub, RSS, XML, snapshot, config or marker failure leaves the previous profile in place.
- Transient HTTP errors retry three times with backoff; requests time out; responses are capped at 8 MB; feeds with DOCTYPE/ENTITY declarations or non-UTF-8 encodings are rejected. The token is only ever sent to the GraphQL endpoint and credential-bearing redirects are refused. Repository names reach GraphQL as variables, never spliced into the query.
- Private repositories are refused even when a local token could read them.
- Blog links must be HTTPS on the blog host under `/posts/`. Cached values (URLs, colours, counts, summaries) are re-validated on every render.
- External text is escaped for Markdown, HTML attributes and SVG. Tests assert generated SVGs contain no scripts, `foreignObject`, links, `@import`, `url()` or `https://`.
- Only the two marker regions are replaced; handwritten content stays as written.

## GitHub display constraints

GitHub strips CSS and scripts from README HTML, so the cards are images. Each card has four variants: light/dark × wide/compact. GitHub's native `#gh-light-mode-only` / `#gh-dark-mode-only` link selectors choose the theme (explicit and automatic); each link wraps a width-only `<picture>` that swaps in the compact layout on phones. Compound colour-scheme media queries are avoided because GitHub's `themed-picture` script rewrites them and drops width conditions.

Card text uses system font stacks and the line-wrapping uses estimated glyph widths, so lettering varies slightly between operating systems. GitHub's image cache may delay a visible update after a run.

Tip: GitHub still shows its own *Pinned* section under the README. Unpin everything there (Customize your pins → uncheck all) if you don't want the projects shown twice.
