# Athirikya Website

Static GitHub Pages site for Athirikya.

## Domain

Production domain:

```text
athirikya.com
```

The `CNAME` file is configured for the custom domain.

## Pages

- `index.html` — landing page
- `privacy.html` — privacy policy
- `terms.html` — terms of use
- `styles.css` — shared styles

## GitHub Pages Setup

In GitHub:

1. Go to repository **Settings**.
2. Open **Pages**.
3. Set source to deploy from `main` branch, root folder.
4. Confirm custom domain is `athirikya.com`.
5. Enable **Enforce HTTPS** once DNS is verified.

## DNS Notes

For NameCheap, keep existing email DNS records for PrivateEmail.

Add GitHub Pages records for the root domain and `www` only.
