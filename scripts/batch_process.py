"""
Batch Processor: runs Pipeline A + Pipeline B on all dataset files.
Idempotent and repeatable.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.extract_account_memo import extract_account_memo
from scripts.generate_agent_spec import generate_agent_spec
from scripts.update_agent_from_onboarding import update_agent_from_onboarding
from scripts.utils.storage import sanitize_account_id, list_accounts, get_all_outputs

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_DIR = os.path.join(BASE_DIR, "data", "demo")
ONBOARDING_DIR = os.path.join(BASE_DIR, "data", "onboarding")


def find_transcript_files(directory: str) -> list[str]:
    """Find all transcript files in a directory."""
    if not os.path.exists(directory):
        print(f"  ⚠️ Directory not found: {directory}")
        return []
    
    transcript_extensions = {'.txt', '.md', '.json', '.csv'}
    files = []
    for root, dirs, filenames in os.walk(directory):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in transcript_extensions:
                files.append(os.path.join(root, fname))
    
    return sorted(files)


def infer_account_id_from_path(file_path: str) -> str:
    """Infer an account ID from the file path or directory name."""
    # Try parent directory name first
    parent = os.path.basename(os.path.dirname(file_path))
    if parent not in ("demo", "onboarding", "data"):
        return sanitize_account_id(parent)
    
    # Fall back to filename
    basename = os.path.splitext(os.path.basename(file_path))[0]
    # Remove common prefixes/suffixes
    for prefix in ["demo_", "onboarding_", "transcript_", "call_"]:
        if basename.lower().startswith(prefix):
            basename = basename[len(prefix):]
    return sanitize_account_id(basename)


def match_demo_to_onboarding(demo_files: list[str], onboarding_files: list[str]) -> list[dict]:
    """
    Match demo files to their corresponding onboarding files.
    Returns list of {"demo": path, "onboarding": path, "account_id": str}
    """
    pairs = []
    
    # Build lookup by account ID
    demo_by_id = {}
    for f in demo_files:
        aid = infer_account_id_from_path(f)
        demo_by_id[aid] = f
    
    onboarding_by_id = {}
    for f in onboarding_files:
        aid = infer_account_id_from_path(f)
        onboarding_by_id[aid] = f
    
    # Match them up
    all_ids = set(list(demo_by_id.keys()) + list(onboarding_by_id.keys()))
    
    for aid in sorted(all_ids):
        pair = {
            "account_id": aid,
            "demo": demo_by_id.get(aid),
            "onboarding": onboarding_by_id.get(aid)
        }
        pairs.append(pair)
    
    return pairs


def run_pipeline_a(transcript_path: str, account_id: str) -> bool:
    """Run Pipeline A for a single demo transcript."""
    try:
        memo = extract_account_memo(transcript_path, account_id, source="demo")
        spec = generate_agent_spec(account_id, "v1")
        return True
    except Exception as e:
        print(f"  ❌ Pipeline A failed for {account_id}: {e}")
        return False


def run_pipeline_b(transcript_path: str, account_id: str) -> bool:
    """Run Pipeline B for a single onboarding transcript."""
    try:
        v2_memo, changelog = update_agent_from_onboarding(transcript_path, account_id)
        return True
    except Exception as e:
        print(f"  ❌ Pipeline B failed for {account_id}: {e}")
        return False


def batch_process(validate_only: bool = False):
    """
    Main batch processing function.
    Runs Pipeline A on all demo files, then Pipeline B on all onboarding files.
    """
    start_time = time.time()
    
    print("\n" + "=" * 70)
    print("🚀 Clara Answers - Batch Processing Pipeline")
    print("=" * 70)
    
    # Find all files
    print(f"\n📁 Looking for transcripts...")
    print(f"  Demo directory: {DEMO_DIR}")
    print(f"  Onboarding directory: {ONBOARDING_DIR}")
    
    demo_files = find_transcript_files(DEMO_DIR)
    onboarding_files = find_transcript_files(ONBOARDING_DIR)
    
    print(f"\n  Found {len(demo_files)} demo transcript(s)")
    for f in demo_files:
        print(f"    - {os.path.relpath(f, BASE_DIR)}")
    
    print(f"  Found {len(onboarding_files)} onboarding transcript(s)")
    for f in onboarding_files:
        print(f"    - {os.path.relpath(f, BASE_DIR)}")
    
    if not demo_files and not onboarding_files:
        print("\n⚠️ No transcript files found!")
        print("Place demo transcripts in: data/demo/")
        print("Place onboarding transcripts in: data/onboarding/")
        print("\nFile format: .txt files (chat transcripts, plain text, or Fireflies format)")
        return
    
    # Match pairs
    pairs = match_demo_to_onboarding(demo_files, onboarding_files)
    
    # FILTER: ONLY process the real transcript folder
    # pairs = [p for p in pairs if p["account_id"] == "bens_electric_solutions"]
    
    print(f"\n📋 Account Pairs:")
    for pair in pairs:
        demo_status = "✅" if pair["demo"] else "❌"
        onboarding_status = "✅" if pair["onboarding"] else "❌"
        print(f"  {pair['account_id']}: Demo {demo_status} | Onboarding {onboarding_status}")
    
    if validate_only:
        print("\n🔍 Validation mode - not processing files")
        return
    
    # Run Pipeline A for all demo files
    results = {"pipeline_a": [], "pipeline_b": []}
    
    print(f"\n{'='*70}")
    print("📋 PHASE 1: Pipeline A (Demo → v1 Agent)")
    print(f"{'='*70}")
    
    for pair in pairs:
        if pair["demo"]:
            success = run_pipeline_a(pair["demo"], pair["account_id"])
            results["pipeline_a"].append({
                "account_id": pair["account_id"],
                "success": success
            })
    
    # Run Pipeline B for all onboarding files
    print(f"\n{'='*70}")
    print("🔄 PHASE 2: Pipeline B (Onboarding → v2 Agent)")
    print(f"{'='*70}")
    
    for pair in pairs:
        if pair["onboarding"]:
            success = run_pipeline_b(pair["onboarding"], pair["account_id"])
            results["pipeline_b"].append({
                "account_id": pair["account_id"],
                "success": success
            })
    
    # Summary
    elapsed = time.time() - start_time
    
    print(f"\n{'='*70}")
    print("📊 BATCH PROCESSING SUMMARY")
    print(f"{'='*70}")
    
    a_success = sum(1 for r in results["pipeline_a"] if r["success"])
    a_total = len(results["pipeline_a"])
    b_success = sum(1 for r in results["pipeline_b"] if r["success"])
    b_total = len(results["pipeline_b"])
    
    print(f"  Pipeline A: {a_success}/{a_total} succeeded")
    print(f"  Pipeline B: {b_success}/{b_total} succeeded")
    print(f"  Total time: {elapsed:.1f}s")
    
    # List all outputs
    print(f"\n📦 Generated Outputs:")
    accounts = list_accounts()
    for aid in accounts:
        outputs = get_all_outputs(aid)
        for version in sorted(outputs.keys()):
            files = list(outputs[version].keys())
            print(f"  {aid}/{version}: {', '.join(files)}")
    
    # Save batch summary
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pipeline_a_results": results["pipeline_a"],
        "pipeline_b_results": results["pipeline_b"],
        "total_accounts": len(accounts),
        "elapsed_seconds": round(elapsed, 1)
    }
    summary_path = os.path.join(BASE_DIR, "outputs", "batch_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\n  📋 Batch summary saved to: outputs/batch_summary.json")
    
    # Auto-export dashboard data
    print(f"\n📊 Exporting dashboard data...")
    try:
        from scripts.export_dashboard_data import export_dashboard_data
        export_dashboard_data()
    except Exception as e:
        print(f"  ⚠️ Dashboard export failed (non-critical): {e}")
    
    print(f"\n✅ Batch processing complete!")


def main():
    parser = argparse.ArgumentParser(description="Batch process all demo and onboarding transcripts")
    parser.add_argument("--validate", action="store_true", help="Only validate files without processing")
    args = parser.parse_args()
    
    batch_process(validate_only=args.validate)


if __name__ == "__main__":
    main()
