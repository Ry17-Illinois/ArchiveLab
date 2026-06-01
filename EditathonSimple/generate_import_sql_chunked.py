#!/usr/bin/env python3
"""
Generate SQL import script in smaller chunks
Easier for phpPgAdmin to handle
"""

import json
import sys
import os


def escape_sql_string(s):
    """Escape string for SQL"""
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''").replace("\\", "\\\\") + "'"


def generate_sql_chunked(dataset_file, chunk_size=50, output_dir='sql_chunks'):
    """Generate SQL INSERT statements in chunks"""
    
    with open(dataset_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    total_pages = len(dataset['pages'])
    num_chunks = (total_pages + chunk_size - 1) // chunk_size
    
    print(f"Generating SQL for {total_pages} pages in {num_chunks} chunks...")
    print(f"Output directory: {output_dir}/")
    print()
    
    for chunk_num in range(num_chunks):
        start_idx = chunk_num * chunk_size
        end_idx = min(start_idx + chunk_size, total_pages)
        chunk_pages = dataset['pages'][start_idx:end_idx]
        
        filename = f"{output_dir}/import_chunk_{chunk_num + 1:02d}_pages_{start_idx + 1}-{end_idx}.sql"
        
        with open(filename, 'w', encoding='utf-8') as out:
            out.write(f"-- Editathon Data Import - Chunk {chunk_num + 1}/{num_chunks}\n")
            out.write(f"-- Pages {start_idx + 1} to {end_idx}\n\n")
            
            out.write("BEGIN;\n\n")
            
            for page in chunk_pages:
                dublin_core = json.dumps(page.get('metadata', {}).get('dublin_core', {}))
                archival_context = json.dumps(page.get('metadata', {}).get('archival_context', {}))
                page_id = page['page_id']
                image_path = f'images/{page_id}.jpg'
                
                # Get document filename - handle both single and multi-document datasets
                if 'document' in dataset:
                    # Single document dataset
                    document_filename = dataset['document']['filename']
                else:
                    # Multi-document dataset - use source_document from page
                    document_filename = page.get('source_document', 'Unknown')
                
                # Insert page
                out.write(f"-- Page {page['page_number']}\n")
                out.write(f"INSERT INTO pages (page_id, page_number, json_file, image_path, document_filename, dublin_core, archival_context)\n")
                out.write(f"VALUES ({escape_sql_string(page_id)}, {page['page_number']}, ")
                out.write(f"{escape_sql_string(page.get('json_file'))}, ")
                out.write(f"{escape_sql_string(image_path)}, ")
                out.write(f"{escape_sql_string(document_filename)}, ")
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
            
            out.write("COMMIT;\n")
        
        print(f"✓ Created {filename}")
    
    # Create a master script that lists all chunks
    with open(f"{output_dir}/README.txt", 'w') as readme:
        readme.write("SQL Import Chunks\n")
        readme.write("=" * 60 + "\n\n")
        readme.write(f"Total pages: {total_pages}\n")
        readme.write(f"Chunks: {num_chunks}\n")
        readme.write(f"Pages per chunk: ~{chunk_size}\n\n")
        readme.write("INSTRUCTIONS:\n")
        readme.write("-" * 60 + "\n\n")
        readme.write("1. Upload all .sql files to your server\n")
        readme.write("2. In phpPgAdmin, go to SQL tab\n")
        readme.write("3. Run each file IN ORDER:\n\n")
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min(start_idx + chunk_size, total_pages)
            readme.write(f"   {i + 1}. import_chunk_{i + 1:02d}_pages_{start_idx + 1}-{end_idx}.sql\n")
        readme.write("\n4. After all chunks complete, verify:\n")
        readme.write("   SELECT COUNT(*) FROM pages;\n")
        readme.write(f"   Should return: {total_pages}\n\n")
        readme.write("5. Restart your Node.js app\n")
    
    print()
    print("=" * 60)
    print(f"✅ Generated {num_chunks} SQL chunk files")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"  1. Upload all files from '{output_dir}/' to your server")
    print("  2. In phpPgAdmin, run each chunk file in order")
    print("  3. Each chunk takes ~30 seconds to 1 minute")
    print(f"  4. After all {num_chunks} chunks, verify page count")
    print("  5. Restart Node.js app")
    print()
    print(f"See {output_dir}/README.txt for detailed instructions")


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_import_sql_chunked.py <dataset.json> [chunk_size]")
        print("\nExample:")
        print("  python generate_import_sql_chunked.py data/editathon_dataset.json 50")
        print("\nThis creates multiple smaller SQL files (default 50 pages each)")
        print("Easier for phpPgAdmin to handle than one large file")
        sys.exit(1)
    
    dataset_file = sys.argv[1]
    chunk_size = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    generate_sql_chunked(dataset_file, chunk_size)


if __name__ == "__main__":
    main()
