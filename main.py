#!/usr/bin/env python3
"""
Drone Health Mapping Pipeline - Main Entry Point

Usage:
    python main.py [command] [options]

Commands:
    train           Train the pixelwise health model.
    extract         Extract metadata (GPS, etc.) from SRT files.
    sync            Sync video frames with metadata and apply health model.
    map-flight      Generate the basic flight trajectory map.
    map-analytical  Generate the analytical health heatmap.
    web             Start the web server for real-time flight visualization.
    pipeline        Run the full pipeline (Extract -> Sync -> Maps). (Model assumed trained)
"""

import argparse
import sys
import subprocess
from pathlib import Path
import importlib.util

# Define paths to scripts
PROJECT_ROOT = Path(__file__).parent.resolve()
SCRIPTS = {
    "train": PROJECT_ROOT / "src" / "models" / "train_model.py",
    "extract": PROJECT_ROOT / "src" / "ingestion" / "extract_metadata.py",
    "sync": PROJECT_ROOT / "src" / "processing" / "sync_video_csv.py",
    "consolidate": PROJECT_ROOT / "src" / "processing" / "consolidate_csvs.py",
    "map-flight": PROJECT_ROOT / "src" / "visualization" / "flight_map.py",
    "map-analytical": PROJECT_ROOT / "src" / "visualization" / "analytical_map.py",
    "web": PROJECT_ROOT / "src" / "web" / "server.py",
}

def run_script(script_name, args=None):
    script_path = SCRIPTS.get(script_name)
    if not script_path or not script_path.exists():
        print(f"❌ Script not found: {script_name} ({script_path})")
        return False
    
    print(f"\n{'='*60}")
    print(f"🚀 Running: {script_name}")
    print(f"{'='*60}\n")
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
        
    try:
        subprocess.check_call(cmd)
        print(f"\n✅ {script_name} finished successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {script_name} failed with exit code {e.returncode}.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Drone Health Mapping Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Subparsers for each command
    subparsers.add_parser("train", help="Train the pixelwise model")
    subparsers.add_parser("extract", help="Extract metadata from SRTs")
    subparsers.add_parser("sync", help="Apply health model to video frames")
    subparsers.add_parser("consolidate", help="Consolidate all CSVs into one")
    subparsers.add_parser("map-flight", help="Generate flight trajectory map")
    subparsers.add_parser("map-analytical", help="Generate analytical health map")
    subparsers.add_parser("web", help="Start the web server for real-time visualization")
    subparsers.add_parser("pipeline", help="Run extract -> sync -> maps sequence")

    args, unknown_args = parser.parse_known_args()
    
    if args.command is None:
        parser.print_help()
        return

    if args.command == "pipeline":
        # Run sequence
        steps = ["extract", "sync", "consolidate", "map-flight", "map-analytical"]
        for step in steps:
            success = run_script(step, unknown_args)
            if not success:
                print(f"\n⛔ Pipeline stopped due to error in {step}.")
                sys.exit(1)
        print("\n🎉 Full pipeline completed successfully!")
    elif args.command == "web":
        # Run web server (long-running process)
        success = run_script("web", unknown_args)
        if not success:
            sys.exit(1)
    else:
        # Run single command
        success = run_script(args.command, unknown_args)
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()
