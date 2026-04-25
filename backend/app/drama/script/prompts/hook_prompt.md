# Hook Prompt Reference

This file documents the psychological hook strategies used by `hook_engine.py`.

| Strategy         | Trigger condition                      | Template text                                                       |
|------------------|----------------------------------------|---------------------------------------------------------------------|
| delayed_reveal   | outcome_type == "betrayal"             | "It already happened… you just didn't notice."                      |
| time_pressure    | tension_score > 85                     | "By the time they realized what was happening… it was already too late." |
| invisible_threat | hidden_conflict present                | "Everything looked normal… until you realize it was never normal at all." |
| question_loop    | outcome_type in revelation/confrontation | "Why would someone do that? The answer changes everything."       |
| escalation_tease | tension_score > 60                     | "What started as nothing… was about to become everything."         |
| normal_to_abnormal | default                              | "Everything looked normal… until it wasn't."                        |

## Design rule

The hook engine NEVER picks a template randomly.  It always routes through
`decision_engine.select_hook_strategy()` which maps drama state → strategy →
template.  This ensures the hook is psychologically consistent with the scene.
