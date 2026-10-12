# Maintaining this profile

The profile is an editorial project index, not a badge wall. Its wordmark and topographic loop are original SVG artwork: warm paper / ink in light mode, charcoal / sage in dark mode, with a small vermilion accent. The contour is decorative, **not** a fabricated activity chart.

## Files

- [README](<../README.md>): handwritten introduction, blog link, PGP identity, and three generated regions.
- [Configuration](<../profile.config.json>): owner, feed URL, project/post limits, exclusions, and reviewed short descriptions.
- [Updater](<../scripts/update_profile.py>): public GitHub collection, RSS parsing, ranking, and deterministic generation. Python 3.11+; **no third-party runtime dependencies**.
- [Artwork](<../scripts/profile_art.py>): all SVG layouts, colors, and accessible image descriptions.
- [Public snapshot](<../data/profile.json>): dated public metadata only; never a token, API credential, private repository, or private contribution history.
- [Generated assets](<../assets/generated/>): repository-owned SVGs, not images served by a third-party statistics service.
- [Tests](<../tests/test_profile.py>): network-free fixtures for pagination, release counting, failure protection, escaping, ranking, and rendering.
- [Update workflow](<../.github/workflows/blog-post-workflow.yml>): the single writer for the README and generated assets.

## What updates, and when?

| Content | UTC schedule | UTC+8 schedule |
| :--- | :--- | :--- |
| Project ranking, counts, artwork, blog | Daily at 00:23 | Daily at 08:23 |
| Additional blog-only refreshes | 06:23, 12:23, 18:23 | 14:23, 20:23, 02:23 |

The blog still refreshes every six hours and still shows **eight posts**. The original `BLOG-POST-LIST` markers are retained, but the old third-party blog updater is replaced by this repository's own generator so two workflows cannot race to edit the same file. The unrelated exchange-rate release workflow is unchanged.

GitHub scheduled runs are best-effort, may be delayed, and only run from the default branch. Public repositories can have schedules disabled after prolonged inactivity; use **Actions → Update profile → Run workflow** if necessary.

A push affecting the source/configuration to `master`, or a manual dispatch, runs a full refresh. Bot commits made with `GITHUB_TOKEN` do not recursively trigger another push workflow. Runs are serialized and never force-push; a concurrent human push fails safely and can be followed by a new run.

## Enabling on GitHub

1. Commit the source, README, snapshot, generated SVGs, tests, and workflow to the public **DejavuMoe/DejavuMoe** repository's **master** branch. Local edits do not change the live profile.
2. Enable GitHub Actions for this repository. The workflow asks for `contents: write` only in its update job. Repository/organization rules must allow that job to commit to `master`; a rule requiring PRs or signed commits may prevent the bot push.
3. Run **Actions → Update profile → Run workflow** once and check its log.
4. Refresh the GitHub profile. GitHub image caching may delay a visible asset update.

No custom PAT, `feed`, `username`, or `mail` secret is required. `GH_TOKEN` is set to the job's built-in `${{ github.token }}`. Collection is explicitly restricted to public owner repositories; the token is used to authenticate/rate-limit GitHub API calls, not to expose private data. Forks of this profile do not run the write job unless its repository guard is deliberately changed.

## Selection and statistical meaning

Eligible repositories belong to `DejavuMoe`, are public and non-fork, are not archived, have a default-branch commit history, and are not in the configured exclusion list. The profile repository itself is excluded so automation commits and exchange-rate releases cannot inflate its ranking. “Non-fork” is GitHub metadata, not a claim that every line or resource is an original creation.

The six highest-scoring entries become clickable project strips. The complete eligible index remains available as accessible text inside the README's **Selection notes & full project index** disclosure.

```text
score = 0.35 × ln(1 + stars)
      + 0.45 × ln(1 + default-branch commits)
      + 0.20 × ln(1 + published releases)
```

The weights slightly favor sustained development; logarithms keep one popular resource pack from overwhelming projects with substantial implementation and release histories. Ties are resolved by stars, commits, releases, then case-insensitive name. This is a presentation heuristic, **not a quality grade**.

- **Stars:** the current `stargazerCount`, not lifetime star events.
- **Commits:** default-branch `history.totalCount`, including **all authors** and the reachable merged history. Not personal contributions, not all branches, and not a recent activity count.
- **Releases:** enumerate the default GraphQL `releases` connection with pagination; count non-draft releases with a publication date. Published prereleases count; Git tags alone do not. Zero releases is valid for browser apps and other projects without packaged releases.
- **Release ordering:** intentionally do not request explicit `CREATED_AT` ordering. During validation, that ordering returned six historical Smoji releases while the default connection and unauthenticated public REST endpoint both returned zero. Sort the returned public releases locally when finding the latest version.
- **Scope:** the footer's star total covers the complete eligible index, not just the six featured repositories.
- **Descriptions:** reviewed one-line descriptions override stale GitHub descriptions. Unknown future projects fall back to their public repository description. Update the override when a project's purpose changes.
- **Language:** GitHub's primary-language label is metadata, not a claim about the backend architecture. For example, a project containing substantial browser code can have a JavaScript label and a Rust/Go backend.

All repository and release connections are paginated. Drafts, private repositories, forks, and foreign-owned results are rejected before caching. Individual private contributions and user access tokens are never saved.

## Updating locally

Windows PowerShell, with the existing `gh` login:

```powershell
python scripts/update_profile.py
python -m unittest discover -s tests -v
```

The script obtains a token from `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token`; it never prints or saves the token. The token is never attached to the blog request. Credential-bearing redirects and non-HTTPS feed redirects are refused.

For visual/source changes without any network access:

```powershell
python scripts/update_profile.py --offline
python scripts/update_profile.py --check
```

`--check` verifies the exact expected file inventory and UTF-8 bytes without network access or writes. If you reduce the configured project count, remove obsolete numbered SVG variants from the generated-assets directory before checking/committing.

Refresh just the blog while preserving the last project snapshot and its date:

```powershell
python scripts/update_profile.py --blog-only
```

Linux validation from this Windows-first workstation:

```powershell
linux-task.ps1 -Mode build -Project 'D:\Forgejo\DejavuMoe' `
  -Command 'python3 -m unittest discover -s tests -v && python3 scripts/update_profile.py --offline'
```

Edit canonical source on Windows. Linux build mirrors are disposable and must not be reverse-synchronized into the source tree.

## Failure behavior

- Fetch all required sources, validate, and render into memory **before writing any output**. If GitHub, RSS, XML parsing, snapshot validation, or region markers fail, the workflow fails without replacing the previous profile with an empty list or zero counts.
- Transient HTTP failures retry up to three times with bounded backoff. Network calls have timeouts, responses have an 8 MB limit, and UTF-8 RSS/Atom feeds with entity/doctype declarations are rejected.
- Blog entries must have HTTPS links on the configured blog host under `/posts/`. Duplicate links, `about`/`now` pages, and foreign URLs are not promoted as posts.
- External text is escaped for Markdown, HTML attributes, and SVG. Generated SVGs contain no scripts, `foreignObject`, external fonts, or remote images.
- Only the three explicit README marker regions are replaced. The introduction and all PGP fingerprints stay handwritten.
- Re-rendering the same snapshot is byte-for-byte deterministic. No file is written when its contents are unchanged. Snapshot dates advance on successful fetches, not on offline rendering.
- All validation precedes writing, but the multi-file write is not a filesystem transaction: disk/power failures during writing require rerunning the generator. Actions only commits after a successful run and determinism check.

## GitHub display constraints

GitHub strips arbitrary CSS and scripts from README HTML. This profile uses supported links, `picture`/`source`, images, headings, and a details disclosure instead of pretending the README is a custom web application.

Four variants per image cover light/dark and wide/compact layouts. GitHub's native `#gh-light-mode-only` / `#gh-dark-mode-only` link selectors handle the site theme; each link contains a width-only `picture` that selects compact art on phones. This separation is deliberate: GitHub's `themed-picture` JavaScript replaces compound color-scheme media queries and discards their width conditions. The native theme-link CSS supports explicit site light/dark modes as well as automatic system theme. There is no user-supplied CSS or JavaScript in the README.

Compact artwork increases the type size and stacks metrics rather than shrinking a desktop dashboard. Each linked project image has a full descriptive `alt`; its numerical data is also available in the native-text index. The original introduction, blog entries, and identity remain real text.

The SVGs can be displayed even when third-party badge services are down. The layout has been checked with GitHub's Markdown sanitizer and by injecting the local markup into the real GitHub page in a browser, without publishing any changes. Local preview screenshots are not proof that a workflow has run or that the live GitHub profile has changed.
