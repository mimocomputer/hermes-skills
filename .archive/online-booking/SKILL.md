---
name: online-booking
description: Conduct online reservations safely and verifiably.
version: 0.1.0
author: Julian Dreykorn, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [booking, reservations, browser-use, payments, verification]
    related_skills: []
---

# Online Booking Skill

Make travel, accommodation, event, and similar online reservations through the provider's official booking flow. Use a managed browser for web-only tasks; use desktop control only when the task genuinely requires an already-open native application or a browser UI that Browser Use cannot handle.

## When to Use

- The user asks to find availability, price, or reserve accommodation, transport, campsites, appointments, or tickets.
- The provider has an online booking form.
- Do not use for price monitoring or broad travel research without a reservation flow.

## Prerequisites

- Confirm the provider, dates including year, party size, and requested service class.
- Gather only data that the form marks as required. Do not invent addresses, birth dates, identity data, or consent.
- Use `browser_exec` for the provider's web flow. Load `computer-use` only if an actual native desktop interaction is needed.

## Procedure

1. Open the provider's official booking page with `browser_exec`; verify the domain and identify the booking widget before entering data.
2. Set arrival and departure dates using the widget's own controls. Re-read the selected range on the next page; do not rely only on a client-side field value.
3. Choose the requested accommodation/service and party size. Verify the itemized price, duration, guest count, mandatory add-ons, and cancellation/deposit terms.
4. Tell the user the verified total and material terms before requesting any missing mandatory data.
5. Enter only user-provided contact and traveller data. Preserve the distinction between the booker/rechnungsempfänger and co-travellers.
6. Before accepting terms, triggering a booking request, or reaching payment, obtain explicit confirmation when the form requires agreement to privacy terms, AGB/reservation conditions, deposits, cancellation terms, or a payment obligation.
7. Never enter payment credentials, one-time codes, passwords, or other secrets. Stop at a payment page and let the user complete it, unless a non-secret payment route has already been explicitly authorized.
8. After submission, verify a provider confirmation page or confirmation reference. Report the booking reference, exact dates, total, deposit/payment status, and any required follow-up; do not claim success from a button click alone.

## Pitfalls

- A date-range picker can display an updated range locally while the server-side booking state still uses the previous range. Advance one step and confirm the exact interval shown in the booking summary before selecting guests or continuing.
- Some dynamic calendars require trusted pointer interaction rather than programmatic DOM clicks. Use the booking widget normally, then verify its displayed summary.
- A button labelled "Buchen" may submit a request, reserve inventory, trigger a deposit obligation, or open a payment flow. Treat it as consequential even when it is not labelled "Pay".
- Do not treat the user's general request to book as consent to unreviewed AGB, privacy terms, cancellation conditions, or a newly disclosed deposit. Ask once those material terms are known.

## Verification

A reservation is complete only when all of these are evidenced by the provider:

- Exact selected dates and service
- Correct guest count
- Total price and material payment/deposit terms
- Submitted confirmation or booking/reference number
- Any remaining action, such as payment by a deadline
