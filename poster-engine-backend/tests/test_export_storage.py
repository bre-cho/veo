from pathlib import Path

from apps.api.core.config import settings
from packages.export_engine.exporter import export_variant_pack


def test_export_variant_pack_local_storage(tmp_path: Path):
    settings.storage_provider = "local"
    settings.storage_dir = str(tmp_path)

    result = export_variant_pack(
        str(tmp_path),
        {
            "id": "var_1",
            "brand_id": "brand_1",
            "project_id": "proj_1",
            "provider": "adobe+canva",
            "canva_design_id": "canva_1",
            "adobe_asset_id": "adobe_1",
        },
    )

    manifest = result["manifest"]
    assert manifest["variant_id"] == "var_1"
    assert len(manifest["assets"]) == 3
    assert all(asset["signed_url"].startswith("file://") for asset in manifest["assets"])
    assert all(asset["checksum"] for asset in manifest["assets"])
