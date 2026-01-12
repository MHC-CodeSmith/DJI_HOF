#!/usr/bin/env python3
"""
DJI SRT Metadata Extraction
Extracts GPS, camera and timestamp information from DJI Mini 4 Pro .SRT files.
Generates CSV files formatted for QGIS/ArcGIS.
"""

import re
import os
import csv
from pathlib import Path
from typing import Dict, List, Optional

def parse_metadata_line(line: str) -> Dict[str, Optional[str]]:
    """
    Extracts metadata from a line containing [key: value] pairs.
    Returns a dictionary with all extracted fields.
    """
    metadata = {}
    
    # Regex patterns for each field
    patterns = {
        'iso': r'\[iso:\s*(\d+)\]',
        'shutter': r'\[shutter:\s*([^\]]+)\]',
        'fnum': r'\[fnum:\s*([\d.]+)\]',
        'ev': r'\[ev:\s*([-\d]+)\]',
        'color_md': r'\[color_md:\s*([^\]]+)\]',
        'focal_len': r'\[focal_len:\s*([\d.]+)\]',
        'latitude': r'\[latitude:\s*([\d.]+)\]',
        'longitude': r'\[longitude:\s*([\d.]+)\]',
        'rel_alt': r'\[rel_alt:\s*([\d.]+)',
        'abs_alt': r'abs_alt:\s*([\d.]+)\]',
        'ct': r'\[ct:\s*(\d+)\]'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, line)
        if match:
            metadata[key] = match.group(1)
        else:
            metadata[key] = None
    
    return metadata

def extract_frame_info(lines: List[str]) -> Optional[Dict[str, str]]:
    """
    Extracts information from an SRT frame block.
    Returns None if valid data cannot be extracted.
    """
    frame_data = {
        'frame_index': None,
        'timestamp': None,
        'iso': None,
        'shutter': None,
        'aperture': None,
        'ev': None,
        'color_mode': None,
        'focal_length': None,
        'latitude': None,
        'longitude': None,
        'relative_altitude': None,
        'absolute_altitude': None,
        'color_temperature': None
    }
    
    # Search for FrameCnt
    for line in lines:
        frame_match = re.search(r'FrameCnt:\s*(\d+)', line)
        if frame_match:
            frame_data['frame_index'] = frame_match.group(1)
            break
    
    # Search for timestamp (format: YYYY-MM-DD HH:MM:SS.mmm)
    timestamp_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'
    for line in lines:
        ts_match = re.search(timestamp_pattern, line)
        if ts_match:
            frame_data['timestamp'] = ts_match.group(1)
            break
    
    # Search for line containing [key: value] metadata
    metadata_line = None
    for line in lines:
        if '[' in line and ':' in line and ']' in line:
            metadata_line = line
            break
    
    if not metadata_line:
        return None
    
    # Extract metadata
    metadata = parse_metadata_line(metadata_line)
    
    # Map fields
    frame_data['iso'] = metadata.get('iso')
    frame_data['shutter'] = metadata.get('shutter')
    frame_data['aperture'] = metadata.get('fnum')
    frame_data['ev'] = metadata.get('ev')
    frame_data['color_mode'] = metadata.get('color_md')
    frame_data['focal_length'] = metadata.get('focal_len')
    frame_data['latitude'] = metadata.get('latitude')
    frame_data['longitude'] = metadata.get('longitude')
    frame_data['relative_altitude'] = metadata.get('rel_alt')
    frame_data['absolute_altitude'] = metadata.get('abs_alt')
    frame_data['color_temperature'] = metadata.get('ct')
    
    # Validate essential fields
    if frame_data['frame_index'] and frame_data['latitude'] and frame_data['longitude']:
        return frame_data
    
    return None

def parse_srt_file(srt_path: Path) -> List[Dict[str, str]]:
    """
    Parses a full SRT file and returns a list of metadata dictionaries.
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into frame blocks (each block separated by double blank line)
    blocks = re.split(r'\n\s*\n', content)
    
    all_frames = []
    
    for block in blocks:
        if not block.strip():
            continue
        
        lines = block.strip().split('\n')
        frame_data = extract_frame_info(lines)
        
        if frame_data:
            all_frames.append(frame_data)
    
    return all_frames

def write_csv(data: List[Dict[str, str]], output_path: Path):
    """
    Writes extracted data to a CSV formatted for QGIS/ArcGIS.
    """
    if not data:
        print(f"⚠️  No data found to write to {output_path}")
        return
    
    # Sort by frame_index
    data_sorted = sorted(data, key=lambda x: int(x.get('frame_index', 0)))
    
    # Columns in the desired order
    fieldnames = [
        'frame_index',
        'timestamp',
        'latitude',
        'longitude',
        'relative_altitude',
        'absolute_altitude',
        'iso',
        'shutter',
        'aperture',
        'ev',
        'color_mode',
        'focal_length',
        'color_temperature'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for frame in data_sorted:
            # Ensure all fields exist
            row = {field: frame.get(field, '') for field in fieldnames}
            writer.writerow(row)
    
    print(f"✅ CSV created: {output_path} ({len(data_sorted)} frames)")

def process_all_srt_files(base_dir: Path):
    """
    Processes all .SRT files in the directory and creates an organized structure.
    """
    base_dir = Path(base_dir)
    
    # Find all SRT files
    srt_files = list(base_dir.rglob('*.SRT')) + list(base_dir.rglob('*.srt'))
    
    if not srt_files:
        print(f"⚠️  No .SRT files found in {base_dir}")
        return
    
    print(f"📁 Found {len(srt_files)} .SRT file(s)\n")
    
    # Create output folder
    # Create output folder
    # Output to data/processed/extracted_metadata
    # We navigate up from datasets/flights (base_dir) to project root then down to data/processed
    project_root = base_dir.parent.parent
    output_base = project_root / 'data' / 'processed' / 'extracted_metadata'
    output_base.mkdir(parents=True, exist_ok=True)
    
    processed_count = 0
    
    for srt_file in sorted(srt_files):
        print(f"🔄 Processing: {srt_file.name}")
        
        try:
            # Extract base name (without extension)
            base_name = srt_file.stem
            
            # Create folder for this file
            file_output_dir = output_base / base_name
            file_output_dir.mkdir(exist_ok=True)
            
            # Process SRT file
            frames_data = parse_srt_file(srt_file)
            
            if frames_data:
                # Create CSV file
                csv_path = file_output_dir / f'{base_name}_metadata.csv'
                write_csv(frames_data, csv_path)
                
                # Create summary text file
                summary_path = file_output_dir / f'{base_name}_summary.txt'
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"File: {srt_file.name}\n")
                    f.write(f"Total frames extracted: {len(frames_data)}\n")
                    f.write(f"\nFirst 5 frames:\n")
                    f.write("-" * 80 + "\n")
                    
                    for i, frame in enumerate(frames_data[:5], 1):
                        f.write(f"\nFrame {i}:\n")
                        f.write(f"  Frame Index: {frame.get('frame_index')}\n")
                        f.write(f"  Timestamp: {frame.get('timestamp')}\n")
                        f.write(f"  Latitude: {frame.get('latitude')}\n")
                        f.write(f"  Longitude: {frame.get('longitude')}\n")
                        f.write(f"  Relative Altitude: {frame.get('relative_altitude')} m\n")
                        f.write(f"  ISO: {frame.get('iso')}\n")
                        f.write(f"  Focal Length: {frame.get('focal_length')} mm\n")
                
                print(f"   ✅ {len(frames_data)} frames extracted\n")
                processed_count += 1
            else:
                print(f"   ⚠️  No valid frames found\n")
                
        except Exception as e:
            print(f"   ❌ Error processing {srt_file.name}: {str(e)}\n")
    
    print(f"\n{'='*80}")
    print(f"✅ Processing complete!")
    print(f"   {processed_count}/{len(srt_files)} files processed successfully")
    print(f"   Extracted files saved to: {output_base}")
    print(f"{'='*80}")

if __name__ == '__main__':
    import sys

    # Project base directory
    project_dir = Path(__file__).resolve().parent.parent.parent
    
    # Check for arguments
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        if input_path.is_file():
            # Process single file
            print(f"🚀 Starting metadata extraction for file: {input_path.name}\n")
            # We need to adapt the process_all logic or just call it on the parent and filter?
            # Actually, `process_all_srt_files` takes a base_dir and rglobs.
            # Let's write a wrapper or just be smart.
            # If file, we can just process that one file.
            
            # Reusing the existing structure which expects a directory output structure
            # We'll treat the parent dir as the base for output calculation or just use the logic below
            # Ideally we want to output to data/processed...
            
            output_base = project_dir / 'data' / 'processed' / 'extracted_metadata'
            output_base.mkdir(parents=True, exist_ok=True)
            
            base_name = input_path.stem
            file_output_dir = output_base / base_name
            file_output_dir.mkdir(exist_ok=True)
            
            try:
                frames_data = parse_srt_file(input_path)
                if frames_data:
                    csv_path = file_output_dir / f'{base_name}_metadata.csv'
                    write_csv(frames_data, csv_path)
                    print(f"   ✅ Saved to: {csv_path}")
                else:
                    print("   ⚠️  No data found.")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                
        elif input_path.is_dir():
            print(f"🚀 Starting metadata extraction from directory: {input_path}\n")
            process_all_srt_files(input_path)
        else:
            print(f"❌ Invalid path: {input_path}")
    else:
        # Default behavior
        flights_dir = project_dir / "datasets" / "flights"
        print("🚀 Starting metadata extraction from DJI SRT files (Default Folder)\n")
        print(f"📂 Directory: {flights_dir}\n")
        process_all_srt_files(flights_dir)
