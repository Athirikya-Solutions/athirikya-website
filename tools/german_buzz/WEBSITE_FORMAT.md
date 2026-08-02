# German Buzz Website Format

Status: Frozen after KW28 implementation.

## Source separation

The weekly German Buzz JSON used by the mobile app remains unchanged and is the shared source for:

- issue id, year and week number;
- date range and weekly summary;
- German topic title;
- German `whatsHappening` text.

The website adds a separate enrichment file under:

```text
tools/german_buzz/web_enrichment/YYYY-W##.web.json
```

The website enrichment never changes the mobile-app payload.

## Required website topic fields

Every weekly topic must appear exactly once in the website enrichment file, matched by its exact German title.

Each entry contains:

- `title` — exact title from the weekly JSON;
- `englishTitle` — reader-facing English heading;
- `englishContext` — English explanation for a global audience;
- `interestingFacts` — optional bilingual fact block;
- `learnMore` — optional practical guide block.

## Frozen optional blocks

### Interesting facts

```json
"interestingFacts": {
  "enabled": true,
  "de": "German fact text",
  "en": "English fact text"
}
```

When disabled:

```json
"interestingFacts": {
  "enabled": false
}
```

### Learn more

```json
"learnMore": {
  "enabled": true,
  "title": "Guide title",
  "summary": "Short reason to open the guide.",
  "url": "/mygermanfreund/guides/example-guide/"
}
```

When disabled:

```json
"learnMore": {
  "enabled": false
}
```

A Learn More guide is added only after editorial approval. The Website Team may suggest guides, but the product owner makes the final decision every Sunday.

## Public website output

Each topic contains only:

1. German topic title;
2. English title;
3. German weekly context from the shared JSON;
4. English website context;
5. optional Interesting to know block;
6. optional Learn more block.

The website does not display:

- conversations;
- vocabulary lists or word meanings;
- internal Life Area or Knowledge Unit terminology;
- internal experience tracking.

## Generator command

```bash
python tools/german_buzz/generate_website_content.py \
  <weekly-app-json> \
  tools/german_buzz/web_enrichment/YYYY-W##.web.json \
  --force
```

Use `--dry-run` before writing a new issue.

## Sunday workflow

1. Approve the four German Buzz topics for the mobile app.
2. Publish the unchanged weekly JSON to the app workflow.
3. Prepare the website enrichment for all four topics.
4. Decide `interestingFacts` yes/no for each topic.
5. Website Team suggests `learnMore` yes/no; product owner approves.
6. Create any approved guide before enabling its link.
7. Run the website generator.
8. Review the generated weekly page, landing page and sitemap diff.
9. Commit, merge and verify the live website.
