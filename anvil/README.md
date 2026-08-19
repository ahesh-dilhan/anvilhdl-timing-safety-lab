# Official-compiler fixtures

These small, original AnvilHDL programs exercise the paper's three timing
safety checks against the official compiler. They are intentionally separate
from the Python bounded oracle.

| Fixture | Expected | Concept |
| --- | --- | --- |
| `safe/dynamic_memory_client.anvil` | accept | Address remains loaned until a dynamic response event. |
| `safe/fixed_lifetime_spacing.anvil` | accept | Two-cycle promises are separated by two cycles. |
| `unsafe/mutate_while_loaned.anvil` | reject | Address register changes before the response ends its loan. |
| `unsafe/use_after_expiry.anvil` | reject | Response data is used after the next request expires it. |
| `unsafe/overlapping_message_send.anvil` | reject | A second two-cycle promise starts before the first expires. |

Run the manifest through a locally installed compiler:

```bash
ANVIL_BIN=/path/to/anvil make anvil-check
```

The harness uses `-json`, not the README's older `-json-output` spelling, and
reads the JSON `success` field. At the pinned revision a compilation failure in
JSON mode can still return process status 0, so exit status alone is not a valid
oracle. This behavior is recorded rather than hidden by the harness.

The language is experimental. GitHub's integration workflow checks the exact
revision in `UPSTREAM.lock`; a local `ANVIL_BIN` is whatever version the caller
provides. Record that version when comparing results. Acceptance on another
commit is useful drift data, not evidence that either revision is wrong.
