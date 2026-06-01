#!/usr/bin/env python3
"""
Export Manager - Export OCR and metadata in archival formats
Option 4: Reference-based (separate document metadata and page files)
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import pandas as pd

class ExportManager:
    def __init__(self, ledger_df: pd.DataFrame):
        self.ledger_df = ledger_df
        
        self.engine_display_names = {
            'easyocr': 'EasyOCR',
            'tesseract': 'Tesseract OCR',
            'pypdf2': 'PyPDF2',
            'openai_ocr': 'OpenAI Vision',
            'ollama_ocr': 'Ollama Vision'
        }
        
        self.model_names = {
            'easyocr': 'easyocr',
            'tesseract': 'tesseract',
            'pypdf2': 'PyPDF2',
            'openai_ocr': 'gpt-4o',
            'ollama_ocr': 'gemma3'
        }
    
    def export_json_sidecars(self, ground_truth_engine: str = None):
        """Export JSON sidecar files next to original files (Option 4: Reference-based)"""
        exported_count = 0
        metadata_files_created = set()
        
        # Group by parent document
        for parent_id in self.ledger_df['parent_id'].unique():
            if not parent_id or str(parent_id) == 'nan' or parent_id == '':
                # Single files (images)
                single_files = self.ledger_df[(self.ledger_df['parent_id'].isna()) | (self.ledger_df['parent_id'] == '')]
                for _, row in single_files.iterrows():
                    json_data = self._create_json_sidecar(row, ground_truth_engine)
                    original_path = Path(row['filepath'])
                    json_path = original_path.parent / f"{original_path.stem}.json"
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    exported_count += 1
            else:
                # PDF with pages
                pages = self.ledger_df[self.ledger_df['parent_id'] == parent_id]
                first_page = pages.iloc[0]
                original_path = Path(first_page['filepath'])
                
                # Create document metadata file (once per PDF)
                metadata_file = original_path.parent / f"{original_path.stem}_metadata.json"
                if str(metadata_file) not in metadata_files_created:
                    metadata_json = self._create_document_metadata(pages, ground_truth_engine)
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata_json, f, indent=2, ensure_ascii=False)
                    metadata_files_created.add(str(metadata_file))
                    exported_count += 1
                
                # Create page files
                for _, row in pages.iterrows():
                    page_json = self._create_page_data(row, ground_truth_engine, original_path.name)
                    page_file = original_path.parent / f"{original_path.stem}_Page{row['page_number']}.json"
                    
                    with open(page_file, 'w', encoding='utf-8') as f:
                        json.dump(page_json, f, indent=2, ensure_ascii=False)
                    exported_count += 1
        
        return exported_count
    
    def _create_document_metadata(self, pages_df: pd.DataFrame, ground_truth_engine: str = None) -> Dict:
        """Create document-level metadata JSON"""
        first_page = pages_df.iloc[0]
        archival_context = self._parse_archival_path(first_page['filepath'])
        
        # Build Dublin Core metadata from first page (same for all pages)
        dublin_core = {}
        for field in ['title', 'creator', 'subject', 'description', 'publisher', 
                      'contributor', 'date', 'type', 'format', 'identifier', 
                      'source', 'language', 'relation', 'coverage', 'rights']:
            dublin_core[field] = str(first_page.get(field, '')) if first_page.get(field) and str(first_page.get(field)) != 'nan' else ''
        
        # Add generation info
        if first_page.get('title') and str(first_page.get('title')) != 'nan':
            dublin_core['_generation_info'] = {
                'generated_by': 'AI',
                'model_name': 'gpt-4o-mini',
                'generation_date': str(first_page.get('date_added', ''))
            }
        
        return {
            'source_document': os.path.basename(first_page['filepath']),
            'file_info': {
                'file_type': str(first_page['file_type']),
                'file_size_bytes': int(first_page['file_size']),
                'total_pages': len(pages_df),
                'date_processed': str(first_page['date_added'])
            },
            'dublin_core_metadata': dublin_core,
            'archival_context': archival_context,
            'pages': [int(row['page_number']) for _, row in pages_df.iterrows()]
        }
    
    def _create_page_data(self, row: pd.Series, ground_truth_engine: str = None, parent_filename: str = None) -> Dict:
        """Create page-level data JSON"""
        # Build OCR results
        ocr_results = {
            'ground_truth_engine': ground_truth_engine or 'easyocr',
            'engines': {}
        }
        
        for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']:
            ocr_col = f'{engine}_ocr'
            status_col = f'{engine}_status'
            
            if ocr_col in row and status_col in row and row[status_col] == 'completed':
                engine_data = {
                    'engine_name': self.engine_display_names.get(engine, engine),
                    'model_name': self.model_names.get(engine, engine),
                    'status': str(row[status_col]),
                    'text': str(row[ocr_col]) if row[ocr_col] and str(row[ocr_col]) != 'nan' else ''
                }
                ocr_results['engines'][engine] = engine_data
        
        # Parse entities
        entities_data = self._parse_entities(row.get('named_entities', ''))
        
        return {
            'page_number': int(row.get('page_number', 0)),
            'parent_document': parent_filename,
            'metadata_file': f"{Path(parent_filename).stem}_metadata.json",
            'file_id': str(row['file_id']),
            'ocr_results': ocr_results,
            'named_entities': entities_data
        }
    
    def _create_json_sidecar(self, row: pd.Series, ground_truth_engine: str = None) -> Dict:
        """Create JSON sidecar for single files (images)"""
        archival_context = self._parse_archival_path(row['filepath'])
        
        ocr_results = {
            'ground_truth_engine': ground_truth_engine or 'easyocr',
            'engines': {}
        }
        
        for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']:
            ocr_col = f'{engine}_ocr'
            status_col = f'{engine}_status'
            
            if ocr_col in row and status_col in row:
                engine_data = {
                    'engine_name': self.engine_display_names.get(engine, engine),
                    'model_name': self.model_names.get(engine, engine),
                    'status': str(row[status_col]),
                    'text': str(row[ocr_col]) if row[ocr_col] and str(row[ocr_col]) != 'nan' else ''
                }
                ocr_results['engines'][engine] = engine_data
        
        entities_data = self._parse_entities(row.get('named_entities', ''))
        
        dublin_core = {}
        for field in ['title', 'creator', 'subject', 'description', 'publisher', 
                      'contributor', 'date', 'type', 'format', 'identifier', 
                      'source', 'language', 'relation', 'coverage', 'rights']:
            dublin_core[field] = str(row.get(field, '')) if row.get(field) and str(row.get(field)) != 'nan' else ''
        
        if row.get('title') and str(row.get('title')) != 'nan':
            dublin_core['_generation_info'] = {
                'generated_by': 'AI',
                'model_name': 'gpt-4o-mini',
                'generation_date': str(row.get('date_added', ''))
            }
        
        return {
            'file_info': {
                'source_file': os.path.basename(row['filepath']),
                'file_id': str(row['file_id']),
                'file_type': str(row['file_type']),
                'file_size_bytes': int(row['file_size']),
                'date_processed': str(row['date_added'])
            },
            'ocr_results': ocr_results,
            'named_entities': entities_data,
            'dublin_core_metadata': dublin_core,
            'archival_context': archival_context
        }
    
    def export_csv_summary(self, output_path: str, ground_truth_engine: str = None):
        """Export CSV summary of all files"""
        summary_rows = []
        
        for _, row in self.ledger_df.iterrows():
            summary_row = self._create_csv_row(row, ground_truth_engine)
            summary_rows.append(summary_row)
        
        df = pd.DataFrame(summary_rows)
        df.to_csv(output_path, index=False)
        
        return len(summary_rows)
    
    def _get_relative_path(self, filepath: str) -> str:
        """Get relative path from archive base directory"""
        base_dir = r"D:\ArchiveData\NEH Domestic Science Project - Digitized Materials"
        filepath_normalized = filepath.replace('/', '\\')
        
        if filepath_normalized.startswith(base_dir):
            relative = filepath_normalized[len(base_dir):].lstrip('\\')
            return relative.replace('\\', '/')
        return filepath.replace('\\', '/')
    
    def _create_csv_row(self, row: pd.Series, ground_truth_engine: str = None) -> Dict:
        """Create CSV summary row for a single file"""
        gt_engine = ground_truth_engine or 'easyocr'
        
        ocr_text = str(row.get(f'{gt_engine}_ocr', ''))
        text_preview = ocr_text[:200] + '...' if len(ocr_text) > 200 else ocr_text
        text_preview = text_preview.replace('\n', ' ').replace('\r', ' ')
        
        entities_str = str(row.get('named_entities', ''))
        entity_counts = self._count_entities(entities_str)
        
        archival_context = self._parse_archival_path(row['filepath'])
        
        return {
            'filename': os.path.basename(row['filepath']),
            'filepath': self._get_relative_path(row['filepath']),
            'page_number': int(row.get('page_number', 0)),
            'collection': archival_context.get('collection', ''),
            'box': archival_context.get('box', ''),
            'folder': archival_context.get('folder', ''),
            'file_type': str(row['file_type']),
            'file_size_mb': round(int(row['file_size']) / (1024*1024), 1),
            'date_processed': str(row['date_added']).split()[0],
            'ocr_engine': self.engine_display_names.get(gt_engine, gt_engine),
            'ocr_model': self.model_names.get(gt_engine, gt_engine),
            'ner_model': 'en_core_web_sm',
            'metadata_model': 'gpt-4o-mini',
            'has_ocr': 'Yes' if row.get(f'{gt_engine}_status') == 'completed' else 'No',
            'has_entities': 'Yes' if entities_str and entities_str != 'nan' else 'No',
            'has_metadata': 'Yes' if row.get('title') and str(row.get('title')) != 'nan' else 'No',
            'title': str(row.get('title', '')),
            'subject': str(row.get('subject', '')),
            'date': str(row.get('date', '')),
            'entity_count_person': entity_counts.get('PERSON', 0),
            'entity_count_org': entity_counts.get('ORG', 0),
            'entity_count_location': entity_counts.get('GPE', 0),
            'full_text_preview': text_preview
        }
    
    def _parse_archival_path(self, filepath: str) -> Dict:
        """Extract collection/box/folder from filepath"""
        parts = filepath.replace('\\', '/').split('/')
        
        context = {'collection': '', 'box': '', 'folder': ''}
        
        for i, part in enumerate(parts):
            if 'box' in part.lower() and i > 0:
                context['collection'] = parts[i-1]
                context['box'] = part
                if i + 1 < len(parts):
                    context['folder'] = parts[i+1]
                break
        
        return context
    
    def _parse_entities(self, entities_str: str) -> Dict:
        """Parse entity string into structured format"""
        if not entities_str or str(entities_str) == 'nan':
            return {'entities': {}}
        
        entities = {}
        lines = str(entities_str).split('\n')
        
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                entity_type = parts[0].strip()
                for char in entity_type:
                    if ord(char) > 127:
                        entity_type = entity_type.replace(char, '').strip()
                
                entity_list = [e.strip() for e in parts[1].split(',')]
                
                type_map = {
                    'People': 'PERSON',
                    'Organizations': 'ORG',
                    'Locations': 'GPE',
                    'Dates': 'DATE',
                    'Money': 'MONEY',
                    'Works': 'WORK_OF_ART',
                    'Products': 'PRODUCT'
                }
                
                for display, standard in type_map.items():
                    if display in entity_type:
                        entities[standard] = entity_list
                        break
        
        return {
            'extraction_method': 'spacy',
            'model_name': 'en_core_web_sm',
            'entities': entities
        }
    
    def _count_entities(self, entities_str: str) -> Dict[str, int]:
        """Count entities by type"""
        parsed = self._parse_entities(entities_str)
        counts = {}
        
        for entity_type, entity_list in parsed.get('entities', {}).items():
            counts[entity_type] = len([e for e in entity_list if e and e != 'None found'])
        
        return counts
