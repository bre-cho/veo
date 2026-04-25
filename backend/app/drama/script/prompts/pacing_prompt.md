# Pacing Prompt Reference

Documents the duration assignment rules used by `pacing_engine.py`.

## Per-purpose duration table

| Purpose      | Duration (sec) |
|--------------|---------------|
| hook         | 3.0           |
| reveal       | 5.0           |
| twist        | 5.0           |
| cliffhanger  | 4.0           |
| escalation   | 4.0           |
| callback     | 4.0           |
| setup        | 3.5           |
| context      | 3.5           |
| default      | 4.0           |

## Multi-scene episode pacing

In the `NextLevelScriptEngine`, durations are derived from:

```
avg_scene_sec = (target_duration_min × 60) ÷ scene_count
```

The binge-callback segment is hard-coded to 8 seconds to give the audience
time to recognize the reference before the narrative moves on.

## Design rule

Pacing is always purpose-driven.  The engine never assigns random durations.
Shorter segments (hook, setup) keep the opening fast.  Longer reveal/cliffhanger
segments give the audience time to absorb the drama peak.
