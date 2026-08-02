# German Buzz Website Format

Status: Frozen after KW32 guide-array update.

## Source separation

The weekly German Buzz JSON used by the mobile app remains unchanged and is the shared source for issue metadata, German topic titles and German `whatsHappening` text.

Website-only enrichment lives under:

```text
tools/german_buzz/web_enrichment/YYYY-W##.web.json
```

## Required website topic fields

Every weekly topic must appear exactly once, matched by its exact German title.

Each entry contains:

- `title`
- `englishTitle`
- `englishContext`
- `interestingFacts`
- `guides`

## Interesting facts

```json
"interestingFacts": {
  "enabled": true,
  "de": "German fact text",
  "en": "English fact text"
}
```

Use `{ "enabled": false }` when no fact is approved.

## Related guides

`guides` is always an array. Use an empty array when no evergreen guide is approved.

```json
"guides": [
  {
    "title": "Guide title",
    "summary": "Short reason to open the guide.",
    "url": "/mygermanfreund/guides/example-guide/"
  }
]
```

A topic may link to more than one approved guide. Duplicate guide URLs are rejected. Older enrichment files using `learnMore` remain supported temporarily, but new and updated issues must use `guides`.

## Public website output

German stays visible. English title, context and English fact appear inside a collapsed dropdown. Only approved guide links are rendered.

The website does not display conversations, vocabulary lists, internal Life Area names, Knowledge Unit terminology or experience tracking.

## Sunday workflow

1. Approve the four mobile-app topics.
2. Keep the mobile JSON unchanged.
3. Prepare website enrichment.
4. Decide `interestingFacts` for each topic.
5. Website Team suggests evergreen guides; the product owner approves or rejects them.
6. Create approved guides and map them internally to a Life Area.
7. Run the website generator and review the static page and sitemap.
8. Merge and verify the live website.
