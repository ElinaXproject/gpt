# AUTORED IDEA core

Provider-neutral, deterministic workflow primitives for the AUTORED IDEA project.

## Scope

This package currently implements:
- the three target profile identities;
- content package validation;
- deterministic publication idempotency keys;
- guarded publication-job state transitions;
- monthly quota reservation;
- conservative retry classification.

It deliberately does **not** publish, call platform APIs, generate AI media, or store credentials. Those are separate adapters and services that must pass their own contract and end-to-end tests before production use.

## Run tests

```bash
python -m unittest discover -s tests -v
```

No third-party Python packages are required for the core module.
