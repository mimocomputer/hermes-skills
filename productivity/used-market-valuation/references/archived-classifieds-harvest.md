# Harvesting Expired Classifieds from the Wayback Machine

Use when a board deletes ads on a rolling window (community boards often keep ~3 weeks) and the user needs the price history anyway. Worked end to end on a PHP classifieds page with ~110 captures spanning 20 years.

## 1. List every capture

```
curl -s "http://web.archive.org/cdx/search/cdx?url=example.com/page.php*&output=text&fl=timestamp,original&filter=statuscode:200&collapse=digest" > captures.txt
```

- Trailing `*` on the url catches query-string variants (`?PHPSESSID=…` etc.).
- `filter=statuscode:200` drops error captures; `collapse=digest` merges snapshots whose content is byte-identical, which cuts the list sharply without losing distinct content.
- Keep the `original` column — you need it to rebuild the fetch URL.

## 2. Fetch the raw archived page

Insert `id_` after the timestamp to get the page as archived, without the Wayback toolbar/banner:

```
https://web.archive.org/web/<timestamp>id_/<original-url>
```

## 3. Throttling is expected — retry, do not conclude "capture missing"

archive.org starts refusing connections after a burst (`urlopen error [Errno 111] Connection refused`). The capture exists; you are being throttled.

- Sleep ~1–1.5 s between fetches.
- Retry each failed URL up to ~4 times with backoff (3 s, 6 s, 9 s + jitter). Every failure in a 112-capture run resolved on retry.
- Write each page to `<timestamp>.txt` and skip files that already exist, so a re-run resumes instead of refetching.
- Run the whole harvest as a background process with completion notification; a full run takes minutes, not seconds.

## 4. Strip HTML yourself

Drop `<script>/<style>`, turn `<br>` and block-end tags into newlines, unescape entities, collapse runs of whitespace. The archive's own rendered view adds navigation chrome you then have to filter out again.

## 5. Extract records

- Preferred: split the text on the page's repeating record marker (e.g. `Anzeige vom <date>`).
- Fallback when the marker is irregular (dates wrapped in markup, entities inside the timestamp): take a keyword window — for each regex hit grab ±300–700 chars — and dedupe on a normalized prefix of the window. Windows survive markup noise that breaks a strict split, and the same record seen from two keyword hits collapses to one entry.
- Dedupe across captures too: one ad appears in every snapshot taken during its lifetime, so key on normalized text, then list the capture timestamps as provenance.
- Sort by the record's own parsed date, never by capture timestamp or lexicographic string order.

## 6. Report the sample honestly

State how many captures were read, over what window, that ads are self-posted asking prices, and that the board's retention window means the sample is a grid of spot-checks rather than a complete history.
