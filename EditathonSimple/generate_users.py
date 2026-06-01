#!/usr/bin/env python3
"""
Generate users.json for editathon with page assignments
"""

import json
import hashlib
import sys
from pathlib import Path


def hash_password(password):
    """Simple SHA256 hash for passwords (Node.js compatible)"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_users(num_users, total_pages, output_file='users.json'):
    """
    Generate users with balanced page assignments
    
    Args:
        num_users: Number of guest accounts to create
        total_pages: Total pages in dataset
        output_file: Output JSON file
    """
    pages_per_user = total_pages // num_users
    remainder = total_pages % num_users
    
    users = {}
    passwords = []
    
    current_page = 1
    
    for i in range(1, num_users + 1):
        username = f"guest{i}"
        password = f"edit{i:03d}"  # edit001, edit002, etc.
        
        # Calculate page range
        pages_for_this_user = pages_per_user + (1 if i <= remainder else 0)
        start_page = current_page
        end_page = current_page + pages_for_this_user - 1
        
        users[username] = {
            "password": hash_password(password),
            "assigned_pages": {
                "start": start_page,
                "end": end_page
            },
            "name": f"Guest User {i}"
        }
        
        passwords.append({
            "username": username,
            "password": password,
            "pages": f"{start_page}-{end_page}"
        })
        
        current_page = end_page + 1
    
    # Save users.json
    with open(output_file, 'w') as f:
        json.dump(users, f, indent=2)
    
    print(f"[OK] Generated {output_file}")
    print(f"  - {num_users} users created")
    print(f"  - {total_pages} pages distributed")
    print(f"  - ~{pages_per_user} pages per user")
    
    # Save passwords.txt
    passwords_file = 'passwords.txt'
    with open(passwords_file, 'w') as f:
        f.write("EDITATHON USER CREDENTIALS\n")
        f.write("=" * 60 + "\n\n")
        for p in passwords:
            f.write(f"Username: {p['username']}\n")
            f.write(f"Password: {p['password']}\n")
            f.write(f"Pages:    {p['pages']}\n")
            f.write("-" * 60 + "\n")
    
    print(f"[OK] Generated {passwords_file}")
    print(f"\n[WARNING] DELETE passwords.txt after distributing credentials!")
    
    return users


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_users.py <num_users> <total_pages>")
        print("\nExample:")
        print("  python generate_users.py 10 504")
        print("\nThis creates:")
        print("  - users.json (with hashed passwords and page assignments)")
        print("  - passwords.txt (plain text - DELETE after distribution)")
        sys.exit(1)
    
    num_users = int(sys.argv[1])
    total_pages = int(sys.argv[2])
    
    generate_users(num_users, total_pages)


if __name__ == "__main__":
    main()
