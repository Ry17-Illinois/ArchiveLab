#!/usr/bin/env python3
"""
Prepare Multi-Document Editathon Dataset
Extracts page data from multiple PDF documents for sequential editathon review
"""

import json
import os
from pathlib import Path
import fitz  # PyMuPDF


def prepare_multi_document_dataset(pdf_paths, output_dir='.'):
    """
    Prepare dataset from multiple PDF documents with sequential page numbering
    
    Args:
        pdf_paths: List of paths to PDF files
        output_dir: Directory to save JSON output
    
    Returns:
        Dictionary with page data in sequential order across all documents
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create images directory
    images_dir = output_dir / 'images'
    images_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("MULTI-DOCUMENT EDITATHON DATASET PREPARATION")
    print("=" * 80)
    print(f"\nProcessing {len(pdf_paths)} documents...")
    print(f"Output directory: {output_dir.absolute()}\n")
    
    all_pages = []
    global_page_number = 1
    total_images_extracted = 0
    
    for doc_index, pdf_path in enumerate(pdf_paths, 1):
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            print(f"[WARNING] PDF not found, skipping: {pdf_path}")
            continue
        
        print(f"\n[{doc_index}/{len(pdf_paths)}] Processing: {pdf_path.name}")
        print("-" * 80)
        
        # Find metadata JSON
        metadata_json = pdf_path.parent / f"{pdf_path.stem}_metadata.json"
        
        if not metadata_json.exists():
            print(f"  [WARNING] Metadata JSON not found, skipping: {metadata_json.name}")
            continue
        
        # Load metadata
        with open(metadata_json, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        total_pages = metadata.get('file_info', {}).get('total_pages', 0)
        dublin_core = metadata.get('dublin_core_metadata', {})
        archival_context = metadata.get('archival_context', {})
        
        print(f"  Document pages: {total_pages}")
        if dublin_core.get('title'):
            print(f"  Title: {dublin_core['title']}")
        
        # Extract page images from PDF
        try:
            pdf_doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"  [ERROR] Could not open PDF: {e}")
            continue
        
        pages_processed = 0
        
        for page_num in range(1, total_pages + 1):
            # Try single-digit format first (Page1, Page2, etc.)
            page_json = pdf_path.parent / f"{pdf_path.stem}_Page{page_num}.json"
            
            # If not found, try two-digit format (Page01, Page02, etc.)
            if not page_json.exists():
                page_json = pdf_path.parent / f"{pdf_path.stem}_Page{page_num:02d}.json"
            
            if not page_json.exists():
                print(f"    [WARNING] Page JSON not found for page {page_num}")
                continue
            
            with open(page_json, 'r', encoding='utf-8') as f:
                page_data = json.load(f)
            
            # Extract OCR versions
            ocr_results = page_data.get('ocr_results', {})
            ocr_versions = {}
            
            engines = ocr_results.get('engines', {})
            for engine_name, engine_data in engines.items():
                if engine_data.get('status') == 'completed' and 'text' in engine_data:
                    ocr_versions[engine_name] = engine_data['text']
            
            # Extract entities
            entities = page_data.get('named_entities', {}).get('entities', {})
            
            # Extract page image
            image_filename = f"page_{global_page_number:04d}.jpg"
            image_path = images_dir / image_filename
            
            try:
                # PyMuPDF uses 0-based indexing
                page = pdf_doc[page_num - 1]
                
                # Render page to image at 2x resolution
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                
                # Save as JPEG
                pix.save(image_path)
                total_images_extracted += 1
                
            except Exception as e:
                print(f"    [WARNING] Failed to extract image for page {page_num}: {e}")
            
            # Build page record with GLOBAL page number
            page_record = {
                'page_id': f"page_{global_page_number:04d}",
                'page_number': global_page_number,  # Sequential across all documents
                'json_file': page_json.name,
                'ocr_versions': ocr_versions,
                'entities': entities,
                'metadata': {
                    'dublin_core': dublin_core,
                    'archival_context': archival_context
                },
                'source_document': pdf_path.name,
                'source_page_number': page_num  # Original page number within document
            }
            
            all_pages.append(page_record)
            pages_processed += 1
            global_page_number += 1
            
            if pages_processed % 50 == 0:
                print(f"    Processed {pages_processed}/{total_pages} pages...")
        
        pdf_doc.close()
        print(f"  [OK] Processed {pages_processed} pages from this document")
    
    print("\n" + "=" * 80)
    print("GENERATING OUTPUT FILES")
    print("=" * 80)
    
    # Generate output JSON
    dataset = {
        'pages': all_pages
    }
    
    output_file = output_dir / 'editathon_dataset.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
    
    print(f"\n[OK] Generated: {output_file.name}")
    
    # Generate entity summary for reference
    entity_summary = {}
    for page in all_pages:
        for entity_type, entity_list in page['entities'].items():
            if entity_type not in entity_summary:
                entity_summary[entity_type] = set()
            entity_summary[entity_type].update(entity_list)
    
    summary_file = output_dir / 'entity_summary.json'
    entity_summary_serializable = {k: sorted(list(v)) for k, v in entity_summary.items()}
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(entity_summary_serializable, f, indent=2)
    
    print(f"[OK] Generated: {summary_file.name}")
    
    # Generate document manifest
    manifest = {
        'total_documents': len(pdf_paths),
        'total_pages': len(all_pages),
        'documents': []
    }
    
    current_doc = None
    doc_start_page = 1
    
    for page in all_pages:
        if current_doc != page['source_document']:
            if current_doc is not None:
                # Save previous document info
                manifest['documents'][-1]['page_range'] = f"{doc_start_page}-{page['page_number']-1}"
                manifest['documents'][-1]['total_pages'] = page['page_number'] - doc_start_page
            
            # Start new document
            manifest['documents'].append({
                'filename': page['source_document'],
                'start_page': page['page_number'],
                'dublin_core': page['metadata']['dublin_core'],
                'archival_context': page['metadata']['archival_context']
            })
            current_doc = page['source_document']
            doc_start_page = page['page_number']
    
    # Close last document
    if manifest['documents']:
        manifest['documents'][-1]['page_range'] = f"{doc_start_page}-{all_pages[-1]['page_number']}"
        manifest['documents'][-1]['total_pages'] = all_pages[-1]['page_number'] - doc_start_page + 1
    
    manifest_file = output_dir / 'document_manifest.json'
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"[OK] Generated: {manifest_file.name}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Documents processed: {len(manifest['documents'])}")
    print(f"Total pages: {len(all_pages)}")
    print(f"Images extracted: {total_images_extracted}")
    print(f"\nEntity types found:")
    for entity_type, entities in entity_summary_serializable.items():
        print(f"  - {entity_type}: {len(entities)} unique entities")
    print(f"\nDocument breakdown:")
    for doc in manifest['documents']:
        print(f"  - {doc['filename']}: pages {doc['page_range']} ({doc['total_pages']} pages)")
    print(f"\nOutput directory: {output_dir.absolute()}")
    print(f"  - editathon_dataset.json: Sequential page data ({len(all_pages)} pages)")
    print(f"  - entity_summary.json: Entity reference list")
    print(f"  - document_manifest.json: Document breakdown")
    print(f"  - images/: {total_images_extracted} page images (JPEGs)")
    print("=" * 80)
    
    return dataset


def prepare_directory_dataset(directory, output_dir='.'):
    """
    Prepare dataset from a directory of image files with JSON sidecars.
    Recursively finds all image+sidecar pairs and creates sequential editathon data.
    
    Args:
        directory: Root directory to scan for image files with JSON sidecars
        output_dir: Directory to save JSON output and images
    """
    from PIL import Image
    
    directory = Path(directory)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / 'images'
    images_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("DIRECTORY-BASED EDITATHON DATASET PREPARATION")
    print("=" * 80)
    print(f"\nScanning: {directory}")
    print(f"Output: {output_dir.absolute()}\n")
    
    # Find all image files with matching JSON sidecars
    image_extensions = {'.tif', '.tiff', '.jpg', '.jpeg', '.png'}
    pairs = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in image_extensions:
                # Look for matching JSON sidecar
                sidecar_path = file_path.with_suffix('.json')
                if sidecar_path.exists():
                    pairs.append((file_path, sidecar_path))
    
    pairs.sort(key=lambda p: str(p[0]))
    print(f"Found {len(pairs)} image+sidecar pairs\n")
    
    if not pairs:
        print("No image files with JSON sidecars found.")
        return None
    
    all_pages = []
    global_page_number = 1
    total_images_extracted = 0
    
    for image_path, sidecar_path in pairs:
        try:
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                sidecar_data = json.load(f)
        except Exception as e:
            print(f"  [ERROR] Reading {sidecar_path.name}: {e}")
            continue
        
        # Extract OCR versions
        ocr_versions = {}
        ocr_results = sidecar_data.get('ocr_results', {})
        engines = ocr_results.get('engines', {})
        for engine_name, engine_data in engines.items():
            if engine_data.get('status') == 'completed' and 'text' in engine_data:
                ocr_versions[engine_name] = engine_data['text']
        
        # Extract entities
        entities = sidecar_data.get('named_entities', {}).get('entities', {})
        
        # Extract metadata
        dublin_core = sidecar_data.get('dublin_core_metadata', {})
        archival_context = sidecar_data.get('archival_context', {})
        
        # Convert image to JPEG
        image_filename = f"page_{global_page_number:04d}.jpg"
        output_image_path = images_dir / image_filename
        
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Resize if very large
                max_dim = 2000
                if max(img.size) > max_dim:
                    ratio = max_dim / max(img.size)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                img.save(output_image_path, 'JPEG', quality=85)
            total_images_extracted += 1
        except Exception as e:
            print(f"  [ERROR] Converting {image_path.name}: {e}")
            continue
        
        # Compute relative path for source tracking
        try:
            rel_path = image_path.relative_to(directory)
        except ValueError:
            rel_path = image_path.name
        
        # Build page record
        page_record = {
            'page_id': f"page_{global_page_number:04d}",
            'page_number': global_page_number,
            'json_file': sidecar_path.name,
            'ocr_versions': ocr_versions,
            'entities': entities,
            'metadata': {
                'dublin_core': dublin_core,
                'archival_context': archival_context
            },
            'source_document': image_path.name,
            'source_path': str(rel_path),
            'source_page_number': 1
        }
        
        all_pages.append(page_record)
        global_page_number += 1
        
        if global_page_number % 50 == 0:
            print(f"  Processed {global_page_number - 1} files...")
    
    print(f"\n  Processed {len(all_pages)} total files")
    
    # Generate output JSON
    dataset = {'pages': all_pages}
    
    output_file = output_dir / 'editathon_dataset.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
    print(f"\n[OK] Generated: {output_file.name}")
    
    # Generate entity summary
    entity_summary = {}
    for page in all_pages:
        for entity_type, entity_list in page['entities'].items():
            if entity_type not in entity_summary:
                entity_summary[entity_type] = set()
            entity_summary[entity_type].update(entity_list)
    
    entity_summary_serializable = {k: sorted(list(v)) for k, v in entity_summary.items()}
    summary_file = output_dir / 'entity_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(entity_summary_serializable, f, indent=2)
    print(f"[OK] Generated: {summary_file.name}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Images processed: {len(all_pages)}")
    print(f"Images extracted: {total_images_extracted}")
    print(f"\nEntity types found:")
    for entity_type, entities in entity_summary_serializable.items():
        print(f"  - {entity_type}: {len(entities)} unique entities")
    print(f"\nOutput directory: {output_dir.absolute()}")
    print(f"  - editathon_dataset.json: Sequential page data ({len(all_pages)} pages)")
    print(f"  - entity_summary.json: Entity reference list")
    print(f"  - images/: {total_images_extracted} page images (JPEGs)")
    print("=" * 80)
    
    return dataset


def main():
    """Command-line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("=" * 80)
        print("Prepare Editathon Dataset")
        print("=" * 80)
        print("\nPrepares sequential page data for editathon from PDFs or image directories")
        print("\nUsage (PDF mode):")
        print("  python prepare_editathon_dataset_multi.py <pdf1> <pdf2> ... [--output <dir>]")
        print("\nUsage (Directory mode - for image archives):")
        print("  python prepare_editathon_dataset_multi.py --directory <archive_dir> [--output <dir>]")
        print("\nArguments:")
        print("  pdf1, pdf2, ...    - Paths to PDF files with JSON sidecars")
        print("  --directory <dir>  - Scan directory for image files with JSON sidecars")
        print("  --output <dir>    - Output directory (default: editathon_data)")
        print("\nExamples:")
        print('  # PDF mode:')
        print('  python prepare_editathon_dataset_multi.py \\')
        print('    "path/to/Letterbook 1.pdf" "path/to/Letterbook 2.pdf" --output editathon_data')
        print()
        print('  # Directory mode (images + sidecars):')
        print('  python prepare_editathon_dataset_multi.py \\')
        print('    --directory "D:\\ArchiveData\\University of Minnesota" --output editathon_data')
        print("\nOutput:")
        print("  - editathon_dataset.json: Sequential page data with global page numbers")
        print("  - entity_summary.json: Reference list of all entities")
        print("  - images/: Page images as JPEGs")
        print("=" * 80)
        sys.exit(1)
    
    # Parse arguments
    pdf_paths = []
    output_dir = 'editathon_data'
    directory_mode = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--output':
            if i + 1 < len(sys.argv):
                output_dir = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --output requires a directory argument")
                sys.exit(1)
        elif sys.argv[i] == '--directory':
            if i + 1 < len(sys.argv):
                directory_mode = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --directory requires a path argument")
                sys.exit(1)
        else:
            pdf_paths.append(sys.argv[i])
            i += 1
    
    try:
        if directory_mode:
            if not os.path.isdir(directory_mode):
                print(f"Error: Directory not found: {directory_mode}")
                sys.exit(1)
            prepare_directory_dataset(directory_mode, output_dir)
        elif pdf_paths:
            prepare_multi_document_dataset(pdf_paths, output_dir)
        else:
            print("Error: Specify either PDF files or --directory")
            sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
