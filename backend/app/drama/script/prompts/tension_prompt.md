# Tension Prompt Reference

Documents the tension-driven narrative structure used by `multi_scene_engine.py`
and the `NextLevelScriptEngine` orchestrator.

## Tension curve → beat sequence (single-scene)

| Tension score | Beat sequence                            |
|---------------|------------------------------------------|
| > 80          | hook → escalation → reveal → cliffhanger |
| > 60          | hook → escalation → reveal → escalation  |
| > 40          | hook → setup → reveal → context          |
| ≤ 40          | setup → context → reveal                 |

## Scene purpose assignment (multi-scene)

| Scene index             | Purpose      |
|-------------------------|--------------|
| 0                       | hook         |
| last                    | cliffhanger  |
| index divisible by 3    | reveal       |
| all others              | escalation   |

## Design rule

Tension is never used to pick a sentence directly.  It flows through
`decision_engine.select_story_strategy()` → purpose assignment → scene line
generation.  This keeps tension data driving structure rather than word choice.
