#!/usr/bin/env python3
"""
Creates a consolidated CSV file combining all extracted metadata.
Useful for global analysis of all flights.
Uses only Python standard libraries (no external dependencies).
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def read_csv_file(csv_path):
    """Reads a CSV file and returns a list of dictionaries."""
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def safe_float(value):
    """Safely converts a value to float."""
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None

def create_consolidated_csv():
    """
    Creates a single CSV file containing all metadata from all videos.
    Adds a 'video_name' column to identify the source.
    """
    base_dir = Path(__file__).parent / 'extracted_metadata'
    
    # Find all metadata CSV files
    csv_files = list(base_dir.glob('*/*_metadata.csv'))
    
    if not csv_files:
        print("⚠️  No CSV file found in extracted_metadata/")
        return
    
    print(f"📁 Found {len(csv_files)} CSV file(s)\n")
    
    all_rows = []
    video_stats = defaultdict(lambda: {'count': 0, 'latitudes': [], 'longitudes': [], 
                                       'altitudes': [], 'timestamps': []})
    
    for csv_file in sorted(csv_files):
        # Extract video name from parent folder
        video_name = csv_file.parent.name
        print(f"🔄 Processing: {video_name}")
        
        try:
            # Load CSV
            rows = read_csv_file(csv_file)
            
            # Add video_name column and collect statistics
            for row in rows:
                row['video_name'] = video_name
                all_rows.append(row)
                
                # Collect statistics
                video_stats[video_name]['count'] += 1
                lat = safe_float(row.get('latitude'))
                lon = safe_float(row.get('longitude'))
                alt = safe_float(row.get('relative_altitude'))
                
                if lat:
                    video_stats[video_name]['latitudes'].append(lat)
                if lon:
                    video_stats[video_name]['longitudes'].append(lon)
                if alt:
                    video_stats[video_name]['altitudes'].append(alt)
                if row.get('timestamp'):
                    video_stats[video_name]['timestamps'].append(row['timestamp'])
            
            print(f"   ✅ {len(rows)} frames added")
            
        except Exception as e:
            print(f"   ❌ Error processing {csv_file}: {str(e)}")
    
    if not all_rows:
        print("\n⚠️  No data was loaded!")
        return
    
    # Define column order (video_name first)
    fieldnames = ['video_name', 'frame_index', 'timestamp', 'latitude', 'longitude',
                  'relative_altitude', 'absolute_altitude', 'iso', 'shutter', 
                  'aperture', 'ev', 'color_mode', 'focal_length', 'color_temperature']
    
    # Sort by video and frame_index
    def sort_key(row):
        video = row.get('video_name', '')
        try:
            frame_idx = int(row.get('frame_index', 0))
        except (ValueError, TypeError):
            frame_idx = 0
        return (video, frame_idx)
    
    all_rows.sort(key=sort_key)
    
    # Save consolidated file
    output_file = base_dir / 'all_metadata_consolidated.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in all_rows:
            # Ensure all columns exist
            output_row = {col: row.get(col, '') for col in fieldnames}
            writer.writerow(output_row)
    
    print(f"\n✅ Consolidated file created: {output_file}")
    print(f"   Total frames: {len(all_rows):,}")
    print(f"   Total videos: {len(video_stats)}")
    
    # Statistics per video
    print("\n📊 Statistics per video:")
    print("-" * 80)
    
    # Gather global statistics
    all_lats = []
    all_lons = []
    all_alts = []
    
    # Create statistics file
    stats_file = base_dir / 'statistics_summary.txt'
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("Consolidated Statistics of Extracted Metadata\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total frames: {len(all_rows):,}\n")
        f.write(f"Total videos: {len(video_stats)}\n\n")
        f.write("Frames per video:\n")
        f.write("-" * 80 + "\n")
        
        for video in sorted(video_stats.keys()):
            stats = video_stats[video]
            count = stats['count']
            f.write(f"{video}: {count:,} frames\n")
            print(f"{video}: {count:,} frames")
            
            # Collect global data
            all_lats.extend(stats['latitudes'])
            all_lons.extend(stats['longitudes'])
            all_alts.extend(stats['altitudes'])
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("\nDetailed Statistics per Video:\n")
        f.write("-" * 80 + "\n")
        
        for video in sorted(video_stats.keys()):
            stats = video_stats[video]
            f.write(f"\n{video}:\n")
            f.write(f"  Frames: {stats['count']}\n")
            
            if stats['latitudes']:
                f.write(f"  Latitude: {min(stats['latitudes']):.6f} to {max(stats['latitudes']):.6f}\n")
            if stats['longitudes']:
                f.write(f"  Longitude: {min(stats['longitudes']):.6f} to {max(stats['longitudes']):.6f}\n")
            if stats['altitudes']:
                avg_alt = sum(stats['altitudes']) / len(stats['altitudes'])
                f.write(f"  Relative Altitude: {min(stats['altitudes']):.2f} to {max(stats['altitudes']):.2f} m (avg: {avg_alt:.2f} m)\n")
            if stats['timestamps']:
                f.write(f"  First timestamp: {min(stats['timestamps'])}\n")
                f.write(f"  Last timestamp: {max(stats['timestamps'])}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("\nGlobal Statistics:\n")
        f.write("-" * 80 + "\n")
        
        if all_lats:
            f.write(f"Minimum latitude: {min(all_lats):.6f}\n")
            f.write(f"Maximum latitude: {max(all_lats):.6f}\n")
        if all_lons:
            f.write(f"Minimum longitude: {min(all_lons):.6f}\n")
            f.write(f"Maximum longitude: {max(all_lons):.6f}\n")
        if all_alts:
            avg_alt_global = sum(all_alts) / len(all_alts)
            f.write(f"\nRelative Altitude:\n")
            f.write(f"  Minimum: {min(all_alts):.2f} m\n")
            f.write(f"  Maximum: {max(all_alts):.2f} m\n")
            f.write(f"  Average: {avg_alt_global:.2f} m\n")
    
    print(f"\n✅ Statistics saved to: {stats_file}")
    print("\n" + "=" * 80)
    print("✅ Processing complete!")

if __name__ == '__main__':
    print("🚀 Creating consolidated CSV from all metadata\n")
    create_consolidated_csv()
