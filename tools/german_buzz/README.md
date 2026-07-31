# German Buzz website generator

The website tools create weekly German Buzz HTML pages from the same JSON used by the mobile app. They work locally only and never commit, push, deploy, connect to Firestore, or track visitors.

## Recommended command

Use the recommendation-aware wrapper:

```powershell
python tools/german_buzz/generate_website_with_recommendations.py path\to\2026-W32.json --dry-run
```

Generate locally after reviewing the dry run:

```powershell
python tools/german_buzz/generate_website_with_recommendations.py path\to\2026-W32.json
```

The wrapper reuses `generate_website.py` and adds curated resources from `recommendations.json`.

## Files managed

For an issue such as `2026-W32`, the generator:

- creates `mygermanfreund/german-buzz/kw-32/index.html`;
- adds the newest issue to `mygermanfreund/german-buzz/index.html`;
- adds the canonical issue URL to `sitemap.xml`.

Existing issue pages are preserved. Replacing an existing issue requires `--force`.

## Canonical JSON fields

The website uses only:

- `id`
- `year`
- `weekNumber`
- `dateRange`
- `tagline`
- `weeklySummary`
- `topics[].title`
- `topics[].whatsHappening`
- `topics[].germanContext`

Mobile-only dialogue and vocabulary fields are ignored.

## Context-aware recommendations

`recommendations.json` contains manually reviewed rules. Each rule has:

- topic keywords;
- one or more HTTPS resources;
- a short description;
- a visible source name.

The wrapper searches the topic title and explanation, shows at most two unique resources, opens external links in a new tab, and omits the recommendation section when nothing relevant matches.

Current controls:

- no paid placements;
- no affiliate parameters;
- no advertising SDK;
- no click tracking;
- no automatic external API lookup;
- recommendations must be reviewed before publication.

A future sponsored or affiliate resource must be explicitly labelled and approved before it is added to `recommendations.json`.

## Review before committing

```powershell
git status
git diff -- mygermanfreund/german-buzz sitemap.xml
grep -R "Helpful resources" mygermanfreund/german-buzz/kw-32/index.html
```

Do not use `--force` unless an existing generated page has been reviewed and intentionally needs correction.
