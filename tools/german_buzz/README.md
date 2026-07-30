# German Buzz website generator

`generate_website.py` creates a weekly German Buzz HTML page from the same JSON content used for the mobile app.

It works locally only. It does not commit, push, deploy, or connect to Firestore.

## Files it manages

For an issue such as `2026-W31`, the generator:

- creates `mygermanfreund/german-buzz/kw-31/index.html`;
- adds the issue to `mygermanfreund/german-buzz/index.html`;
- adds the canonical issue URL to `sitemap.xml`.

Existing issue pages are preserved. Replacing an existing issue requires `--force`.

## Recommended workflow

Run validation first:

```powershell
python tools/german_buzz/generate_website.py path\to\2026-W31.json --dry-run
```

Generate the files locally:

```powershell
python tools/german_buzz/generate_website.py path\to\2026-W31.json
```

Then review the changes before committing:

```powershell
git status
git diff -- mygermanfreund/german-buzz sitemap.xml
```

Do not use `--force` unless the already published issue has been reviewed and intentionally needs correction.

## Expected JSON

The canonical format is:

```json
{
  "id": "2026-W31",
  "title": "A concise weekly headline",
  "summary": "A short introduction for the web issue and search metadata.",
  "start_date": "2026-07-27",
  "end_date": "2026-08-02",
  "topics": [
    {
      "eyebrow": "German topic label",
      "title": "English topic heading",
      "context": "Why this may come up in everyday conversations.",
      "explanation": "Simple German explanation of the topic.",
      "sentence": "A practical German sentence for conversation."
    }
  ]
}
```

`start_date` and `end_date` are optional. When omitted, the ISO calendar week in `id` is used.

For compatibility with existing mobile JSON, the generator also accepts common aliases such as `issue_id`, `issueId`, `headline`, `description`, `german_title`, `english_title`, `english_context`, `german_explanation`, and `conversation_sentence`.

## Safety checks

The command fails without writing files when:

- the issue id is not in `YYYY-W##` format;
- required content is missing;
- `topics` is empty or malformed;
- the website landing page or sitemap is missing;
- the weekly page already exists and `--force` was not supplied;
- the landing page structure cannot be located safely.
