# Research-path verification checklist

Use this as a compact preflight and post-fix checklist.

## Before research

- State the intended path: native model search, Hermes web provider, browser, direct fetch, or local data.
- Confirm the selected backend is available, not merely configured.
- For provider/billing questions, distinguish API billing, subscription-backed access, and managed gateways.

## If the primary path errors

- Preserve the exact error once.
- Inspect the effective backend and the provider/plugin state.
- If a fallback is used, name it in the final response and describe any material difference.
- Do not say a configured service was used solely because it appears in configuration.

## After a repair

- Verify the provider/plugin is active.
- Run the same minimal operation that failed, not just a status check.
- For a web backend, test both search and extraction if both are promised.
- State the successful evidence and avoid conflating unrelated browser success with provider recovery.

## Upstream reports

Include: version, minimal effective configuration (redacted), exact error, reproduction steps, expected invariant, and tested workaround. Search for a matching open issue first; add evidence to it rather than filing a duplicate.
