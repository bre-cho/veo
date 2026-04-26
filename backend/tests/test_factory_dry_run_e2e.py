from __future__ import annotations

from app.api.factory import _build_factory_run_detail
from app.factory.factory_publish_control import FactoryPublishControl
from app.state import timeline_service


class _FakeQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


class _FakeDB:
    def query(self, *_args, **_kwargs):
        return _FakeQuery()


def test_factory_dry_run_then_approve_publish() -> None:
    run_id = "factory-run-dry-run"
    timeline_service.repository.upsert_run(
        {
            "id": run_id,
            "title": "Demo Factory Run",
            "render_job_id": None,
            "status": "running",
            "current_stage": "PUBLISH",
            "metadata_json": {},
        }
    )

    detail_before = _build_factory_run_detail(_FakeDB(), timeline_service.repository.get_run(run_id) or {})
    assert detail_before["run"]["publish"]["status"] in {"dry_run", "blocked_pending_approval"}

    FactoryPublishControl().approve(run_id, approved_by="qa")
    detail_after = _build_factory_run_detail(_FakeDB(), timeline_service.repository.get_run(run_id) or {})
    assert detail_after["run"]["metadata_json"]["publish_approved"] is True
