#!/usr/bin/env python3
"""
Archive Report Generator
Scans archive directory for JSON sidecars and generates summary report
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class ArchiveReporter:
    def __init__(self, base_directory):
        self.base_directory = base_directory
        self.data = {
            'collections': defaultdict(lambda: defaultdict(dict)),
            'totals': {
                'files': 0,
                'pdfs': 0,
                'images': 0,
                'other': 0,
                'metadata_files': 0,
                'page_files': 0,
                'total_pages': 0
            },
            'entities': {
                'PERSON': defaultdict(lambda: {'count': 0, 'documents': []}),
                'ORG': defaultdict(lambda: {'count': 0, 'documents': []})
            },
            'entity_instances': defaultdict(lambda: defaultdict(list))
        }
        self.files_with_sidecars = set()
        self.original_files = set()
    
    def scan(self):
        """Scan directory structure for files and JSON sidecars"""
        print(f"Scanning: {self.base_directory}")
        
        for root, dirs, files in os.walk(self.base_directory):
            for file in files:
                filepath = os.path.join(root, file)
                
                # Parse archival structure
                rel_path = os.path.relpath(filepath, self.base_directory)
                parts = rel_path.split(os.sep)
                
                if len(parts) < 3:
                    continue
                
                collection = parts[0]
                box = parts[1] if len(parts) > 1 else 'Unknown'
                folder = parts[2] if len(parts) > 2 else 'Unknown'
                
                # Count original files (exclude JSON)
                if file.endswith('.json'):
                    # Track which files have sidecars
                    if file.endswith('_metadata.json'):
                        base_name = file.replace('_metadata.json', '')
                        self.files_with_sidecars.add(os.path.join(root, base_name + '.pdf'))
                        self.data['totals']['metadata_files'] += 1
                        self._process_metadata_json(filepath, collection, box, folder)
                    elif '_Page' in file:
                        base_name = file.split('_Page')[0]
                        self.files_with_sidecars.add(os.path.join(root, base_name + '.pdf'))
                        self.data['totals']['page_files'] += 1
                        self.data['totals']['total_pages'] += 1
                        self._process_page_json(filepath, collection, box, folder)
                    else:
                        # Image sidecar
                        base_name = file.replace('.json', '')
                        for ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                            potential_file = os.path.join(root, base_name + ext)
                            if os.path.exists(potential_file):
                                self.files_with_sidecars.add(potential_file)
                                self._process_image_sidecar(filepath, collection, box, folder)
                                break
                elif file.endswith('.pdf'):
                    self.original_files.add(filepath)
                    self.data['totals']['pdfs'] += 1
                    self.data['totals']['files'] += 1
                elif file.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                    self.original_files.add(filepath)
                    self.data['totals']['images'] += 1
                    self.data['totals']['files'] += 1
                else:
                    self.original_files.add(filepath)
                    self.data['totals']['other'] += 1
                    self.data['totals']['files'] += 1
    
    def _process_metadata_json(self, filepath, collection, box, folder):
        """Extract info from metadata JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if box not in self.data['collections'][collection]:
                self.data['collections'][collection][box] = {}
            
            if folder not in self.data['collections'][collection][box]:
                self.data['collections'][collection][box][folder] = {
                    'files': [],
                    'total_pages': 0,
                    'ocr_engines': set(),
                    'entities': {'PERSON': 0, 'ORG': 0, 'GPE': 0}
                }
            
            folder_data = self.data['collections'][collection][box][folder]
            
            # Extract file info
            file_info = {
                'filename': data.get('source_document', ''),
                'total_pages': data.get('file_info', {}).get('total_pages', 0),
                'has_metadata': bool(data.get('dublin_core_metadata', {}).get('title'))
            }
            
            folder_data['files'].append(file_info)
            folder_data['total_pages'] += file_info['total_pages']
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    def _process_page_json(self, filepath, collection, box, folder):
        """Extract info from page JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if box not in self.data['collections'][collection]:
                self.data['collections'][collection][box] = {}
            
            if folder not in self.data['collections'][collection][box]:
                self.data['collections'][collection][box][folder] = {
                    'files': [],
                    'total_pages': 0,
                    'ocr_engines': set(),
                    'entities': {'PERSON': 0, 'ORG': 0, 'GPE': 0}
                }
            
            folder_data = self.data['collections'][collection][box][folder]
            
            # Extract OCR engines used
            ocr_results = data.get('ocr_results', {})
            for engine, engine_data in ocr_results.get('engines', {}).items():
                if engine_data.get('status') == 'completed':
                    model_name = engine_data.get('model_name', engine)
                    folder_data['ocr_engines'].add(model_name)
            
            # Count entities
            entities = data.get('named_entities', {}).get('entities', {})
            source_file = data.get('file_info', {}).get('source_file', os.path.basename(filepath))
            page_number = data.get('page_number', 0)
            
            # Get OCR text for context extraction
            ocr_results = data.get('ocr_results', {})
            ground_truth_engine = ocr_results.get('ground_truth_engine', 'easyocr')
            ocr_text = ''
            
            # Try to get text from ground truth engine
            engines = ocr_results.get('engines', {})
            if ground_truth_engine in engines:
                ocr_text = engines[ground_truth_engine].get('text', '')
            else:
                # Fallback to first completed engine
                for engine_data in engines.values():
                    if engine_data.get('status') == 'completed':
                        ocr_text = engine_data.get('text', '')
                        break
            
            for entity_type, entity_list in entities.items():
                if entity_type in folder_data['entities']:
                    folder_data['entities'][entity_type] += len(entity_list)
                
                # Aggregate all entity types globally
                if entity_type not in self.data['entities']:
                    self.data['entities'][entity_type] = defaultdict(lambda: {'count': 0, 'documents': []})
                
                for entity_name in entity_list:
                    if entity_name and entity_name.strip():
                        self.data['entities'][entity_type][entity_name]['count'] += 1
                        if source_file not in self.data['entities'][entity_type][entity_name]['documents']:
                            self.data['entities'][entity_type][entity_name]['documents'].append(source_file)
                        
                        # Store instance with full page text
                        instance = {
                            'document': source_file,
                            'page_number': page_number,
                            'text_sample': ocr_text.replace('\n', ' ').replace('\r', ' ').strip()
                        }
                        
                        # Only add if not already added for this page
                        existing = self.data['entity_instances'][entity_type][entity_name]
                        if not any(i['document'] == source_file and i['page_number'] == page_number for i in existing):
                            self.data['entity_instances'][entity_type][entity_name].append(instance)
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    def _process_image_sidecar(self, filepath, collection, box, folder):
        """Extract info from image sidecar JSON (same structure as page JSON)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if box not in self.data['collections'][collection]:
                self.data['collections'][collection][box] = {}
            
            if folder not in self.data['collections'][collection][box]:
                self.data['collections'][collection][box][folder] = {
                    'files': [],
                    'total_pages': 0,
                    'ocr_engines': set(),
                    'entities': {'PERSON': 0, 'ORG': 0, 'GPE': 0}
                }
            
            folder_data = self.data['collections'][collection][box][folder]
            
            # Count as a page
            folder_data['total_pages'] += 1
            self.data['totals']['total_pages'] += 1
            
            # Extract OCR engines used
            ocr_results = data.get('ocr_results', {})
            for engine, engine_data in ocr_results.get('engines', {}).items():
                if engine_data.get('status') == 'completed':
                    model_name = engine_data.get('model_name', engine)
                    folder_data['ocr_engines'].add(model_name)
            
            # Count entities
            entities = data.get('named_entities', {}).get('entities', {})
            source_file = data.get('file_info', {}).get('source_file', os.path.basename(filepath).replace('.json', ''))
            page_number = data.get('page_number', 1)
            
            # Get OCR text for context
            ground_truth_engine = ocr_results.get('ground_truth_engine', 'easyocr')
            ocr_text = ''
            engines = ocr_results.get('engines', {})
            if ground_truth_engine in engines:
                ocr_text = engines[ground_truth_engine].get('text', '')
            else:
                for engine_data in engines.values():
                    if engine_data.get('status') == 'completed':
                        ocr_text = engine_data.get('text', '')
                        break
            
            for entity_type, entity_list in entities.items():
                if entity_type in folder_data['entities']:
                    folder_data['entities'][entity_type] += len(entity_list)
                
                if entity_type not in self.data['entities']:
                    self.data['entities'][entity_type] = defaultdict(lambda: {'count': 0, 'documents': []})
                
                for entity_name in entity_list:
                    if entity_name and entity_name.strip():
                        self.data['entities'][entity_type][entity_name]['count'] += 1
                        if source_file not in self.data['entities'][entity_type][entity_name]['documents']:
                            self.data['entities'][entity_type][entity_name]['documents'].append(source_file)
                        
                        instance = {
                            'document': source_file,
                            'page_number': page_number,
                            'text_sample': ocr_text.replace('\n', ' ').replace('\r', ' ').strip()
                        }
                        
                        existing = self.data['entity_instances'][entity_type][entity_name]
                        if not any(i['document'] == source_file and i['page_number'] == page_number for i in existing):
                            self.data['entity_instances'][entity_type][entity_name].append(instance)
            
            # Also track file info (like metadata does for PDFs)
            file_info = {
                'filename': source_file,
                'total_pages': 1,
                'has_metadata': bool(data.get('dublin_core_metadata', {}).get('title'))
            }
            folder_data['files'].append(file_info)
            
        except Exception as e:
            print(f"Error processing image sidecar {filepath}: {e}")
    
    def _extract_context(self, text, entity_name, context_length=200):
        """Extract context around entity mention"""
        if not text or not entity_name:
            return ''
        
        # Find entity in text (case insensitive)
        text_lower = text.lower()
        entity_lower = entity_name.lower()
        
        pos = text_lower.find(entity_lower)
        if pos == -1:
            return text[:context_length] if len(text) > context_length else text
        
        # Calculate start and end positions
        start = max(0, pos - context_length // 2)
        end = min(len(text), pos + len(entity_name) + context_length // 2)
        
        # Extract context
        context = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
        
        return context.replace('\n', ' ').replace('\r', ' ').strip()
    
    def generate_report(self, output_file=None):
        """Generate summary report (Option A format)"""
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("ARCHIVE ANALYSIS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Base Directory: {self.base_directory}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Overall summary
        report_lines.append("OVERALL SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Files: {self.data['totals']['files']}")
        report_lines.append(f"  - PDFs: {self.data['totals']['pdfs']}")
        report_lines.append(f"  - Images: {self.data['totals']['images']}")
        report_lines.append(f"  - Other: {self.data['totals']['other']}")
        
        files_with_sidecars = len(self.files_with_sidecars)
        files_without_sidecars = self.data['totals']['files'] - files_with_sidecars
        
        report_lines.append(f"Files with JSON Sidecars: {files_with_sidecars}")
        report_lines.append(f"Files without JSON Sidecars: {files_without_sidecars}")
        report_lines.append(f"Total Pages Processed: {self.data['totals']['total_pages']}")
        report_lines.append(f"Unique Persons Found: {len(self.data['entities'].get('PERSON', {}))}")
        report_lines.append(f"Unique Organizations Found: {len(self.data['entities'].get('ORG', {}))}")
        
        if self.data['totals']['files'] > 0:
            completion_rate = (files_with_sidecars / self.data['totals']['files']) * 100
            report_lines.append(f"Completion Rate: {completion_rate:.1f}%")
        
        report_lines.append("")
        
        # Collection details
        report_lines.append("COLLECTION DETAILS")
        report_lines.append("-" * 80)
        
        for collection, boxes in sorted(self.data['collections'].items()):
            report_lines.append(f"\nCollection: {collection}")
            
            for box, folders in sorted(boxes.items()):
                report_lines.append(f"  {box}:")
                
                for folder, folder_data in sorted(folders.items()):
                    report_lines.append(f"    {folder}/")
                    report_lines.append(f"      - Total files: {len(folder_data['files'])} PDFs")
                    
                    if len(folder_data['files']) > 0:
                        metadata_count = sum(1 for f in folder_data['files'] if f['has_metadata'])
                        metadata_pct = (metadata_count / len(folder_data['files'])) * 100
                        report_lines.append(f"      - Files with metadata: {metadata_count} ({metadata_pct:.0f}%)")
                    else:
                        report_lines.append(f"      - Files with metadata: 0 (0%)")
                    
                    report_lines.append(f"      - Total pages: {folder_data['total_pages']}")
                    
                    if folder_data['ocr_engines']:
                        engines_str = ', '.join(sorted(folder_data['ocr_engines']))
                        report_lines.append(f"      - OCR completed: {folder_data['total_pages']} pages ({engines_str})")
                    
                    total_entities = sum(folder_data['entities'].values())
                    if total_entities > 0:
                        report_lines.append(f"      - Entities found: {total_entities} "
                                          f"({folder_data['entities']['PERSON']} people, "
                                          f"{folder_data['entities']['ORG']} orgs, "
                                          f"{folder_data['entities']['GPE']} locations)")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        # Output
        report_text = '\n'.join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_file}")
        
        return report_text
    
    def generate_entity_csvs(self, output_dir='.'):
        """Generate CSV files for all entity types (aggregated and instance-by-instance)"""
        import csv
        
        for entity_type, entities in self.data['entities'].items():
            if not entities:
                continue
            
            # Generate aggregated CSV
            type_name = entity_type.lower().replace('_', '')
            agg_file = os.path.join(output_dir, f'entity_{type_name}.csv')
            
            with open(agg_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['entity_name', 'frequency', 'documents'])
                
                sorted_entities = sorted(entities.items(), key=lambda x: x[1]['count'], reverse=True)
                
                for entity_name, data in sorted_entities:
                    docs_str = ', '.join(data['documents'])
                    writer.writerow([entity_name, data['count'], docs_str])
            
            print(f"  - {agg_file}")
            
            # Generate instance-by-instance CSV (only for entities with 5+ mentions)
            instance_file = os.path.join(output_dir, f'instance_by_instance_{type_name}.csv')
            
            with open(instance_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['entity_name', 'document', 'page_number', 'text_sample'])
                
                sorted_entities = sorted(entities.items(), key=lambda x: x[1]['count'], reverse=True)
                
                for entity_name, data in sorted_entities:
                    # Only include entities with 5+ mentions
                    if data['count'] >= 5:
                        instances = self.data['entity_instances'][entity_type].get(entity_name, [])
                        for instance in instances:
                            writer.writerow([
                                entity_name,
                                instance['document'],
                                instance['page_number'],
                                instance['text_sample']
                            ])
            
            print(f"  - {instance_file}")
            
            # Generate filtered instance-by-instance CSV (5+ mentions only)
            filtered_file = os.path.join(output_dir, f'instance_by_instance_{type_name}_5plus.csv')
            
            with open(filtered_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['entity_name', 'document', 'page_number', 'text_sample'])
                
                for entity_name, data in sorted_entities:
                    if data['count'] >= 5:
                        instances = self.data['entity_instances'][entity_type].get(entity_name, [])
                        for instance in instances:
                            writer.writerow([
                                entity_name,
                                instance['document'],
                                instance['page_number'],
                                instance['text_sample']
                            ])
            
            print(f"  - {filtered_file}")
        
        print(f"\nEntity CSVs generated for {len(self.data['entities'])} entity types")
        
        # Generate full name filtered versions for PERSON entities
        if 'PERSON' in self.data['entities']:
            self._generate_fullname_csvs(output_dir)
    
    def _generate_fullname_csvs(self, output_dir='.'):
        """Generate filtered CSVs containing only full names (names with spaces)"""
        import csv
        
        # Filter aggregated person entities
        fullname_file = os.path.join(output_dir, 'entity_person_fullname.csv')
        with open(fullname_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['entity_name', 'frequency', 'documents'])
            
            sorted_persons = sorted(self.data['entities']['PERSON'].items(), 
                                   key=lambda x: x[1]['count'], reverse=True)
            
            for person_name, data in sorted_persons:
                # Only include names with spaces (full names)
                if ' ' in person_name:
                    docs_str = ', '.join(data['documents'])
                    writer.writerow([person_name, data['count'], docs_str])
        
        print(f"\nFull name filtered CSVs:")
        print(f"  - {fullname_file}")
        
        # Filter instance-by-instance person entities
        instance_fullname_file = os.path.join(output_dir, 'instance_by_instance_person_fullname.csv')
        with open(instance_fullname_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['entity_name', 'document', 'page_number', 'text_sample'])
            
            sorted_persons = sorted(self.data['entities']['PERSON'].items(), 
                                   key=lambda x: x[1]['count'], reverse=True)
            
            for person_name, data in sorted_persons:
                # Only include names with spaces and 5+ mentions
                if ' ' in person_name and data['count'] >= 5:
                    instances = self.data['entity_instances']['PERSON'].get(person_name, [])
                    for instance in instances:
                        writer.writerow([
                            person_name,
                            instance['document'],
                            instance['page_number'],
                            instance['text_sample']
                        ])
        
        print(f"  - {instance_fullname_file}")
        
        # Filter instance-by-instance person entities (5+ mentions only)
        instance_fullname_5plus_file = os.path.join(output_dir, 'instance_by_instance_person_fullname_5plus.csv')
        with open(instance_fullname_5plus_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['entity_name', 'document', 'page_number', 'text_sample'])
            
            for person_name, data in sorted_persons:
                if ' ' in person_name and data['count'] >= 5:
                    instances = self.data['entity_instances']['PERSON'].get(person_name, [])
                    for instance in instances:
                        writer.writerow([
                            person_name,
                            instance['document'],
                            instance['page_number'],
                            instance['text_sample']
                        ])
        
        print(f"  - {instance_fullname_5plus_file}")


def main():
    """Command-line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python archive_report_generator.py <archive_directory> [output_file]")
        print("\nExample:")
        print('  python archive_report_generator.py "D:\\ArchiveData\\NEH Domestic Science Project - Digitized Materials"')
        print('  python archive_report_generator.py "D:\\ArchiveData\\NEH Domestic Science Project - Digitized Materials" report.txt')
        sys.exit(1)
    
    base_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(base_dir):
        print(f"Error: Directory not found: {base_dir}")
        sys.exit(1)
    
    print("Archive Report Generator")
    print("=" * 80)
    
    reporter = ArchiveReporter(base_dir)
    reporter.scan()
    report = reporter.generate_report(output_file)
    
    # Generate entity CSVs
    output_dir = os.path.dirname(output_file) if output_file else '.'
    reporter.generate_entity_csvs(output_dir)
    
    if not output_file:
        print("\n" + report)


if __name__ == "__main__":
    main()
