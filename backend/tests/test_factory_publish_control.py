from __future__ import annotations

from app.factory.factory_publish_control import FactoryPublishControl
from app.state import timeline_service


def test_publish_control_approve_sets_metadata() -> None:
    run_id = "factory-run-approve"
    timeline_service.repository.upsert_run({"id": run_id, "metadata_json": {}})

    metadata = FactoryPublishControl().approve(run_id, approved_by="tester")

    assert metadata["publish_approved"] is True
    assert metadata["publish_approved_by"] == "tester"


def test_publish_control_is_approved_reads_flag() -> None:
    run = {"id": "factory-run-check", "metadata_json": {"publish_approved": True}}
    assert FactoryPublishControl().is_approved(run) is True
