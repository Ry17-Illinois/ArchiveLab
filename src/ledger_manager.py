#!/usr/bin/env python3
"""
Ledger Manager for Dublin Core Metadata
Handles the creation and management of the metadata ledger
"""

import pandas as pd
import os
import uuid
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any

class LedgerManager:
    """Manages the metadata ledger with Dublin Core fields"""
    
    # Dublin Core metadata fields
    DUBLIN_CORE_FIELDS = [
        'title', 'creator', 'subject', 'description', 'publisher', 
        'contributor', 'date', 'type', 'format', 'identifier', 
        'source', 'language', 'relation', 'coverage', 'rights'
    ]
    
    def __init__(self, ledger_path: str = "metadata_ledger.csv"):
        self.ledger_path = ledger_path
        self._lock = threading.Lock()
        self.df = self.load_or_create_ledger()
    
    def load_or_create_ledger(self) -> pd.DataFrame:
        """Load existing ledger or create new one"""
        if os.path.exists(self.ledger_path):
            df = pd.read_csv(self.ledger_path)
            
            # Ensure string columns are object dtype (not float64 from empty values)
            string_columns = [
                'parent_id', 'document_type', 'document_type_status', 
                'named_entities', 'batch_request_id', 'batch_status',
                'tesseract_ocr', 'tesseract_status', 'pypdf2_ocr', 'pypdf2_status',
                'openai_ocr_ocr', 'openai_ocr_status', 'ollama_ocr_ocr', 'ollama_ocr_status',
                'easyocr_ocr', 'easyocr_status'
            ]
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].fillna('').astype(object)
            
            # Add missing columns if they don't exist
            if 'parent_id' not in df.columns:
                df['parent_id'] = ''
            if 'page_number' not in df.columns:
                df['page_number'] = 0
            if 'tesseract_ocr' not in df.columns:
                df['tesseract_ocr'] = ''
            if 'tesseract_status' not in df.columns:
                df['tesseract_status'] = 'pending'
            if 'pypdf2_ocr' not in df.columns:
                df['pypdf2_ocr'] = ''
            if 'pypdf2_status' not in df.columns:
                df['pypdf2_status'] = 'pending'
            if 'openai_ocr_ocr' not in df.columns:
                df['openai_ocr_ocr'] = ''
            if 'openai_ocr_status' not in df.columns:
                df['openai_ocr_status'] = 'pending'
            if 'ollama_ocr_ocr' not in df.columns:
                df['ollama_ocr_ocr'] = ''
            if 'ollama_ocr_status' not in df.columns:
                df['ollama_ocr_status'] = 'pending'
            if 'document_type' not in df.columns:
                df['document_type'] = ''
            if 'document_type_status' not in df.columns:
                df['document_type_status'] = 'pending'
            if 'named_entities' not in df.columns:
                df['named_entities'] = ''
            if 'batch_request_id' not in df.columns:
                df['batch_request_id'] = ''
            if 'batch_status' not in df.columns:
                df['batch_status'] = ''
        else:
            # Create base columns
            columns = [
                'file_id', 'parent_id', 'page_number', 'filename', 'filepath', 'file_type', 'file_size',
                'date_added', 'easyocr_ocr', 'easyocr_status', 'tesseract_ocr', 'tesseract_status', 'pypdf2_ocr', 'pypdf2_status', 'openai_ocr_ocr', 'openai_ocr_status', 'ollama_ocr_ocr', 'ollama_ocr_status',
                'document_type', 'document_type_status', 'named_entities', 'batch_request_id', 'batch_status'
            ] + self.DUBLIN_CORE_FIELDS + [f"{field}_status" for field in self.DUBLIN_CORE_FIELDS]
            
            df = pd.DataFrame(columns=columns)
        
        return df
    
    def save_ledger(self):
        """Save the ledger to CSV with thread safety"""
        with self._lock:
            print(f"DEBUG: Saving ledger with {len(self.df)} rows to {self.ledger_path}")
            self.df.to_csv(self.ledger_path, index=False)
            print(f"DEBUG: Ledger saved successfully")
    
    def add_files(self, file_paths: List[str]) -> int:
        """Add new files to the ledger, creating separate rows for PDF pages"""
        print(f"DEBUG: add_files called with {len(file_paths)} paths")
        added_count = 0
        new_files = []
        
        for i, file_path in enumerate(file_paths):
            print(f"DEBUG: Processing file {i+1}/{len(file_paths)}: {file_path}")
            if not os.path.exists(file_path):
                print(f"DEBUG: File does not exist, skipping")
                continue
                
            # Check if file already exists
            if not self.df[self.df['filepath'] == file_path].empty:
                print(f"DEBUG: File already in ledger, skipping")
                continue
            
            file_type = Path(file_path).suffix.lower()
            
            # For PDFs, create a row for each page
            if file_type == '.pdf':
                page_count = self.get_page_count(file_path)
                parent_id = str(uuid.uuid4())
                
                for page_num in range(1, page_count + 1):
                    file_info = {
                        'file_id': str(uuid.uuid4()),
                        'parent_id': parent_id,
                        'page_number': page_num,
                        'filename': f"{os.path.basename(file_path)} (Page {page_num})",
                        'filepath': file_path,
                        'file_type': file_type,
                        'file_size': os.path.getsize(file_path),
                        'date_added': pd.Timestamp.now(),
                        'easyocr_ocr': '',
                        'easyocr_status': 'pending',
                        'tesseract_ocr': '',
                        'tesseract_status': 'pending',
                        'pypdf2_ocr': '',
                        'pypdf2_status': 'pending',
                        'openai_ocr_ocr': '',
                        'openai_ocr_status': 'pending',
                        'ollama_ocr_ocr': '',
                        'ollama_ocr_status': 'pending',
                        'document_type': 'document',
                        'document_type_status': 'completed',
                        'named_entities': '',
                        'batch_request_id': '',
                        'batch_status': ''
                    }
                    
                    # Initialize Dublin Core fields
                    for field in self.DUBLIN_CORE_FIELDS:
                        file_info[field] = ''
                        file_info[f"{field}_status"] = 'pending'
                    
                    new_files.append(file_info)
                    added_count += 1
            else:
                # For images, create single row
                file_info = {
                    'file_id': str(uuid.uuid4()),
                    'parent_id': '',
                    'page_number': 0,
                    'filename': os.path.basename(file_path),
                    'filepath': file_path,
                    'file_type': file_type,
                    'file_size': os.path.getsize(file_path),
                    'date_added': pd.Timestamp.now(),
                    'easyocr_ocr': '',
                    'easyocr_status': 'pending',
                    'tesseract_ocr': '',
                    'tesseract_status': 'pending',
                    'pypdf2_ocr': '',
                    'pypdf2_status': 'pending',
                    'openai_ocr_ocr': '',
                    'openai_ocr_status': 'pending',
                    'ollama_ocr_ocr': '',
                    'ollama_ocr_status': 'pending',
                    'document_type': '',
                    'document_type_status': 'pending',
                    'named_entities': '',
                    'batch_request_id': '',
                    'batch_status': ''
                }
                
                # Initialize Dublin Core fields
                for field in self.DUBLIN_CORE_FIELDS:
                    file_info[field] = ''
                    file_info[f"{field}_status"] = 'pending'
                
                new_files.append(file_info)
                added_count += 1
            
            print(f"DEBUG: Added file to batch, total so far: {added_count}")
        
        # Add all files at once
        if new_files:
            print(f"DEBUG: Adding {len(new_files)} files to dataframe")
            self.df = pd.concat([self.df, pd.DataFrame(new_files)], ignore_index=True)
            print(f"DEBUG: Dataframe now has {len(self.df)} rows")
            self.save_ledger()
        else:
            print(f"DEBUG: No new files to add")
        
        return added_count
    
    def update_ocr_result(self, file_id: str, ocr_text: str, status: str = 'completed', model: str = 'easyocr'):
        """Update OCR results"""
        mask = self.df['file_id'] == file_id
        self.df.loc[mask, f'{model}_ocr'] = ocr_text
        self.df.loc[mask, f'{model}_status'] = status
        self.save_ledger()
    
    def update_dublin_core_field(self, file_id: str, field: str, value: str, status: str = 'completed'):
        """Update a Dublin Core metadata field"""
        if field not in self.DUBLIN_CORE_FIELDS:
            raise ValueError(f"Invalid Dublin Core field: {field}")
        
        mask = self.df['file_id'] == file_id
        self.df.loc[mask, field] = value
        self.df.loc[mask, f"{field}_status"] = status
        self.save_ledger()
    
    def update_document_type(self, file_id: str, doc_type: str, status: str = 'completed'):
        """Update document type classification"""
        # Ensure column is object type to accept string values
        if self.df['document_type'].dtype != object:
            self.df['document_type'] = self.df['document_type'].astype(object)
        mask = self.df['file_id'] == file_id
        self.df.loc[mask, 'document_type'] = doc_type
        self.df.loc[mask, 'document_type_status'] = status
        self.save_ledger()
    
    def update_named_entities(self, file_id: str, entities: str):
        """Update named entities for a file"""
        mask = self.df['file_id'] == file_id
        # Ensure named_entities column is object type to avoid dtype warnings
        if 'named_entities' not in self.df.columns:
            self.df['named_entities'] = ''
        self.df['named_entities'] = self.df['named_entities'].astype(object)
        self.df.loc[mask, 'named_entities'] = entities
        self.save_ledger()
    
    def update_batch_status(self, file_id: str, field: str, request_id: str, status: str):
        """Update batch request status for a metadata field"""
        mask = self.df['file_id'] == file_id
        self.df.loc[mask, 'batch_request_id'] = request_id
        self.df.loc[mask, 'batch_status'] = status
        self.df.loc[mask, f"{field}_status"] = status
        self.save_ledger()
    
    def get_files_by_status(self, operation: str, status: str = 'pending') -> pd.DataFrame:
        """Get files by operation status"""
        if operation in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr', 'document_type']:
            return self.df[self.df[f'{operation}_status'] == status]
        elif operation in self.DUBLIN_CORE_FIELDS:
            return self.df[self.df[f"{operation}_status"] == status]
        else:
            return pd.DataFrame()
    
    def clear_rows(self, file_ids: List[str]):
        """Clear specified rows from the ledger"""
        self.df = self.df[~self.df['file_id'].isin(file_ids)]
        self.save_ledger()
    
    def get_file_id_by_path(self, filepath: str) -> str:
        """Get file ID by filepath"""
        matching_rows = self.df[self.df['filepath'] == filepath]
        if not matching_rows.empty:
            return matching_rows.iloc[0]['file_id']
        return None
    
    def get_page_count(self, filepath: str) -> int:
        """Get page count for a file (PDF pages or 1 for images)"""
        try:
            file_ext = Path(filepath).suffix.lower()
            if file_ext == '.pdf':
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(filepath)
                    page_count = len(doc)
                    doc.close()
                    return page_count
                except ImportError:
                    return 1  # Fallback if PyMuPDF not available
                except Exception:
                    return 1  # Fallback if PDF can't be opened
            else:
                return 1  # Images count as 1 page
        except Exception:
            return 1  # Fallback
    
    def import_from_sidecars(self, directory_path: str, options: Dict[str, Any]) -> Dict[str, int]:
        """
        Import files with existing JSON sidecars
        
        Args:
            directory_path: Path to directory containing files and sidecars
            options: Import configuration
                - import_ocr: Load OCR from sidecars
                - import_metadata: Load Dublin Core metadata
                - import_entities: Load existing entities
                - rerun_ner: Mark entities for re-extraction
                - ground_truth_engine: Engine to use for NER (if rerun_ner=True)
        
        Returns:
            Dictionary with import statistics
        """
        import json
        
        stats = {
            'files_found': 0,
            'sidecars_found': 0,
            'files_imported': 0,
            'ocr_imported': 0,
            'metadata_imported': 0,
            'entities_imported': 0
        }
        
        # Scan directory for files and sidecars
        file_sidecar_pairs = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file).suffix.lower()
                
                # Skip JSON files themselves
                if file_ext == '.json':
                    continue
                
                # Check for supported file types
                if file_ext not in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pdf']:
                    continue
                
                stats['files_found'] += 1
                
                # Look for corresponding JSON sidecar
                base_name = Path(file_path).stem
                
                # For PDFs, look for page-level JSON files
                if file_ext == '.pdf':
                    # Look for metadata file
                    metadata_file = os.path.join(root, f"{base_name}_metadata.json")
                    page_files = []
                    
                    # Find all page JSON files
                    for json_file in files:
                        if json_file.startswith(f"{base_name}_Page") and json_file.endswith('.json'):
                            page_files.append(os.path.join(root, json_file))
                    
                    if os.path.exists(metadata_file) and page_files:
                        stats['sidecars_found'] += 1
                        file_sidecar_pairs.append({
                            'file_path': file_path,
                            'metadata_file': metadata_file,
                            'page_files': sorted(page_files),
                            'file_type': 'pdf'
                        })
                else:
                    # For images, look for single JSON sidecar
                    sidecar_path = os.path.join(root, f"{base_name}.json")
                    if os.path.exists(sidecar_path):
                        stats['sidecars_found'] += 1
                        file_sidecar_pairs.append({
                            'file_path': file_path,
                            'sidecar_path': sidecar_path,
                            'file_type': 'image'
                        })
        
        # Import files with sidecars
        new_files = []
        
        for pair in file_sidecar_pairs:
            file_path = pair['file_path']
            
            # Skip if already in ledger
            if not self.df[self.df['filepath'] == file_path].empty:
                continue
            
            if pair['file_type'] == 'pdf':
                # Import PDF with pages
                parent_id = str(uuid.uuid4())
                
                # Load metadata file
                with open(pair['metadata_file'], 'r', encoding='utf-8') as f:
                    metadata_json = json.load(f)
                
                # Import each page
                for page_file in pair['page_files']:
                    with open(page_file, 'r', encoding='utf-8') as f:
                        page_json = json.load(f)
                    
                    page_num = page_json.get('page_number', 0)
                    file_info = self._create_file_info_from_sidecar(
                        file_path, page_json, metadata_json, options, 
                        parent_id=parent_id, page_number=page_num
                    )
                    new_files.append(file_info)
                    
                    # Update stats
                    if options.get('import_ocr'):
                        stats['ocr_imported'] += 1
                    if options.get('import_metadata'):
                        stats['metadata_imported'] += 1
                    if options.get('import_entities') and not options.get('rerun_ner'):
                        stats['entities_imported'] += 1
                
                stats['files_imported'] += 1
                
            else:
                # Import single image file
                with open(pair['sidecar_path'], 'r', encoding='utf-8') as f:
                    sidecar_json = json.load(f)
                
                file_info = self._create_file_info_from_sidecar(
                    file_path, sidecar_json, None, options
                )
                new_files.append(file_info)
                
                # Update stats
                stats['files_imported'] += 1
                if options.get('import_ocr'):
                    stats['ocr_imported'] += 1
                if options.get('import_metadata'):
                    stats['metadata_imported'] += 1
                if options.get('import_entities') and not options.get('rerun_ner'):
                    stats['entities_imported'] += 1
        
        # Add all imported files to ledger
        if new_files:
            new_df = pd.DataFrame(new_files)
            if self.df.empty:
                self.df = new_df
            else:
                self.df = pd.concat([self.df, new_df], ignore_index=True)
            self.save_ledger()
        
        return stats
    
    def _create_file_info_from_sidecar(self, file_path: str, sidecar_json: Dict, 
                                       metadata_json: Dict = None, options: Dict = None,
                                       parent_id: str = '', page_number: int = 0) -> Dict:
        """Create file info dictionary from JSON sidecar data"""
        file_type = Path(file_path).suffix.lower()
        
        # Base file info
        file_info = {
            'file_id': str(uuid.uuid4()),
            'parent_id': parent_id,
            'page_number': page_number,
            'filename': os.path.basename(file_path) if page_number == 0 else f"{os.path.basename(file_path)} (Page {page_number})",
            'filepath': file_path,
            'file_type': file_type,
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'date_added': pd.Timestamp.now(),
            'document_type': 'document' if file_type == '.pdf' else '',
            'document_type_status': 'completed' if file_type == '.pdf' else 'pending',
            'batch_request_id': '',
            'batch_status': ''
        }
        
        # Import OCR results if requested
        if options.get('import_ocr', True):
            ocr_results = sidecar_json.get('ocr_results', {})
            engines = ocr_results.get('engines', {})
            
            # Map engine names from JSON to ledger columns
            engine_map = {
                'easyocr': 'easyocr',
                'tesseract': 'tesseract',
                'pypdf2': 'pypdf2',
                'openai_ocr': 'openai_ocr',
                'ollama_ocr': 'ollama_ocr'
            }
            
            for json_engine, ledger_engine in engine_map.items():
                if json_engine in engines:
                    engine_data = engines[json_engine]
                    file_info[f'{ledger_engine}_ocr'] = engine_data.get('text', '')
                    file_info[f'{ledger_engine}_status'] = engine_data.get('status', 'completed')
                else:
                    file_info[f'{ledger_engine}_ocr'] = ''
                    file_info[f'{ledger_engine}_status'] = 'pending'
        else:
            # Set all OCR to pending
            for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']:
                file_info[f'{engine}_ocr'] = ''
                file_info[f'{engine}_status'] = 'pending'
        
        # Import metadata if requested
        metadata_source = metadata_json if metadata_json else sidecar_json
        dublin_core = metadata_source.get('dublin_core_metadata', {})
        
        for field in self.DUBLIN_CORE_FIELDS:
            if options.get('import_metadata', True) and field in dublin_core:
                value = dublin_core[field]
                file_info[field] = value if value and value != '' else ''
                file_info[f"{field}_status"] = 'completed' if value and value != '' else 'pending'
            else:
                file_info[field] = ''
                file_info[f"{field}_status"] = 'pending'
        
        # Import entities if requested
        if options.get('import_entities', True) and not options.get('rerun_ner', False):
            entities_data = sidecar_json.get('named_entities', {})
            entities = entities_data.get('entities', {})
            
            # Format entities as string for ledger
            entity_lines = []
            entity_type_map = {
                'PERSON': '👤 People',
                'ORG': '🏢 Organizations',
                'GPE': '📍 Locations',
                'DATE': '📅 Dates',
                'MONEY': '💰 Money',
                'WORK_OF_ART': '🎨 Works',
                'PRODUCT': '📦 Products'
            }
            
            for entity_type, entity_list in entities.items():
                if entity_list and len(entity_list) > 0:
                    display_name = entity_type_map.get(entity_type, entity_type)
                    entity_lines.append(f"{display_name}: {', '.join(entity_list)}")
            
            file_info['named_entities'] = '\n'.join(entity_lines) if entity_lines else ''
        else:
            file_info['named_entities'] = ''
        
        return file_info
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the ledger with page counts"""
        total_files = len(self.df)
        
        # Calculate total pages correctly - each row is now a page
        total_pages = total_files
        
        summary = {
            'total_files': total_files,
            'total_pages': total_pages,
            'easyocr_completed': len(self.df[self.df['easyocr_status'] == 'completed']),
            'easyocr_pending': len(self.df[self.df['easyocr_status'] == 'pending']),
            'easyocr_error': len(self.df[self.df['easyocr_status'] == 'error']),
            'tesseract_completed': len(self.df[self.df.get('tesseract_status', pd.Series()) == 'completed']),
            'tesseract_pending': len(self.df[self.df.get('tesseract_status', pd.Series()) == 'pending']),
            'tesseract_error': len(self.df[self.df.get('tesseract_status', pd.Series()) == 'error']),
            'pypdf2_completed': len(self.df[self.df.get('pypdf2_status', pd.Series()) == 'completed']),
            'pypdf2_pending': len(self.df[self.df.get('pypdf2_status', pd.Series()) == 'pending']),
            'pypdf2_error': len(self.df[self.df.get('pypdf2_status', pd.Series()) == 'error']),
            'openai_ocr_completed': len(self.df[self.df.get('openai_ocr_status', pd.Series()) == 'completed']),
            'openai_ocr_pending': len(self.df[self.df.get('openai_ocr_status', pd.Series()) == 'pending']),
            'openai_ocr_error': len(self.df[self.df.get('openai_ocr_status', pd.Series()) == 'error']),
            'ollama_ocr_completed': len(self.df[self.df.get('ollama_ocr_status', pd.Series()) == 'completed']),
            'ollama_ocr_pending': len(self.df[self.df.get('ollama_ocr_status', pd.Series()) == 'pending']),
            'ollama_ocr_error': len(self.df[self.df.get('ollama_ocr_status', pd.Series()) == 'error']),
            'document_type_completed': len(self.df[self.df.get('document_type_status', pd.Series()) == 'completed']),
            'document_type_pending': len(self.df[self.df.get('document_type_status', pd.Series()) == 'pending']),
            'document_type_error': len(self.df[self.df.get('document_type_status', pd.Series()) == 'error']),
            'dublin_core_fields': {}
        }
        
        for field in self.DUBLIN_CORE_FIELDS:
            status_col = f"{field}_status"
            summary['dublin_core_fields'][field] = {
                'completed': len(self.df[self.df[status_col] == 'completed']),
                'pending': len(self.df[self.df[status_col] == 'pending']),
                'error': len(self.df[self.df[status_col] == 'error'])
            }
        
        return summary