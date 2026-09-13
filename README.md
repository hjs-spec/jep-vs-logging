# Structured events and logging

JEP (Judgment Event Protocol) defines signed atomic events and explicit verification results. Logs remain useful evidence. This repository illustrates a local application's structured, hash-linked envelope using only the Python standard library; the runnable demo does not implement JEP-Core-0.6 signatures or conformance.

## Protocol and demonstration boundaries

| Concern | JEP-Core-0.6 or another explicit layer | This local demo |
|---|---|---|
| Event format | Core uses `jep`, `verb`, `who`, `when`, `what`, `nonce`, `sig` and permitted optional members | Illustrative `actor`, `intent`, `delegation`, `authority_scope` fields |
| Cryptographic verification | Core canonicalization and detached JWS under a trusted key | Recomputed SHA-256 only; no authentication |
| Hash links | Core event hash is computed by its specified rules; references/extensions may declare relationships | `event_hash` and `previous_event_hash` are local envelope fields |
| Delegation | `D` statements and explicit application policy; JAC may declare dependencies | Local structured statements, not valid authority proofs |
| Archive lifecycle | HJS defines its own archive, privacy and receipt responsibilities | JSON file with no HJS conformance claim |
| Completeness | Requires a separate trust and evidence model | No independent trusted anchor or completeness guarantee |

Core does not require every event to carry a previous-event hash. JAC does not replace Core canonicalization, and a valid signature does not establish that an event's claim is true. See [jep-v06](https://github.com/hjs-spec/jep-v06), [hjs-05](https://github.com/hjs-spec/hjs-05) and [jac-agent-02](https://github.com/hjs-spec/jac-agent-02) for their respective contracts.

## Run the local illustration

```bash
python3 demo.py
python3 demo.py --verify out/jep_archive.json
```

The script writes ordinary text to `out/audit.log` and local hash envelopes to `out/jep_archive.json`. The filename is retained for compatibility. `verification_state: "verified"` is an old demo marker, not a protocol verification result or signature assurance.

Editing content without updating its stored hash is detected. An author who can rewrite the archive can recompute every hash and pass these local checks; deletion of a tail has no independently trusted completeness check. Accordingly the output says **local hash consistency**, not authenticated Core verification. Existing hashing and archived bytes retain their historical meaning.

For a real signed path, use [jep-quickstart](https://github.com/hjs-spec/jep-quickstart) or [jep-e2e-demo](https://github.com/hjs-spec/jep-e2e-demo). Those examples call a local API and report their actual Core Level 1 scope.
