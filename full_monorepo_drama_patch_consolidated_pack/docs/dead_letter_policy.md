# Drama Engine Dead Letter Policy

## Purpose
This policy defines how failed drama jobs are quarantined when automatic retry is no longer safe.

## When a job must go to dead letter
A job must be moved to dead letter when any of the following is true:
- maximum retry count has been exhausted
- payload is structurally invalid and cannot be normalized safely
- required upstream state is missing for more than the retry window
- persistence fails because of repeated integrity conflicts that indicate state corruption
- continuity rebuild produces contradictory downstream state on repeated attempts

## Dead letter payload requirements
Each dead-letter entry must store:
- job_type
- scene_id / episode_id / project_id when available
- original payload
- error_class
- error_message
- retry_count
- first_failure_at
- last_failure_at
- worker_name
- suggested_action

## Suggested action categories
- `requeue_safe`: can be replayed after upstream dependency is fixed
- `manual_review`: human must inspect payload or state graph
- `drop_invalid`: payload should not be replayed
- `repair_then_rebuild`: run state repair before replay

## Routing guidance
- Scene analysis failures with transient DB/queue/network causes -> retry first, dead-letter only after retry ceiling
- Data contract mismatches -> dead letter immediately with `drop_invalid`
- Continuity drift conflicts -> dead letter with `repair_then_rebuild`
- Arc update inconsistencies -> dead letter with `manual_review`

## Operational SLA
- Critical story pipeline jobs: review within 30 minutes
- Non-blocking recompute jobs: review within 4 hours
- Bulk rebuild jobs: review next business cycle
