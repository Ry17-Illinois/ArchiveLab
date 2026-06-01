#!/usr/bin/env python3
"""
Import editathon dataset into PostgreSQL
"""

import json
import sys
import psycopg2
from pathlib import Path


def import_dataset(dataset_file, db_config):
    """Import editathon_dataset.json into PostgreSQL"""
    
    # Load dataset
    with open(dataset_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Connect to database
    conn = psycopg2.connect(
        host=db_config['host'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password'],
        port=db_config.get('port', 5432)
    )
    cur = conn.cursor()
    
    print(f"Importing {len(dataset['pages'])} pages...")
    
    # Import pages
    for page in dataset['pages']:
        # Insert page
        cur.execute("""
            INSERT INTO pages (page_id, page_number, json_file, image_path, document_filename, dublin_core, archival_context)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (page_id) DO NOTHING
        """, (
            page['page_id'],
            page['page_number'],
            page.get('json_file'),
            f"images/{page['page_id']}.jpg",
            dataset['document']['filename'],
            json.dumps(page.get('metadata', {}).get('dublin_core', {})),
            json.dumps(page.get('metadata', {}).get('archival_context', {}))
        ))
        
        # Insert OCR versions
        for engine_name, ocr_text in page.get('ocr_versions', {}).items():
            cur.execute("""
                INSERT INTO ocr_versions (page_id, engine_name, ocr_text)
                VALUES (%s, %s, %s)
                ON CONFLICT (page_id, engine_name) DO NOTHING
            """, (page['page_id'], engine_name, ocr_text))
        
        # Insert entities
        for entity_type, entity_list in page.get('entities', {}).items():
            for entity_name in entity_list:
                if entity_name and entity_name.strip():
                    cur.execute("""
                        INSERT INTO entities (page_id, entity_type, entity_name)
                        VALUES (%s, %s, %s)
                    """, (page['page_id'], entity_type, entity_name))
        
        if page['page_number'] % 50 == 0:
            print(f"  Imported {page['page_number']} pages...")
    
    conn.commit()
    
    # Get counts
    cur.execute("SELECT COUNT(*) FROM pages")
    page_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM ocr_versions")
    ocr_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM entities")
    entity_count = cur.fetchone()[0]
    
    print(f"\n[OK] Import complete!")
    print(f"  - Pages: {page_count}")
    print(f"  - OCR versions: {ocr_count}")
    print(f"  - Entities: {entity_count}")
    
    cur.close()
    conn.close()


def import_users(users_file, db_config):
    """Import users.json into PostgreSQL"""
    
    with open(users_file, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    conn = psycopg2.connect(
        host=db_config['host'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password'],
        port=db_config.get('port', 5432)
    )
    cur = conn.cursor()
    
    print(f"\nImporting {len(users)} users...")
    
    for username, data in users.items():
        cur.execute("""
            INSERT INTO users (username, password_hash, name, assigned_start, assigned_end)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, (
            username,
            data['password'],
            data.get('name', username),
            data['assigned_pages']['start'],
            data['assigned_pages']['end']
        ))
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    
    print(f"[OK] Imported {user_count} users")
    
    cur.close()
    conn.close()


def main():
    if len(sys.argv) < 6:
        print("Usage: python import_to_postgres.py <dataset.json> <users.json> <db_host> <db_name> <db_user> <db_password>")
        print("\nExample:")
        print('  python import_to_postgres.py data/editathon_dataset.json users.json localhost editathon_db editathon_user mypassword')
        sys.exit(1)
    
    dataset_file = sys.argv[1]
    users_file = sys.argv[2]
    
    db_config = {
        'host': sys.argv[3],
        'database': sys.argv[4],
        'user': sys.argv[5],
        'password': sys.argv[6]
    }
    
    print("Editathon Dataset Import to PostgreSQL")
    print("=" * 60)
    
    import_dataset(dataset_file, db_config)
    import_users(users_file, db_config)
    
    print("\n" + "=" * 60)
    print("Import complete! Database is ready.")


if __name__ == "__main__":
    main()
