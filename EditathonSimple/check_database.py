#!/usr/bin/env python3
"""
Quick database status check for EditathonSimple
"""

import sys
import psycopg2


def check_database(db_config):
    """Check if database has required data"""
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_config['host'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password'],
            port=db_config.get('port', 5432)
        )
        cur = conn.cursor()
        
        print("=" * 70)
        print("EDITATHON DATABASE STATUS CHECK")
        print("=" * 70)
        print()
        
        # Check connection
        print("✓ Database connection successful")
        print(f"  Host: {db_config['host']}")
        print(f"  Database: {db_config['database']}")
        print()
        
        # Check tables exist
        print("Checking tables...")
        tables = ['users', 'pages', 'ocr_versions', 'entities', 'edits', 
                  'metadata_validations', 'entity_validations']
        
        missing_tables = []
        for table in tables:
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                );
            """)
            exists = cur.fetchone()[0]
            if exists:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} - MISSING!")
                missing_tables.append(table)
        
        if missing_tables:
            print()
            print("❌ ERROR: Missing tables!")
            print("   Solution: Run schema.sql to create tables")
            print("   In cPanel: phpPgAdmin → SQL → paste schema.sql → Execute")
            return False
        
        print()
        
        # Check data counts
        print("Checking data...")
        
        cur.execute("SELECT COUNT(*) FROM pages")
        page_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM ocr_versions")
        ocr_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM entities")
        entity_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM edits")
        edit_count = cur.fetchone()[0]
        
        print(f"  Pages:        {page_count:>6}")
        print(f"  OCR versions: {ocr_count:>6}")
        print(f"  Entities:     {entity_count:>6}")
        print(f"  Users:        {user_count:>6}")
        print(f"  Edits:        {edit_count:>6}")
        print()
        
        # Evaluate status
        if page_count == 0:
            print("❌ ERROR: No pages in database!")
            print("   Solution: Run import_to_postgres.py to import data")
            print("   Command: python import_to_postgres.py data/editathon_dataset.json users.json ...")
            return False
        
        if user_count == 0:
            print("❌ ERROR: No users in database!")
            print("   Solution: Generate users and import")
            print("   Commands:")
            print("     python generate_users.py 10 504")
            print("     python import_to_postgres.py ... (include users.json)")
            return False
        
        # Show user assignments
        print("User assignments:")
        cur.execute("""
            SELECT username, assigned_start, assigned_end, 
                   (assigned_end - assigned_start + 1) as page_count
            FROM users 
            ORDER BY assigned_start
        """)
        
        for row in cur.fetchall():
            username, start, end, count = row
            print(f"  {username:12} → Pages {start:3}-{end:3} ({count:2} pages)")
        
        print()
        
        # Check for sample data
        print("Sample data check:")
        cur.execute("SELECT page_id, page_number FROM pages LIMIT 1")
        sample_page = cur.fetchone()
        if sample_page:
            print(f"  ✓ Sample page: {sample_page[0]} (page {sample_page[1]})")
        
        cur.execute("""
            SELECT engine_name, COUNT(*) 
            FROM ocr_versions 
            GROUP BY engine_name
        """)
        ocr_engines = cur.fetchall()
        if ocr_engines:
            print(f"  ✓ OCR engines:")
            for engine, count in ocr_engines:
                print(f"    - {engine}: {count} pages")
        
        print()
        print("=" * 70)
        print("✅ DATABASE IS READY!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Upload data/images/ folder to server")
        print("  2. Deploy application (dist/, server-postgres.js, etc.)")
        print("  3. Configure .env.local with these database credentials")
        print("  4. Restart Node.js app in cPanel")
        print("  5. Test login with a user account")
        print()
        
        cur.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print("=" * 70)
        print("❌ DATABASE CONNECTION FAILED")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        print("Possible causes:")
        print("  1. Database doesn't exist")
        print("     → Create in cPanel: PostgreSQL Databases")
        print()
        print("  2. Wrong credentials")
        print("     → Check username, password, database name")
        print()
        print("  3. PostgreSQL not running")
        print("     → Contact hosting support")
        print()
        print("  4. Remote access not enabled (if connecting remotely)")
        print("     → Enable in cPanel: Remote PostgreSQL")
        print()
        return False
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    if len(sys.argv) < 5:
        print("EditathonSimple Database Status Checker")
        print("=" * 70)
        print()
        print("Usage: python check_database.py <host> <database> <user> <password>")
        print()
        print("Example:")
        print("  python check_database.py localhost editathon_db editathon_user mypassword")
        print()
        print("This script checks:")
        print("  ✓ Database connection")
        print("  ✓ Required tables exist")
        print("  ✓ Data has been imported")
        print("  ✓ Users are configured")
        print("  ✓ Sample data is accessible")
        print()
        sys.exit(1)
    
    db_config = {
        'host': sys.argv[1],
        'database': sys.argv[2],
        'user': sys.argv[3],
        'password': sys.argv[4]
    }
    
    success = check_database(db_config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
