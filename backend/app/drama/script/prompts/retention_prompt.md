# Retention Prompt Reference

Documents the curiosity-loop injection and scoring logic in `retention_engine.py`
and the binge-chain callback logic in `binge_chain_engine.py`.

## Standard retention hooks

Injected at the end of every script:

1. "But that's not even the worst part."
2. "What happened next changed everything."
3. "And this is where things stop making sense."

If the retention score is below threshold (15), an extra hook is appended:

4. "You're not going to believe what happened next."

## Retention scoring heuristics

| Signal                                      | Points |
|---------------------------------------------|--------|
| Ellipsis (`...` or `…`) count × 2 (cap 10) | 0–10   |
| Curiosity phrase present                    | +10    |
| Word count > 800                            | +20    |
| Word count 400–800                          | +10    |

## Binge-chain callback

Injected at position 2 (after hook + first escalation) when `open_loops` is
non-empty.  Source: `open_loops[0]["callback_line"]` or default fallback.

Default line: *"But this was not the first time something like this had happened."*

## Design rule

Retention hooks are never random.  They are drawn from a fixed vocabulary
ranked by psychological effectiveness.  Scoring is deterministic — the same
script always gets the same score.
