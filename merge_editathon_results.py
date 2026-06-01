#!/usr/bin/env python3
"""
Merge Editathon Results Back to Archive Sidecars

Takes the JSON export from the editathon admin panel and merges
human-validated data back into the original JSON sidecar files.

This is ADDITIVE only - no existing data in sidecars is overwritten or deleted.
New sections are added:
  - human_transcription: editor-selected/corrected transcription
  - dublin_core_metadata[field].validation: approved/rejected/removed
  - named_entities.validations: per-entity approval/rejection/correction

Usage:
  python merge_editathon_results.py <export_json> <archive_dir> [--dry-run]

Arguments:
  export_json  - JSON file exported from editathon admin panel
  archive_dir  - Root directory of archive with JSON sidecars
  --dry-run    - Preview changes without writing files
"""

import json
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime


class EditathonMerger:
    def __init__(self, export_path, archive_dir, dry_run=False):
        self.export_path = Path(export_path)
        self.archive_dir = Path(archive_dir)
        self.dry_run = dry_run
        self.stats = {
            'pages_processed': 0,
            'sidecars_updated': 0,
            'sidecars_not_found': 0,
            'transcriptions_merged': 0,
            'metadata_validations_merged': 0,
            'entity_validations_merged': 0,
            'errors': 0
        }
    
    def run(self):
        """Main merge process"""
        print("=" * 80)
        print("EDITATHON RESULTS MERGER")
        print("=" * 80)
        if self.dry_run:
            print("*** DRY RUN - No files will be modified ***")
        print(f"\nExport file: {self.export_path}")
        print(f"Archive dir: {self.archive_dir}")
        print()
        
        # Load export data
        with open(self.export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        # Handle both list format and object format
        if isinstance(export_data, list):
            edits = export_data
        elif isinstance(export_data, dict) and 'edits' in export_data:
            edits = export_data['edits']
        else:
            print("Error: Unrecognized export format")
            return
        
        print(f"Found {len(edits)} edit records in export\n")
        
        # Process each edit
        for edit in edits:
            self._process_edit(edit)
        
        # Print summary
        self._print_summary()
    
    def _process_edit(self, edit):
        """Process a single edit record and merge into sidecar"""
        self.stats['pages_processed'] += 1
        
        page_id = edit.get('page_id', '')
        json_file = edit.get('json_file', '')
        username = edit.get('username', 'unknown')
        
        if not json_file:
            # Try to find sidecar by page_id pattern
            print(f"  [SKIP] No json_file for {page_id} (editor: {username})")
            self.stats['sidecars_not_found'] += 1
            return
        
        # Find the sidecar in archive directory
        sidecar_path = self._find_sidecar(json_file)
        
        if not sidecar_path:
            print(f"  [NOT FOUND] {json_file}")
            self.stats['sidecars_not_found'] += 1
            return
        
        # Load existing sidecar
        try:
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                sidecar = json.load(f)
        except Exception as e:
            print(f"  [ERROR] Reading {sidecar_path}: {e}")
            self.stats['errors'] += 1
            return
        
        modified = False
        
        # 1. Merge transcription
        if edit.get('transcription') and edit.get('transcription_edited'):
            self._merge_transcription(sidecar, edit)
            modified = True
            self.stats['transcriptions_merged'] += 1
        
        # 2. Merge metadata validations
        metadata_validations = edit.get('metadata_validations', [])
        if metadata_validations:
            self._merge_metadata_validations(sidecar, metadata_validations, username)
            modified = True
            self.stats['metadata_validations_merged'] += len(metadata_validations)
        
        # 3. Merge entity validations
        entity_validations = edit.get('entity_validations', [])
        if entity_validations:
            self._merge_entity_validations(sidecar, entity_validations, username)
            modified = True
            self.stats['entity_validations_merged'] += len(entity_validations)
        
        # Write back if modified
        if modified and not self.dry_run:
            # Backup original
            backup_path = sidecar_path.with_suffix('.json.bak')
            if not backup_path.exists():
                shutil.copy2(sidecar_path, backup_path)
            
            # Write updated sidecar
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(sidecar, f, indent=2, ensure_ascii=False)
            
            self.stats['sidecars_updated'] += 1
            print(f"  [UPDATED] {json_file}")
        elif modified:
            self.stats['sidecars_updated'] += 1
            print(f"  [WOULD UPDATE] {json_file}")
    
    def _find_sidecar(self, json_file):
        """Find a JSON sidecar file in the archive directory"""
        # Direct search
        matches = list(self.archive_dir.rglob(json_file))
        if matches:
            return matches[0]
        
        # Try without path components (just filename)
        filename = Path(json_file).name
        matches = list(self.archive_dir.rglob(filename))
        if matches:
            return matches[0]
        
        return None
    
    def _merge_transcription(self, sidecar, edit):
        """Add human transcription to sidecar (does not overwrite OCR)"""
        sidecar['human_transcription'] = {
            'text': edit['transcription'],
            'source_engine': edit.get('ocr_selected', 'unknown'),
            'edited': edit.get('transcription_edited', True),
            'editor': edit.get('username', 'unknown'),
            'timestamp': edit.get('timestamp', datetime.now().isoformat()),
            'completed': edit.get('completed', False)
        }
    
    def _merge_metadata_validations(self, sidecar, validations, username):
        """Add validation status to Dublin Core metadata fields"""
        # Ensure dublin_core_metadata exists
        if 'dublin_core_metadata' not in sidecar:
            sidecar['dublin_core_metadata'] = {}
        
        # Add validations section
        if 'metadata_validations' not in sidecar:
            sidecar['metadata_validations'] = {}
        
        for validation in validations:
            field_name = validation.get('field_name', '')
            status = validation.get('validation_status') or validation.get('status', '')
            
            if not field_name or not status:
                continue
            
            sidecar['metadata_validations'][field_name] = {
                'status': status,
                'original_value': validation.get('original_value', ''),
                'editor': username,
                'timestamp': validation.get('timestamp', datetime.now().isoformat()),
                'notes': validation.get('notes', '')
            }
    
    def _merge_entity_validations(self, sidecar, validations, username):
        """Add validation status to named entities"""
        # Ensure named_entities section exists
        if 'named_entities' not in sidecar:
            sidecar['named_entities'] = {}
        
        if 'validations' not in sidecar['named_entities']:
            sidecar['named_entities']['validations'] = {}
        
        for validation in validations:
            # The export should include entity_name and entity_type
            # (resolved from database IDs at export time)
            entity_name = validation.get('entity_name', '')
            entity_type = validation.get('entity_type', '')
            status = validation.get('validation_status') or validation.get('status', '')
            
            if not entity_name or not status:
                continue
            
            key = f"{entity_type}:{entity_name}" if entity_type else entity_name
            
            entry = {
                'status': status,
                'entity_type': entity_type,
                'editor': username,
                'timestamp': validation.get('timestamp', datetime.now().isoformat())
            }
            
            # Include corrections if present
            if validation.get('corrected_name'):
                entry['corrected_name'] = validation['corrected_name']
            if validation.get('corrected_type'):
                entry['corrected_type'] = validation['corrected_type']
            if validation.get('notes'):
                entry['notes'] = validation['notes']
            
            sidecar['named_entities']['validations'][key] = entry
    
    def _print_summary(self):
        """Print merge summary"""
        print("\n" + "=" * 80)
        print("MERGE SUMMARY")
        print("=" * 80)
        print(f"Pages processed:              {self.stats['pages_processed']}")
        print(f"Sidecars updated:             {self.stats['sidecars_updated']}")
        print(f"Sidecars not found:           {self.stats['sidecars_not_found']}")
        print(f"Transcriptions merged:        {self.stats['transcriptions_merged']}")
        print(f"Metadata validations merged:  {self.stats['metadata_validations_merged']}")
        print(f"Entity validations merged:    {self.stats['entity_validations_merged']}")
        print(f"Errors:                       {self.stats['errors']}")
        if self.dry_run:
            print("\n*** DRY RUN - No files were modified ***")
        else:
            print(f"\nBackups saved as .json.bak (only first time per file)")
        print("=" * 80)


def main():
    if len(sys.argv) < 3:
        print("=" * 80)
        print("Merge Editathon Results Back to Archive Sidecars")
        print("=" * 80)
        print("\nMerges human-validated transcriptions, metadata, and entity")
        print("corrections from the editathon back into JSON sidecar files.")
        print("\nThis is ADDITIVE only - existing data is never overwritten.")
        print("\nUsage:")
        print("  python merge_editathon_results.py <export_json> <archive_dir> [--dry-run]")
        print("\nArguments:")
        print("  export_json  - JSON export from editathon admin panel")
        print("  archive_dir  - Root archive directory with JSON sidecars")
        print("  --dry-run    - Preview changes without writing files")
        print("\nExample:")
        print('  python merge_editathon_results.py \\')
        print('    editathon-export-2025-05-28.json \\')
        print('    "D:\\ArchiveData\\NEH Domestic Science Project"')
        print("\nWhat gets merged into each sidecar:")
        print("  - human_transcription: editor-corrected text + metadata")
        print("  - metadata_validations: approved/rejected/removed per field")
        print("  - named_entities.validations: per-entity status + corrections")
        print("\nPrerequisites:")
        print("  - Export must include json_file field (source sidecar filename)")
        print("  - Export must resolve entity IDs to names (see export endpoint)")
        print("=" * 80)
        sys.exit(1)
    
    export_path = sys.argv[1]
    archive_dir = sys.argv[2]
    dry_run = '--dry-run' in sys.argv
    
    if not os.path.exists(export_path):
        print(f"Error: Export file not found: {export_path}")
        sys.exit(1)
    
    if not os.path.isdir(archive_dir):
        print(f"Error: Archive directory not found: {archive_dir}")
        sys.exit(1)
    
    merger = EditathonMerger(export_path, archive_dir, dry_run)
    merger.run()


if __name__ == "__main__":
    main()
