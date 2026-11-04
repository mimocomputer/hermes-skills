---
name: used-market-valuation
description: "Use when pricing used gear for sale from listing data."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Pricing, Resale, Listings, Research]
    related_skills: [product-price-monitor, research-execution]
---

# Used-Market Valuation

Answer "what can I realistically charge / what is this worth?" with listing evidence, not a hunch. The deliverable is a **price band**: a recommended start price, the realistic proceeds, a quick-sale floor, and the arguments that justify each end.

## When to Use

- "What could I realistically ask for my X?" / "Is this a fair price for a used Y?"
- Any resale or purchase decision where the user wants market grounding before naming a number.

Not for: watching one listing over time (`product-price-monitor`), or a single "what does it cost new" lookup (`web_search` directly).

## Procedure

1. **Pin the exact model, generation, and configuration.** Confusable siblings dominate used pricing: same family with vs. without a keyboard, USB-only vs. Bluetooth + battery, 20 vs. 40 cells, one generation back. Price the user's exact variant, and say in the answer which variant the band is for.
2. **Establish the new price first.** Dealer/reseller list prices incl. VAT; manufacturer sites frequently hide prices, so use resellers, medical/B2B marketplaces, and specialist shops. A used band is read as a fraction of this, so without it the band is unfounded.
3. **Collect asking prices from several sources, most-specific first:** niche/community boards for the device class, then general classifieds. Record per observation: date, model, condition, accessories, and whether the price was fixed or "VB"/negotiable.
4. **Weight recency and outcome, not the headline number.** Recent beats old. A listing that was cut repeatedly and never marked sold is stronger evidence than any single high asking price. Only an explicit sold/verkauft note is a real sale datum.
5. **Recover expired listings from the Wayback Machine** when the board deletes ads on a rolling window — see `references/archived-classifieds-harvest.md`.
6. **Check for a market shift:** a successor model, a new low-cost competitor, or a change in funding rules depresses the band regardless of the item's own condition.
7. **Report the band and its drivers** (format below), with the observation window and the sources named.

## Pitfalls

- **Asking prices are not achieved prices.** Say so explicitly in the answer; the whole band is inference unless a sale is documented.
- **A single correct-spelling grep silently truncates the sample.** Run a second, looser keyword pass over the harvested text — brands get misspelled or abbreviated by sellers (Papenmeier: "Papenmaier", "Pappenmayer"; Braillex: "Brailex", "Brailley").
- **Do not price by brand line.** Within one product family the configuration (input keyboard, Bluetooth, battery, cell count) moves the price more than the brand does.
- **Job-lot ads mislead.** A device price buried in a household-clearance list ("1 Braillezeile 40 Zeichen für 800 €") is a filler number, not a considered asking price; note it as an outlier or drop it.
- **Small buyer pool.** Assistive tech and other niche gear can sit for months with 50–70 % price cuts. A defensible asking price is not a promise of a fast sale — give the quick-sale floor separately.
- **Ownership/funding caveat (DE).** Devices financed by a Kostenträger (Krankenkasse, Rentenversicherung) may not be the user's to sell. Ask, or have the user confirm, before pricing; private listings routinely state "mein Eigentum, nicht kassenfinanziert".
- **Do not average across eras.** Pooling asking prices from twenty years apart produces a meaningless mean; weight by recency and present the recent cluster.

## Reporting Format

Structure the answer as short labeled blocks, in the user's language:

1. **Source and scope** — which sources, how many records, what window, and the honest limit (asking prices, sales usually unconfirmed).
2. **Evidence** — dated observations grouped by device class/era, most relevant first.
3. **Current market** — the freshest independent data points (other platforms, competing models).
4. **Band** — recommended start price (VB), realistic proceeds, quick-sale floor.
5. **What raises / what lowers** the price, and **channels** to sell through.

Close with the caveats that actually apply (funding/ownership, warranty transfer, successor model).

## References

- `references/archived-classifieds-harvest.md` — bulk-harvest expired listings from the Wayback Machine (CDX index, raw snapshots, throttling retries, record extraction).
- `references/blindenhilfsmittel-market-de.md` — German second-hand market for Braille displays / blind assistive tech: channels, model traps, price bands.
