#!/usr/bin/env python3
"""
Adds a dummy vegetation health index (0–100%) to the consolidated CSV.
The index is generated in a controlled way for demonstration purposes.
"""

import csv
import random
import math
from pathlib import Path
from statistics import mean


def generate_health_index(latitude, longitude, relative_altitude, frame_index, video_name):
    """
    Generates a dummy health index (0–100%) based on spatial patterns.
    Uses latitude/longitude to create zones with different health levels.
    """
    # Seed based on position to ensure consistency
    seed = int(abs(latitude * 10000) + abs(longitude * 10000))
    random.seed(seed)
    
    # Creates spatial patterns (central area healthier, edges less healthy)
    # Approximate center of the flight area (adjust if needed)
    center_lat = 50.329
    center_lon = 11.939
    
    # Distance from the center
    lat_diff = abs(latitude - center_lat)
    lon_diff = abs(longitude - center_lon)
    distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000  # approx in meters
    
    # Base health: decreases with distance from the center
    base_health = 85.0 - (distance / 50.0)  # Max ~85% at center, decreases outward
    
    # Controlled random variation
    variation = random.gauss(0, 8)  # gaussian variation
    
    # Effect of altitude (higher altitude = better lighting = potentially healthier)
    altitude_bonus = 0
    if relative_altitude:
        altitude_bonus = min(5.0, (relative_altitude - 1.5) * 2.0)
    
    # Final calculation
    health = base_health + variation + altitude_bonus
    
    # Clamp to 0–100
    health = max(0.0, min(100.0, health))
    
    return round(health, 2)


def add_health_index_to_csv(input_csv, output_csv):
    """Adds a health_index column to the CSV."""
    rows = []
    
    print(f"📖 Reading: {input_csv}")
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        if not fieldnames:
            print("❌ Error: Empty or invalid CSV")
            return
        
        # Add health_index to fieldnames
        new_fieldnames = list(fieldnames) + ['health_index']
        
        for row in reader:
            try:
                lat = float(row.get('latitude', 0) or 0)
                lon = float(row.get('longitude', 0) or 0)
                rel_alt = None
                if row.get('relative_altitude'):
                    try:
                        rel_alt = float(row.get('relative_altitude'))
                    except (ValueError, TypeError):
                        pass
                
                frame_idx = row.get('frame_index', '0')
                video = row.get('video_name', 'unknown')
                
                # Generate health index
                health = generate_health_index(lat, lon, rel_alt, frame_idx, video)
                row['health_index'] = str(health)
                
                rows.append(row)
                
            except Exception as e:
                print(f"⚠️  Error processing row: {e}")
                continue
    
    print(f"💾 Writing: {output_csv}")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Statistics
    health_values = [float(row['health_index']) for row in rows if row.get('health_index')]
    if health_values:
        print(f"\n✅ Health index added!")
        print(f"   Total records: {len(rows):,}")
        print(f"   Minimum health: {min(health_values):.2f}%")
        print(f"   Maximum health: {max(health_values):.2f}%")
        print(f"   Average health: {mean(health_values):.2f}%")
        print(f"   File saved: {output_csv}")


def main():
    base_dir = Path(__file__).parent
    input_csv = base_dir / "extracted_metadata" / "all_metadata_consolidated.csv"
    output_csv = base_dir / "extracted_metadata" / "all_metadata_with_health.csv"
    
    if not input_csv.exists():
        print(f"❌ File not found: {input_csv}")
        print("   Run extract_srt_metadata.py and create_consolidated_csv.py first")
        return
    
    print("🚀 Adding dummy vegetation health index to the consolidated CSV\n")
    add_health_index_to_csv(input_csv, output_csv)
    print("\n✅ Processing complete!")


if __name__ == '__main__':
    main()
