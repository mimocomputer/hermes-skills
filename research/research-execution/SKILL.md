---
name: research-execution
description: "Use for live research; disclose provenance and fallbacks."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Research Execution

Use this skill for live web research, source verification, provider comparisons, and any task where the path used to obtain information matters to the user.

## Core principle

A successful final answer does not erase failed or substituted research steps. The user needs to know which system actually supplied the evidence, especially when the configured backend, billing path, source controls, privacy properties, or output quality may differ.

## Workflow

1. **Identify the intended research path.** Before relying on it, distinguish between model-native search, Hermes `web_search`/`web_extract`, browser automation, direct HTTP retrieval, and local data.
2. **Exercise the real path.** A configuration value or advertised tool is not proof that the backend works. Run one minimal search and, where relevant, one extraction/read operation.
3. **Record provenance while working.** Keep enough evidence to state which tool and backend succeeded, including direct sources used for material claims.
4. **Diagnose a failed primary path once.** Read the exact error and inspect the relevant live configuration/state. Do not silently repeat a failing call.
5. **Fallback only when appropriate.** Use another available path to complete the user’s task when safe, but preserve the distinction between the requested/configured route and the route actually used.
6. **Report both outcome and path.** If the primary tool fails or a material fallback is used, explicitly state:
   - what failed and the concise error/cause;
   - what alternative was used;
   - whether the final result is still live and source-grounded;
   - any material implications (cost, access scope, source coverage, or limitations).
7. **Repair and verify when asked.** After a configuration or plugin fix, repeat the exact operations that had failed. Do not infer success from a restart, a status command, or a successful unrelated tool.

## Reporting standard

Use direct language. Example:

> The configured web-search backend failed because its provider plugin was disabled. I completed the research through browser automation instead; the result is live-source-based, but it did not use the configured gateway. I have not changed the configuration unless stated.

Do not say that a managed tool, model-native capability, or billing route was used unless a successful real invocation establishes it.

## Escalation and issue reports

When a configuration migration or update leaves a configured capability unavailable:

1. Preserve the minimal reproduction: effective configuration, plugin/provider state, exact failure, version, and a verified workaround.
2. Search the upstream issue tracker before creating a new issue.
3. File a focused bug report for the broken invariant; avoid including secrets, account tokens, or unrelated failures.
4. For an already-tracked feature, add concrete current-version evidence instead of creating a duplicate issue.
5. Verify publication and permissions separately: creating an issue does not imply permission to apply labels or manage upstream triage.

## Pitfalls

- **Silent fallback:** Never present browser-based research as successful use of a configured web provider.
- **Config-as-proof:** `backend: ...` does not establish that a matching plugin, credential, or gateway route is active.
- **Success-only reporting:** A good answer obtained through a fallback still needs path disclosure.
- **Overclaiming billing:** API-model pricing, subscription plans, and managed tool gateways may be separate; verify the actual routing before comparing costs.
- **Duplicate upstream issues:** Search and contribute to an existing issue when it already covers the requested capability.

## Reference

See `references/research-path-verification.md` for a concise diagnostic and verification checklist.
