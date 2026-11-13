# AUTORED IDEA core

Provider-neutral, deterministic workflow primitives for the AUTORED IDEA project.

## Scope

This package currently implements:
- the three target profile identities;
- content package validation;
- deterministic publication idempotency keys;
- guarded publication-job state transitions;
- monthly quota reservation;
- conservative retry classification;
- fresh-source requirements for research profiles (72-hour window, independent domains and explicit fact-check reference);
- structured fact-check reports with direct evidence mapping, source allowlists and deterministic report hashes;
- a compliance-gated Publora pipeline for exact profile matching, draft creation, media upload and scheduled delivery.

It deliberately does **not** autonomously decide whether a factual claim is true. The fact-check report validator verifies evidence structure, freshness, allowlisted domains and explicit reviewer decisions; semantic correctness still requires a competent review step. The Publora client is tested against mocks but requires a secret API key and live account preflight before any real post can be scheduled. Credentials are never stored in this repository.

## Run tests

```bash
python -m unittest discover -s tests -v
```

No third-party Python packages are required for the core module.
