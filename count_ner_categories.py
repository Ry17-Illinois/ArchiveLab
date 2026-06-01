#!/usr/bin/env python3
"""
Count NER Categories from JSON Files
Generates a CSV with entity type counts from specified page JSON files
"""

import json
import csv
import sys
from pathlib import Path
from collections import defaultdict


def count_ner_from_files(json_files, output_csv='ner_category_counts.csv'):
    """
    Count NER entities from a list of JSON files
    
    Args:
        json_files: List of paths to JSON files
        output_csv: Output CSV filename
    
    Returns:
        Dictionary with entity counts
    """
    
    # Track counts for each entity name
    entity_counts = defaultdict(int)
    entity_types = {}  # Map entity name to its type
    
    # Track per-file statistics
    files_processed = 0
    files_with_entities = 0
    total_entities = 0
    
    print(f"Processing {len(json_files)} files...")
    
    for json_file in json_files:
        json_path = Path(json_file)
        
        if not json_path.exists():
            print(f"Warning: File not found - {json_file}")
            continue
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            files_processed += 1
            
            # Extract entities from named_entities section
            entities = data.get('named_entities', {}).get('entities', {})
            
            if entities:
                files_with_entities += 1
            
            # Count each entity name
            for entity_type, entity_list in entities.items():
                for entity_name in entity_list:
                    if entity_name and entity_name.strip():
                        entity_counts[entity_name] += 1
                        entity_types[entity_name] = entity_type
                        total_entities += 1
            
            if files_processed % 100 == 0:
                print(f"  Processed {files_processed} files...")
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON in {json_file}: {e}")
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    # Generate CSV
    print(f"\nGenerating CSV: {output_csv}")
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Rank', 'Entity Name', 'Entity Type', 'Count', 'Percentage'])
        
        # Sort by count (descending)
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Write data rows
        for rank, (entity_name, count) in enumerate(sorted_entities, 1):
            entity_type = entity_types.get(entity_name, 'UNKNOWN')
            percentage = (count / total_entities * 100) if total_entities > 0 else 0
            writer.writerow([
                rank,
                entity_name,
                entity_type,
                count,
                f"{percentage:.2f}%"
            ])
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files processed: {files_processed}")
    print(f"Files with entities: {files_with_entities}")
    print(f"Total entity mentions: {total_entities}")
    print(f"Unique entities: {len(entity_counts)}")
    print(f"\nTop 10 most frequent entities:")
    for rank, (entity_name, count) in enumerate(sorted_entities[:10], 1):
        entity_type = entity_types.get(entity_name, 'UNKNOWN')
        print(f"  {rank}. {entity_name} ({entity_type}): {count} mentions")
    print(f"\nOutput saved to: {output_csv}")
    print("=" * 60)
    
    return dict(entity_counts)


def main():
    """Command-line interface"""
    
    if len(sys.argv) < 2:
        print("=" * 60)
        print("Count NER Categories from JSON Files")
        print("=" * 60)
        print("\nUsage:")
        print("  python count_ner_categories.py <file1.json> <file2.json> ... [--output <csv>]")
        print("\nOr with wildcard:")
        print("  python count_ner_categories.py path/to/*_Page*.json")
        print("\nArguments:")
        print("  file1.json, file2.json, ... - Paths to JSON files with NER data")
        print("  --output <csv>               - Output CSV filename (default: ner_category_counts.csv)")
        print("\nExamples:")
        print('  python count_ner_categories.py "data/*_Page*.json"')
        print('  python count_ner_categories.py file1.json file2.json --output results.csv')
        print("\nOutput:")
        print("  CSV with columns: Entity Type, Total Count, Unique Count, Percentage")
        print("=" * 60)
        sys.exit(1)
    
    # Parse arguments
    json_files = []
    output_csv = 'ner_category_counts.csv'
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--output':
            if i + 1 < len(sys.argv):
                output_csv = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --output requires a filename argument")
                sys.exit(1)
        else:
            # Handle wildcards by expanding paths
            from glob import glob
            matches = glob(sys.argv[i])
            if matches:
                json_files.extend(matches)
            else:
                json_files.append(sys.argv[i])
            i += 1
    
    if not json_files:
        print("Error: No JSON files specified")
        sys.exit(1)
    
    try:
        count_ner_from_files(json_files, output_csv)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
