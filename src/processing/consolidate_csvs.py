#!/usr/bin/env python3
"""
Consolidates all per-video CSVs into a single master CSV.
Rewritten to use standard 'csv' module to avoid dependencies.
Handles varying headers by using the union of all fieldnames.
"""
import csv
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent.parent
    processed_dir = base_dir / "data" / "processed" / "extracted_metadata"
    output_file = base_dir / "data" / "processed" / "extracted_metadata" / "all_metadata_with_health.csv"
    
    csv_files = list(processed_dir.rglob("*_with_health.csv"))
    
    if not csv_files:
        print("❌ No '_with_health.csv' files found.")
        return

    print(f"found {len(csv_files)} files to consolidate.")
    
    all_rows = []
    all_fieldnames = set()
    
    # 1. Read all files and collect rows + fieldnames
    for f in csv_files:
        try:
            with open(f, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                if reader.fieldnames:
                    all_fieldnames.update(reader.fieldnames)
                
                rows = list(reader)
                
                # Normalize columns: Ensure 'health_index' exists
                for row in rows:
                    if 'health_index' not in row and 'health_ratio_percent' in row:
                        row['health_index'] = row['health_ratio_percent']
                        
                all_rows.extend(rows)
        except Exception as e:
            print(f"⚠️ Failed to read {f}: {e}")
            
    if all_rows and all_fieldnames:
        # Sort fieldnames for consistency, putting standard ones first
        sorted_fields = sorted(list(all_fieldnames))
        
        # Ensure video_name, timestamp are first if present
        priority_cols = ["video_name", "frame_index", "timestamp", "latitude", "longitude", "health_index"]
        final_fields = [c for c in priority_cols if c in sorted_fields]
        final_fields += [c for c in sorted_fields if c not in priority_cols]
        
        # Create output dir if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=final_fields)
            writer.writeheader()
            writer.writerows(all_rows)
            
        print(f"✅ Consolidated {len(all_rows)} rows to {output_file}")
    else:
        print("⚠️ No data to consolidate.")

if __name__ == "__main__":
    main()
