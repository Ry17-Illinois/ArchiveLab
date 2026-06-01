#!/usr/bin/env python3
"""
Generate SQL import script from editathon_dataset.json
No database connection needed - just creates a .sql file
"""

import json
import sys


def escape_sql_string(s):
    """Escape string for SQL"""
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''").replace("\\", "\\\\") + "'"


def generate_sql(dataset_file, output_file='import_data.sql'):
    """Generate SQL INSERT statements from JSON"""
    
    with open(dataset_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("-- Editathon Data Import\n")
        out.write("-- Generated from editathon_dataset.json\n")
        out.write("-- Run this in phpPgAdmin SQL tab\n\n")
        
        out.write("BEGIN;\n\n")
        
        print(f"Generating SQL for {len(dataset['pages'])} pages...")
        
        for i, page in enumerate(dataset['pages']):
            # Insert page
            dublin_core = json.dumps(page.get('metadata', {}).get('dublin_core', {}))
            archival_context = json.dumps(page.get('metadata', {}).get('archival_context', {}))
            page_id = page['page_id']
            image_path = f'images/{page_id}.jpg'
            
            out.write(f"-- Page {page['page_number']}\n")
            out.write(f"INSERT INTO pages (page_id, page_number, json_file, image_path, document_filename, dublin_core, archival_context)\n")
            out.write(f"VALUES ({escape_sql_string(page_id)}, {page['page_number']}, ")
            out.write(f"{escape_sql_string(page.get('json_file'))}, ")
            out.write(f"{escape_sql_string(image_path)}, ")
            out.write(f"{escape_sql_string(dataset['document']['filename'])}, ")
            out.write(f"{escape_sql_string(dublin_core)}, ")
            out.write(f"{escape_sql_string(archival_context)})\n")
            out.write(f"ON CONFLICT (page_id) DO NOTHING;\n\n")
            
            # Insert OCR versions
            for engine_name, ocr_text in page.get('ocr_versions', {}).items():
                out.write(f"INSERT INTO ocr_versions (page_id, engine_name, ocr_text)\n")
                out.write(f"VALUES ({escape_sql_string(page_id)}, {escape_sql_string(engine_name)}, {escape_sql_string(ocr_text)})\n")
                out.write(f"ON CONFLICT (page_id, engine_name) DO NOTHING;\n\n")
            
            # Insert entities
            for entity_type, entity_list in page.get('entities', {}).items():
                for entity_name in entity_list:
                    if entity_name and str(entity_name).strip():
                        out.write(f"INSERT INTO entities (page_id, entity_type, entity_name)\n")
                        out.write(f"VALUES ({escape_sql_string(page_id)}, {escape_sql_string(entity_type)}, {escape_sql_string(entity_name)});\n\n")
            
            if (i + 1) % 50 == 0:
                print(f"  Generated SQL for {i + 1} pages...")
        
        out.write("COMMIT;\n")
    
    print(f"\n[OK] Generated {output_file}")
    print(f"  - {len(dataset['pages'])} pages")
    print(f"\nNext steps:")
    print(f"  1. Upload {output_file} to your server")
    print(f"  2. In phpPgAdmin, go to SQL tab")
    print(f"  3. Click 'Choose File' and select {output_file}")
    print(f"  4. Click 'Execute'")
    print(f"  5. Wait for import to complete (may take a few minutes)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_import_sql.py <dataset.json>")
        print("\nExample:")
        print("  python generate_import_sql.py data/editathon_dataset.json")
        print("\nThis creates import_data.sql that you can run in phpPgAdmin")
        sys.exit(1)
    
    dataset_file = sys.argv[1]
    generate_sql(dataset_file)


if __name__ == "__main__":
    main()
