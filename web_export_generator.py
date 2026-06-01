#!/usr/bin/env python3
"""
Web Export Generator for Archive Analyzer
Generates a static web interface for browsing entity mentions with images and OCR text
"""

import os
import sys
import json
import csv
import shutil
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF for PDF extraction


class WebExportGenerator:
    def __init__(self, archive_dir, entity_csv, instance_csv, output_dir):
        self.archive_dir = Path(archive_dir)
        self.entity_csv = entity_csv
        self.instance_csv = instance_csv
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / 'images'
        
        self.data = {
            'entities': [],
            'pages': {}
        }
        self.page_counter = 1
        self.page_map = {}  # (document, page_num) -> page_id
    
    def generate(self):
        """Main generation process"""
        print("Web Export Generator")
        print("=" * 80)
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        
        # Load entity frequencies
        entity_freq = self._load_entity_frequencies()
        
        # Load instances and process pages
        print("\nProcessing instances and extracting pages...")
        self._process_instances(entity_freq)
        
        # Generate data.json
        data_file = self.output_dir / 'data.json'
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)
        print(f"\nGenerated: {data_file}")
        
        # Generate HTML interface
        self._generate_html()
        
        print(f"\nExport complete!")
        print(f"  - {len(self.data['entities'])} entities")
        print(f"  - {len(self.data['pages'])} unique pages")
        print(f"  - Output: {self.output_dir}")
    
    def _load_entity_frequencies(self):
        """Load entity names and frequencies from aggregated CSV"""
        freq = {}
        with open(self.entity_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                freq[row['entity_name']] = int(row['frequency'])
        print(f"Loaded {len(freq)} entities from {self.entity_csv}")
        return freq
    
    def _process_instances(self, entity_freq):
        """Process instance CSV and extract pages"""
        entities_dict = {}
        
        with open(self.instance_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entity_name = row['entity_name']
                document = row['document']
                page_number = int(row['page_number'])
                text_sample = row['text_sample']
                
                # Get or create page_id
                page_key = (document, page_number)
                if page_key not in self.page_map:
                    page_id = f"page_{self.page_counter:04d}"
                    self.page_map[page_key] = page_id
                    self.page_counter += 1
                    
                    # Extract page data
                    self._extract_page(page_id, document, page_number)
                else:
                    page_id = self.page_map[page_key]
                
                # Build entity data structure
                if entity_name not in entities_dict:
                    entities_dict[entity_name] = {
                        'name': entity_name,
                        'frequency': entity_freq.get(entity_name, 0),
                        'instances': []
                    }
                
                entities_dict[entity_name]['instances'].append({
                    'page_id': page_id,
                    'document': document,
                    'page_number': page_number,
                    'text_sample': text_sample
                })
        
        # Sort entities by frequency
        self.data['entities'] = sorted(entities_dict.values(), 
                                       key=lambda x: x['frequency'], 
                                       reverse=True)
    
    def _extract_page(self, page_id, document, page_number):
        """Extract page image and OCR text"""
        print(f"\n  DEBUG: Looking for JSON: {document}")
        print(f"  DEBUG: Archive dir: {self.archive_dir}")
        
        # Document field may be the image filename or the JSON filename
        # Always look for the JSON sidecar
        if document.lower().endswith(('.tif', '.tiff', '.jpg', '.jpeg', '.png')):
            # Image filename - look for corresponding JSON sidecar
            json_name = Path(document).stem + '.json'
        elif document.lower().endswith('.json'):
            json_name = document
        else:
            # Try appending .json
            json_name = document + '.json'
        
        json_matches = list(self.archive_dir.rglob(json_name))
        
        print(f"  DEBUG: Looking for sidecar: {json_name}")
        print(f"  DEBUG: Found {len(json_matches)} matches")
        if json_matches:
            print(f"  DEBUG: First match: {json_matches[0]}")
        
        if not json_matches:
            print(f"  Warning: JSON not found: {document}")
            return
        
        json_path = json_matches[0]
        print(f"  DEBUG: Using JSON path: {json_path}")
        
        # Read JSON to get original source file
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            print(f"  DEBUG: JSON keys: {json_data.keys()}")
            
            # Extract all OCR versions
            ocr_versions = {}
            page_metadata = {}
            doc_metadata = {}
            
            # Handle both old and new JSON formats
            if 'parent_document' in json_data:
                # New format - page-level JSON
                source_file = json_data['parent_document']
                engines = json_data.get('ocr_results', {}).get('engines', {})
                for engine_name, engine_data in engines.items():
                    if 'text' in engine_data:
                        ocr_versions[engine_name] = engine_data['text']
                
                # Get page-level metadata
                page_metadata = {
                    'page_number': json_data.get('page_number'),
                    'parent_document': json_data.get('parent_document'),
                    'file_id': json_data.get('file_id'),
                    'named_entities': json_data.get('named_entities', {}).get('entities', {})
                }
                
                # Load document-level metadata from _metadata.json
                metadata_file = json_data.get('metadata_file')
                if metadata_file:
                    metadata_path = json_path.parent / metadata_file
                    if metadata_path.exists():
                        with open(metadata_path, 'r', encoding='utf-8') as mf:
                            metadata_json = json.load(mf)
                            doc_metadata = {
                                'source_document': metadata_json.get('source_document'),
                                'dublin_core': metadata_json.get('dublin_core_metadata', {}),
                                'archival_context': metadata_json.get('archival_context', {}),
                                'file_info': metadata_json.get('file_info', {})
                            }
            elif 'file_info' in json_data:
                # Image sidecar format - has file_info with source_file
                source_file = json_data['file_info']['source_file']
                engines = json_data.get('ocr_results', {}).get('engines', {})
                for engine_name, engine_data in engines.items():
                    if 'text' in engine_data:
                        ocr_versions[engine_name] = engine_data['text']
                
                # Extract named entities from image sidecar
                page_metadata = {
                    'page_number': json_data.get('page_number', 1),
                    'parent_document': source_file,
                    'file_id': json_data.get('file_id', ''),
                    'named_entities': json_data.get('named_entities', {}).get('entities', {})
                }
                
                # Extract Dublin Core metadata (stored directly in image sidecar)
                dublin_core = json_data.get('dublin_core_metadata', {})
                archival_context = json_data.get('archival_context', {})
                doc_metadata = {
                    'source_document': source_file,
                    'dublin_core': dublin_core,
                    'archival_context': archival_context,
                    'file_info': json_data.get('file_info', {})
                }
            else:
                # Very old format
                base_name = document.replace('.json', '').rsplit('_Page', 1)[0]
                source_file = base_name + '.PDF'
                ocr_results = json_data.get('ocr_results', {})
                if 'ground_truth' in ocr_results:
                    ocr_versions['ground_truth'] = ocr_results['ground_truth'].get('text', '')
            
            print(f"  DEBUG: Source file from JSON: {source_file}")
            print(f"  DEBUG: OCR versions found: {list(ocr_versions.keys())}")
            
            # Find the actual source file in same directory as JSON
            source_path = json_path.parent / source_file
            print(f"  DEBUG: Looking for source at: {source_path}")
            print(f"  DEBUG: Source exists: {source_path.exists()}")
            
            if not source_path.exists():
                print(f"  Warning: Source file not found: {source_path}")
                return
            
            # Extract or copy image
            image_filename = f"{page_id}.jpg"
            image_path = self.images_dir / image_filename
            
            if source_path.suffix.lower() == '.pdf':
                self._extract_pdf_page(source_path, page_number, image_path)
            else:
                self._convert_image_to_jpeg(source_path, image_path)
            
            # Store page data
            self.data['pages'][page_id] = {
                'image': f"images/{image_filename}",
                'ocr_versions': ocr_versions,
                'source': f"{source_file} - Page {page_number}",
                'page_metadata': page_metadata,
                'doc_metadata': doc_metadata
            }
            
            print(f"  Extracted: {page_id} from {source_file} p.{page_number}")
        
        except Exception as e:
            import traceback
            print(f"  Error processing {document}: {e}")
            print(f"  DEBUG: Traceback: {traceback.format_exc()}")
    

    
    def _convert_image_to_jpeg(self, source_path, output_path):
        """Convert any image format (TIF, PNG, etc.) to web-friendly JPEG"""
        try:
            with Image.open(source_path) as img:
                # Convert to RGB if necessary (handles RGBA, palette, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if very large (keep aspect ratio, max 2000px on longest side)
                max_dim = 2000
                if max(img.size) > max_dim:
                    ratio = max_dim / max(img.size)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                
                img.save(output_path, 'JPEG', quality=85)
        except Exception as e:
            print(f"  Error converting image {source_path}: {e}")
            # Fallback: try direct copy
            shutil.copy2(source_path, output_path)

    def _extract_pdf_page(self, pdf_path, page_number, output_path):
        """Extract a single page from PDF as image"""
        try:
            doc = fitz.open(pdf_path)
            # Page numbers are 1-indexed in our system, 0-indexed in PyMuPDF
            page = doc[page_number - 1]
            
            # Render page to image at high resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for quality
            pix = page.get_pixmap(matrix=mat)
            
            # Save as JPEG
            pix.save(output_path)
            doc.close()
        except Exception as e:
            print(f"  Error extracting PDF page: {e}")
    
    def _generate_html(self):
        """Generate the HTML interface"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archive Entity Browser</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
        
        .toolbar { background: #1565C0; color: white; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
        .site-name { font-size: 18px; font-weight: bold; }
        .toolbar-menu { display: flex; gap: 15px; }
        .toolbar-item { color: white; text-decoration: none; padding: 6px 12px; border-radius: 4px; transition: background 0.2s; cursor: pointer; }
        .toolbar-item:hover { background: rgba(255,255,255,0.2); }
        
        .container { display: flex; flex: 1; overflow: hidden; }
        
        .panel { border-right: 1px solid #ccc; overflow-y: auto; }
        .panel h2 { padding: 15px; background: #f5f5f5; border-bottom: 1px solid #ccc; position: sticky; top: 0; z-index: 10; }
        
        #entities-panel { width: 12.5%; }
        #instances-panel { width: 12.5%; }
        #viewer-panel { width: 75%; display: flex; flex-direction: column; }
        
        .entity-item, .instance-item { 
            padding: 12px 15px; 
            cursor: pointer; 
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
        }
        .entity-item:hover, .instance-item:hover { background: #f0f0f0; }
        .entity-item.active, .instance-item.active { background: #e3f2fd; }
        
        .entity-name { font-weight: bold; }
        .entity-freq { color: #666; font-size: 0.9em; }
        
        .instance-doc { font-size: 0.85em; color: #666; margin-top: 4px; }
        
        #viewer-panel { border-right: none; }
        .viewer-content { display: flex; flex: 1; overflow: hidden; }
        .viewer-half { width: 50%; overflow: auto; padding: 20px; padding-top: 0; }
        .viewer-half img { max-width: 100%; height: auto; display: block; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-top: 20px; }
        
        .metadata-section { margin-bottom: 20px; padding: 15px; background: #f9f9f9; border-left: 3px solid #2196F3; }
        .metadata-section h3 { margin-bottom: 10px; font-size: 16px; color: #333; }
        .metadata-field { margin: 5px 0; font-size: 13px; }
        .metadata-label { font-weight: bold; color: #555; }
        .metadata-value { color: #333; }
        .date-highlight { font-size: 18px; font-weight: bold; color: #2196F3; margin: 10px 0; }
        
        .doc-header { padding: 15px; background: #f0f7ff; border-bottom: 2px solid #2196F3; margin-bottom: 20px; }
        .doc-title { font-size: 16px; font-weight: bold; color: #1565C0; margin-bottom: 5px; }
        .doc-date { font-size: 14px; color: #2196F3; margin-bottom: 10px; }
        .doc-context { font-size: 12px; color: #666; }
        
        .ner-tags { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 5px; }
        .ner-tag { padding: 4px 8px; background: #e3f2fd; border: 1px solid #90caf9; border-radius: 3px; font-size: 11px; cursor: pointer; transition: all 0.2s; }
        .ner-tag:hover { background: #bbdefb; transform: scale(1.05); }
        .ner-tag-label { font-weight: bold; color: #1976D2; margin-right: 3px; }
        
        #ocr-text { white-space: pre-wrap; line-height: 1.6; font-family: 'Courier New', monospace; font-size: 14px; }
        .highlight { background-color: #ffeb3b; font-weight: bold; }
        .ner-highlight { background-color: #a5d6a7; font-weight: bold; }
        
        .nav-controls { padding: 15px; background: #f5f5f5; border-top: 1px solid #ccc; display: flex; justify-content: space-between; align-items: center; }
        .nav-controls button { padding: 8px 16px; cursor: pointer; background: #2196F3; color: white; border: none; border-radius: 4px; }
        .nav-controls button:disabled { background: #ccc; cursor: not-allowed; }
        .nav-controls button:not(:disabled):hover { background: #1976D2; }
        .nav-info { color: #666; }
        
        .empty-state { padding: 40px; text-align: center; color: #999; }
    </style>
</head>
<body>
    <div class="toolbar">
        <div class="site-name">Archive Entity Browser</div>
        <div class="toolbar-menu">
            <a class="toolbar-item" href="#" onclick="showAbout(); return false;">About</a>
            <a class="toolbar-item" href="#" onclick="showStats(); return false;">Statistics</a>
        </div>
    </div>
    <div class="container">
        <!-- Entities Panel -->
        <div id="entities-panel" class="panel">
            <h2>Entities</h2>
            <div id="entities-list"></div>
        </div>
        
        <!-- Instances Panel -->
        <div id="instances-panel" class="panel">
            <h2>Instances</h2>
            <div id="instances-list"></div>
        </div>
        
        <!-- Viewer Panel -->
        <div id="viewer-panel">
            <h2 style="padding: 15px; background: #f5f5f5; border-bottom: 1px solid #ccc;">Document Viewer</h2>
            <div id="doc-header"></div>
            <div class="viewer-content">
                <div class="viewer-half">
                    <div id="image-container"></div>
                </div>
                <div class="viewer-half">
                    <div id="ocr-text"></div>
                </div>
            </div>
            <div class="nav-controls">
                <button id="prev-btn" onclick="navigateInstance(-1)">← Previous</button>
                <span class="nav-info" id="nav-info"></span>
                <button id="next-btn" onclick="navigateInstance(1)">Next →</button>
            </div>
        </div>
    </div>

    <script>
        let data = null;
        let currentEntity = null;
        let currentInstanceIndex = -1;

        // Load data
        fetch('data.json')
            .then(r => r.json())
            .then(d => {
                data = d;
                renderEntities();
            });

        function renderEntities() {
            const list = document.getElementById('entities-list');
            list.innerHTML = data.entities.map((entity, idx) => `
                <div class="entity-item" onclick="selectEntity(${idx})">
                    <div class="entity-name">${escapeHtml(entity.name)}</div>
                    <div class="entity-freq">${entity.frequency} mentions</div>
                </div>
            `).join('');
        }

        function selectEntity(idx) {
            currentEntity = data.entities[idx];
            currentInstanceIndex = -1;
            
            // Update active state
            document.querySelectorAll('.entity-item').forEach((el, i) => {
                el.classList.toggle('active', i === idx);
            });
            
            // Render instances
            const list = document.getElementById('instances-list');
            list.innerHTML = currentEntity.instances.map((inst, i) => `
                <div class="instance-item" onclick="selectInstance(${i})">
                    <div>${escapeHtml(inst.text_sample.substring(0, 100))}...</div>
                    <div class="instance-doc">${escapeHtml(inst.document)} - Page ${inst.page_number}</div>
                </div>
            `).join('');
            
            // Clear viewer
            document.getElementById('doc-header').innerHTML = '';
            document.getElementById('image-container').innerHTML = '<div class="empty-state">Select an instance to view</div>';
            document.getElementById('ocr-text').innerHTML = '';
            updateNavControls();
        }

        function selectInstance(idx) {
            currentInstanceIndex = idx;
            
            // Update active state
            document.querySelectorAll('.instance-item').forEach((el, i) => {
                el.classList.toggle('active', i === idx);
            });
            
            renderViewer();
            updateNavControls();
        }

        function renderViewer() {
            if (!currentEntity || currentInstanceIndex < 0) return;
            
            const instance = currentEntity.instances[currentInstanceIndex];
            const page = data.pages[instance.page_id];
            const dc = page.doc_metadata?.dublin_core || {};
            const arch = page.doc_metadata?.archival_context || {};
            const entities = page.page_metadata?.named_entities || {};
            
            // Render document header
            let headerHtml = '<div class="doc-header">';
            if (dc.title) {
                headerHtml += `<div class="doc-title">${escapeHtml(dc.title)}</div>`;
            }
            if (dc.date) {
                headerHtml += `<div class="doc-date">📅 ${escapeHtml(dc.date)}</div>`;
            }
            if (arch.collection || arch.box || arch.folder) {
                headerHtml += '<div class="doc-context">';
                if (arch.collection) headerHtml += escapeHtml(arch.collection);
                if (arch.box) headerHtml += ` › ${escapeHtml(arch.box)}`;
                if (arch.folder) headerHtml += ` › ${escapeHtml(arch.folder)}`;
                if (page.page_metadata?.page_number) headerHtml += ` › Page ${page.page_metadata.page_number}`;
                headerHtml += '</div>';
            }
            
            // Add NER tags
            if (Object.keys(entities).length > 0) {
                headerHtml += '<div class="ner-tags">';
                for (const [type, items] of Object.entries(entities)) {
                    if (items && items.length > 0) {
                        for (const entity of items) {
                            headerHtml += `<span class="ner-tag" onmouseover="highlightNER('${escapeHtml(entity).replace(/'/g, "\\'")}')"
                                onmouseout="clearNERHighlight()">
                                <span class="ner-tag-label">${type}:</span>${escapeHtml(entity)}
                            </span>`;
                        }
                    }
                }
                headerHtml += '</div>';
            }
            headerHtml += '</div>';
            document.getElementById('doc-header').innerHTML = headerHtml;
            
            // Render image
            document.getElementById('image-container').innerHTML = 
                `<img src="${page.image}" alt="Page ${instance.page_number}">`;
            
            // Get OCR text - prefer openai_ocr, then other engines, then CSV snippet
            let ocrText = '';
            let ocrSource = 'No OCR available';
            
            const ocrVersions = page.ocr_versions || {};
            const engines = Object.keys(ocrVersions);
            
            // Prefer openai_ocr
            if (ocrVersions['openai_ocr']) {
                ocrText = ocrVersions['openai_ocr'];
                ocrSource = 'OCR: openai_ocr';
            } else if (engines.length > 0) {
                const engineName = engines[0];
                ocrText = ocrVersions[engineName] || '';
                ocrSource = `OCR: ${engineName}`;
            } else if (instance.text_sample) {
                ocrText = instance.text_sample;
                ocrSource = 'OCR: Entity context snippet';
            }
            
            // Display OCR with label
            let ocrHtml = `<div style="font-size: 11px; color: #666; margin-bottom: 10px; padding: 5px; background: #f5f5f5; border-radius: 3px;">${ocrSource}</div>`;
            const highlightedText = highlightEntity(ocrText, currentEntity.name);
            ocrHtml += highlightedText;
            document.getElementById('ocr-text').innerHTML = ocrHtml;
        }
        
        function highlightNER(entityText) {
            const ocrDiv = document.getElementById('ocr-text');
            const text = ocrDiv.textContent;
            const regex = new RegExp(`(${escapeRegex(entityText)})`, 'gi');
            const highlighted = escapeHtml(text).replace(regex, '<span class="ner-highlight">$1</span>');
            ocrDiv.innerHTML = highlighted;
        }
        
        function clearNERHighlight() {
            if (currentEntity && currentInstanceIndex >= 0) {
                const instance = currentEntity.instances[currentInstanceIndex];
                const page = data.pages[instance.page_id];
                
                // Get OCR text same way as renderViewer
                let ocrText = '';
                let ocrSource = 'No OCR available';
                const ocrVersions = page.ocr_versions || {};
                const engines = Object.keys(ocrVersions);
                
                if (ocrVersions['openai_ocr']) {
                    ocrText = ocrVersions['openai_ocr'];
                    ocrSource = 'OCR: openai_ocr';
                } else if (engines.length > 0) {
                    ocrText = ocrVersions[engines[0]] || '';
                    ocrSource = `OCR: ${engines[0]}`;
                } else if (instance.text_sample) {
                    ocrText = instance.text_sample;
                    ocrSource = 'OCR: Entity context snippet';
                }
                
                let ocrHtml = `<div style="font-size: 11px; color: #666; margin-bottom: 10px; padding: 5px; background: #f5f5f5; border-radius: 3px;">${ocrSource}</div>`;
                const highlightedText = highlightEntity(ocrText, currentEntity.name);
                ocrHtml += highlightedText;
                document.getElementById('ocr-text').innerHTML = ocrHtml;
            }
        }

        function highlightEntity(text, entityName) {
            if (!text) return '';
            const escaped = escapeHtml(text);
            const regex = new RegExp(`(${escapeRegex(entityName)})`, 'gi');
            return escaped.replace(regex, '<span class="highlight">$1</span>');
        }

        function navigateInstance(direction) {
            if (!currentEntity) return;
            
            const newIndex = currentInstanceIndex + direction;
            if (newIndex >= 0 && newIndex < currentEntity.instances.length) {
                selectInstance(newIndex);
                
                // Scroll instance into view
                const items = document.querySelectorAll('.instance-item');
                if (items[newIndex]) {
                    items[newIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        }

        function updateNavControls() {
            const prevBtn = document.getElementById('prev-btn');
            const nextBtn = document.getElementById('next-btn');
            const info = document.getElementById('nav-info');
            
            if (!currentEntity || currentInstanceIndex < 0) {
                prevBtn.disabled = true;
                nextBtn.disabled = true;
                info.textContent = '';
            } else {
                prevBtn.disabled = currentInstanceIndex === 0;
                nextBtn.disabled = currentInstanceIndex === currentEntity.instances.length - 1;
                info.textContent = `${currentInstanceIndex + 1} of ${currentEntity.instances.length}`;
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function escapeRegex(text) {
            return text.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
        }
        
        function showAbout() {
            alert('Archive Entity Browser\\n\\nInteractive interface for exploring named entities in archival documents.\\n\\nFeatures:\\n- Browse entities by frequency\\n- View document images and OCR text\\n- Highlight entity mentions\\n- Explore page-level named entities');
        }
        
        function showStats() {
            if (!data) return;
            const totalEntities = data.entities.length;
            const totalPages = Object.keys(data.pages).length;
            const totalInstances = data.entities.reduce((sum, e) => sum + e.frequency, 0);
            alert(`Statistics\\n\\nTotal Entities: ${totalEntities}\\nTotal Pages: ${totalPages}\\nTotal Mentions: ${totalInstances}`);
        }
    </script>
</body>
</html>"""
        
        html_file = self.output_dir / 'index.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Generated: {html_file}")


def main():
    if len(sys.argv) < 5:
        print("="*80)
        print("Web Export Generator for Archive Analyzer")
        print("="*80)
        print("\nGenerates a static HTML website for browsing entity mentions with page images")
        print("and OCR text. Extracts document metadata and creates an interactive interface.")
        print("\nUsage:")
        print("  python web_export_generator.py <archive_dir> <entity_csv> <instance_csv> <output_dir>")
        print("\nArguments:")
        print("  archive_dir   - Path to archive with JSON sidecars (searches recursively)")
        print("  entity_csv    - Aggregated entity CSV (e.g., entity_person_fullname.csv)")
        print("  instance_csv  - Instance-by-instance CSV (e.g., instance_by_instance_person_fullname_5plus.csv)")
        print("  output_dir    - Output directory for web export (will be created)")
        print("\nExample:")
        print('  python web_export_generator.py \\')
        print('    "D:\\ArchiveData\\NEH Domestic Science Project - Digitized Materials" \\')
        print('    entity_person_fullname.csv \\')
        print('    instance_by_instance_person_fullname_5plus.csv \\')
        print('    web_export_persons')
        print("\nOutput:")
        print("  - index.html: Interactive web interface")
        print("  - data.json: Entity and page data with metadata")
        print("  - images/: Extracted page images (JPEGs from PDFs)")
        print("\nNote: Requires entity CSVs generated by archive_report_generator.py")
        print("="*80)
        sys.exit(1)
    
    archive_dir = sys.argv[1]
    entity_csv = sys.argv[2]
    instance_csv = sys.argv[3]
    output_dir = sys.argv[4]
    
    generator = WebExportGenerator(archive_dir, entity_csv, instance_csv, output_dir)
    generator.generate()


if __name__ == "__main__":
    main()
