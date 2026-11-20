"""File and metadata validation rules for a dataset delivery."""

import csv
import hashlib
import json
from pathlib import Path


def _load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _get_manifest_items(manifest):
    """Support both {'items': ...} and image-id keyed manifest formats."""
    if isinstance(manifest, list):
        return manifest

    if not isinstance(manifest, dict):
        return []

    if "items" in manifest:
        items = manifest["items"]
        if isinstance(items, dict):
            return list(items.values())
        if isinstance(items, list):
            return items
        return []

    # The observed manifest format may be keyed directly by image ID.
    return [
        value
        for value in manifest.values()
        if isinstance(value, dict) and "image" in value
    ]


def _get_metadata_items(metadata):
    if isinstance(metadata, list):
        return metadata

    if not isinstance(metadata, dict):
        return []

    items = metadata.get("items", [])
    if isinstance(items, dict):
        return list(items.values())
    if isinstance(items, list):
        return items
    return []


def _image_target(image_path):
    """Return image basename without extension."""
    return Path(str(image_path)).stem


def _safe_delivery_path(delivery, relative_path):
    """Resolve a manifest path while preventing access outside delivery/."""
    if not relative_path:
        return None

    root = Path(delivery).resolve()
    candidate = (root / str(relative_path)).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        return None

    return candidate


def _sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _load_jobs(jobs_path):
    jobs = {}

    with jobs_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            job_id = row.get("job_id")
            if job_id:
                jobs[job_id.strip()] = row

    return jobs


def find_errors(delivery):
    """
    Check:
      1. missing_image
      2. wrong_hash
      3. scene_leak
      4. guideline_mismatch

    Args:
        delivery: pathlib.Path or path to the delivery directory.

    Returns:
        A list of dictionaries containing 'type' and 'target'.
    """
    delivery = Path(delivery)

    manifest_path = delivery / "manifest.json"
    metadata_path = delivery / "metadata.json"
    jobs_path = delivery / "jobs.csv"

    manifest = _load_json(manifest_path)
    metadata = _load_json(metadata_path)
    jobs = _load_jobs(jobs_path)

    errors = set()

    # ---------------------------------------------------------
    # 1. File checks: missing image and SHA-256 mismatch
    # ---------------------------------------------------------
    manifest_items = _get_manifest_items(manifest)

    hash_fields = (
        ("image", "image_sha256"),
        ("label", "label_sha256"),
        ("mask", "mask_sha256"),
    )

    for item in manifest_items:
        if not isinstance(item, dict):
            continue

        image_path = item.get("image")
        if not image_path:
            continue

        target = _image_target(image_path)

        # Check whether the image file exists.
        image_file = _safe_delivery_path(delivery, image_path)

        if image_file is None or not image_file.is_file():
            errors.add(("missing_image", target))

        # Check hashes for every declared asset whose file exists.
        for path_field, hash_field in hash_fields:
            relative_path = item.get(path_field)
            expected_hash = item.get(hash_field)

            if not relative_path or not expected_hash:
                continue

            asset_file = _safe_delivery_path(delivery, relative_path)

            # Missing non-image assets are outside the missing_image rule.
            if asset_file is None or not asset_file.is_file():
                continue

            actual_hash = _sha256(asset_file)

            if actual_hash.lower() != str(expected_hash).strip().lower():
                errors.add(("wrong_hash", target))

    # ---------------------------------------------------------
    # 2. Metadata checks: scene leakage and guideline mismatch
    # ---------------------------------------------------------
    metadata_items = _get_metadata_items(metadata)

    scene_splits = {}

    for item in metadata_items:
        if not isinstance(item, dict):
            continue

        image_id = str(item.get("image", "")).strip()
        target = _image_target(image_id)

        scene_id = str(item.get("scene_id", "")).strip()
        split = str(item.get("split", "")).strip().lower()

        if scene_id and split:
            scene_splits.setdefault(scene_id, set()).add(split)

        # Compare image metadata guideline with its job guideline.
        job_id = str(item.get("job_id", "")).strip()
        image_guideline = str(item.get("guideline_version", "")).strip()

        job = jobs.get(job_id)

        if job is not None:
            job_guideline = str(job.get("guideline", "")).strip()

            if image_guideline and job_guideline:
                if image_guideline != job_guideline:
                    errors.add(("guideline_mismatch", target))

    # A scene is leaking only when it appears in both train and val.
    for scene_id, splits in scene_splits.items():
        if "train" in splits and "val" in splits:
            errors.add(("scene_leak", scene_id))

    return [
        {"type": error_type, "target": target} for error_type, target in sorted(errors)
    ]
