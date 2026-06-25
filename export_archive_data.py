"""
Export Archive Data - Produces SQLite, CSV, and GEXF (Gephi) from processed JSON files.

Scans all subdirectories of the archive data folder for:
- *_metadata.json (document-level metadata)
- *_PageN.json (per-page OCR + NER data)

Outputs:
- archive_export.db (SQLite database)
- archive_export.csv (unified CSV)
- archive_network.gexf (co-occurrence network for Gephi)
"""

import os
import json
import re
import csv
import sqlite3
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict, Counter
from pathlib import Path
from itertools import combinations
from difflib import SequenceMatcher

# ============================================================================
# Configuration
# ============================================================================
DATA_ROOT = r"D:\ArchiveData\NEH Domestic Science Project - Digitized Materials"
OUTPUT_DIR = r"D:\ArchiveData\exports"

SQLITE_FILE = os.path.join(OUTPUT_DIR, "archive_export.db")
CSV_FILE = os.path.join(OUTPUT_DIR, "archive_export.csv")
GEXF_FILE = os.path.join(OUTPUT_DIR, "archive_network.gexf")
GEXF_ARCHIVAL_FILE = os.path.join(OUTPUT_DIR, "archive_network_archival.gexf")
MASTER_JSON_FILE = os.path.join(OUTPUT_DIR, "archive_master.json")
MERGES_FILE = os.path.join(OUTPUT_DIR, "entity_merges_log.json")
REVIEW_FILE = os.path.join(OUTPUT_DIR, "entity_merges_review.json")
APPROVED_FILE = os.path.join(OUTPUT_DIR, "entity_merges_approved.json")

# Minimum mentions to keep a PERSON entity (applied before merging)
MIN_PERSON_MENTIONS = 5


# ============================================================================
# Entity Resolution: Stoplist, normalization, and fuzzy merging
# ============================================================================

# Strings that SpaCy commonly misclassifies as PERSON
PERSON_STOPLIST = {
    # Honorifics alone
    "miss", "mrs", "mr", "dr", "prof", "sir", "madam", "madame",
    # Greetings and closings
    "dear", "sincerely", "yours truly", "yours", "truly", "cordially",
    "faithfully", "respectfully", "dear sir", "dear madam",
    "dear friend", "my dear",
    # Generic roles
    "president", "secretary", "treasurer", "chairman", "chairwoman",
    "professor", "dean", "director", "editor", "superintendent",
    # Common NER errors
    "ill", "ill.", "cal", "cal.", "mich", "mich.", "dec", "jan", "feb",
    "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}

HONORIFIC_PREFIXES = re.compile(
    r"^(miss|mrs\.?|mr\.?|dr\.?|prof\.?|rev\.?|hon\.?|ms\.?)\s+",
    re.IGNORECASE
)


def is_false_person(name):
    """Check if this name is likely a false positive PERSON entity."""
    lower = name.lower().strip().rstrip(".,;:")
    if lower in PERSON_STOPLIST:
        return True
    if len(name.strip()) < 3:
        return True
    # All digits or punctuation
    if re.match(r"^[\d\W]+$", name):
        return True
    # Single word that's all lowercase (likely not a proper name)
    if " " not in name.strip() and name.strip().islower():
        return True
    return False


def normalize_person_name(name):
    """Normalize a person name for comparison."""
    name = name.strip().rstrip(".,;:")
    # Remove honorific prefixes
    name = HONORIFIC_PREFIXES.sub("", name).strip()
    # Normalize whitespace
    name = re.sub(r"\s+", " ", name)
    return name


def extract_surname(name):
    """Extract likely surname from a name string."""
    normalized = normalize_person_name(name)
    if not normalized:
        return ""
    parts = normalized.split()
    if len(parts) == 0:
        return ""
    # If "Last, First" format
    if "," in parts[0]:
        return parts[0].rstrip(",").lower()
    # Otherwise last word is likely surname
    return parts[-1].lower()


def initial_matches(name_a, name_b):
    """Check if initials in one name match full first names in another."""
    parts_a = normalize_person_name(name_a).split()
    parts_b = normalize_person_name(name_b).split()

    if len(parts_a) < 2 or len(parts_b) < 2:
        return False

    # Check if first part of one is an initial matching the other
    for pa, pb in [(parts_a, parts_b), (parts_b, parts_a)]:
        if len(pa[0]) <= 2 and pa[0].rstrip(".").upper() == pb[0][0].upper():
            # Initial matches first letter — check surname
            if pa[-1].lower() == pb[-1].lower():
                return True
    return False


def names_are_similar(name_a, name_b):
    """
    Determine if two person names likely refer to the same person.
    Returns (is_match, confidence) tuple.
    """
    norm_a = normalize_person_name(name_a)
    norm_b = normalize_person_name(name_b)

    if not norm_a or not norm_b:
        return False, 0.0

    # Exact match after normalization
    if norm_a.lower() == norm_b.lower():
        return True, 1.0

    # One is a substring of the other (e.g., "Bevier" in "Isabel Bevier")
    if norm_a.lower() in norm_b.lower() or norm_b.lower() in norm_a.lower():
        # Only if the substring is the surname (not a common short word)
        shorter = norm_a if len(norm_a) < len(norm_b) else norm_b
        if len(shorter) >= 4:  # Avoid matching on "Ann" in "Joanne"
            return True, 0.9

    # Same surname + initial match
    surname_a = extract_surname(name_a)
    surname_b = extract_surname(name_b)

    if surname_a and surname_b and surname_a == surname_b:
        # Same surname — check if first names/initials are compatible
        if initial_matches(name_a, name_b):
            return True, 0.85
        # If one is just the surname alone
        parts_a = normalize_person_name(name_a).split()
        parts_b = normalize_person_name(name_b).split()
        if len(parts_a) == 1 or len(parts_b) == 1:
            return True, 0.7

    # Fuzzy match as fallback (catch typos)
    ratio = SequenceMatcher(None, norm_a.lower(), norm_b.lower()).ratio()
    if ratio > 0.85 and len(norm_a) > 5:
        return True, ratio

    return False, 0.0


def resolve_person_entities(entities):
    """
    Main entity resolution pipeline for PERSON entities.
    
    1. Filter out false positives (stoplist)
    2. Drop entities with <= MIN_PERSON_MENTIONS mentions
    3. Cluster similar names
    4. Pick canonical form for each cluster
    5. Return mapping: {original_name: canonical_name} and rejected set
    
    Modifies the entities list in-place by updating entity_name for PERSON entities.
    """
    # Count person mentions
    person_counts = Counter()
    for ent in entities:
        if ent["entity_type"] == "PERSON":
            person_counts[ent["entity_name"]] += 1

    # Phase 1: Identify rejections (false positives)
    rejected = set()
    for name in person_counts:
        if is_false_person(name):
            rejected.add(name)

    # Phase 2: Drop low-frequency persons
    surviving_names = set()
    for name, count in person_counts.items():
        if name not in rejected and count > MIN_PERSON_MENTIONS:
            surviving_names.add(name)

    # Phase 3: Cluster similar names
    # Sort by frequency descending so the most common form tends to be canonical
    sorted_names = sorted(surviving_names, key=lambda n: -person_counts[n])
    clusters = []  # list of sets
    name_to_cluster = {}

    for name in sorted_names:
        if name in name_to_cluster:
            continue

        # Try to find an existing cluster this name belongs to
        matched_cluster = None
        for cluster in clusters:
            for existing in cluster:
                is_match, confidence = names_are_similar(name, existing)
                if is_match and confidence >= 0.7:
                    matched_cluster = cluster
                    break
            if matched_cluster:
                break

        if matched_cluster:
            matched_cluster.add(name)
            name_to_cluster[name] = matched_cluster
        else:
            new_cluster = {name}
            clusters.append(new_cluster)
            name_to_cluster[name] = new_cluster

    # Phase 4: Pick canonical name per cluster (most frequent, then longest)
    merge_map = {}  # original -> canonical
    for cluster in clusters:
        if len(cluster) == 1:
            canonical = list(cluster)[0]
        else:
            # Pick the most complete form: prefer longest name among top-frequency variants
            ranked = sorted(cluster, key=lambda n: (-person_counts[n], -len(n)))
            # Among top-frequency, pick longest
            top_freq = person_counts[ranked[0]]
            top_tier = [n for n in ranked if person_counts[n] >= top_freq * 0.3]
            canonical = max(top_tier, key=lambda n: len(normalize_person_name(n)))

        for name in cluster:
            if name != canonical:
                merge_map[name] = canonical

    # Build the full mapping including rejections
    print(f"  Entity resolution:")
    print(f"    Total unique PERSON names: {len(person_counts)}")
    print(f"    Rejected (false positives): {len(rejected)}")
    print(f"    Dropped (<=5 mentions): {len(person_counts) - len(rejected) - len(surviving_names)}")
    print(f"    Surviving names: {len(surviving_names)}")
    print(f"    Clusters formed: {len(clusters)}")
    print(f"    Names merged: {len(merge_map)}")

    # Apply to entities
    resolved_count = 0
    removed_count = 0
    entities_to_keep = []

    for ent in entities:
        if ent["entity_type"] == "PERSON":
            name = ent["entity_name"]
            # Reject false positives
            if name in rejected:
                removed_count += 1
                continue
            # Drop low-frequency
            if name not in surviving_names and name not in merge_map:
                removed_count += 1
                continue
            # Apply merge
            if name in merge_map:
                ent["entity_name"] = merge_map[name]
                resolved_count += 1
        entities_to_keep.append(ent)

    print(f"    Entity records removed: {removed_count}")
    print(f"    Entity records renamed: {resolved_count}")

    # Return the log for reference
    merge_log = {
        "rejected_names": sorted(rejected),
        "merges": [
            {"canonical": canonical, "variants": sorted([v for v, c in merge_map.items() if c == canonical])}
            for canonical in sorted(set(merge_map.values()))
        ],
        "stats": {
            "total_unique_persons": len(person_counts),
            "rejected": len(rejected),
            "dropped_low_freq": len(person_counts) - len(rejected) - len(surviving_names),
            "surviving": len(surviving_names),
            "clusters": len(clusters),
            "merges_applied": len(merge_map),
        }
    }

    return entities_to_keep, merge_log


def generate_review_file(entities, output_path):
    """
    Generate a review file for manual evaluation of proposed merges.
    
    The file contains clusters with:
    - canonical: the proposed canonical name
    - variants: list of names that would merge into canonical
    - mentions: count for each variant
    - status: "pending" (user sets to "approved", "reject", or leaves as-is)
    - move_to: (optional) if a variant should go to a different cluster, put the canonical name here
    
    Also includes a rejected_names list that user can restore from.
    """
    from collections import Counter

    # Count person mentions
    person_counts = Counter()
    for ent in entities:
        if ent["entity_type"] == "PERSON":
            person_counts[ent["entity_name"]] += 1

    # Filter and cluster (same logic as resolve_person_entities but without applying)
    rejected = set()
    for name in person_counts:
        if is_false_person(name):
            rejected.add(name)

    surviving_names = set()
    for name, count in person_counts.items():
        if name not in rejected and count > MIN_PERSON_MENTIONS:
            surviving_names.add(name)

    # Cluster
    sorted_names = sorted(surviving_names, key=lambda n: -person_counts[n])
    clusters = []
    name_to_cluster = {}

    for name in sorted_names:
        if name in name_to_cluster:
            continue

        matched_cluster = None
        for cluster in clusters:
            for existing in cluster:
                is_match, confidence = names_are_similar(name, existing)
                if is_match and confidence >= 0.7:
                    matched_cluster = cluster
                    break
            if matched_cluster:
                break

        if matched_cluster:
            matched_cluster.add(name)
            name_to_cluster[name] = matched_cluster
        else:
            new_cluster = {name}
            clusters.append(new_cluster)
            name_to_cluster[name] = new_cluster

    # Build review structure
    review_data = {
        "_instructions": (
            "Review each cluster below. For each cluster:\n"
            "  - Set status to 'approved' to accept the merge as-is\n"
            "  - Set status to 'reject' to keep all variants as separate entities\n"
            "  - Change 'canonical' to set a different canonical name\n"
            "  - In 'variants', set 'move_to' to a canonical name to reassign a variant to another cluster\n"
            "  - In 'variants', set 'action' to 'reject' to exclude a single variant from this cluster\n"
            "\n"
            "In 'rejected_names', set 'restore' to true on any name to bring it back.\n"
            "\n"
            "After editing, save as 'entity_merges_approved.json' (or rename this file).\n"
            "Then re-run the export script — it will use your approved merges."
        ),
        "clusters": [],
        "rejected_names": []
    }

    for cluster in clusters:
        ranked = sorted(cluster, key=lambda n: (-person_counts[n], -len(n)))
        top_freq = person_counts[ranked[0]]
        top_tier = [n for n in ranked if person_counts[n] >= top_freq * 0.3]
        canonical = max(top_tier, key=lambda n: len(normalize_person_name(n)))

        cluster_entry = {
            "canonical": canonical,
            "status": "pending",
            "variants": [
                {
                    "name": name,
                    "mentions": person_counts[name],
                    "action": "merge",  # "merge", "reject", or "move_to"
                    "move_to": ""
                }
                for name in sorted(cluster, key=lambda n: -person_counts[n])
                if name != canonical
            ],
            "canonical_mentions": person_counts[canonical]
        }
        review_data["clusters"].append(cluster_entry)

    # Sort clusters: multi-variant clusters first, then by mention count
    review_data["clusters"].sort(key=lambda c: (-len(c["variants"]), -c["canonical_mentions"]))

    # Add rejected names for potential restoration
    for name in sorted(rejected):
        review_data["rejected_names"].append({
            "name": name,
            "mentions": person_counts[name],
            "restore": False
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(review_data, f, indent=2, ensure_ascii=False)

    multi_variant = sum(1 for c in review_data["clusters"] if len(c["variants"]) > 0)
    print(f"  Review file generated: {output_path}")
    print(f"    Total clusters: {len(review_data['clusters'])}")
    print(f"    Clusters with merges to review: {multi_variant}")
    print(f"    Rejected names (reviewable): {len(review_data['rejected_names'])}")

    return review_data


def apply_approved_merges(entities, approved_path):
    """
    Apply manually reviewed merges from the approved file.
    
    Returns filtered entities list with merges applied.
    """
    with open(approved_path, "r", encoding="utf-8") as f:
        approved = json.load(f)

    from collections import Counter
    person_counts = Counter()
    for ent in entities:
        if ent["entity_type"] == "PERSON":
            person_counts[ent["entity_name"]] += 1

    # Build merge map from approved clusters
    merge_map = {}
    approved_names = set()  # names that survive

    for cluster in approved.get("clusters", []):
        status = cluster.get("status", "pending")
        canonical = cluster["canonical"]

        if status != "approved":
            # Only explicitly approved clusters survive — skip pending and rejected
            continue

        # Status is "approved"
        approved_names.add(canonical)

        for v in cluster.get("variants", []):
            name = v["name"]
            action = v.get("action", "merge")
            move_to = v.get("move_to", "")

            if action == "reject":
                # This variant is excluded entirely
                continue
            elif action == "move_to" or move_to:
                # Reassign to a different canonical
                target = move_to if move_to else v.get("move_to", "")
                if target:
                    merge_map[name] = target
                    approved_names.add(target)
            else:
                # Normal merge
                merge_map[name] = canonical
                approved_names.add(name)

    # Check for restored rejected names
    restored = set()
    for entry in approved.get("rejected_names", []):
        if entry.get("restore", False):
            restored.add(entry["name"])

    # Build rejected set (original rejects minus restored)
    rejected = set()
    for entry in approved.get("rejected_names", []):
        if not entry.get("restore", False):
            rejected.add(entry["name"])

    # Apply
    entities_to_keep = []
    merged_count = 0
    removed_count = 0

    for ent in entities:
        if ent["entity_type"] == "PERSON":
            name = ent["entity_name"]

            # Only keep PERSON entities that are in an approved cluster (or merged into one)
            if name in merge_map:
                ent["entity_name"] = merge_map[name]
                merged_count += 1
            elif name in approved_names or name in restored:
                pass  # keep as-is
            else:
                # Not explicitly approved — remove
                removed_count += 1
                continue

        entities_to_keep.append(ent)

    print(f"  Applied approved merges from: {approved_path}")
    print(f"    Names merged: {merged_count}")
    print(f"    Entities removed: {removed_count}")
    print(f"    Entities remaining: {len(entities_to_keep)}")

    return entities_to_keep


# ============================================================================
# Step 1: Discover and parse all JSON files
# ============================================================================

def find_json_files(root_dir):
    """Recursively find all metadata and page JSON files."""
    metadata_files = []
    page_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(dirpath, filename)
            if filename.endswith("_metadata.json"):
                metadata_files.append(filepath)
            elif filename.startswith("_"):
                # Skip summary/internal files like _collection_metadata_summary
                continue
            else:
                # Both *_PageN.json and standalone .json files go here
                page_files.append(filepath)

    return metadata_files, page_files


def parse_metadata_file(filepath):
    """Parse a document-level metadata JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "filepath": filepath,
        "source_document": data.get("source_document", ""),
        "file_info": data.get("file_info", {}),
        "dublin_core": data.get("dublin_core_metadata", {}),
        "archival_context": data.get("archival_context", {}),
        "pages": data.get("pages", []),
    }


def parse_page_file(filepath):
    """Parse a per-page JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Get the best OCR text
    ocr_text = ""
    ocr_engine = ""
    engines = data.get("ocr_results", {}).get("engines", {})
    ground_truth = data.get("ocr_results", {}).get("ground_truth_engine", "")

    if ground_truth and ground_truth in engines:
        ocr_text = engines[ground_truth].get("text", "")
        ocr_engine = ground_truth
    else:
        # Take the first engine with text
        for eng_name, eng_data in engines.items():
            if eng_data.get("text"):
                ocr_text = eng_data["text"]
                ocr_engine = eng_name
                break

    # Get entities
    entities = data.get("named_entities", {}).get("entities", {})

    return {
        "filepath": filepath,
        "page_number": data.get("page_number", 0),
        "parent_document": data.get("parent_document", ""),
        "file_id": data.get("file_id", ""),
        "ocr_text": ocr_text,
        "ocr_engine": ocr_engine,
        "entities": entities,
    }


# ============================================================================
# Step 2: Aggregate data
# ============================================================================

def aggregate_data(metadata_files, page_files):
    """Build unified data structures from parsed files."""
    documents = []
    pages = []
    all_entities = []
    errors = []

    # Index metadata by source document name
    metadata_index = {}
    print(f"  Parsing {len(metadata_files)} metadata files...")
    for i, mf in enumerate(metadata_files):
        try:
            meta = parse_metadata_file(mf)
            doc_key = meta["source_document"]
            metadata_index[doc_key] = meta

            documents.append({
                "source_document": doc_key,
                "filepath": mf,
                "title": meta["dublin_core"].get("title", ""),
                "creator": meta["dublin_core"].get("creator", ""),
                "date": meta["dublin_core"].get("date", ""),
                "subject": meta["dublin_core"].get("subject", ""),
                "description": meta["dublin_core"].get("description", ""),
                "type": meta["dublin_core"].get("type", ""),
                "collection": meta["archival_context"].get("collection", ""),
                "box": meta["archival_context"].get("box", ""),
                "folder": meta["archival_context"].get("folder", ""),
                "total_pages": meta["file_info"].get("total_pages", 0),
                "date_processed": meta["file_info"].get("date_processed", ""),
            })
        except Exception as e:
            errors.append(f"  ERROR parsing metadata {mf}: {e}")
        
        if (i + 1) % 100 == 0:
            print(f"    Metadata: {i+1}/{len(metadata_files)}")

    print(f"  Metadata done. {len(documents)} documents indexed.")

    # Process page files
    print(f"  Parsing {len(page_files)} page files...")
    skipped = 0
    for i, pf in enumerate(page_files):
        try:
            page = parse_page_file(pf)
            parent_doc = page["parent_document"]

            # Look up archival context from metadata
            meta = metadata_index.get(parent_doc, {})
            collection = meta.get("archival_context", {}).get("collection", "") if meta else ""
            box = meta.get("archival_context", {}).get("box", "") if meta else ""
            folder = meta.get("archival_context", {}).get("folder", "") if meta else ""

            page_record = {
                "source_document": parent_doc,
                "page_number": page["page_number"],
                "file_id": page["file_id"],
                "ocr_text": page["ocr_text"],
                "ocr_engine": page["ocr_engine"],
                "collection": collection,
                "box": box,
                "folder": folder,
            }
            pages.append(page_record)

            # Extract entities
            for entity_type, entity_list in page["entities"].items():
                for entity_name in entity_list:
                    all_entities.append({
                        "source_document": parent_doc,
                        "page_number": page["page_number"],
                        "entity_type": entity_type,
                        "entity_name": entity_name.strip(),
                        "collection": collection,
                        "box": box,
                        "folder": folder,
                    })
        except Exception as e:
            skipped += 1
            if skipped <= 10:
                errors.append(f"  ERROR parsing page {pf}: {e}")
            elif skipped == 11:
                errors.append(f"  ... (suppressing further page parse errors)")
        
        if (i + 1) % 2000 == 0:
            print(f"    Pages: {i+1}/{len(page_files)} ({len(all_entities)} entities so far)")

    print(f"  Pages done. {len(pages)} parsed, {skipped} skipped due to errors.")
    
    if errors:
        print(f"  Errors encountered ({len(errors)}):")
        for err in errors[:20]:
            print(f"    {err}")
        if len(errors) > 20:
            print(f"    ... and {len(errors) - 20} more")

    return documents, pages, all_entities


# ============================================================================
# Step 3: Generate SQLite database
# ============================================================================

def create_sqlite(documents, pages, entities, output_path):
    """Create SQLite database with all data."""
    if os.path.exists(output_path):
        os.remove(output_path)

    conn = sqlite3.connect(output_path)
    c = conn.cursor()

    # Create tables
    c.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_document TEXT UNIQUE,
            title TEXT,
            creator TEXT,
            date TEXT,
            subject TEXT,
            description TEXT,
            type TEXT,
            collection TEXT,
            box TEXT,
            folder TEXT,
            total_pages INTEGER,
            date_processed TEXT
        )
    """)

    c.execute("""
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_document TEXT,
            page_number INTEGER,
            file_id TEXT,
            ocr_text TEXT,
            ocr_engine TEXT,
            collection TEXT,
            box TEXT,
            folder TEXT,
            FOREIGN KEY (source_document) REFERENCES documents(source_document)
        )
    """)

    c.execute("""
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_document TEXT,
            page_number INTEGER,
            entity_type TEXT,
            entity_name TEXT,
            collection TEXT,
            box TEXT,
            folder TEXT,
            FOREIGN KEY (source_document) REFERENCES documents(source_document)
        )
    """)

    c.execute("""
        CREATE TABLE collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection TEXT,
            box TEXT,
            folder TEXT,
            document_count INTEGER
        )
    """)

    # Insert documents
    for doc in documents:
        c.execute("""
            INSERT OR IGNORE INTO documents 
            (source_document, title, creator, date, subject, description, type, collection, box, folder, total_pages, date_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc["source_document"], doc["title"], doc["creator"], doc["date"],
            doc["subject"], doc["description"], doc["type"],
            doc["collection"], doc["box"], doc["folder"],
            doc["total_pages"], doc["date_processed"]
        ))

    # Insert pages
    for page in pages:
        c.execute("""
            INSERT INTO pages 
            (source_document, page_number, file_id, ocr_text, ocr_engine, collection, box, folder)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page["source_document"], page["page_number"], page["file_id"],
            page["ocr_text"], page["ocr_engine"],
            page["collection"], page["box"], page["folder"]
        ))

    # Insert entities
    for ent in entities:
        c.execute("""
            INSERT INTO entities 
            (source_document, page_number, entity_type, entity_name, collection, box, folder)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            ent["source_document"], ent["page_number"],
            ent["entity_type"], ent["entity_name"],
            ent["collection"], ent["box"], ent["folder"]
        ))

    # Build collections summary
    c.execute("""
        INSERT INTO collections (collection, box, folder, document_count)
        SELECT collection, box, folder, COUNT(DISTINCT source_document)
        FROM documents
        WHERE collection != ''
        GROUP BY collection, box, folder
    """)

    # Create indexes
    c.execute("CREATE INDEX idx_pages_doc ON pages(source_document)")
    c.execute("CREATE INDEX idx_entities_doc ON entities(source_document)")
    c.execute("CREATE INDEX idx_entities_type ON entities(entity_type)")
    c.execute("CREATE INDEX idx_entities_name ON entities(entity_name)")

    conn.commit()
    conn.close()
    print(f"SQLite database: {output_path}")
    print(f"  Documents: {len(documents)}")
    print(f"  Pages: {len(pages)}")
    print(f"  Entities: {len(entities)}")


# ============================================================================
# Step 4: Generate CSV
# ============================================================================

def create_csv(documents, pages, entities, output_path):
    """Create a unified CSV with one row per entity occurrence."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "source_document", "page_number", "entity_type", "entity_name",
            "collection", "box", "folder",
            "doc_title", "doc_creator", "doc_date", "doc_subject"
        ])

        # Build a lookup for document metadata
        doc_lookup = {d["source_document"]: d for d in documents}

        for ent in entities:
            doc = doc_lookup.get(ent["source_document"], {})
            writer.writerow([
                ent["source_document"],
                ent["page_number"],
                ent["entity_type"],
                ent["entity_name"],
                ent["collection"],
                ent["box"],
                ent["folder"],
                doc.get("title", ""),
                doc.get("creator", ""),
                doc.get("date", ""),
                doc.get("subject", ""),
            ])

    print(f"CSV export: {output_path}")
    print(f"  Rows: {len(entities)}")


# ============================================================================
# Step 5: Generate GEXF co-occurrence network for Gephi
# ============================================================================

def create_gexf(entities, output_path):
    """
    Create a co-occurrence network in GEXF format.
    
    Nodes: unique entities (PERSON, ORG, GPE)
    Edges: two entities co-occur on the same page (weighted by frequency)
    
    Node attributes: entity_type, total_occurrences
    Edge attributes: weight (number of co-occurrences), shared_documents
    """
    # Filter to interesting entity types for the network
    network_types = {"PERSON", "ORG", "GPE", "ORGANIZATION", "LOC", "LOCATION", "DATE"}

    # Group entities by document+page for co-occurrence
    page_entities = defaultdict(set)
    entity_occurrences = defaultdict(lambda: {"type": "", "count": 0, "documents": set()})

    for ent in entities:
        etype = ent["entity_type"].upper()
        if etype not in network_types:
            continue

        name = ent["entity_name"].strip()
        if not name or len(name) < 2:
            continue

        # Normalize type labels
        if etype in ("GPE", "LOC", "LOCATION"):
            etype = "LOCATION"
        if etype == "ORGANIZATION":
            etype = "ORG"

        key = (etype, name)
        page_key = (ent["source_document"], ent["page_number"])

        page_entities[page_key].add(key)
        entity_occurrences[key]["type"] = etype
        entity_occurrences[key]["count"] += 1
        entity_occurrences[key]["documents"].add(ent["source_document"])

    # Build edges from co-occurrences
    edge_weights = defaultdict(lambda: {"weight": 0, "documents": set()})

    for page_key, ent_set in page_entities.items():
        doc = page_key[0]
        ent_list = sorted(ent_set)
        for a, b in combinations(ent_list, 2):
            edge_key = (a, b)
            edge_weights[edge_key]["weight"] += 1
            edge_weights[edge_key]["documents"].add(doc)

    # Filter: only keep nodes that appear in at least one edge
    connected_nodes = set()
    for (a, b) in edge_weights:
        connected_nodes.add(a)
        connected_nodes.add(b)

    # Filter: only keep nodes with more than 5 occurrences
    connected_nodes = {n for n in connected_nodes if entity_occurrences[n]["count"] > 5}

    # Remove edges that reference filtered-out nodes
    edge_weights = {(a, b): data for (a, b), data in edge_weights.items() 
                    if a in connected_nodes and b in connected_nodes}

    # Build GEXF XML
    gexf = ET.Element("gexf", {
        "xmlns": "http://gexf.net/1.3",
        "version": "1.3"
    })

    # Meta
    meta = ET.SubElement(gexf, "meta")
    ET.SubElement(meta, "creator").text = "ArchiveLab Export Script"
    ET.SubElement(meta, "description").text = (
        "Co-occurrence network of named entities from NEH Domestic Science digitized materials. "
        "Nodes are people, organizations, and places. "
        "Edges connect entities that co-occur on the same page."
    )

    # Graph
    graph = ET.SubElement(gexf, "graph", {
        "defaultedgetype": "undirected",
        "mode": "static"
    })

    # Node attributes
    node_attrs = ET.SubElement(graph, "attributes", {"class": "node"})
    ET.SubElement(node_attrs, "attribute", {"id": "0", "title": "entity_type", "type": "string"})
    ET.SubElement(node_attrs, "attribute", {"id": "1", "title": "occurrences", "type": "integer"})
    ET.SubElement(node_attrs, "attribute", {"id": "2", "title": "document_count", "type": "integer"})

    # Edge attributes
    edge_attrs = ET.SubElement(graph, "attributes", {"class": "edge"})
    ET.SubElement(edge_attrs, "attribute", {"id": "0", "title": "shared_documents", "type": "integer"})

    # Nodes
    nodes_el = ET.SubElement(graph, "nodes")
    node_id_map = {}
    for i, node_key in enumerate(sorted(connected_nodes)):
        node_id = str(i)
        node_id_map[node_key] = node_id
        etype, name = node_key
        info = entity_occurrences[node_key]

        node_el = ET.SubElement(nodes_el, "node", {"id": node_id, "label": name})
        attvalues = ET.SubElement(node_el, "attvalues")
        ET.SubElement(attvalues, "attvalue", {"for": "0", "value": etype})
        ET.SubElement(attvalues, "attvalue", {"for": "1", "value": str(info["count"])})
        ET.SubElement(attvalues, "attvalue", {"for": "2", "value": str(len(info["documents"]))})

    # Edges
    edges_el = ET.SubElement(graph, "edges")
    for i, ((a, b), data) in enumerate(sorted(edge_weights.items(), key=lambda x: -x[1]["weight"])):
        if a not in node_id_map or b not in node_id_map:
            continue
        edge_el = ET.SubElement(edges_el, "edge", {
            "id": str(i),
            "source": node_id_map[a],
            "target": node_id_map[b],
            "weight": str(data["weight"])
        })
        attvalues = ET.SubElement(edge_el, "attvalues")
        ET.SubElement(attvalues, "attvalue", {"for": "0", "value": str(len(data["documents"]))})

    # Write formatted XML
    xml_str = ET.tostring(gexf, encoding="unicode")
    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
    # Remove extra XML declaration from minidom
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"GEXF network: {output_path}")
    print(f"  Nodes: {len(connected_nodes)}")
    print(f"  Edges: {len(edge_weights)}")


# ============================================================================
# Step 6: Generate GEXF archival context network for Gephi
# ============================================================================

def create_gexf_archival(entities, output_path):
    """
    TOO BIG OF A GRAPH. ABANDON THIS APPROACH.
    
    Create a network connecting all entity types to archival folder nodes.
    
    Nodes:
      - PERSON entities (from approved merges)
      - ORG entities
      - LOCATION entities (GPE/LOC normalized)
      - FOLDER nodes (collection | box | folder as a single node)
    
    Edges:
      - Entity ↔ Folder (weighted by page count in that folder)
      - Entity ↔ Entity (weighted by folder co-occurrence)
    """
    # Entity types to include
    network_types = {"PERSON", "ORG", "GPE", "LOCATION", "LOC", "ORGANIZATION", "DATE", "MONEY", "PRODUCT", "WORK_OF_ART"}

    # Build entity → folder connections
    entity_folders = defaultdict(lambda: defaultdict(int))  # {(type, name): {folder_key: count}}
    folder_info = {}  # {folder_key: {collection, box, folder}}
    entity_occurrences = defaultdict(int)

    for ent in entities:
        etype = ent["entity_type"].upper()
        if etype not in network_types:
            continue

        name = ent["entity_name"].strip()
        if not name or len(name) < 2:
            continue

        # Normalize type labels
        if etype in ("GPE", "LOC", "LOCATION"):
            etype = "LOCATION"
        if etype == "ORGANIZATION":
            etype = "ORG"

        collection = ent.get("collection", "")
        box = ent.get("box", "")
        folder = ent.get("folder", "")

        if not collection:
            continue

        folder_key = f"{collection} | {box} | {folder}" if folder else f"{collection} | {box}"
        entity_key = (etype, name)

        entity_folders[entity_key][folder_key] += 1
        entity_occurrences[entity_key] += 1

        if folder_key not in folder_info:
            folder_info[folder_key] = {
                "collection": collection,
                "box": box,
                "folder": folder
            }

    # Filter: only keep entities with more than 5 occurrences
    active_entities = {k for k, v in entity_occurrences.items() if v > 5}

    # Build entity co-occurrence edges (via shared folders)
    entity_cooccurrence = defaultdict(lambda: {"weight": 0, "shared_folders": set()})
    folder_entities = defaultdict(set)  # {folder_key: set of entity keys}

    for entity_key, folders in entity_folders.items():
        if entity_key not in active_entities:
            continue
        for fk in folders:
            folder_entities[fk].add(entity_key)

    for fk, ents in folder_entities.items():
        ent_list = sorted(ents)
        for a, b in combinations(ent_list, 2):
            edge_key = (a, b)
            entity_cooccurrence[edge_key]["weight"] += 1
            entity_cooccurrence[edge_key]["shared_folders"].add(fk)

    # Build GEXF
    gexf = ET.Element("gexf", {
        "xmlns": "http://gexf.net/1.3",
        "version": "1.3"
    })

    meta = ET.SubElement(gexf, "meta")
    ET.SubElement(meta, "creator").text = "ArchiveLab Export Script"
    ET.SubElement(meta, "description").text = (
        "Network connecting people, organizations, and locations to archival folders. "
        "Entity-entity edges represent co-occurrence in the same archival folder."
    )

    graph = ET.SubElement(gexf, "graph", {
        "defaultedgetype": "undirected",
        "mode": "static"
    })

    # Node attributes
    node_attrs = ET.SubElement(graph, "attributes", {"class": "node"})
    ET.SubElement(node_attrs, "attribute", {"id": "0", "title": "node_type", "type": "string"})
    ET.SubElement(node_attrs, "attribute", {"id": "1", "title": "occurrences", "type": "integer"})
    ET.SubElement(node_attrs, "attribute", {"id": "2", "title": "collection", "type": "string"})
    ET.SubElement(node_attrs, "attribute", {"id": "3", "title": "box", "type": "string"})
    ET.SubElement(node_attrs, "attribute", {"id": "4", "title": "folder", "type": "string"})

    # Edge attributes
    edge_attrs = ET.SubElement(graph, "attributes", {"class": "edge"})
    ET.SubElement(edge_attrs, "attribute", {"id": "0", "title": "edge_type", "type": "string"})
    ET.SubElement(edge_attrs, "attribute", {"id": "1", "title": "shared_folders", "type": "integer"})

    # Nodes
    nodes_el = ET.SubElement(graph, "nodes")
    node_id_map = {}
    node_counter = 0

    # Entity nodes
    for entity_key in sorted(active_entities):
        etype, name = entity_key
        node_id = str(node_counter)
        node_id_map[entity_key] = node_id
        node_counter += 1

        node_el = ET.SubElement(nodes_el, "node", {"id": node_id, "label": name})
        attvalues = ET.SubElement(node_el, "attvalues")
        ET.SubElement(attvalues, "attvalue", {"for": "0", "value": etype})
        ET.SubElement(attvalues, "attvalue", {"for": "1", "value": str(entity_occurrences[entity_key])})
        ET.SubElement(attvalues, "attvalue", {"for": "2", "value": ""})
        ET.SubElement(attvalues, "attvalue", {"for": "3", "value": ""})
        ET.SubElement(attvalues, "attvalue", {"for": "4", "value": ""})

    # Folder nodes
    for folder_key in sorted(folder_info.keys()):
        info = folder_info[folder_key]
        node_id = str(node_counter)
        node_id_map[("FOLDER", folder_key)] = node_id
        node_counter += 1

        # Count total entity mentions in this folder
        folder_mention_count = sum(
            entity_folders[ek].get(folder_key, 0) for ek in active_entities
        )

        node_el = ET.SubElement(nodes_el, "node", {"id": node_id, "label": folder_key})
        attvalues = ET.SubElement(node_el, "attvalues")
        ET.SubElement(attvalues, "attvalue", {"for": "0", "value": "FOLDER"})
        ET.SubElement(attvalues, "attvalue", {"for": "1", "value": str(folder_mention_count)})
        ET.SubElement(attvalues, "attvalue", {"for": "2", "value": info["collection"]})
        ET.SubElement(attvalues, "attvalue", {"for": "3", "value": info["box"]})
        ET.SubElement(attvalues, "attvalue", {"for": "4", "value": info["folder"]})

    # Edges
    edges_el = ET.SubElement(graph, "edges")
    edge_counter = 0

    # Entity ↔ Folder edges
    for entity_key in active_entities:
        for folder_key, count in entity_folders[entity_key].items():
            entity_node = node_id_map.get(entity_key)
            folder_node = node_id_map.get(("FOLDER", folder_key))
            if entity_node and folder_node:
                etype = entity_key[0].lower()
                edge_el = ET.SubElement(edges_el, "edge", {
                    "id": str(edge_counter),
                    "source": entity_node,
                    "target": folder_node,
                    "weight": str(count)
                })
                attvalues = ET.SubElement(edge_el, "attvalues")
                ET.SubElement(attvalues, "attvalue", {"for": "0", "value": f"{etype}-folder"})
                ET.SubElement(attvalues, "attvalue", {"for": "1", "value": "1"})
                edge_counter += 1

    # Entity ↔ Entity edges (co-occurrence in same folder)
    for (a, b), data in sorted(entity_cooccurrence.items(), key=lambda x: -x[1]["weight"]):
        a_node = node_id_map.get(a)
        b_node = node_id_map.get(b)
        if a_node and b_node:
            edge_el = ET.SubElement(edges_el, "edge", {
                "id": str(edge_counter),
                "source": a_node,
                "target": b_node,
                "weight": str(data["weight"])
            })
            attvalues = ET.SubElement(edge_el, "attvalues")
            ET.SubElement(attvalues, "attvalue", {"for": "0", "value": "entity-entity"})
            ET.SubElement(attvalues, "attvalue", {"for": "1", "value": str(len(data["shared_folders"]))})
            edge_counter += 1

    # Write formatted XML
    xml_str = ET.tostring(gexf, encoding="unicode")
    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Count by type
    type_counts = defaultdict(int)
    for ek in active_entities:
        type_counts[ek[0]] += 1

    print(f"GEXF archival network: {output_path}")
    print(f"  PERSON nodes: {type_counts.get('PERSON', 0)}")
    print(f"  ORG nodes: {type_counts.get('ORG', 0)}")
    print(f"  LOCATION nodes: {type_counts.get('LOCATION', 0)}")
    print(f"  DATE nodes: {type_counts.get('DATE', 0)}")
    print(f"  MONEY nodes: {type_counts.get('MONEY', 0)}")
    print(f"  PRODUCT nodes: {type_counts.get('PRODUCT', 0)}")
    print(f"  WORK_OF_ART nodes: {type_counts.get('WORK_OF_ART', 0)}")
    print(f"  FOLDER nodes: {len(folder_info)}")
    print(f"  Total edges: {edge_counter}")


# ============================================================================
# Step 7: Generate master JSON (flat documents with full data)
# ============================================================================

def create_master_json(metadata_files, page_files, output_path):
    """
    Create a master JSON containing all documents with full OCR text and entities.
    
    Handles two file formats:
    1. Multi-page PDFs: metadata JSON + separate page JSONs (linked by parent_document)
    2. Standalone files: single JSON with all data (no parent_document, file_info at top level)
    
    Includes human validation data when present:
    - human_transcription (edited text)
    - named_entities.validations (entity approve/reject)
    - metadata_validations (Dublin Core field approve/reject)
    """
    print("  Parsing metadata files...")
    
    # Parse all metadata, indexed by source document
    metadata_index = {}
    for mf in metadata_files:
        try:
            with open(mf, "r", encoding="utf-8") as f:
                data = json.load(f)
            doc_key = data.get("source_document", "")
            if doc_key:
                metadata_index[doc_key] = {
                    "filepath": mf,
                    "data": data
                }
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"    WARNING: Could not parse metadata file: {mf} ({e})")

    # Separate page files into two categories:
    # - Standard pages (have parent_document) 
    # - Standalone files (no parent_document, have file_info at top level)
    print("  Parsing page files...")
    pages_by_doc = defaultdict(list)
    standalone_files = []
    orphaned_pages = []
    parse_errors = 0

    for i, pf in enumerate(page_files):
        try:
            with open(pf, "r", encoding="utf-8") as f:
                page_data = json.load(f)
            
            parent = page_data.get("parent_document", "")
            
            if parent:
                # Standard multi-page format
                if parent in metadata_index:
                    pages_by_doc[parent].append(page_data)
                else:
                    orphaned_pages.append(pf)
            else:
                # Standalone file format (UMN style)
                page_data["_source_path"] = pf
                standalone_files.append(page_data)
                
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            parse_errors += 1
            if parse_errors <= 5:
                print(f"    ERROR: {pf}: {e}")

        if (i + 1) % 2000 == 0:
            print(f"    Pages: {i+1}/{len(page_files)} ({len(standalone_files)} standalone)")

    print(f"  Page parsing complete:")
    print(f"    Multi-page docs with pages: {len(pages_by_doc)}")
    print(f"    Standalone files: {len(standalone_files)}")
    print(f"    Orphaned pages: {len(orphaned_pages)}")
    print(f"    Parse errors: {parse_errors}")

    # Build flat documents array
    print("  Assembling documents...")
    documents = []
    duplicate_pages_count = 0
    mismatched_docs = 0

    # Process standard multi-page documents
    for doc_key, meta_entry in sorted(metadata_index.items()):
        meta_data = meta_entry["data"]
        
        archival = meta_data.get("archival_context", {})
        dublin_core = meta_data.get("dublin_core_metadata", {})
        file_info = meta_data.get("file_info", {})
        expected_pages = meta_data.get("pages", [])

        # Get and sort pages
        raw_pages = pages_by_doc.get(doc_key, [])
        
        # Check for duplicates
        seen_page_numbers = set()
        deduped_pages = []
        for p in raw_pages:
            pnum = p.get("page_number", 0)
            if pnum in seen_page_numbers:
                duplicate_pages_count += 1
            else:
                seen_page_numbers.add(pnum)
                deduped_pages.append(p)

        deduped_pages.sort(key=lambda p: p.get("page_number", 0))

        if expected_pages and len(deduped_pages) != len(expected_pages):
            mismatched_docs += 1

        # Build page records
        page_records = []
        for p in deduped_pages:
            page_records.append(_build_page_record(p))

        # Clean dublin_core
        dc_clean = {k: v for k, v in dublin_core.items() if k != "_generation_info"} if dublin_core else {}

        doc_record = {
            "source_document": doc_key,
            "document_type": "multi_page",
            "collection": archival.get("collection", ""),
            "box": archival.get("box", ""),
            "folder": archival.get("folder", ""),
            "dublin_core": dc_clean,
            "file_info": {
                "file_type": file_info.get("file_type", ""),
                "file_size_bytes": file_info.get("file_size_bytes", 0),
                "total_pages": file_info.get("total_pages", 0),
                "date_processed": file_info.get("date_processed", "")
            },
            "pages": page_records
        }
        documents.append(doc_record)

    # Process standalone files (UMN format)
    for sf in standalone_files:
        file_info = sf.get("file_info", {})
        archival = sf.get("archival_context", {})
        dublin_core = sf.get("dublin_core_metadata", {})
        source_file = file_info.get("source_file", sf.get("_source_path", ""))

        dc_clean = {k: v for k, v in dublin_core.items() if k != "_generation_info"} if dublin_core else {}

        # Build the single page record
        page_record = _build_page_record(sf)

        doc_record = {
            "source_document": source_file,
            "document_type": "standalone",
            "collection": archival.get("collection", ""),
            "box": archival.get("box", ""),
            "folder": archival.get("folder", ""),
            "dublin_core": dc_clean,
            "file_info": {
                "file_type": file_info.get("file_type", ""),
                "file_size_bytes": file_info.get("file_size_bytes", 0),
                "total_pages": 1,
                "date_processed": file_info.get("date_processed", "")
            },
            "pages": [page_record]
        }
        documents.append(doc_record)

    # Build final output
    master = {
        "metadata": {
            "generated_at": str(os.popen("echo %date% %time%").read().strip()) if os.name == "nt" else "",
            "source_directory": DATA_ROOT,
            "stats": {
                "total_documents": len(documents),
                "total_pages": sum(len(d["pages"]) for d in documents),
                "multi_page_documents": sum(1 for d in documents if d["document_type"] == "multi_page"),
                "standalone_documents": sum(1 for d in documents if d["document_type"] == "standalone"),
                "pages_with_human_transcription": sum(
                    1 for d in documents for p in d["pages"] if p.get("human_transcription")
                ),
                "pages_with_entity_validations": sum(
                    1 for d in documents for p in d["pages"] if p.get("entity_validations")
                ),
                "pages_with_metadata_validations": sum(
                    1 for d in documents for p in d["pages"] if p.get("metadata_validations")
                ),
                "orphaned_pages": len(orphaned_pages),
                "duplicate_pages_removed": duplicate_pages_count,
                "page_count_mismatches": mismatched_docs,
                "parse_errors": parse_errors
            }
        },
        "documents": documents
    }

    # Write
    print(f"  Writing JSON ({len(documents)} documents, {master['metadata']['stats']['total_pages']} pages)...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=1)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Master JSON: {output_path}")
    print(f"    File size: {file_size_mb:.1f} MB")
    print(f"    Documents: {len(documents)} ({master['metadata']['stats']['multi_page_documents']} multi-page, {master['metadata']['stats']['standalone_documents']} standalone)")
    print(f"    Pages: {master['metadata']['stats']['total_pages']}")
    print(f"    Human transcriptions: {master['metadata']['stats']['pages_with_human_transcription']}")
    print(f"    Entity validations: {master['metadata']['stats']['pages_with_entity_validations']}")
    print(f"    Metadata validations: {master['metadata']['stats']['pages_with_metadata_validations']}")
    if orphaned_pages:
        print(f"    WARNING: {len(orphaned_pages)} orphaned page files (no matching metadata)")
    if duplicate_pages_count:
        print(f"    WARNING: {duplicate_pages_count} duplicate pages removed")
    if mismatched_docs:
        print(f"    WARNING: {mismatched_docs} documents with page count mismatch")
    if parse_errors:
        print(f"    WARNING: {parse_errors} files with parse errors")


def _build_page_record(page_data):
    """Build a normalized page record from either format."""
    # OCR
    ocr_results = page_data.get("ocr_results", {})
    engines = ocr_results.get("engines", {})
    ground_truth = ocr_results.get("ground_truth_engine", "")

    ocr_versions = {}
    for eng_name, eng_data in engines.items():
        text = eng_data.get("text", "")
        if text:
            ocr_versions[eng_name] = text

    # Entities (raw)
    ner_data = page_data.get("named_entities", {})
    entities = ner_data.get("entities", {})
    
    # Entity validations (human review)
    entity_validations = ner_data.get("validations", None)

    # Human transcription
    human_tx = page_data.get("human_transcription", None)

    # Metadata validations
    metadata_vals = page_data.get("metadata_validations", None)

    record = {
        "page_number": page_data.get("page_number", 1),
        "file_id": page_data.get("file_id", page_data.get("file_info", {}).get("file_id", "")),
        "ground_truth_engine": ground_truth,
        "ocr_versions": ocr_versions,
        "named_entities": entities,
    }

    # Only include validated/human data if present
    if entity_validations:
        record["entity_validations"] = entity_validations
    if human_tx:
        record["human_transcription"] = human_tx
    if metadata_vals:
        record["metadata_validations"] = metadata_vals

    return record


# ============================================================================
# Main
# ============================================================================

def main():
    overall_start = time.time()
    print(f"Scanning: {DATA_ROOT}")
    print(f"Output:   {OUTPUT_DIR}")
    print("=" * 60)

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Find files
    t0 = time.time()
    metadata_files, page_files = find_json_files(DATA_ROOT)
    print(f"[Step 1] Found {len(metadata_files)} metadata files, {len(page_files)} page/standalone files ({time.time()-t0:.1f}s)")
    if metadata_files:
        print(f"  Sample metadata: {metadata_files[0]}")
    if page_files:
        print(f"  Sample page: {page_files[0]}")
    print()

    # Step 2: Parse and aggregate
    t0 = time.time()
    print("[Step 2] Parsing and aggregating files...")
    documents, pages, entities = aggregate_data(metadata_files, page_files)
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Documents: {len(documents)}")
    print(f"  Pages: {len(pages)}")
    print(f"  Entity mentions: {len(entities)}")
    # Entity type breakdown
    type_counter = Counter(e["entity_type"] for e in entities)
    print(f"  Entity type breakdown:")
    for etype, count in type_counter.most_common():
        print(f"    {etype}: {count}")
    print()

    # Step 2.5: Entity resolution (PERSON cleanup)
    t0 = time.time()
    print("[Step 2.5] Resolving PERSON entities...")
    
    if os.path.exists(APPROVED_FILE):
        # Use manually reviewed merges
        print(f"  Found approved merges file: {APPROVED_FILE}")
        entities = apply_approved_merges(entities, APPROVED_FILE)
    else:
        # Generate review file for manual editing (from raw entities)
        print("  No approved merges file found. Running automatic resolution...")
        print()
        print("  Generating review file for manual evaluation...")
        generate_review_file(entities, REVIEW_FILE)
        
        # Also apply automatic resolution for immediate (unreviewed) export
        entities, merge_log = resolve_person_entities(entities)
        print(f"  Entities after auto-resolution: {len(entities)}")
        
        # Save merge log
        with open(MERGES_FILE, "w", encoding="utf-8") as f:
            json.dump(merge_log, f, indent=2, ensure_ascii=False)
        print(f"  Merge log saved: {MERGES_FILE}")
        print()
        print("  *** REVIEW AVAILABLE ***")
        print(f"  To manually review merges, edit: {REVIEW_FILE}")
        print(f"  Then save/rename it to: {APPROVED_FILE}")
        print(f"  Re-run this script to apply your reviewed merges instead.")
    
    print(f"  Resolution completed in {time.time()-t0:.1f}s")
    print()

    # Determine which steps to run
    # Usage: python export_archive_data.py --steps 7
    #        python export_archive_data.py --steps 3,4,7
    #        python export_archive_data.py  (runs all enabled steps)
    requested_steps = None
    if '--steps' in sys.argv:
        idx = sys.argv.index('--steps')
        if idx + 1 < len(sys.argv):
            requested_steps = set(int(s) for s in sys.argv[idx + 1].split(','))
            print(f"Running only steps: {sorted(requested_steps)}")
            print()

    def should_run(step_num):
        return requested_steps is None or step_num in requested_steps

    # Step 3: SQLite
    if should_run(3):
        t0 = time.time()
        print("[Step 3] Creating SQLite database...")
        create_sqlite(documents, pages, entities, SQLITE_FILE)
        print(f"  Completed in {time.time()-t0:.1f}s")
        print()

    # Step 4: CSV
    if should_run(4):
        t0 = time.time()
        print("[Step 4] Creating CSV export...")
        create_csv(documents, pages, entities, CSV_FILE)
        print(f"  Completed in {time.time()-t0:.1f}s")
        print()

    # Step 5: GEXF co-occurrence network
    # NOTE: Disabled by default — produces files too large with full dataset.
    # To run: python export_archive_data.py --steps 5
    if should_run(5) and requested_steps is not None:
        t0 = time.time()
        print("[Step 5] Creating GEXF co-occurrence network...")
        create_gexf(entities, GEXF_FILE)
        print(f"  Completed in {time.time()-t0:.1f}s")
        print()
    elif should_run(5):
        print("[Step 5] SKIPPED (co-occurrence GEXF disabled — too large)")
        print("  To force: python export_archive_data.py --steps 5")
        print()

    # Step 6: GEXF archival context network
    if should_run(6):
        t0 = time.time()
        print("[Step 6] Creating GEXF archival context network...")
        create_gexf_archival(entities, GEXF_ARCHIVAL_FILE)
        print(f"  Completed in {time.time()-t0:.1f}s")
        print()

    # Step 7: Master JSON
    if should_run(7):
        t0 = time.time()
        print("[Step 7] Creating master JSON...")
        create_master_json(metadata_files, page_files, MASTER_JSON_FILE)
        print(f"  Completed in {time.time()-t0:.1f}s")
        print()

    total_elapsed = time.time() - overall_start
    print("=" * 60)
    print(f"Done! Total time: {total_elapsed:.1f}s")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"FATAL ERROR: {e}")
        print(f"{'='*60}")
        traceback.print_exc()
        input("\nPress Enter to exit...")
