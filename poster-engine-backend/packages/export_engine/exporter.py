import json
from pathlib import Path

from packages.export_engine.storage import file_sha256, upload_file_to_storage

EXPORT_SIZES = {
    "poster_4x5": "1080x1350",
    "square_1x1": "1080x1080",
    "story_9x16": "1080x1920",
}

def export_variant_pack(storage_dir: str, variant: dict) -> dict:
    path = Path(storage_dir) / "exports" / variant["id"]
    path.mkdir(parents=True, exist_ok=True)

    assets = []
    for name, size in EXPORT_SIZES.items():
        local_file = path / f"{name}.txt"
        local_file.write_text(
            f"placeholder export for {variant['id']} size={size}\n",
            encoding="utf-8",
        )
        checksum = file_sha256(local_file)
        storage_key = (
            f"brands/{variant.get('brand_id', 'unknown')}/"
            f"projects/{variant['project_id']}/variants/{variant['id']}/{name}.txt"
        )
        upload_result = upload_file_to_storage(local_file, storage_key, content_type="text/plain")
        assets.append(
            {
                "name": local_file.name,
                "size": size,
                "status": "ready",
                "mime_type": "text/plain",
                "checksum": checksum,
                "storage_key": upload_result["storage_key"],
                "signed_url": upload_result["signed_url"],
                "provider": upload_result["provider"],
            }
        )

    manifest = {
        "variant_id": variant["id"],
        "sizes": EXPORT_SIZES,
        "assets": assets,
        "source_job_id": variant.get("source_job_id"),
        "provider": variant.get("provider"),
        "replayable_input": {
            "canva_design_id": variant.get("canva_design_id"),
            "adobe_asset_id": variant.get("adobe_asset_id"),
        },
    }
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"export_dir": str(path), "manifest": manifest}
