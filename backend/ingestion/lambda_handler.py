"""
AWS Lambda handler for Synapse code ingestion.

Triggered by S3 events (e.g., repo archive uploaded) or direct invocation.
Downloads code from S3, runs the parsing pipeline, and uploads results
(repo_graph.json) back to S3.

Event Sources:
    - S3 PUT event (zip/tar archive uploaded)
    - Direct invocation (manual or API Gateway trigger)

Environment Variables:
    OUTPUT_BUCKET       S3 bucket for results (default: same as input)
    OUTPUT_KEY          S3 key for output (default: repo_graph.json)
"""

import os
import sys
import json
import zipfile
import tarfile
import tempfile
import traceback
from typing import Dict, Any

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda entry point.
    
    Supports two event types:
    1. S3 event: Triggered when a repo archive is uploaded
    2. Direct invocation: {"repo_s3_bucket": "...", "repo_s3_key": "..."}
    """
    print(f"[Lambda] Ingestion handler invoked")
    print(f"[Lambda] Event: {json.dumps(event, default=str)[:500]}")

    try:
        # Parse event to get S3 location
        bucket, key = _parse_event(event)
        print(f"[Lambda] Processing: s3://{bucket}/{key}")

        # Download and extract
        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = os.path.join(tmp_dir, "repo_archive")
            repo_path = os.path.join(tmp_dir, "repo")
            os.makedirs(repo_path, exist_ok=True)

            # Download from S3
            _download_from_s3(bucket, key, archive_path)

            # Extract archive
            _extract_archive(archive_path, repo_path)

            # Run parsing pipeline
            result = _run_ingestion(repo_path)

            # Upload results to S3
            output_bucket = os.getenv("OUTPUT_BUCKET", bucket)
            output_key = os.getenv("OUTPUT_KEY", "repo_graph.json")
            _upload_to_s3(output_bucket, output_key, result)

            return {
                "statusCode": 200,
                "body": {
                    "message": "Ingestion complete",
                    "entities_count": len(result),
                    "output": f"s3://{output_bucket}/{output_key}",
                },
            }

    except Exception as e:
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": {
                "message": f"Ingestion failed: {str(e)}",
                "error": traceback.format_exc(),
            },
        }


def _parse_event(event: Dict) -> tuple:
    """Extract S3 bucket and key from Lambda event."""
    # S3 trigger event
    if "Records" in event:
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        return bucket, key

    # Direct invocation
    if "repo_s3_bucket" in event and "repo_s3_key" in event:
        return event["repo_s3_bucket"], event["repo_s3_key"]

    raise ValueError(
        "Invalid event format. Expected S3 event or "
        "{'repo_s3_bucket': '...', 'repo_s3_key': '...'}"
    )


def _download_from_s3(bucket: str, key: str, local_path: str) -> None:
    """Download a file from S3."""
    import boto3

    s3 = boto3.client("s3")
    print(f"[Lambda] Downloading s3://{bucket}/{key}...")
    s3.download_file(bucket, key, local_path)
    size = os.path.getsize(local_path)
    print(f"[Lambda] Downloaded {size / 1024:.1f} KB")


def _extract_archive(archive_path: str, extract_to: str) -> None:
    """Extract a zip or tar archive."""
    print(f"[Lambda] Extracting archive...")

    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_to)
            print(f"[Lambda] Extracted {len(zf.namelist())} files (zip)")

    elif tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(extract_to)
            print(f"[Lambda] Extracted {len(tf.getnames())} files (tar)")

    else:
        # Assume it's a single file or a directory dump
        print("[Lambda] Not an archive, treating as raw content")


def _run_ingestion(repo_path: str) -> list:
    """
    Run the Synapse parsing pipeline on the extracted repo.
    
    Returns a list of entity dicts (the repo_graph.json content).
    """
    from backend.parsing import scan_repository, get_all_entities

    print(f"[Lambda] Scanning repository at: {repo_path}")

    # Find the actual repo root (archives sometimes have a top-level dir)
    entries = os.listdir(repo_path)
    if len(entries) == 1 and os.path.isdir(os.path.join(repo_path, entries[0])):
        repo_path = os.path.join(repo_path, entries[0])
        print(f"[Lambda] Adjusted repo root: {repo_path}")

    # Parse
    parsed_files = scan_repository(repo_path)
    entities = get_all_entities(parsed_files)

    print(f"[Lambda] Parsed {len(parsed_files)} files, {len(entities)} entities")
    return entities


def _upload_to_s3(bucket: str, key: str, data: list) -> None:
    """Upload parsed results to S3 as JSON."""
    import boto3

    s3 = boto3.client("s3")
    json_data = json.dumps(data, indent=2, default=str)
    size_kb = len(json_data.encode()) / 1024

    print(f"[Lambda] Uploading results to s3://{bucket}/{key} ({size_kb:.1f} KB)...")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json_data.encode("utf-8"),
        ContentType="application/json",
    )
    print(f"[Lambda] Upload complete")


# ─────────────────────────────────────────────
# Local testing support
# ─────────────────────────────────────────────

def local_test(repo_path: str, output_file: str = "repo_graph.json"):
    """Run the ingestion pipeline locally without S3."""
    print(f"[Local] Running ingestion on: {repo_path}")
    
    from backend.parsing import scan_repository, get_all_entities

    parsed_files = scan_repository(repo_path)
    entities = get_all_entities(parsed_files)

    with open(output_file, "w") as f:
        json.dump(entities, f, indent=2, default=str)

    print(f"[Local] Written {len(entities)} entities to {output_file}")
    return entities


if __name__ == "__main__":
    # Usage: python -m backend.ingestion.lambda_handler ./my_repo
    import sys
    
    repo = sys.argv[1] if len(sys.argv) > 1 else "./dummy_repo"
    output = sys.argv[2] if len(sys.argv) > 2 else "repo_graph.json"
    local_test(repo, output)
