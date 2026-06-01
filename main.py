#!/usr/bin/env python3
"""
ARCHIVE ANALYZER - AI-Powered Archival Document Analysis
Main application with GUI interface
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import threading
from pathlib import Path
from typing import List, Dict, Any, Tuple

from src.ledger_manager import LedgerManager
from src.ocr_processor import OCRProcessor
from src.prompt_processor import PromptProcessor
from src.ocr_evaluator import OCREvaluator
from src.config_manager import ConfigManager
from src.ner_processor import NERProcessor
from src.entity_matcher import EntityMatcher
from src.topic_modeler import TopicModeler
from src.timeline_extractor import TimelineExtractor
from src.geo_mapper import GeoMapper

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class CodebooksApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ARCHIVE ANALYZER - AI-Powered Archival Document Analysis")
        
        # Initialize configuration
        self.config = ConfigManager()
        self.root.geometry(self.config.get('ui_settings', 'window_geometry', '1000x700'))
        
        # Initialize components
        self.ledger = LedgerManager()
        self.ocr = OCRProcessor()
        self.prompt_processor = None
        self.ner_processor = NERProcessor()
        self.entity_matcher = EntityMatcher()
        self.topic_modeler = TopicModeler()
        self.timeline_extractor = TimelineExtractor()
        self.geo_mapper = GeoMapper()
        # Load saved ground truth engine
        self.ground_truth_engine = self.config.get('ocr_settings', 'ground_truth_engine', None)
        
        # Activity log for status tracking
        self.activity_log = []
        self.operation_times = []
        self.stop_requested = False
        
        self.setup_ui()
        
        # Load AI configurations after UI is set up
        self.load_ai_configurations()
        
        self.refresh_display()
        # Force update analysis display
        self.update_analysis_display()
        
        # Save config on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        # Configure root
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Title bar
        title_frame = ttk.Frame(main_container)
        title_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(1, weight=1)
        
        ttk.Label(title_frame, text="ARCHIVE ANALYZER", font=("Arial", 18, "bold")).grid(row=0, column=0, sticky=tk.W)
        
        # Progress bar and stop button
        progress_frame = ttk.Frame(title_frame)
        progress_frame.grid(row=0, column=1, sticky=(tk.E), padx=(20, 0))
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(progress_frame, text="⏹️ Stop", command=self.stop_processing, state='disabled')
        self.stop_button.pack(side=tk.LEFT)
        
        # Redesigned workflow control panel
        control_frame = ttk.LabelFrame(main_container, text="Workflow", padding="15")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        
        # STEP 1: FILE MANAGEMENT
        ttk.Label(control_frame, text="1️⃣ FILE MANAGEMENT", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        file_buttons_frame = ttk.Frame(control_frame)
        file_buttons_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        file_buttons_frame.columnconfigure(0, weight=1)
        file_buttons_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_buttons_frame, text="📁 Add Files/Directory", command=self.add_files).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        ttk.Button(file_buttons_frame, text="📥 Import from Sidecars", command=self.import_from_sidecars_dialog).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(2, 0))
        
        # STEP 2: AI CONFIGURATION
        ttk.Label(control_frame, text="2️⃣ AI CONFIGURATION", font=("Arial", 11, "bold")).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        config_frame = ttk.Frame(control_frame)
        config_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)
        
        ttk.Button(config_frame, text="⚙️ Configure AI Models & OCR Engines", command=self.show_configuration_dialog).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        ttk.Button(config_frame, text="🔄 Check Batch Status", command=self.check_batch_status).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(2, 0))
        
        # Configuration status display
        self.config_status = tk.StringVar(value="Configuration: Not set")
        ttk.Label(control_frame, textvariable=self.config_status, font=("Arial", 9), foreground="gray").grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        
        # STEP 3: PROCESSING
        ttk.Label(control_frame, text="3️⃣ PROCESSING", font=("Arial", 11, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        process_frame = ttk.Frame(control_frame)
        process_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        process_frame.columnconfigure(0, weight=1)
        process_frame.columnconfigure(1, weight=1)
        
        ttk.Button(process_frame, text="⚡ Batch Process N Files", command=self.batch_process_files).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        ttk.Button(process_frame, text="🔍 Process All Files", command=self.process_all_files).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(2, 0))
        
        # STEP 4: GROUND TRUTH
        ttk.Label(control_frame, text="4️⃣ GROUND TRUTH", font=("Arial", 11, "bold")).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        gt_frame = ttk.Frame(control_frame)
        gt_frame.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        gt_frame.columnconfigure(0, weight=1)
        
        ttk.Button(gt_frame, text="📊 Evaluate & Set Ground Truth", command=self.evaluate_ocr).grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Ground truth status
        self.ground_truth_status = tk.StringVar(value="Ground Truth: Not set")
        ttk.Label(control_frame, textvariable=self.ground_truth_status, font=("Arial", 9), foreground="gray").grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        
        # STEP 5: CONTENT ANALYSIS (Requires Ground Truth)
        ttk.Label(control_frame, text="5️⃣ CONTENT ANALYSIS (Requires Ground Truth)", font=("Arial", 11, "bold")).grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        analysis_frame = ttk.Frame(control_frame)
        analysis_frame.grid(row=11, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        analysis_frame.columnconfigure(0, weight=1)
        analysis_frame.columnconfigure(1, weight=1)
        analysis_frame.columnconfigure(2, weight=1)
        
        ttk.Button(analysis_frame, text="📝 Generate Metadata", command=self.generate_metadata).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 1))
        ttk.Button(analysis_frame, text="⚡ Batch Metadata", command=self.generate_batch_metadata).grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 1), pady=(2, 0))
        ttk.Button(analysis_frame, text="🏷️ Extract Entities", command=self.extract_named_entities).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(1, 1))
        ttk.Button(analysis_frame, text="🔗 Analyze Relationships", command=self.analyze_document_relationships).grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(1, 0))
        
        # STEP 6: DATA MANAGEMENT
        ttk.Label(control_frame, text="6️⃣ DATA MANAGEMENT", font=("Arial", 11, "bold")).grid(row=12, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        data_frame = ttk.Frame(control_frame)
        data_frame.grid(row=13, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        data_frame.columnconfigure(0, weight=1)
        data_frame.columnconfigure(1, weight=1)
        data_frame.columnconfigure(2, weight=1)
        data_frame.columnconfigure(2, weight=1)
        
        ttk.Button(data_frame, text="💾 Export Results", command=self.export_results).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 1))
        ttk.Button(data_frame, text="📋 Import CSV", command=self.import_csv_with_paths).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(1, 1))
        ttk.Button(data_frame, text="📂 Expand All", command=lambda: self.expand_collapse_tree(self.tree, True)).grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(1, 1))
        ttk.Button(data_frame, text="📁 Collapse All", command=lambda: self.expand_collapse_tree(self.tree, False)).grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(1, 1))
        ttk.Button(data_frame, text="🔄 Refresh", command=self.refresh_display).grid(row=0, column=4, sticky=(tk.W, tk.E), padx=(1, 1))
        ttk.Button(data_frame, text="🗑️ Clear Selected", command=self.clear_rows).grid(row=0, column=5, sticky=(tk.W, tk.E), padx=(1, 0))
        
        # Create main paned window for resizable layout
        main_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_paned.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Data display in notebook
        self.notebook = ttk.Notebook(main_paned)
        
        # Processing tab
        processing_frame = ttk.Frame(self.notebook)
        self.notebook.add(processing_frame, text="📊 Processing")
        processing_frame.columnconfigure(0, weight=1)
        processing_frame.rowconfigure(0, weight=1)
        
        # Create frame for treeview with scrollbars
        tree_frame = ttk.Frame(processing_frame)
        tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Treeview for data display with tree structure
        columns = ['filename', 'status', 'document_type', 'ocr_preview', 'named_entities', 'filepath']
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=20)
        
        # Configure columns
        self.tree.heading('#0', text='Archive Structure')
        self.tree.heading('filename', text='File')
        self.tree.heading('status', text='Status')
        self.tree.heading('document_type', text='Doc Type')
        self.tree.heading('ocr_preview', text='OCR Preview')
        self.tree.heading('named_entities', text='NER')
        self.tree.heading('filepath', text='File Path')
        
        self.tree.column('#0', width=250)
        self.tree.column('filename', width=200)
        self.tree.column('status', width=100)
        self.tree.column('document_type', width=100)
        self.tree.column('ocr_preview', width=300)
        self.tree.column('named_entities', width=200)
        self.tree.column('filepath', width=400)
        
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        self.tree.bind('<Button-3>', self.on_tree_right_click)  # Right-click context menu
        
        # Scrollbars with proper grid layout
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Grid layout for treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_scroll_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Analysis tab
        analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(analysis_frame, text="📈 Analysis")
        
        # Entity Browser tab
        entity_frame = ttk.Frame(self.notebook)
        self.notebook.add(entity_frame, text="🏷️ Entities")
        self.setup_entity_browser(entity_frame)
        analysis_frame.columnconfigure(0, weight=1)
        analysis_frame.rowconfigure(0, weight=1)
        
        # Create frame for analysis text with scrollbars
        analysis_text_frame = ttk.Frame(analysis_frame)
        analysis_text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        analysis_text_frame.columnconfigure(0, weight=1)
        analysis_text_frame.rowconfigure(0, weight=1)
        
        self.analysis_text = tk.Text(analysis_text_frame, wrap=tk.WORD, font=("Consolas", 9))
        analysis_scroll_y = ttk.Scrollbar(analysis_text_frame, orient=tk.VERTICAL, command=self.analysis_text.yview)
        analysis_scroll_x = ttk.Scrollbar(analysis_text_frame, orient=tk.HORIZONTAL, command=self.analysis_text.xview)
        self.analysis_text.configure(yscrollcommand=analysis_scroll_y.set, xscrollcommand=analysis_scroll_x.set)
        
        self.analysis_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        analysis_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        analysis_scroll_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        main_paned.add(self.notebook, weight=3)
        
        # Status bar at bottom with activity log
        status_frame = ttk.Frame(main_container)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(1, weight=1)
        
        # Current status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Activity log
        log_frame = ttk.LabelFrame(status_frame, text="Activity Log")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.activity_text = tk.Text(log_frame, height=10, wrap=tk.WORD, font=("Consolas", 8))
        activity_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.activity_text.yview)
        self.activity_text.configure(yscrollcommand=activity_scroll.set)
        
        self.activity_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        activity_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S), pady=5)
        
        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.add_files())
        self.root.bind('<Control-r>', lambda e: self.run_selected_ocr())
        self.root.bind('<F5>', lambda e: self.refresh_display())
    
    def run_selected_ocr(self):
        """Run the selected OCR engine or all engines"""
        engine = self.ocr_engine.get()
        if engine == "EasyOCR (AI)":
            self.run_ocr()
        elif engine == "Tesseract":
            self.run_tesseract_ocr()
        elif engine == "PyPDF2":
            self.run_pypdf2_ocr()
        elif engine == "OpenAI OCR":
            self.run_openai_ocr()
        elif engine == "Ollama OCR":
            self.run_ollama_ocr()
        elif engine == "All OCR Engines":
            self.run_all_ocr()
    
    def add_files(self):
        """Add files or directory to the ledger"""
        choice = messagebox.askyesnocancel("Add Files", 
                                          "Yes: Add individual files\nNo: Add entire directory\nCancel: Cancel")
        
        if choice is None:  # Cancel
            return
        elif choice:  # Yes - individual files
            files = filedialog.askopenfilenames(
                title="Select files",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.tif *.tiff"), 
                          ("PDFs", "*.pdf"), ("All files", "*.*")]
            )
            file_paths = list(files)
            
            if file_paths:
                added_count = self.ledger.add_files(file_paths)
                messagebox.showinfo("Files Added", f"Added {added_count} new files to the ledger")
                self.refresh_display()
        else:  # No - directory
            directory = filedialog.askdirectory(title="Select directory")
            if not directory:
                return
            
            # Check for JSON sidecars in directory
            has_sidecars = self.check_for_sidecars(directory)
            
            if has_sidecars:
                # Offer smart import
                import_choice = messagebox.askyesno(
                    "JSON Sidecars Detected",
                    "This directory contains JSON sidecar files with pre-processed data.\n\n"
                    "Would you like to IMPORT existing data from sidecars?\n\n"
                    "Yes: Import with options (OCR, metadata, entities)\n"
                    "No: Add files as new (ignore sidecars)"
                )
                
                if import_choice:
                    self.import_with_sidecars(directory)
                    return
            
            # Standard file addition
            file_paths = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if Path(file).suffix.lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pdf']:
                        file_paths.append(os.path.join(root, file))
            
            if file_paths:
                added_count = self.ledger.add_files(file_paths)
                messagebox.showinfo("Files Added", f"Added {added_count} new files to the ledger")
                self.refresh_display()
    
    def check_for_sidecars(self, directory: str) -> bool:
        """Check if directory contains JSON sidecar files"""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json') and not file.startswith('_'):
                    # Check if it's a sidecar (has corresponding image/PDF)
                    base_name = file.replace('.json', '').replace('_metadata', '').split('_Page')[0]
                    for ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pdf', '.PDF']:
                        if f"{base_name}{ext}" in files:
                            return True
        return False
    
    def import_with_sidecars(self, directory: str):
        """Import files with JSON sidecars using configuration dialog"""
        # Show import configuration dialog
        options = self.show_import_options_dialog(directory)
        
        if not options:
            return
        
        # Run import in background thread
        def import_worker():
            self.status_var.set("Importing files with sidecars...")
            self.log_activity(f"Starting smart import from {directory}")
            self.progress.start()
            
            try:
                stats = self.ledger.import_from_sidecars(directory, options)
                
                result_msg = (
                    f"✅ Import Complete!\n\n"
                    f"📁 Files found: {stats['files_found']}\n"
                    f"📄 Sidecars found: {stats['sidecars_found']}\n"
                    f"✨ Files imported: {stats['files_imported']}\n\n"
                )
                
                if options.get('import_ocr'):
                    result_msg += f"🔍 OCR transcripts imported: {stats['ocr_imported']}\n"
                if options.get('import_metadata'):
                    result_msg += f"📝 Metadata imported: {stats['metadata_imported']}\n"
                if options.get('import_entities') and not options.get('rerun_ner'):
                    result_msg += f"🏷️ Entities imported: {stats['entities_imported']}\n"
                if options.get('rerun_ner'):
                    result_msg += f"🔄 Entities marked for re-extraction\n"
                
                self.status_var.set("Import completed")
                self.log_activity(f"Import completed: {stats['files_imported']} files")
                self.root.after(0, lambda: [
                    self.progress.stop(),
                    messagebox.showinfo("Import Complete", result_msg),
                    self.refresh_display()
                ])
            except Exception as e:
                self.status_var.set("Import failed")
                self.log_activity(f"Import error: {e}")
                self.root.after(0, lambda: [
                    self.progress.stop(),
                    messagebox.showerror("Import Error", f"Failed to import:\n{e}")
                ])
        
        threading.Thread(target=import_worker, daemon=True).start()
    
    def show_import_options_dialog(self, directory: str) -> dict:
        """Show dialog for configuring sidecar import options"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Options - JSON Sidecars")
        dialog.geometry("600x550")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {}
        
        # Header
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="📦 Smart Import from JSON Sidecars", 
                 font=("Arial", 14, "bold")).pack()
        ttk.Label(header_frame, text=f"Directory: {os.path.basename(directory)}", 
                 font=("Arial", 9), foreground="gray").pack()
        
        # Instructions
        inst_frame = ttk.LabelFrame(dialog, text="ℹ️ About Smart Import", padding="10")
        inst_frame.pack(fill=tk.X, padx=10, pady=5)
        
        instructions = tk.Text(inst_frame, height=4, wrap=tk.WORD, bg='#f8f8f8')
        instructions.pack(fill=tk.X)
        instructions.insert(1.0,
            "Import pre-processed files with existing JSON sidecars.\n"
            "Choose what to import and what to re-process.\n\n"
            "💡 Tip: Import OCR to avoid expensive re-processing, but re-run NER "
            "if you want to use a different transcript source.")
        instructions.config(state=tk.DISABLED)
        
        # Options frame
        options_frame = ttk.LabelFrame(dialog, text="Import Options", padding="15")
        options_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # OCR Import
        import_ocr_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="🔍 Import OCR Transcripts", 
                       variable=import_ocr_var).pack(anchor=tk.W, pady=5)
        ttk.Label(options_frame, text="   Load existing OCR results from all engines (EasyOCR, Tesseract, PyPDF2, OpenAI, Ollama)",
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=20)
        
        # Metadata Import
        import_metadata_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="📝 Import Dublin Core Metadata", 
                       variable=import_metadata_var).pack(anchor=tk.W, pady=5)
        ttk.Label(options_frame, text="   Load existing metadata (title, creator, subject, description, etc.)",
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=20)
        
        # Entity Import
        import_entities_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="🏷️ Import Named Entities", 
                       variable=import_entities_var).pack(anchor=tk.W, pady=5)
        ttk.Label(options_frame, text="   Load existing entity extractions (people, organizations, locations, etc.)",
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=20)
        
        # NER Re-run
        ttk.Separator(options_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        rerun_ner_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="🔄 Re-run Named Entity Recognition", 
                       variable=rerun_ner_var).pack(anchor=tk.W, pady=5)
        ttk.Label(options_frame, text="   Extract entities again (useful if you want to use a different OCR source)",
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=20)
        
        # Ground truth engine selection
        gt_frame = ttk.Frame(options_frame)
        gt_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(gt_frame, text="OCR Source for NER:", font=("Arial", 9)).pack(side=tk.LEFT)
        
        gt_engine_var = tk.StringVar(value=self.ground_truth_engine or 'openai_ocr')
        gt_combo = ttk.Combobox(gt_frame, textvariable=gt_engine_var, width=15, state='readonly')
        gt_combo['values'] = ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']
        gt_combo.pack(side=tk.LEFT, padx=5)
        
        # Disable entity import if rerun is selected
        def toggle_entity_import():
            if rerun_ner_var.get():
                import_entities_var.set(False)
        
        rerun_ner_var.trace_add('write', lambda *args: toggle_entity_import())
        
        # Preview frame
        preview_frame = ttk.LabelFrame(dialog, text="📊 Preview", padding="10")
        preview_frame.pack(fill=tk.X, padx=10, pady=5)
        
        preview_text = tk.Text(preview_frame, height=3, wrap=tk.WORD, bg='#f0f0f0')
        preview_text.pack(fill=tk.X)
        preview_text.insert(1.0, "Scanning directory for files and sidecars...")
        preview_text.config(state=tk.DISABLED)
        
        # Scan directory for preview
        def update_preview():
            import json
            file_count = 0
            sidecar_count = 0
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pdf']:
                        file_count += 1
                    if file.endswith('.json') and not file.startswith('_'):
                        sidecar_count += 1
            
            preview_text.config(state=tk.NORMAL)
            preview_text.delete(1.0, tk.END)
            preview_text.insert(1.0, 
                f"📁 Found {file_count} image/PDF files\n"
                f"📄 Found {sidecar_count} JSON sidecar files\n"
                f"✨ Ready to import with selected options")
            preview_text.config(state=tk.DISABLED)
        
        dialog.after(100, update_preview)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def on_import():
            result['import_ocr'] = import_ocr_var.get()
            result['import_metadata'] = import_metadata_var.get()
            result['import_entities'] = import_entities_var.get()
            result['rerun_ner'] = rerun_ner_var.get()
            result['ground_truth_engine'] = gt_engine_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="📥 Import", command=on_import).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        dialog.wait_window()
        return result
    
    def import_from_sidecars_dialog(self):
        """Direct import from sidecars - select directory"""
        directory = filedialog.askdirectory(title="Select directory with JSON sidecars")
        if not directory:
            return
        
        # Check for sidecars
        has_sidecars = self.check_for_sidecars(directory)
        
        if not has_sidecars:
            messagebox.showwarning(
                "No Sidecars Found",
                "No JSON sidecar files found in this directory.\n\n"
                "Sidecars should be named:\n"
                "• filename.json (for images)\n"
                "• filename_metadata.json + filename_PageN.json (for PDFs)"
            )
            return
        
        self.import_with_sidecars(directory)
    
    def run_ocr(self):
        """Run OCR on pending files"""
        # Check if OCR models are available
        if not self.ocr.models:
            messagebox.showerror("OCR Not Available", 
                               "EasyOCR not available. Install with: pip install easyocr")
            return
        
        pending_files = self.ledger.get_files_by_status('easyocr', 'pending')
        
        if pending_files.empty:
            messagebox.showinfo("OCR", "No files pending OCR processing")
            return
        
        def ocr_worker():
            self.status_var.set("Running OCR...")
            self.log_activity("Started EasyOCR processing")
            processed = 0
            operation_times = []
            
            for _, row in pending_files.iterrows():
                op_start = time.time()
                
                if operation_times:
                    avg_time = sum(operation_times) / len(operation_times)
                    remaining_ops = len(pending_files) - processed
                    est_remaining = avg_time * remaining_ops
                    est_min = int(est_remaining // 60)
                    est_sec = int(est_remaining % 60)
                    time_str = f" (Est: {est_min}m {est_sec}s remaining)"
                else:
                    time_str = ""
                
                status_msg = f"OCR: {processed + 1}/{len(pending_files)} - {row['filename']}{time_str}"
                self.status_var.set(status_msg)
                self.log_activity(f"Processing EasyOCR for {row['filename']}")
                
                page_num = row.get('page_number', 0)
                text, status = self.ocr.process_file(row['filepath'], 'easyocr', page_number=page_num if page_num > 0 else None)
                self.ledger.update_ocr_result(row['file_id'], text, status, 'easyocr')
                
                op_time = time.time() - op_start
                operation_times.append(op_time)
                if len(operation_times) > 20:
                    operation_times.pop(0)
                
                processed += 1
            
            self.status_var.set("OCR completed")
            self.root.after(0, lambda: [self.progress.stop(), self.refresh_display()])
        
        self.progress.start()
        threading.Thread(target=ocr_worker, daemon=True).start()
    
    def run_tesseract_ocr(self):
        """Run Tesseract OCR on pending files"""
        # Check if Tesseract model is available
        if 'tesseract' not in self.ocr.models:
            # Try to get more specific error info
            try:
                import pytesseract
                from PIL import Image
                # Test with a small image
                test_img = Image.new('RGB', (100, 50), color='white')
                pytesseract.image_to_string(test_img)
                error_msg = "Tesseract model failed to initialize for unknown reasons."
            except Exception as e:
                error_msg = f"Tesseract Error: {str(e)}\n\nPlease install Tesseract OCR from:\nhttps://github.com/UB-Mannheim/tesseract/wiki"
            
            messagebox.showerror("Tesseract Not Available", error_msg)
            return
        
        pending_files = self.ledger.get_files_by_status('tesseract', 'pending')
        
        if pending_files.empty:
            messagebox.showinfo("Tesseract OCR", "No files pending Tesseract OCR processing")
            return
        
        def tesseract_worker():
            self.status_var.set("Running Tesseract OCR...")
            self.log_activity("Started Tesseract OCR processing")
            processed = 0
            
            for _, row in pending_files.iterrows():
                self.status_var.set(f"Tesseract OCR: {processed + 1}/{len(pending_files)} - {row['filename']}")
                self.log_activity(f"Processing Tesseract OCR for {row['filename']}")
                
                try:
                    page_num = row.get('page_number', 0)
                    text, status = self.ocr.process_file(row['filepath'], 'tesseract', page_number=page_num if page_num > 0 else None)
                    self.ledger.update_ocr_result(row['file_id'], text, status, 'tesseract')
                except Exception as e:
                    error_text = f"Error processing {row['filename']}: {str(e)}"
                    self.ledger.update_ocr_result(row['file_id'], error_text, 'error', 'tesseract')
                    print(f"Tesseract error: {e}")
                processed += 1
            
            self.status_var.set("Tesseract OCR completed")
            self.root.after(0, self.refresh_display)
        
        threading.Thread(target=tesseract_worker, daemon=True).start()
    
    def run_pypdf2_ocr(self):
        """Run PyPDF2 text extraction on pending PDF files"""
        # Check if PyPDF2 model is available
        if 'pypdf2' not in self.ocr.models:
            messagebox.showerror("PyPDF2 Not Available", 
                               "PyPDF2 not available. Install with: pip install PyPDF2")
            return
        
        pending_files = self.ledger.get_files_by_status('pypdf2', 'pending')
        
        if pending_files.empty:
            messagebox.showinfo("PyPDF2 Extract", "No files pending PyPDF2 processing")
            return
        
        def pypdf2_worker():
            self.status_var.set("Running PyPDF2 extraction...")
            processed = 0
            
            for _, row in pending_files.iterrows():
                self.status_var.set(f"PyPDF2: {processed + 1}/{len(pending_files)} - {row['filename']}")
                
                try:
                    page_num = row.get('page_number', 0)
                    text, status = self.ocr.process_file(row['filepath'], 'pypdf2', page_number=page_num if page_num > 0 else None)
                    self.ledger.update_ocr_result(row['file_id'], text, status, 'pypdf2')
                except Exception as e:
                    error_text = f"Error processing {row['filename']}: {str(e)}"
                    self.ledger.update_ocr_result(row['file_id'], error_text, 'error', 'pypdf2')
                    print(f"PyPDF2 error: {e}")
                processed += 1
            
            self.status_var.set("PyPDF2 extraction completed")
            self.root.after(0, self.refresh_display)
        
        threading.Thread(target=pypdf2_worker, daemon=True).start()
    
    def run_openai_ocr(self):
        """Run OpenAI OCR on pending files"""
        # Check if OpenAI OCR is available
        if 'openai_ocr' not in self.ocr.models:
            messagebox.showwarning("OpenAI Not Setup", "Please configure OpenAI in AI Configuration first")
            return
        
        pending_files = self.ledger.get_files_by_status('openai_ocr', 'pending')
        
        if pending_files.empty:
            messagebox.showinfo("OpenAI OCR", "No files pending OpenAI OCR processing")
            return
        
        # Check if batching is enabled
        batching_enabled = hasattr(self.ocr, 'batching_enabled') and self.ocr.batching_enabled
        
        def ocr_callback(file_id, result, status):
            """Callback for batch processing results"""
            self.ledger.update_ocr_result(file_id, result, status, 'openai_ocr')
            self.root.after(0, self.refresh_display)
        
        def openai_worker():
            self.status_var.set("Running OpenAI OCR...")
            self.log_activity(f"Started OpenAI OCR processing ({len(pending_files)} files)")
            processed = 0
            queued = 0
            
            for _, row in pending_files.iterrows():
                self.status_var.set(f"OpenAI OCR: {processed + 1}/{len(pending_files)} - {row['filename']}")
                
                try:
                    if batching_enabled:
                        # Process with batching - provide callback
                        text, status = self.ocr.process_image(
                            row['filepath'], 
                            'openai_ocr',
                            callback=ocr_callback,
                            file_id=row['file_id']
                        )
                        
                        if status == 'queued':
                            # Mark as queued in ledger
                            self.ledger.update_ocr_result(row['file_id'], 'Queued for batch processing', 'queued', 'openai_ocr')
                            queued += 1
                        else:
                            # Immediate result
                            self.ledger.update_ocr_result(row['file_id'], text, status, 'openai_ocr')
                    else:
                        # Process immediately without batching
                        page_num = row.get('page_number', 0)
                        text, status = self.ocr.process_file(row['filepath'], 'openai_ocr', page_number=page_num if page_num > 0 else None)
                        self.ledger.update_ocr_result(row['file_id'], text, status, 'openai_ocr')
                except Exception as e:
                    error_text = f"Error processing {row['filename']}: {str(e)}"
                    self.ledger.update_ocr_result(row['file_id'], error_text, 'error', 'openai_ocr')
                    self.log_activity(f"OpenAI OCR error on {row['filename']}: {e}")
                processed += 1
            
            if batching_enabled and queued > 0:
                self.status_var.set(f"OpenAI OCR: {queued} files queued for batch processing")
                self.log_activity(f"Queued {queued} files for batch processing. Use 'Check Batch Status' to retrieve results.")
                messagebox.showinfo("Batch Queued", 
                    f"{queued} files queued for batch processing.\n\n"
                    f"Results will be available in ~24 hours.\n"
                    f"Use 'Check Batch Status' button to retrieve completed results.")
            else:
                self.status_var.set("OpenAI OCR completed")
                self.log_activity(f"OpenAI OCR completed: {processed} files processed")
            
            self.root.after(0, self.refresh_display)
        
        threading.Thread(target=openai_worker, daemon=True).start()
    
    def run_ollama_ocr(self):
        """Run Ollama OCR on pending files"""
        # Check if Ollama is available and get model name
        model_name = simpledialog.askstring("Ollama Model", 
                                           "Enter Ollama model name:", 
                                           initialvalue="gemma3")
        if not model_name:
            return
        
        # Add Ollama OCR model
        self.ocr.add_ollama_ocr(model_name)
        
        if 'ollama_ocr' not in self.ocr.models:
            messagebox.showerror("Ollama OCR Not Available", 
                               "Ollama OCR not available. Make sure Ollama is running and the model is installed.")
            return
        
        pending_files = self.ledger.get_files_by_status('ollama_ocr', 'pending')
        
        if pending_files.empty:
            messagebox.showinfo("Ollama OCR", "No files pending Ollama OCR processing")
            return
        
        def ollama_worker():
            self.status_var.set("Running Ollama OCR...")
            processed = 0
            
            for _, row in pending_files.iterrows():
                self.status_var.set(f"Ollama OCR: {processed + 1}/{len(pending_files)} - {row['filename']}")
                
                try:
                    page_num = row.get('page_number', 0)
                    text, status = self.ocr.process_file(row['filepath'], 'ollama_ocr', page_number=page_num if page_num > 0 else None)
                    self.ledger.update_ocr_result(row['file_id'], text, status, 'ollama_ocr')
                except Exception as e:
                    error_text = f"Error processing {row['filename']}: {str(e)}"
                    self.ledger.update_ocr_result(row['file_id'], error_text, 'error', 'ollama_ocr')
                    print(f"Ollama OCR error: {e}")
                processed += 1
            
            self.status_var.set("Ollama OCR completed")
            self.root.after(0, self.refresh_display)
        
        threading.Thread(target=ollama_worker, daemon=True).start()
    
    def launch_ollama(self):
        """Launch Ollama service"""
        import subprocess
        import platform
        
        try:
            system = platform.system().lower()
            if system == "windows":
                # Try to start Ollama service on Windows
                subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # Unix-like systems
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            messagebox.showinfo("Ollama Launch", "Ollama service started successfully!\n\nYou can now use Ollama OCR.")
        except FileNotFoundError:
            messagebox.showerror("Ollama Not Found", 
                               "Ollama not found. Please install Ollama from:\nhttps://ollama.ai")
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch Ollama: {str(e)}")
    
    def setup_ai(self):
        """Setup AI for metadata processing"""
        # Ask user what they want to configure
        choice = messagebox.askyesnocancel("AI Setup", 
                                          "Yes: Setup OpenAI API\nNo: Setup Ollama\nCancel: Cancel")
        
        if choice is None:  # Cancel
            return
        elif choice:  # Yes - OpenAI setup
            api_key = simpledialog.askstring("OpenAI API Key", 
                                            "Enter your OpenAI API key:", show='*')
            if api_key:
                try:
                    self.prompt_processor = PromptProcessor(api_key, "openai")
                    messagebox.showinfo("AI Setup", "OpenAI processor initialized successfully")
                except Exception as e:
                    messagebox.showerror("AI Setup Error", f"Failed to initialize OpenAI: {str(e)}")
        else:  # No - Setup Ollama
            try:
                self.prompt_processor = PromptProcessor(model_type="ollama")
                messagebox.showinfo("AI Setup", "Ollama processor initialized successfully")
            except Exception as e:
                messagebox.showerror("AI Setup Error", f"Failed to initialize Ollama: {str(e)}")
    
    def generate_metadata(self):
        """Generate metadata using configured AI models"""
        if not self.prompt_processor:
            messagebox.showwarning("AI Not Configured", "Please configure AI models first in Step 2")
            return
        
        if not self.ground_truth_engine:
            messagebox.showwarning("Ground Truth Required", "Please set ground truth OCR engine first by evaluating OCR")
            return
        
        # Show metadata generation setup dialog
        config = self.show_metadata_config_dialog()
        if not config:
            return
        
        # Process files with selected configuration
        def metadata_worker():
            import time
            
            self.status_var.set("Generating metadata...")
            self.log_activity(f"Started metadata generation for {config['field']}")
            processed = 0
            
            start_time = time.time()
            operation_times = []
            total_files = len(config['files'])
            
            for _, row in config['files'].iterrows():
                # Skip if already processed
                if row[f"{config['field']}_status"] == 'completed':
                    continue
                
                op_start = time.time()
                
                # Update status with time estimate
                if operation_times:
                    avg_time = sum(operation_times) / len(operation_times)
                    remaining_ops = total_files - processed
                    est_remaining = avg_time * remaining_ops
                    est_min = int(est_remaining // 60)
                    est_sec = int(est_remaining % 60)
                    time_str = f" (Est: {est_min}m {est_sec}s remaining)"
                else:
                    time_str = ""
                
                status_msg = f"Metadata: {processed + 1}/{total_files} - {row['filename']}{time_str}"
                self.status_var.set(status_msg)
                self.log_activity(f"Generating metadata for {row['filename']}")
                
                # Get OCR text from selected source
                ocr_text = row.get(f"{config['ocr_source']}_ocr", '')
                if not ocr_text or str(ocr_text).strip() == '' or str(ocr_text) == 'nan':
                    self.status_var.set(f"Skipping {row['filename']} - no {config['ocr_source']} text")
                    continue
                
                examples = self.prompt_processor.generate_examples(str(ocr_text), config['field'])
                
                # Show examples to user for approval
                approved_value = self.show_examples_dialog(row['filename'], config['field'], examples, config['ocr_source'])
                
                if approved_value:
                    self.ledger.update_dublin_core_field(row['file_id'], config['field'], approved_value)
                
                # Track operation time
                op_time = time.time() - op_start
                operation_times.append(op_time)
                
                # Keep only last 20 times for better accuracy
                if len(operation_times) > 20:
                    operation_times.pop(0)
                
                processed += 1
            
            total_time = time.time() - start_time
            self.status_var.set(f"Metadata generation completed in {int(total_time//60)}m {int(total_time%60)}s")
            self.root.after(0, self.refresh_display)
        
        self.progress.start()
        threading.Thread(target=metadata_worker, daemon=True).start()
    
    def generate_batch_metadata(self):
        """Generate multiple metadata fields at once using batching"""
        if not self.prompt_processor:
            messagebox.showwarning("AI Not Configured", "Please configure AI models first in Step 2")
            return
        
        if not self.ground_truth_engine:
            messagebox.showwarning("Ground Truth Required", "Please set ground truth OCR engine first by evaluating OCR")
            return
        
        # Show batch metadata configuration dialog
        config = self.show_batch_metadata_config_dialog()
        if not config:
            return
        
        # Check if batching is enabled
        batching_enabled = hasattr(self.prompt_processor, 'use_batching') and self.prompt_processor.use_batching
        
        def batch_metadata_worker():
            import time
            
            self.status_var.set("Generating batch metadata...")
            self.log_activity(f"Started batch metadata generation for {len(config['files'])} files")
            processed = 0
            queued = 0
            
            start_time = time.time()
            
            def metadata_callback(file_id, result, status):
                """Callback for batch metadata processing"""
                if isinstance(result, dict) and 'error' not in result:
                    # Update multiple fields at once
                    for field, value in result.items():
                        if value and value != 'null':
                            self.ledger.update_dublin_core_field(file_id, field, value)
                    self.log_activity(f"Batch metadata completed for file_id {file_id}")
                else:
                    self.log_activity(f"Batch metadata error for file_id {file_id}: {result}")
                self.root.after(0, self.refresh_display)
            
            for _, row in config['files'].iterrows():
                processed += 1
                filename = row['filename']
                file_id = row['file_id']
                
                self.status_var.set(f"Batch Metadata: {processed}/{len(config['files'])} - {filename}")
                self.log_activity(f"Processing batch metadata for {filename}")
                
                # Get OCR text from ground truth source
                ocr_text = row.get(f"{config['ocr_source']}_ocr", '')
                if not ocr_text or str(ocr_text).strip() == '' or str(ocr_text) == 'nan':
                    self.log_activity(f"Skipping {filename} - no {config['ocr_source']} text")
                    continue
                
                try:
                    if batching_enabled:
                        # Use batching
                        result = self.prompt_processor.generate_multi_metadata(
                            str(ocr_text), 
                            use_batch=True,
                            callback=metadata_callback,
                            metadata={'file_id': file_id, 'filename': filename}
                        )
                        if 'BATCH_QUEUED' in str(result):
                            queued += 1
                        else:
                            # Immediate result
                            metadata_callback(file_id, result, 'completed')
                    else:
                        # Process immediately
                        result = self.prompt_processor.generate_multi_metadata(str(ocr_text))
                        metadata_callback(file_id, result, 'completed')
                        
                except Exception as e:
                    self.log_activity(f"Error processing {filename}: {e}")
            
            total_time = time.time() - start_time
            
            if batching_enabled and queued > 0:
                self.status_var.set(f"Batch metadata: {queued} files queued for processing")
                self.log_activity(f"Queued {queued} files for batch metadata processing")
                messagebox.showinfo("Batch Queued", 
                    f"{queued} files queued for batch metadata processing.\n\n"
                    f"Results will be available in ~24 hours.\n"
                    f"Use 'Check Batch Status' to retrieve completed results.")
            else:
                self.status_var.set(f"Batch metadata completed in {int(total_time//60)}m {int(total_time%60)}s")
                self.log_activity(f"Batch metadata completed: {processed} files processed")
            
            self.root.after(0, self.refresh_display)
        
        self.progress.start()
        threading.Thread(target=batch_metadata_worker, daemon=True).start()
    
    def show_batch_metadata_config_dialog(self) -> dict:
        """Dialog to configure batch metadata generation"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Batch Metadata Generation")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {}
        
        ttk.Label(dialog, text="⚡ Batch Metadata Generation", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Instructions
        inst_text = tk.Text(dialog, height=4, wrap=tk.WORD, bg='#f8f8f8')
        inst_text.pack(fill=tk.X, padx=10, pady=5)
        inst_text.insert(1.0, 
            "Generate multiple metadata fields at once using AI:\n"
            "• Title, Creator, Subject, Date, Description\n"
            "• Uses ground truth OCR for best quality\n"
            "• Supports batch processing for efficiency")
        inst_text.config(state=tk.DISABLED)
        
        # OCR Source (defaults to ground truth)
        ocr_frame = ttk.LabelFrame(dialog, text="OCR Source")
        ocr_frame.pack(fill=tk.X, padx=10, pady=5)
        
        default_ocr = self.ground_truth_engine if self.ground_truth_engine else "easyocr"
        ocr_var = tk.StringVar(value=default_ocr)
        
        ttk.Label(ocr_frame, text=f"Using: {default_ocr.upper()} (Ground Truth)").pack(padx=10, pady=5)
        
        # File selection
        files_frame = ttk.LabelFrame(dialog, text="Files to Process")
        files_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Get files with completed OCR from ground truth source
        available_files = self.ledger.get_files_by_status(default_ocr, 'completed')
        
        if available_files.empty:
            ttk.Label(files_frame, text=f"❌ No files with completed {default_ocr.upper()} found", 
                     foreground="red").pack(padx=10, pady=5)
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
            return None
        
        ttk.Label(files_frame, text=f"✅ Found {len(available_files)} files ready for processing").pack(padx=10, pady=5)
        
        def on_ok():
            result['ocr_source'] = default_ocr
            result['files'] = available_files
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="▶️ Start Batch Processing", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        return result
    
    def classify_document_types(self):
        """Classify document types using configured AI models"""
        if not self.prompt_processor:
            messagebox.showwarning("AI Not Configured", "Please configure AI models first in Step 2")
            return
        
        # Show AI model selection dialog
        ai_model = self.show_ai_model_selection_dialog()
        if not ai_model:
            return
        
        # Get files pending document type classification (exclude PDFs)
        all_pending = self.ledger.get_files_by_status('document_type', 'pending')
        pending_files = all_pending[all_pending['file_type'] != '.pdf']
        
        if pending_files.empty:
            messagebox.showinfo("Document Type Classification", "No files pending document type classification")
            return
        
        def classify_worker():
            import time
            
            self.status_var.set("Classifying document types...")
            self.log_activity("Started document type classification")
            processed = 0
            
            start_time = time.time()
            operation_times = []
            total_files = len(pending_files)
            
            for _, row in pending_files.iterrows():
                op_start = time.time()
                
                # Update status with time estimate
                if operation_times:
                    avg_time = sum(operation_times) / len(operation_times)
                    remaining_ops = total_files - processed
                    est_remaining = avg_time * remaining_ops
                    est_min = int(est_remaining // 60)
                    est_sec = int(est_remaining % 60)
                    time_str = f" (Est: {est_min}m {est_sec}s remaining)"
                else:
                    time_str = ""
                
                status_msg = f"Classifying: {processed + 1}/{total_files} - {row['filename']}{time_str}"
                self.status_var.set(status_msg)
                self.log_activity(f"Classifying {row['filename']}")
                
                try:
                    # Only classify image files
                    file_ext = row.get('file_type', '').lower()
                    if file_ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                        doc_type = self.prompt_processor.classify_document_type(row['filepath'])
                        if doc_type.startswith('error:'):
                            self.ledger.update_document_type(row['file_id'], doc_type, 'error')
                        else:
                            self.ledger.update_document_type(row['file_id'], doc_type, 'completed')
                    else:
                        # Skip non-image files (should not reach here due to filtering)
                        continue
                        
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    self.ledger.update_document_type(row['file_id'], error_msg, 'error')
                    print(f"Classification error: {e}")
                
                # Track operation time
                op_time = time.time() - op_start
                operation_times.append(op_time)
                
                # Keep only last 20 times for better accuracy
                if len(operation_times) > 20:
                    operation_times.pop(0)
                
                processed += 1
            
            total_time = time.time() - start_time
            self.status_var.set(f"Document type classification completed in {int(total_time//60)}s {int(total_time%60)}s")
            self.root.after(0, self.refresh_display)
        
        self.progress.start()
        threading.Thread(target=classify_worker, daemon=True).start()
    def run_all_ocr(self):
        """Run all available OCR engines on pending files"""
        # Get all files that have at least one pending OCR status
        all_files = self.ledger.df
        pending_files = all_files[
            (all_files['easyocr_status'] == 'pending') |
            (all_files['tesseract_status'] == 'pending') |
            (all_files['pypdf2_status'] == 'pending') |
            (all_files['openai_ocr_status'] == 'pending') |
            (all_files['ollama_ocr_status'] == 'pending')
        ]
        
        if pending_files.empty:
            messagebox.showinfo("All OCR", "No files pending OCR processing")
            return
        
        # Ask user which engines to run
        engines_to_run = self.select_ocr_engines()
        if not engines_to_run:
            return
        
        def all_ocr_worker():
            self.status_var.set("Running all OCR engines...")
            total_operations = len(pending_files) * len(engines_to_run)
            current_op = 0
            
            for _, row in pending_files.iterrows():
                for engine in engines_to_run:
                    current_op += 1
                    
                    # Skip if already completed for this engine
                    if row[f'{engine}_status'] == 'completed':
                        continue
                    
                    self.status_var.set(f"OCR ({current_op}/{total_operations}): {engine.upper()} - {row['filename']}")
                    
                    try:
                        page_num = row.get('page_number', 0)
                        text, status = self.ocr.process_file(row['filepath'], engine, page_number=page_num if page_num > 0 else None)
                        self.ledger.update_ocr_result(row['file_id'], text, status, engine)
                    except Exception as e:
                        error_text = f"Error: {str(e)}"
                        self.ledger.update_ocr_result(row['file_id'], error_text, 'error', engine)
                        print(f"{engine} error: {e}")
            
            self.status_var.set("All OCR processing completed")
            self.root.after(0, lambda: [self.progress.stop(), self.refresh_display()])
        
        self.progress.start()
        threading.Thread(target=all_ocr_worker, daemon=True).start()
    
    def select_ocr_engines(self):
        """Dialog to select which OCR engines to run"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select OCR Engines")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        selected_engines = []
        
        ttk.Label(dialog, text="Select OCR engines to run:", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Engine selection with availability check
        engine_vars = {}
        available_engines = [
            ('easyocr', 'EasyOCR (AI-powered)', 'easyocr' in self.ocr.models),
            ('tesseract', 'Tesseract (Traditional)', 'tesseract' in self.ocr.models),
            ('pypdf2', 'PyPDF2 (PDF text)', 'pypdf2' in self.ocr.models),
            ('openai_ocr', 'OpenAI OCR (Vision)', 'openai_ocr' in self.ocr.models),
            ('ollama_ocr', 'Ollama OCR (Local)', 'ollama_ocr' in self.ocr.models)
        ]
        
        for engine_key, engine_name, is_available in available_engines:
            var = tk.BooleanVar(value=is_available)
            engine_vars[engine_key] = var
            
            cb = ttk.Checkbutton(dialog, text=engine_name, variable=var)
            if not is_available:
                cb.configure(state='disabled')
                engine_name += " (Not Available)"
            cb.pack(anchor=tk.W, padx=20, pady=2)
        
        def on_ok():
            nonlocal selected_engines
            selected_engines = [key for key, var in engine_vars.items() if var.get()]
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        def select_all():
            for key, var in engine_vars.items():
                if key in [e[0] for e in available_engines if e[2]]:
                    var.set(True)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        

    
    def on_tree_right_click(self, event):
        """Handle right-click on tree items"""
        # Select the item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Run All OCR on Selected", command=self.run_all_ocr_on_selected)
            context_menu.add_command(label="View OCR Results", command=lambda: self.on_tree_double_click(None))
            context_menu.add_separator()
            context_menu.add_command(label="Remove from Ledger", command=self.clear_rows)
            
            # Show context menu
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def run_all_ocr_on_selected(self):
        """Run all OCR engines on selected files only"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select files to process")
            return
        
        # Get selected filenames
        selected_filenames = []
        for item in selected_items:
            values = self.tree.item(item)['values']
            selected_filenames.append(values[0])
        
        # Filter to selected files with pending OCR
        selected_files = self.ledger.df[
            (self.ledger.df['filename'].isin(selected_filenames)) &
            (
                (self.ledger.df['easyocr_status'] == 'pending') |
                (self.ledger.df['tesseract_status'] == 'pending') |
                (self.ledger.df['pypdf2_status'] == 'pending') |
                (self.ledger.df['openai_ocr_status'] == 'pending') |
                (self.ledger.df['ollama_ocr_status'] == 'pending')
            )
        ]
        
        if selected_files.empty:
            messagebox.showinfo("OCR Complete", "Selected files have no pending OCR operations")
            return
        
        # Ask user which engines to run
        engines_to_run = self.select_ocr_engines()
        if not engines_to_run:
            return
        
        def selected_ocr_worker():
            self.status_var.set(f"Running OCR on {len(selected_files)} selected files...")
            total_operations = len(selected_files) * len(engines_to_run)
            current_op = 0
            
            for _, row in selected_files.iterrows():
                for engine in engines_to_run:
                    current_op += 1
                    
                    # Skip if already completed for this engine
                    if row[f'{engine}_status'] == 'completed':
                        continue
                    
                    self.status_var.set(f"OCR ({current_op}/{total_operations}): {engine.upper()} - {row['filename']}")
                    
                    try:
                        page_num = row.get('page_number', 0)
                        text, status = self.ocr.process_file(row['filepath'], engine, page_number=page_num if page_num > 0 else None)
                        self.ledger.update_ocr_result(row['file_id'], text, status, engine)
                    except Exception as e:
                        error_text = f"Error: {str(e)}"
                        self.ledger.update_ocr_result(row['file_id'], error_text, 'error', engine)
                        print(f"{engine} error: {e}")
            
            self.status_var.set(f"OCR completed on {len(selected_files)} selected files")
            self.root.after(0, lambda: [self.progress.stop(), self.refresh_display()])
        
        self.progress.start()

    
    def load_ai_configurations(self):
        """Load AI configurations from config file"""
        ai_config = self.config.get_section('ai_models')
        ocr_config = self.config.get_section('ocr_engines')
        
        # Initialize OpenAI if enabled
        if ai_config.get('openai_enabled') and ai_config.get('openai_api_key'):
            try:
                api_key = ai_config['openai_api_key'].strip()
                batch_enabled = ai_config.get('openai_batch_enabled', False)
                
                self.prompt_processor = PromptProcessor(api_key, "openai")
                # Enable batching if configured
                if batch_enabled:
                    self.prompt_processor.set_batching_enabled(True)
                
                # Initialize OpenAI OCR with batching configuration
                if ocr_config.get('openai_ocr_enabled'):
                    self.ocr.add_openai_ocr(api_key, enable_batching=batch_enabled)
            except Exception as e:
                error_msg = str(e)
                if '401' in error_msg or 'invalid_api_key' in error_msg or 'Incorrect API key' in error_msg:
                    print(f"❌ OpenAI API Key Error: Invalid or expired key")
                    print(f"   Please update your API key in AI Configuration")
                    print(f"   Get your key at: https://platform.openai.com/api-keys")
                else:
                    print(f"Failed to initialize OpenAI: {e}")
        
        # Initialize Ollama if enabled
        if ai_config.get('ollama_enabled'):
            try:
                if not self.prompt_processor:
                    self.prompt_processor = PromptProcessor(model_type="ollama")
                if ocr_config.get('ollama_ocr_enabled'):
                    self.ocr.add_ollama_ocr(ai_config.get('ollama_model', 'gemma3'))
            except Exception as e:
                print(f"Failed to initialize Ollama: {e}")
        
        self.update_config_status()
    
    def update_config_status(self):
        """Update configuration status display"""
        if not hasattr(self, 'config_status'):
            return
            
        ai_config = self.config.get_section('ai_models')
        enabled_models = []
        
        if ai_config.get('openai_enabled'):
            model_str = 'OpenAI'
            if ai_config.get('openai_batch_enabled'):
                model_str += ' (Batch Mode)'
            enabled_models.append(model_str)
        if ai_config.get('ollama_enabled'):
            enabled_models.append('Ollama')
        
        if enabled_models:
            status = f"AI Models: {', '.join(enabled_models)}"
        else:
            status = "AI Models: None configured"
        
        self.config_status.set(status)
        
        # Update ground truth status if available
        if hasattr(self, 'ground_truth_status'):
            if self.ground_truth_engine:
                self.ground_truth_status.set(f"Ground Truth: {self.ground_truth_engine.upper()}")
            else:
                self.ground_truth_status.set("Ground Truth: Not set")
    
    def show_configuration_dialog(self):
        """Show comprehensive configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("AI Models & OCR Configuration")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # AI Models Tab
        ai_frame = ttk.Frame(notebook)
        notebook.add(ai_frame, text="🤖 AI Models")
        
        # OpenAI Configuration
        openai_frame = ttk.LabelFrame(ai_frame, text="OpenAI Configuration", padding="10")
        openai_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.openai_enabled_var = tk.BooleanVar(value=self.config.get('ai_models', 'openai_enabled', False))
        ttk.Checkbutton(openai_frame, text="Enable OpenAI", variable=self.openai_enabled_var).pack(anchor=tk.W)
        
        ttk.Label(openai_frame, text="API Key:").pack(anchor=tk.W, pady=(5, 0))
        self.openai_key_var = tk.StringVar(value=self.config.get('ai_models', 'openai_api_key', ''))
        ttk.Entry(openai_frame, textvariable=self.openai_key_var, width=50).pack(fill=tk.X, pady=2)
        
        self.openai_batch_var = tk.BooleanVar(value=False)
        batch_cb = ttk.Checkbutton(openai_frame, text="Use Batch API (50% cost savings, 24h processing) [DISABLED]", variable=self.openai_batch_var, state='disabled')
        batch_cb.pack(anchor=tk.W, pady=(5, 0))
        ttk.Label(openai_frame, text="  Feature temporarily disabled", font=("Arial", 8), foreground="red").pack(anchor=tk.W, padx=20)
        
        # Ollama Configuration
        ollama_frame = ttk.LabelFrame(ai_frame, text="Ollama Configuration", padding="10")
        ollama_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.ollama_enabled_var = tk.BooleanVar(value=self.config.get('ai_models', 'ollama_enabled', False))
        ttk.Checkbutton(ollama_frame, text="Enable Ollama (Local)", variable=self.ollama_enabled_var).pack(anchor=tk.W)
        
        ttk.Label(ollama_frame, text="Model Name:").pack(anchor=tk.W, pady=(5, 0))
        self.ollama_model_var = tk.StringVar(value=self.config.get('ai_models', 'ollama_model', 'gemma3'))
        ttk.Entry(ollama_frame, textvariable=self.ollama_model_var, width=30).pack(anchor=tk.W, pady=2)
        
        ttk.Button(ollama_frame, text="Launch Ollama Service", command=self.launch_ollama).pack(anchor=tk.W, pady=5)
        
        # OCR Engines Tab
        ocr_frame = ttk.Frame(notebook)
        notebook.add(ocr_frame, text="🔍 OCR Engines")
        
        ttk.Label(ocr_frame, text="Select OCR engines to enable:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=10)
        
        ocr_config = self.config.get_section('ocr_engines')
        self.ocr_vars = {}
        
        ocr_engines = [
            ('easyocr_enabled', 'EasyOCR (AI-powered)', True),
            ('tesseract_enabled', 'Tesseract (Traditional)', True),
            ('pypdf2_enabled', 'PyPDF2 (PDF text extraction)', True),
            ('openai_ocr_enabled', 'OpenAI OCR (Vision model)', False),
            ('ollama_ocr_enabled', 'Ollama OCR (Local vision)', False)
        ]
        
        for key, label, default_available in ocr_engines:
            var = tk.BooleanVar(value=ocr_config.get(key, default_available))
            self.ocr_vars[key] = var
            cb = ttk.Checkbutton(ocr_frame, text=label, variable=var)
            cb.pack(anchor=tk.W, padx=20, pady=2)
            
            if key in ['openai_ocr_enabled', 'ollama_ocr_enabled']:
                ttk.Label(ocr_frame, text=f"  Requires {key.split('_')[0].title()} AI model enabled", 
                         font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=40)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_config():
            # Save AI model settings with key validation
            api_key = self.openai_key_var.get().strip()  # Remove whitespace
            
            # Validate API key format if provided
            if api_key and self.openai_enabled_var.get():
                if not (api_key.startswith('sk-') or api_key.startswith('sk-proj-')):
                    messagebox.showwarning("Invalid API Key", 
                        "OpenAI API key should start with 'sk-' or 'sk-proj-'\n\n"
                        "Please check your key at:\nhttps://platform.openai.com/api-keys")
                    return
                if len(api_key) < 20:
                    messagebox.showwarning("Invalid API Key", "API key appears too short. Please verify.")
                    return
            
            self.config.set('ai_models', 'openai_enabled', self.openai_enabled_var.get())
            self.config.set('ai_models', 'openai_api_key', api_key)
            self.config.set('ai_models', 'openai_batch_enabled', self.openai_batch_var.get())
            self.config.set('ai_models', 'ollama_enabled', self.ollama_enabled_var.get())
            self.config.set('ai_models', 'ollama_model', self.ollama_model_var.get())
            
            # Save OCR engine settings
            for key, var in self.ocr_vars.items():
                self.config.set('ocr_engines', key, var.get())
            
            # Reload configurations
            self.load_ai_configurations()
            messagebox.showinfo("Configuration Saved", "Settings saved and applied successfully!")
            dialog.destroy()
        
        ttk.Button(button_frame, text="💾 Save Configuration", command=save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def process_all_files(self):
        """Process all files with classification and OCR"""
        # Use batch processing with all files
        config = {
            'num_files': len(self.ledger.df),
            'ocr_engines': self.get_enabled_ocr_engines(),
            'include_ner': False,
            'ner_method': 'spacy'
        }
        
        if not config['ocr_engines']:
            messagebox.showwarning("No OCR Engines", "No OCR engines are enabled. Please configure them first.")
            return
        
        self.run_batch_processing(config)
    
    def get_enabled_ocr_engines(self):
        """Get list of enabled OCR engines"""
        ocr_config = self.config.get_section('ocr_engines')
        enabled_engines = []
        
        engine_map = {
            'easyocr_enabled': 'easyocr',
            'tesseract_enabled': 'tesseract', 
            'pypdf2_enabled': 'pypdf2',
            'openai_ocr_enabled': 'openai_ocr',
            'ollama_ocr_enabled': 'ollama_ocr'
        }
        
        for config_key, engine_name in engine_map.items():
            if ocr_config.get(config_key, True) and engine_name in self.ocr.models:
                enabled_engines.append(engine_name)
        
        return enabled_engines
    
    def run_all_available_ocr_old(self):
        """Run all enabled OCR engines"""
        ocr_config = self.config.get_section('ocr_engines')
        enabled_engines = [key.replace('_enabled', '') for key, enabled in ocr_config.items() if enabled]
        
        if not enabled_engines:
            messagebox.showwarning("No OCR Engines", "No OCR engines are enabled. Please configure them first.")
            return
        
        # Get files with pending OCR
        all_files = self.ledger.df
        
        # Create boolean mask for files with any pending OCR
        pending_mask = False
        for engine in enabled_engines:
            pending_mask = pending_mask | (all_files[f'{engine}_status'] == 'pending')
        
        pending_files = all_files[pending_mask]
        
        if pending_files.empty:
            messagebox.showinfo("OCR Complete", "No files pending OCR processing")
            return
        
        def ocr_worker():
            import time
            
            self.status_var.set("Running enabled OCR engines...")
            total_ops = len(pending_files) * len(enabled_engines)
            current_op = 0
            
            start_time = time.time()
            operation_times = []
            
            for _, row in pending_files.iterrows():
                for engine in enabled_engines:
                    current_op += 1
                    if row[f'{engine}_status'] == 'completed':
                        continue
                    
                    op_start = time.time()
                    
                    # Update status with time estimate
                    if operation_times:
                        avg_time = sum(operation_times) / len(operation_times)
                        remaining_ops = total_ops - current_op
                        est_remaining = avg_time * remaining_ops
                        est_min = int(est_remaining // 60)
                        est_sec = int(est_remaining % 60)
                        time_str = f" (Est: {est_min}m {est_sec}s remaining)"
                    else:
                        time_str = ""
                    
                    status_msg = f"OCR ({current_op}/{total_ops}): {engine.upper()} - {row['filename']}{time_str}"
                    self.status_var.set(status_msg)
                    self.log_activity(f"Processing {engine.upper()} for {row['filename']}")
                    
                    try:
                        page_num = row.get('page_number', 0)
                        text, status = self.ocr.process_file(row['filepath'], engine, page_number=page_num if page_num > 0 else None)
                        self.ledger.update_ocr_result(row['file_id'], text, status, engine)
                    except Exception as e:
                        self.ledger.update_ocr_result(row['file_id'], f"Error: {e}", 'error', engine)
                    
                    # Track operation time
                    op_time = time.time() - op_start
                    operation_times.append(op_time)
                    
                    # Keep only last 50 times for better accuracy
                    if len(operation_times) > 50:
                        operation_times.pop(0)
            
            total_time = time.time() - start_time
            self.status_var.set(f"OCR processing completed in {int(total_time//60)}m {int(total_time%60)}s")
            self.root.after(0, lambda: [self.progress.stop(), self.refresh_display()])
        
        self.progress.start()
        threading.Thread(target=ocr_worker, daemon=True).start()
    
    def export_results(self):
        """Export results in archival format (JSON + CSV)"""
        from tkinter import filedialog
        from src.export_manager import ExportManager
        
        # Choose directory for CSV summary
        output_dir = filedialog.askdirectory(title="Select Directory for CSV Summary")
        if not output_dir:
            return
        
        try:
            exporter = ExportManager(self.ledger.df)
            
            # Export JSON sidecars next to original files
            json_count = exporter.export_json_sidecars(self.ground_truth_engine)
            
            # Export CSV summary to selected directory
            csv_path = os.path.join(output_dir, "_collection_metadata_summary.csv")
            csv_count = exporter.export_csv_summary(csv_path, self.ground_truth_engine)
            
            messagebox.showinfo("Export Complete", 
                f"✅ Exported {json_count} JSON sidecar files\n"
                f"   (placed next to original files)\n\n"
                f"✅ Exported CSV summary with {csv_count} rows\n"
                f"   Location: {csv_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
            import traceback
            traceback.print_exc()
    
    def on_closing(self):
        """Handle application closing"""
        # Save window geometry
        self.config.set('ui_settings', 'window_geometry', self.root.geometry())
        self.root.destroy()
    
    def select_dublin_core_field(self, available_fields: List[str]) -> str:
        """Dialog to select Dublin Core field"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Dublin Core Field")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        selected_field = tk.StringVar()
        
        ttk.Label(dialog, text="Select a Dublin Core field:").pack(pady=10)
        
        for field in available_fields:
            ttk.Radiobutton(dialog, text=field.title(), variable=selected_field, 
                           value=field).pack(anchor=tk.W, padx=20)
        
        def on_ok():
            dialog.destroy()
        
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
        
        dialog.wait_window()
        return selected_field.get()
    
    def show_metadata_config_dialog(self) -> dict:
        """Dialog to configure metadata generation settings"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Metadata Generation")
        dialog.geometry("900x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {}
        
        # Main container with left and right panels
        main_container = ttk.Frame(dialog)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left panel for configuration
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Right panel for OCR preview
        right_panel = ttk.LabelFrame(main_container, text="📄 OCR Text Preview")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Instructions
        instructions = tk.Text(left_panel, height=6, wrap=tk.WORD, bg='#f0f0f0')
        instructions.pack(fill=tk.X, pady=5)
        instructions.insert(1.0, 
            "📋 METADATA GENERATION SETUP\n\n"
            "1️⃣ Choose OCR Source: Select which OCR text to use for AI analysis\n"
            "2️⃣ Choose Dublin Core Field: Select metadata field to generate\n"
            "3️⃣ AI will analyze OCR text and suggest metadata values\n"
            "4️⃣ You'll review and approve each suggestion")
        instructions.config(state=tk.DISABLED)
        
        # OCR Source Selection (defaults to ground truth)
        ttk.Label(left_panel, text="1️⃣ Select OCR Source:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10,5))
        
        default_ocr = self.ground_truth_engine if self.ground_truth_engine else "easyocr"
        ocr_var = tk.StringVar(value=default_ocr)
        ocr_frame = ttk.Frame(left_panel)
        ocr_frame.pack(fill=tk.X, padx=10)
        
        ocr_options = [
            ("easyocr", "🤖 EasyOCR (AI-powered)"),
            ("tesseract", "📄 Tesseract (Traditional OCR)"),
            ("pypdf2", "📋 PyPDF2 (Direct PDF text)"),
            ("openai_ocr", "🤖📄 OpenAI OCR (AI transcription)"),
            ("ollama_ocr", "🏠🤖 Ollama OCR (Local LLM)")
        ]
        
        for engine, label in ocr_options:
            display_label = label
            if engine == self.ground_truth_engine:
                display_label += " (Ground Truth)"
            ttk.Radiobutton(ocr_frame, text=display_label, 
                           variable=ocr_var, value=engine).pack(anchor=tk.W)
        
        # Dublin Core Field Selection
        ttk.Label(left_panel, text="2️⃣ Select Dublin Core Field:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(15,5))
        
        available_fields = self.prompt_processor.get_available_fields() if self.prompt_processor else []
        if not available_fields:
            ttk.Label(left_panel, text="❌ No prompt files found in prompts directory", 
                     foreground="red").pack(anchor=tk.W, padx=10)
            return None
        
        field_var = tk.StringVar()
        field_frame = ttk.Frame(left_panel)
        field_frame.pack(fill=tk.X, padx=10)
        
        for field in available_fields:
            ttk.Radiobutton(field_frame, text=f"📝 {field.title()}", 
                           variable=field_var, value=field).pack(anchor=tk.W)
        
        def on_ok():
            ocr_source = ocr_var.get()
            field = field_var.get()
            
            if not field:
                messagebox.showwarning("Selection Required", "Please select a Dublin Core field")
                return
            
            # Get files with completed OCR from selected source
            files = self.ledger.get_files_by_status(ocr_source, 'completed')
            
            if files.empty:
                messagebox.showinfo("No Files", f"No files with completed {ocr_source.upper()} found")
                return
            
            result['ocr_source'] = ocr_source
            result['field'] = field
            result['files'] = files
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # OCR Preview Text Widget
        preview_text = tk.Text(right_panel, wrap=tk.WORD, height=15, width=40)
        preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        preview_text.insert(1.0, "Select an OCR source to preview text...")
        preview_text.config(state=tk.DISABLED)
        
        def update_preview():
            """Update OCR text preview when source changes"""
            ocr_source = ocr_var.get()
            files = self.ledger.get_files_by_status(ocr_source, 'completed')
            
            preview_text.config(state=tk.NORMAL)
            preview_text.delete(1.0, tk.END)
            
            if files.empty:
                preview_text.insert(1.0, f"❌ No files with completed {ocr_source.upper()} found.\n\nRun {ocr_source.upper()} first to see preview.")
            else:
                preview_text.insert(1.0, f"📊 Found {len(files)} files with {ocr_source.upper()} text\n\n")
                preview_text.insert(tk.END, "📄 Sample from first file:\n")
                preview_text.insert(tk.END, "-" * 40 + "\n")
                
                # Show sample from first file
                sample_text = str(files.iloc[0].get(f'{ocr_source}_ocr', '') or '')
                if sample_text and sample_text != 'nan':
                    preview_sample = sample_text[:500] + "..." if len(sample_text) > 500 else sample_text
                    preview_text.insert(tk.END, preview_sample)
                else:
                    preview_text.insert(tk.END, "No text available")
            
            preview_text.config(state=tk.DISABLED)
        
        # Bind OCR selection change to preview update
        for child in ocr_frame.winfo_children():
            if isinstance(child, ttk.Radiobutton):
                child.configure(command=update_preview)
        
        # Update preview initially
        dialog.after(100, update_preview)
        
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="▶️ Start Generation", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        return result
    
    def show_examples_dialog(self, filename: str, field: str, examples: List[str], ocr_source: str = "easyocr") -> str:
        """Show examples dialog for user approval"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Approve {field.title()} for {filename}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = tk.StringVar()
        
        # Header with instructions
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(header_frame, text=f"📝 {field.title()} Suggestions for: {filename}", 
                 font=("Arial", 12, "bold")).pack()
        ttk.Label(header_frame, text=f"📊 Source: {ocr_source.upper()} OCR", 
                 font=("Arial", 9), foreground="gray").pack()
        
        # Instructions
        inst_text = tk.Text(dialog, height=3, wrap=tk.WORD, bg='#f8f8f8')
        inst_text.pack(fill=tk.X, padx=10, pady=5)
        inst_text.insert(1.0, 
            "🤖 AI analyzed the OCR text and generated these suggestions.\n"
            "✅ Select a suggestion OR enter your own value below.\n"
            "❌ Click Reject to skip this file.")
        inst_text.config(state=tk.DISABLED)
        
        # AI Suggestions section
        ttk.Label(dialog, text="🤖 AI Suggestions:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(10,5))
        
        suggestions_frame = ttk.Frame(dialog)
        suggestions_frame.pack(fill=tk.X, padx=20)
        
        for i, example in enumerate(examples, 1):
            ttk.Radiobutton(suggestions_frame, text=f"{i}. {example}", variable=result, 
                           value=example).pack(anchor=tk.W, pady=2)
        
        # Custom entry section
        ttk.Label(dialog, text="✏️ Or enter custom value:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(15, 5))
        custom_entry = ttk.Entry(dialog, width=60)
        custom_entry.pack(padx=20, pady=5)
        
        def on_approve():
            if custom_entry.get().strip():
                result.set(custom_entry.get().strip())
            dialog.destroy()
        
        def on_reject():
            result.set("")
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="✅ Approve", command=on_approve).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Reject", command=on_reject).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        return result.get()
    
    def clear_rows(self):
        """Clear selected rows from the ledger"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select rows to clear")
            return
        
        file_ids = []
        for item in selected_items:
            values = self.tree.item(item)['values']
            if len(values) > 5:
                filepath = values[5]
                display_filename = values[0]
                
                # Match by filepath and filename
                matching_rows = self.ledger.df[
                    (self.ledger.df['filepath'] == filepath) & 
                    (self.ledger.df['filename'] == display_filename)
                ]
                
                if not matching_rows.empty:
                    file_ids.extend(matching_rows['file_id'].tolist())
        
        if file_ids:
            self.ledger.clear_rows(file_ids)
            self.refresh_display()
            messagebox.showinfo("Deleted", f"Deleted {len(file_ids)} file records")
        else:
            messagebox.showwarning("Delete Failed", "Could not find matching records to delete")
    
    def parse_archival_path(self, filepath):
        """Parse filepath to extract archival structure"""
        path_parts = filepath.replace('\\', '/').split('/')
        
        # Look for common archival patterns
        collection = "Unknown Collection"
        box = "Unknown Box"
        folder = "Unknown Folder"
        
        for i, part in enumerate(path_parts):
            part_lower = part.lower()
            if 'collection' in part_lower or len(path_parts) - i > 3:
                collection = part
            elif 'box' in part_lower:
                box = part
            elif 'folder' in part_lower or (i == len(path_parts) - 2):
                folder = part
        
        return collection, box, folder
    
    def refresh_display(self):
        """Refresh the data display with archival grouping"""
        # Reload ledger data from CSV to get latest updates
        self.ledger.df = self.ledger.load_or_create_ledger()
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Group files by archival structure
        groups = {}
        for _, row in self.ledger.df.iterrows():
            collection, box, folder = self.parse_archival_path(row['filepath'])
            
            # For PDF pages, group by parent document
            if row.get('page_number', 0) > 0:
                # Extract base filename without page info
                base_filename = row['filepath'].split('/')[-1] if '/' in row['filepath'] else row['filepath'].split('\\')[-1]
                group_key = f"{collection} > {box} > {folder} > {base_filename}"
            else:
                group_key = f"{collection} > {box} > {folder}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(row)
        
        # Add grouped data to tree
        for group_key, files in groups.items():
            # Calculate group statistics
            total_files = len(files)
            completed_files = sum(1 for f in files if self.get_file_status(f) == "🟢 Complete")
            
            # For page-level groups, count actual pages; for file-level groups, count total pages
            if any(f.get('page_number', 0) > 0 for f in files):
                # This is a PDF with individual pages
                total_pages = len(files)
                completed_pages = sum(1 for f in files if f.get('openai_ocr_status') == 'completed')
            else:
                # This is a regular file group
                total_pages = sum(self.ledger.get_page_count(f['filepath']) for f in files)
                completed_pages = sum(self.ledger.get_page_count(f['filepath']) for f in files if f.get('openai_ocr_status') == 'completed')
            
            # Insert group header with proper text in first column
            if any(f.get('page_number', 0) > 0 for f in files):
                # PDF document with pages
                group_item = self.tree.insert('', 'end', 
                    text=f"📄 {group_key.split(' > ')[-1]}",
                    values=[f"({total_pages} pages, {completed_pages} complete)", '', '', '', '', '', '', ''],
                    tags=('pdf_group',),
                    open=True)
            else:
                # Regular file group
                group_item = self.tree.insert('', 'end', 
                    text=f"📁 {group_key}",
                    values=[f"({total_files} files, {total_pages} pages, {completed_pages} complete)", '', '', '', '', '', '', ''],
                    tags=('group',),
                    open=True)
            
            # Insert files under group
            for row in files:
                status_display = self.get_file_status(row)
                preview = self.get_file_preview(row)
                
                # Use filename directly (already contains page info for PDFs)
                values = [
                    row['filename'],
                    status_display,
                    row.get('document_type', ''),
                    preview,
                    row.get('named_entities', ''),
                    row['filepath']
                ]
                self.tree.insert(group_item, 'end', text='', values=values, tags=('file',))
        
        # Configure styling
        self.tree.tag_configure('group', background='#e8f4fd', font=('Arial', 9, 'bold'))
        self.tree.tag_configure('pdf_group', background='#f0f8ff', font=('Arial', 9, 'bold'))
        self.tree.tag_configure('file', background='white')
        
        # Update analysis tab
        self.update_analysis_display()
    
    def get_file_status(self, row):
        """Get status display for a file"""
        # Check for batch status first
        batch_status = row.get('batch_status', '')
        if batch_status in ['queued', 'submitted', 'processing']:
            return f"⏳ Batch {batch_status}"
        
        statuses = [
            row.get('easyocr_status', 'pending'),
            row.get('tesseract_status', 'pending'),
            row.get('pypdf2_status', 'pending'),
            row.get('openai_ocr_status', 'pending'),
            row.get('ollama_ocr_status', 'pending')
        ]
        
        completed = sum(1 for s in statuses if s == 'completed')
        errors = sum(1 for s in statuses if s == 'error')
        
        if errors > 0:
            return f"🔴 {completed}/5 ({errors} errors)"
        elif completed == 5:
            return "🟢 Complete"
        elif completed > 0:
            return f"🟡 {completed}/5"
        else:
            return "⚪ Pending"
    
    def get_file_preview(self, row):
        """Get OCR preview text for a file"""
        if self.ground_truth_engine:
            if self.ground_truth_engine == 'openai_ocr':
                preview_text = str(row.get('openai_ocr_ocr', '') or '')
            elif self.ground_truth_engine == 'ollama_ocr':
                preview_text = str(row.get('ollama_ocr_ocr', '') or '')
            else:
                preview_text = str(row.get(f'{self.ground_truth_engine}_ocr', '') or '')
        else:
            # Fallback to best available OCR text
            ocr_texts = [
                str(row.get('easyocr_ocr', '') or ''),
                str(row.get('tesseract_ocr', '') or ''),
                str(row.get('pypdf2_ocr', '') or ''),
                str(row.get('openai_ocr_ocr', '') or ''),
                str(row.get('ollama_ocr_ocr', '') or '')
            ]
            preview_text = max(ocr_texts, key=len) if any(ocr_texts) else ""
        
        return preview_text[:50] + '...' if len(preview_text) > 50 else preview_text
    
    def update_analysis_display(self):
        """Update the analysis tab with current statistics"""
        summary = self.ledger.get_summary()
        analysis_text = f"""CODEBOOKS ANALYSIS REPORT
{'='*50}

📊 PROCESSING OVERVIEW:
Total Files: {summary['total_files']}
Total Pages: {summary['total_pages']} (PDF pages + images)

🔍 OCR ENGINE PERFORMANCE:
• EasyOCR:    ✅{summary['easyocr_completed']:3d} ⏳{summary['easyocr_pending']:3d} ❌{summary['easyocr_error']:3d}
• Tesseract:  ✅{summary['tesseract_completed']:3d} ⏳{summary['tesseract_pending']:3d} ❌{summary['tesseract_error']:3d}
• PyPDF2:     ✅{summary['pypdf2_completed']:3d} ⏳{summary['pypdf2_pending']:3d} ❌{summary['pypdf2_error']:3d}
• OpenAI OCR: ✅{summary['openai_ocr_completed']:3d} ⏳{summary['openai_ocr_pending']:3d} ❌{summary['openai_ocr_error']:3d}
• Ollama OCR: ✅{summary['ollama_ocr_completed']:3d} ⏳{summary['ollama_ocr_pending']:3d} ❌{summary['ollama_ocr_error']:3d}

📄 DOCUMENT TYPE CLASSIFICATION:
• Doc Types:  ✅{summary['document_type_completed']:3d} ⏳{summary['document_type_pending']:3d} ❌{summary['document_type_error']:3d}

📝 METADATA FIELDS:"""
        
        for field in self.ledger.DUBLIN_CORE_FIELDS:
            field_stats = summary['dublin_core_fields'][field]
            analysis_text += f"\n• {field.title():12} ✅{field_stats['completed']:3d} ⏳{field_stats['pending']:3d} ❌{field_stats['error']:3d}"
        
        # Add document type breakdown if any are completed
        if summary['document_type_completed'] > 0:
            type_counts = self.ledger.df[self.ledger.df['document_type_status'] == 'completed']['document_type'].value_counts()
            if not type_counts.empty:
                analysis_text += "\n\n📊 DOCUMENT TYPE BREAKDOWN:\n"
                for doc_type, count in type_counts.items():
                    ocr_note = " (OCR skipped)" if doc_type == 'image' else ""
                    analysis_text += f"• {doc_type.title():12} {count:3d} files{ocr_note}\n"
        
        analysis_text += "\n\n" + "="*50 + "\n\n"
        if summary['total_files'] > 0:
            # Calculate pages with OCR
            pages_with_ocr = 0
            for _, row in self.ledger.df.iterrows():
                # Check if file has at least one completed OCR
                has_ocr = any(row.get(f'{engine}_status') == 'completed' 
                            for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr'])
                if has_ocr:
                    pages_with_ocr += self.ledger.get_page_count(row['filepath'])
            
            ocr_percentage = (pages_with_ocr / summary['total_pages'] * 100) if summary['total_pages'] > 0 else 0
            
            analysis_text += "📏 SCALE INFORMATION:\n"
            analysis_text += f"• Processing {summary['total_pages']} total pages across {summary['total_files']} files\n"
            analysis_text += f"• Pages with OCR: {pages_with_ocr}/{summary['total_pages']} ({ocr_percentage:.1f}%)\n"
            analysis_text += f"• Average pages per file: {summary['total_pages']/summary['total_files']:.1f}\n\n"
        analysis_text += "⚠️ NOTE: Document classification is required before OCR processing.\n"
        analysis_text += "Files classified as 'image' are excluded from OCR.\n\n"
        analysis_text += "Double-click files to view detailed OCR results."
        
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(1.0, analysis_text)
        
        # Update analysis tab
        summary = self.ledger.get_summary()
        analysis_text = f"""CODEBOOKS ANALYSIS REPORT
{'='*50}

📊 PROCESSING OVERVIEW:
Total Files: {summary['total_files']}
Total Pages: {summary['total_pages']} (PDF pages + images)

🔍 OCR ENGINE PERFORMANCE:
• EasyOCR:    ✅{summary['easyocr_completed']:3d} ⏳{summary['easyocr_pending']:3d} ❌{summary['easyocr_error']:3d}
• Tesseract:  ✅{summary['tesseract_completed']:3d} ⏳{summary['tesseract_pending']:3d} ❌{summary['tesseract_error']:3d}
• PyPDF2:     ✅{summary['pypdf2_completed']:3d} ⏳{summary['pypdf2_pending']:3d} ❌{summary['pypdf2_error']:3d}
• OpenAI OCR: ✅{summary['openai_ocr_completed']:3d} ⏳{summary['openai_ocr_pending']:3d} ❌{summary['openai_ocr_error']:3d}
• Ollama OCR: ✅{summary['ollama_ocr_completed']:3d} ⏳{summary['ollama_ocr_pending']:3d} ❌{summary['ollama_ocr_error']:3d}

📄 DOCUMENT TYPE CLASSIFICATION:
• Doc Types:  ✅{summary['document_type_completed']:3d} ⏳{summary['document_type_pending']:3d} ❌{summary['document_type_error']:3d}

📝 METADATA FIELDS:"""
        

        

        
        # Add document type breakdown if any are completed
        if summary['document_type_completed'] > 0:
            type_counts = self.ledger.df[self.ledger.df['document_type_status'] == 'completed']['document_type'].value_counts()
            if not type_counts.empty:
                analysis_text += "\n\n📊 DOCUMENT TYPE BREAKDOWN:\n"
                for doc_type, count in type_counts.items():
                    ocr_note = " (OCR skipped)" if doc_type == 'image' else ""
                    analysis_text += f"• {doc_type.title():12} {count:3d} files{ocr_note}\n"
        
        analysis_text += "\n\n" + "="*50 + "\n\n"
        if summary['total_files'] > 0:
            analysis_text += "📏 SCALE INFORMATION:\n"
            analysis_text += f"• Processing {summary['total_pages']} total pages across {summary['total_files']} files\n"
            analysis_text += f"• Average pages per file: {summary['total_pages']/summary['total_files']:.1f}\n\n"
        analysis_text += "⚠️ NOTE: Document classification is required before OCR processing.\n"
        analysis_text += "Files classified as 'image' are excluded from OCR.\n\n"
        analysis_text += "Double-click files to view detailed OCR results."
        
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(1.0, analysis_text)
    
    def evaluate_ocr(self):
        """Evaluate OCR quality for selected files"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select files to evaluate")
            return
        
        # Get selected files data
        files_data = []
        for item in selected_items:
            values = self.tree.item(item)['values']
            filename = values[0]
            matching_rows = self.ledger.df[self.ledger.df['filename'] == filename]
            if not matching_rows.empty:
                files_data.append(matching_rows.iloc[0])
        
        if not files_data:
            messagebox.showwarning("No Data", "No OCR data found for selected files")
            return
        
        self.show_ocr_evaluation_dialog(files_data)
    
    def show_ocr_evaluation_dialog(self, files_data: List):
        """Show OCR evaluation results dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("OCR Quality Evaluation")
        dialog.geometry("900x600")
        dialog.transient(self.root)
        
        # Main container
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(header_frame, text="🔍 OCR Quality Evaluation", 
                 font=("Arial", 14, "bold")).pack()
        ttk.Label(header_frame, text=f"Evaluating {len(files_data)} files", 
                 font=("Arial", 10), foreground="gray").pack()
        
        # Notebook for different views
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Summary tab
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="📊 Summary")
        
        summary_text = tk.Text(summary_frame, wrap=tk.WORD, font=("Consolas", 9))
        summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Calculate overall metrics
        all_results = []
        for file_data in files_data:
            ocr_results = {
                'easyocr': file_data.get('easyocr_ocr', ''),
                'tesseract': file_data.get('tesseract_ocr', ''),
                'pypdf2': file_data.get('pypdf2_ocr', ''),
                'openai_ocr': file_data.get('openai_ocr_ocr', ''),
                'ollama_ocr': file_data.get('ollama_ocr_ocr', '')
            }
            evaluation = OCREvaluator.evaluate_ocr_engines(ocr_results)
            all_results.append((file_data['filename'], evaluation))
        
        # Generate summary report
        summary_report = self.generate_evaluation_summary(all_results)
        summary_text.insert(1.0, summary_report)
        summary_text.config(state=tk.DISABLED)
        
        # Detailed results tab
        details_frame = ttk.Frame(notebook)
        notebook.add(details_frame, text="📋 Detailed Results")
        
        # Treeview for detailed results
        detail_columns = ['filename', 'engine', 'quality_score', 'text_length', 'similarity']
        detail_tree = ttk.Treeview(details_frame, columns=detail_columns, show='headings')
        
        for col in detail_columns:
            detail_tree.heading(col, text=col.replace('_', ' ').title())
            detail_tree.column(col, width=120)
        
        # Populate detailed results
        for filename, evaluation in all_results:
            for engine, metrics in evaluation.items():
                similarity = metrics.get('avg_similarity_to_others', 0.0)
                detail_tree.insert('', 'end', values=[
                    filename[:20] + '...' if len(filename) > 20 else filename,
                    engine,
                    f"{metrics['quality_score']:.3f}",
                    metrics['text_length'],
                    f"{similarity:.3f}" if similarity else "N/A"
                ])
        
        detail_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # OCR Performance Comparison tab
        comparison_frame = ttk.Frame(notebook)
        notebook.add(comparison_frame, text="🔍 OCR Performance")
        
        # Instructions
        inst_frame = ttk.LabelFrame(comparison_frame, text="📋 Instructions", padding="10")
        inst_frame.pack(fill=tk.X, padx=5, pady=5)
        
        instructions = tk.Text(inst_frame, height=4, wrap=tk.WORD, bg='#f8f8f8')
        instructions.pack(fill=tk.X)
        instructions.insert(1.0, 
            "1. Browse files below to see OCR results and document images\n"
            "2. Select an OCR engine as ground truth (reference standard)\n"
            "3. Click 'Evaluate Performance' to compare all engines against the reference\n"
            "4. View aggregated performance metrics across all selected files")
        instructions.config(state=tk.DISABLED)
        
        # Main content with paned window
        main_paned = ttk.PanedWindow(comparison_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel: File browser and OCR samples
        left_panel = ttk.LabelFrame(main_paned, text="📄 File Browser & OCR Samples")
        
        # File selector
        file_frame = ttk.Frame(left_panel)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="File:").pack(side=tk.LEFT)
        current_file_var = tk.StringVar(value=files_data[0]['filename'] if files_data else "")
        file_combo = ttk.Combobox(file_frame, textvariable=current_file_var, 
                                 values=[f['filename'] for f in files_data], width=30)
        file_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # OCR samples display
        samples_notebook = ttk.Notebook(left_panel)
        samples_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Document image tab
        image_frame = ttk.Frame(samples_notebook)
        samples_notebook.add(image_frame, text="🖼️ Document")
        
        # OCR text tabs
        ocr_tabs = {}
        for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']:
            tab_frame = ttk.Frame(samples_notebook)
            samples_notebook.add(tab_frame, text=engine.upper())
            
            text_widget = tk.Text(tab_frame, wrap=tk.WORD, font=("Consolas", 9), height=15)
            scroll = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scroll.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
            ocr_tabs[engine] = text_widget
        
        main_paned.add(left_panel, weight=1)
        
        # Right panel: Ground truth selection and results
        right_panel = ttk.LabelFrame(main_paned, text="⚖️ Performance Evaluation")
        
        # Ground truth selection
        gt_selection_frame = ttk.LabelFrame(right_panel, text="Select Ground Truth (Reference Standard)")
        gt_selection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        gt_source_var = tk.StringVar(value="openai_ocr")
        engines = [
            ('easyocr', '🤖 EasyOCR (AI-powered)'),
            ('tesseract', '📄 Tesseract (Traditional)'),
            ('pypdf2', '📋 PyPDF2 (Direct text)'),
            ('openai_ocr', '🤖📄 OpenAI OCR (Vision)'),
            ('ollama_ocr', '🏠🤖 Ollama OCR (Local)')
        ]
        
        for engine_key, engine_label in engines:
            ttk.Radiobutton(gt_selection_frame, text=engine_label, 
                           variable=gt_source_var, value=engine_key).pack(anchor=tk.W, padx=10, pady=2)
        
        # Evaluation button
        ttk.Button(gt_selection_frame, text="🔍 Evaluate Performance", 
                  command=lambda: self.evaluate_ocr_performance(files_data, gt_source_var.get(), results_text)).pack(pady=10)
        
        # Results display
        results_frame = ttk.LabelFrame(right_panel, text="📊 Performance Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        results_text = tk.Text(results_frame, wrap=tk.WORD, font=("Consolas", 9))
        results_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results_text.yview)
        results_text.configure(yscrollcommand=results_scroll.set)
        
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        main_paned.add(right_panel, weight=1)
        
        # Update display when file changes
        def update_file_display():
            filename = current_file_var.get()
            selected_file = None
            for file_data in files_data:
                if file_data['filename'] == filename:
                    selected_file = file_data
                    break
            
            if selected_file is not None:
                # Update OCR text displays
                for engine, text_widget in ocr_tabs.items():
                    text_widget.config(state=tk.NORMAL)
                    text_widget.delete(1.0, tk.END)
                    
                    if engine == 'openai_ocr':
                        ocr_text = str(selected_file.get('openai_ocr_ocr', '') or '')
                    elif engine == 'ollama_ocr':
                        ocr_text = str(selected_file.get('ollama_ocr_ocr', '') or '')
                    else:
                        ocr_text = str(selected_file.get(f'{engine}_ocr', '') or '')
                    
                    if ocr_text and ocr_text != 'nan':
                        text_widget.insert(1.0, ocr_text)
                    else:
                        text_widget.insert(1.0, "No text extracted")
                    
                    text_widget.config(state=tk.DISABLED)
                
                # Update document image
                self._create_document_preview(image_frame, selected_file.get('filepath', ''))
        
        file_combo.bind('<<ComboboxSelected>>', lambda e: update_file_display())
        
        # Initialize display
        dialog.after(100, update_file_display)
        
        # Visualization tab
        viz_frame = ttk.Frame(notebook)
        notebook.add(viz_frame, text="📈 Visualizations")
        
        # Debug label to show matplotlib status
        ttk.Label(viz_frame, text=f"Matplotlib Available: {MATPLOTLIB_AVAILABLE}", 
                 font=("Arial", 10)).pack(pady=5)
        
        if MATPLOTLIB_AVAILABLE:
            # Visualization controls
            viz_controls = ttk.Frame(viz_frame)
            viz_controls.pack(fill=tk.X, padx=5, pady=5)
            
            # Use updated results if available, otherwise use original
            def get_results_to_use():
                return getattr(self, 'updated_evaluation_results', all_results)
            
            ttk.Button(viz_controls, text="📊 Quality Comparison", 
                      command=lambda: self.plot_quality_comparison(viz_frame, get_results_to_use())).pack(side=tk.LEFT, padx=5)
            ttk.Button(viz_controls, text="🔗 Similarity Matrix", 
                      command=lambda: self.plot_similarity_matrix(viz_frame, get_results_to_use())).pack(side=tk.LEFT, padx=5)
            ttk.Button(viz_controls, text="📏 Length vs Quality", 
                      command=lambda: self.plot_length_vs_quality(viz_frame, get_results_to_use())).pack(side=tk.LEFT, padx=5)
            
            # Show ground truth label if updated results are being used
            if hasattr(self, 'ground_truth_label'):
                ttk.Label(viz_frame, text=f"Using Ground Truth: {self.ground_truth_label}", 
                         font=("Arial", 9), foreground="blue").pack(pady=5)
            
            ttk.Label(viz_frame, text="Click buttons above to generate visualizations", 
                     font=("Arial", 10), foreground="gray").pack(pady=10)
        else:
            ttk.Label(viz_frame, text="📊 Matplotlib not available\n\nInstall with: pip install matplotlib", 
                     font=("Arial", 12), justify=tk.CENTER).pack(expand=True)
        
        # Close button
    def _create_document_preview(self, parent_frame, filepath):
        """Create document preview widget"""
        try:
            from PIL import Image, ImageTk
            import fitz  # PyMuPDF for PDF preview
        except ImportError:
            ttk.Label(parent_frame, text="Preview unavailable\n(Install Pillow and PyMuPDF)", 
                     justify=tk.CENTER).pack(expand=True)
            return
        
        if not filepath or not os.path.exists(filepath):
            ttk.Label(parent_frame, text="File not found", justify=tk.CENTER).pack(expand=True)
            return
        
        # Create scrollable canvas
        canvas = tk.Canvas(parent_frame, bg='white')
        scrollbar_v = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar_h = ttk.Scrollbar(parent_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        try:
            file_ext = Path(filepath).suffix.lower()
            
            if file_ext == '.pdf':
                # PDF preview - show first page
                doc = fitz.open(filepath)
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 150% zoom
                img_data = pix.tobytes("ppm")
                doc.close()
                
                # Convert to PIL Image
                from io import BytesIO
                pil_image = Image.open(BytesIO(img_data))
                
            else:
                # Image file
                pil_image = Image.open(filepath)
                
                # Resize if too large
                max_size = (800, 600)
                pil_image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage and display
            photo = ImageTk.PhotoImage(pil_image)
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            canvas.configure(scrollregion=canvas.bbox("all"))
            
            # Keep reference to prevent garbage collection
            canvas.image = photo
            
        except Exception as e:
            ttk.Label(parent_frame, text=f"Preview error:\n{str(e)}", 
                     justify=tk.CENTER).pack(expand=True)
    
    def generate_evaluation_summary(self, all_results: List[Tuple]) -> str:
        """Generate evaluation summary report"""
        report = "📊 OCR QUALITY EVALUATION SUMMARY\n"
        report += "=" * 50 + "\n\n"
        
        # Engine performance summary
        engine_stats = {'easyocr': [], 'tesseract': [], 'pypdf2': [], 'openai_ocr': [], 'ollama_ocr': []}
        
        for filename, evaluation in all_results:
            for engine, metrics in evaluation.items():
                if metrics['text_length'] > 0:
                    engine_stats[engine].append(metrics['quality_score'])
        
        report += "🏆 ENGINE PERFORMANCE (Average Quality Score):\n"
        for engine, scores in engine_stats.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                report += f"   {engine.upper()}: {avg_score:.3f} ({len(scores)} files)\n"
            else:
                report += f"   {engine.upper()}: No data\n"
        
        report += "\n" + "=" * 50 + "\n\n"
        
        # Per-file summary
        report += "📋 PER-FILE RESULTS:\n\n"
        for filename, evaluation in all_results:
            report += f"📄 {filename}:\n"
            
            # Sort engines by quality score
            sorted_engines = sorted(evaluation.items(), 
                                  key=lambda x: x[1]['quality_score'], reverse=True)
            
            for engine, metrics in sorted_engines:
                if metrics['text_length'] > 0:
                    similarity = metrics.get('avg_similarity_to_others', 0)
                    report += f"   {engine:12} | Quality: {metrics['quality_score']:.3f} | "
                    report += f"Length: {metrics['text_length']:4d} | Similarity: {similarity:.3f}\n"
                else:
                    report += f"   {engine:12} | No text extracted\n"
            report += "\n"
        
        return report
    
    def plot_quality_comparison(self, parent_frame, all_results):
        """Plot quality comparison bar chart"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showwarning("Matplotlib Required", "Install matplotlib: pip install matplotlib")
            return
        
        # Clear existing plots
        for widget in parent_frame.winfo_children():
            if isinstance(widget, tk.Canvas):
                widget.destroy()
        
        # Calculate average quality scores
        engine_scores = {'easyocr': [], 'tesseract': [], 'pypdf2': [], 'openai_ocr': [], 'ollama_ocr': []}
        
        for filename, evaluation in all_results:
            for engine, metrics in evaluation.items():
                if metrics['text_length'] > 0:
                    engine_scores[engine].append(metrics['quality_score'])
        
        engines = []
        scores = []
        for engine, score_list in engine_scores.items():
            if score_list:
                engines.append(engine.upper())
                scores.append(sum(score_list) / len(score_list))
        
        if not engines:
            return
        
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(engines, scores, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFA07A'])
        ax.set_ylabel('Average Quality Score')
        ax.set_title('OCR Engine Quality Comparison')
        ax.set_ylim(0, 1)
        
        # Add value labels on bars
        for bar, score in zip(bars, scores):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                   f'{score:.3f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def plot_similarity_matrix(self, parent_frame, all_results):
        """Plot similarity matrix heatmap"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showwarning("Matplotlib Required", "Install matplotlib: pip install matplotlib")
            return
        
        # Clear existing plots
        for widget in parent_frame.winfo_children():
            if isinstance(widget, tk.Canvas):
                widget.destroy()
        
        engines = ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']
        similarity_matrix = np.zeros((5, 5))
        
        # Get actual OCR texts for similarity calculation
        from difflib import SequenceMatcher
        
        # Collect all OCR texts by engine
        engine_texts = {engine: [] for engine in engines}
        
        # Extract OCR texts from ledger data instead of evaluation results
        for _, row in self.ledger.df.iterrows():
            for engine in engines:
                if engine == 'openai_ocr':
                    text = str(row.get('openai_ocr_ocr', '') or '')
                elif engine == 'ollama_ocr':
                    text = str(row.get('ollama_ocr_ocr', '') or '')
                else:
                    text = str(row.get(f'{engine}_ocr', '') or '')
                
                if text and text != 'nan' and len(text.strip()) > 10:
                    engine_texts[engine].append(text.strip())
        
        # Calculate pairwise text similarities
        for i, engine1 in enumerate(engines):
            for j, engine2 in enumerate(engines):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    similarities = []
                    # Compare texts from same documents
                    min_texts = min(len(engine_texts[engine1]), len(engine_texts[engine2]))
                    
                    for k in range(min_texts):
                        if k < len(engine_texts[engine1]) and k < len(engine_texts[engine2]):
                            text1 = engine_texts[engine1][k]
                            text2 = engine_texts[engine2][k]
                            
                            if text1 and text2:
                                # Calculate actual text similarity
                                similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
                                similarities.append(similarity)
                    
                    if similarities:
                        similarity_matrix[i][j] = sum(similarities) / len(similarities)
                    else:
                        similarity_matrix[i][j] = 0.0
        
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(similarity_matrix, cmap='RdYlBu', vmin=0, vmax=1)
        
        # Set ticks and labels
        ax.set_xticks(range(5))
        ax.set_yticks(range(5))
        ax.set_xticklabels([e.upper() for e in engines])
        ax.set_yticklabels([e.upper() for e in engines])
        
        # Add text annotations
        for i in range(5):
            for j in range(5):
                text = ax.text(j, i, f'{similarity_matrix[i, j]:.2f}',
                             ha="center", va="center", color="black")
        
        ax.set_title('OCR Engine Similarity Matrix')
        plt.colorbar(im, ax=ax, label='Similarity Score')
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def plot_length_vs_quality(self, parent_frame, all_results):
        """Plot text length vs quality scatter plot"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showwarning("Matplotlib Required", "Install matplotlib: pip install matplotlib")
            return
        
        # Clear existing plots
        for widget in parent_frame.winfo_children():
            if isinstance(widget, tk.Canvas):
                widget.destroy()
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        colors = {'easyocr': '#FF6B6B', 'tesseract': '#4ECDC4', 'pypdf2': '#45B7D1', 'openai_ocr': '#96CEB4', 'ollama_ocr': '#FFA07A'}
        
        for engine, color in colors.items():
            lengths = []
            qualities = []
            
            for filename, evaluation in all_results:
                if engine in evaluation and evaluation[engine]['text_length'] > 0:
                    lengths.append(evaluation[engine]['text_length'])
                    qualities.append(evaluation[engine]['quality_score'])
            
            if lengths:
                ax.scatter(lengths, qualities, c=color, label=engine.upper(), alpha=0.7, s=50)
        
        ax.set_xlabel('Text Length (characters)')
        ax.set_ylabel('Quality Score')
        ax.set_title('Text Length vs Quality Score by OCR Engine')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def recalculate_quality_scores(self, files_data, gt_source, selected_filename, gt_text_widget):
        """Recalculate quality scores using selected ground truth"""
        if gt_source == "manual":
            ground_truth = gt_text_widget.get(1.0, tk.END).strip()
            if not ground_truth:
                messagebox.showwarning("No Ground Truth", "Please enter ground truth text")
                return
            reference_label = "Manual Entry"
        else:
            # Find selected file data
            selected_file = None
            for file_data in files_data:
                if file_data['filename'] == selected_filename:
                    selected_file = file_data
                    break
            
            if selected_file is None:
                messagebox.showwarning("No File Selected", "Please select a file")
                return
            
            if gt_source == 'openai_ocr':
                ground_truth = str(selected_file.get('openai_ocr_ocr', '') or '')
            elif gt_source == 'ollama_ocr':
                ground_truth = str(selected_file.get('ollama_ocr_ocr', '') or '')
            else:
                ground_truth = str(selected_file.get(f'{gt_source}_ocr', '') or '')
            
            if not ground_truth or ground_truth == 'nan':
                messagebox.showwarning("No Reference Text", f"No {gt_source.upper()} text found for this file")
                return
            
            reference_label = f"{gt_source.upper()} OCR"
        
        # Recalculate quality scores for all files using the selected ground truth
        updated_results = []
        for file_data in files_data:
            # Get ground truth text for this specific file if using OCR as reference
            if gt_source != "manual":
                if gt_source == 'openai_ocr':
                    file_ground_truth = str(file_data.get('openai_ocr_ocr', '') or '')
                elif gt_source == 'ollama_ocr':
                    file_ground_truth = str(file_data.get('ollama_ocr_ocr', '') or '')
                else:
                    file_ground_truth = str(file_data.get(f'{gt_source}_ocr', '') or '')
            else:
                file_ground_truth = ground_truth
            
            # Skip if no ground truth for this file
            if not file_ground_truth or file_ground_truth == 'nan':
                continue
            
            ocr_results = {
                'easyocr': file_data.get('easyocr_ocr', ''),
                'tesseract': file_data.get('tesseract_ocr', ''),
                'pypdf2': file_data.get('pypdf2_ocr', ''),
                'openai_ocr': file_data.get('openai_ocr_ocr', ''),
                'ollama_ocr': file_data.get('ollama_ocr_ocr', '')
            }
            
            # Remove the ground truth engine from comparison if using OCR as reference
            if gt_source != "manual":
                comparison_results = {k: v for k, v in ocr_results.items() if k != gt_source}
            else:
                comparison_results = ocr_results
            
            # Use the file-specific ground truth for quality calculation
            evaluation = OCREvaluator.evaluate_ocr_engines(comparison_results, file_ground_truth)
            updated_results.append((file_data['filename'], evaluation))
        
        # Store updated results for visualization access
        self.updated_evaluation_results = updated_results
        self.ground_truth_label = reference_label
        
        # Show updated summary
        summary_report = self.generate_evaluation_summary(updated_results)
        summary_report = f"📊 QUALITY SCORES RECALCULATED\nGround Truth: {reference_label}\n{'='*50}\n\n" + summary_report
        
        # Create new dialog to show updated results
        result_dialog = tk.Toplevel(self.root)
        result_dialog.title(f"Updated Quality Scores - {reference_label}")
        result_dialog.geometry("800x600")
        result_dialog.transient(self.root)
        
        result_text = tk.Text(result_dialog, wrap=tk.WORD, font=("Consolas", 9))
        result_scroll = ttk.Scrollbar(result_dialog, orient=tk.VERTICAL, command=result_text.yview)
        result_text.configure(yscrollcommand=result_scroll.set)
        
        result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        result_text.insert(1.0, summary_report)
        result_text.config(state=tk.DISABLED)
        
        ttk.Button(result_dialog, text="Close", command=result_dialog.destroy).pack(pady=5)
        

    
    def evaluate_ocr_performance(self, files_data, gt_source, results_text):
        """Evaluate OCR performance across all files using selected ground truth"""
        results_text.delete(1.0, tk.END)
        results_text.insert(tk.END, "🔄 Evaluating OCR performance...\n")
        results_text.update()
        
        # Collect all evaluations
        all_evaluations = []
        valid_files = 0
        
        for file_data in files_data:
            # Get ground truth for this file
            if gt_source == 'openai_ocr':
                ground_truth = str(file_data.get('openai_ocr_ocr', '') or '')
            elif gt_source == 'ollama_ocr':
                ground_truth = str(file_data.get('ollama_ocr_ocr', '') or '')
            else:
                ground_truth = str(file_data.get(f'{gt_source}_ocr', '') or '')
            
            if not ground_truth or ground_truth == 'nan':
                continue
            
            # Get OCR results (excluding ground truth engine)
            ocr_results = {}
            for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']:
                if engine == gt_source:
                    continue
                
                if engine == 'openai_ocr':
                    text = str(file_data.get('openai_ocr_ocr', '') or '')
                elif engine == 'ollama_ocr':
                    text = str(file_data.get('ollama_ocr_ocr', '') or '')
                else:
                    text = str(file_data.get(f'{engine}_ocr', '') or '')
                
                if text and text != 'nan':
                    ocr_results[engine] = text
            
            if ocr_results:
                evaluation = OCREvaluator.evaluate_ocr_engines(ocr_results, ground_truth)
                all_evaluations.append(evaluation)
                valid_files += 1
        
        if not all_evaluations:
            results_text.delete(1.0, tk.END)
            results_text.insert(1.0, "❌ No valid files found for evaluation")
            return
        
        # Aggregate results across all files
        engine_metrics = {}
        for evaluation in all_evaluations:
            for engine, metrics in evaluation.items():
                if engine not in engine_metrics:
                    engine_metrics[engine] = {'cer': [], 'wer': [], 'similarity': [], 'quality': []}
                
                if metrics['text_length'] > 0:
                    engine_metrics[engine]['cer'].append(metrics.get('cer', 0))
                    engine_metrics[engine]['wer'].append(metrics.get('wer', 0))
                    engine_metrics[engine]['similarity'].append(metrics.get('similarity_to_ground_truth', 0))
                    engine_metrics[engine]['quality'].append(metrics.get('quality_score', 0))
        
        # Calculate averages and display results
        results_text.delete(1.0, tk.END)
        
        report = f"📊 OCR PERFORMANCE EVALUATION\n"
        report += f"Ground Truth: {gt_source.upper()}\n"
        report += f"Files Evaluated: {valid_files}\n"
        report += "=" * 50 + "\n\n"
        
        # Sort engines by average quality score
        engine_averages = []
        for engine, metrics in engine_metrics.items():
            if metrics['quality']:
                avg_quality = sum(metrics['quality']) / len(metrics['quality'])
                avg_cer = sum(metrics['cer']) / len(metrics['cer'])
                avg_wer = sum(metrics['wer']) / len(metrics['wer'])
                avg_similarity = sum(metrics['similarity']) / len(metrics['similarity'])
                
                engine_averages.append({
                    'engine': engine,
                    'quality': avg_quality,
                    'cer': avg_cer,
                    'wer': avg_wer,
                    'similarity': avg_similarity,
                    'files': len(metrics['quality'])
                })
        
        engine_averages.sort(key=lambda x: x['quality'], reverse=True)
        
        report += "🏆 OVERALL PERFORMANCE RANKING:\n\n"
        for i, engine_data in enumerate(engine_averages, 1):
            report += f"{i}. {engine_data['engine'].upper()}\n"
            report += f"   Quality Score: {engine_data['quality']:.3f}\n"
            report += f"   Similarity:    {engine_data['similarity']:.3f}\n"
            report += f"   Char Error:    {engine_data['cer']:.3f}\n"
            report += f"   Word Error:    {engine_data['wer']:.3f}\n"
            report += f"   Files:         {engine_data['files']}/{valid_files}\n\n"
        
        report += "=" * 50 + "\n\n"
        report += "📈 INTERPRETATION:\n"
        report += "• Quality Score: Higher is better (0.0-1.0)\n"
        report += "• Similarity: Higher is better (0.0-1.0)\n"
        report += "• Error Rates: Lower is better (0.0+)\n"
        report += "• Files: Number of files with valid OCR text\n"
        
        results_text.insert(1.0, report)
        
        # Store results for visualization
        self.updated_evaluation_results = [(f"aggregate_{i}", {engine_data['engine']: {
            'quality_score': engine_data['quality'],
            'similarity_to_ground_truth': engine_data['similarity'],
            'cer': engine_data['cer'],
            'wer': engine_data['wer'],
            'text_length': 100  # Placeholder
        }}) for i, engine_data in enumerate(engine_averages)]
        self.ground_truth_label = f"{gt_source.upper()} (Aggregated)"
        
        # Set global ground truth engine
        self.ground_truth_engine = gt_source
        self.ground_truth_status.set(f"Ground Truth: {gt_source.upper()}")
        
        # Save ground truth selection to config
        self.config.set('ocr_settings', 'ground_truth_engine', gt_source)
        
        # Update OCR Preview column header
        if self.ground_truth_engine:
            self.tree.heading('ocr_preview', text=f'OCR Preview ({self.ground_truth_engine.upper()} - Ground Truth)')
        else:
            self.tree.heading('ocr_preview', text='OCR Preview (Best Available)')
        
        self.refresh_display()  # Refresh to update OCR preview column
    
    def show_ai_model_selection_dialog(self):
        """Show dialog to select AI model for document classification"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select AI Model for Document Classification")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        selected_model = None
        
        ttk.Label(dialog, text="Choose AI model for document type classification:", 
                 font=("Arial", 11, "bold")).pack(pady=10)
        
        model_var = tk.StringVar()
        
        # Check which models are available
        ai_config = self.config.get_section('ai_models')
        
        if ai_config.get('openai_enabled') and ai_config.get('openai_api_key'):
            ttk.Radiobutton(dialog, text="🤖 OpenAI GPT-4o (Cloud-based, high accuracy)", 
                           variable=model_var, value="openai").pack(anchor=tk.W, padx=20, pady=5)
        
        if ai_config.get('ollama_enabled'):
            model_name = ai_config.get('ollama_model', 'gemma3')
            ttk.Radiobutton(dialog, text=f"🏠 Ollama {model_name} (Local, privacy-focused)", 
                           variable=model_var, value="ollama").pack(anchor=tk.W, padx=20, pady=5)
        
        if not ai_config.get('openai_enabled') and not ai_config.get('ollama_enabled'):
            ttk.Label(dialog, text="❌ No AI models configured", 
                     foreground="red").pack(pady=10)
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
            return None
        
        def on_ok():
            selected_model = model_var.get()
            if selected_model:
                dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select an AI model")
        
        ttk.Button(dialog, text="▶️ Start Classification", command=on_ok).pack(pady=20)
        ttk.Button(dialog, text="❌ Cancel", command=dialog.destroy).pack(pady=5)
        
        dialog.wait_window()
        return model_var.get() if model_var.get() else None
    
    def archive_ocr_result(self, file_id, engine):
        """Archive an OCR result to allow reprocessing"""
        import datetime
        
        # Get current OCR result
        mask = self.ledger.df['file_id'] == file_id
        current_result = self.ledger.df.loc[mask, f'{engine}_ocr'].iloc[0]
        
        if not current_result or str(current_result) == 'nan':
            messagebox.showinfo("No Result", f"No {engine.upper()} result to archive")
            return
        
        # Create archive entry with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_text = f"[ARCHIVED {timestamp}] {current_result}"
        
        # Clear current result and set status to pending
        self.ledger.df.loc[mask, f'{engine}_ocr'] = archive_text
        self.ledger.df.loc[mask, f'{engine}_status'] = 'pending'
        self.ledger.save_ledger()
        
        filename = self.ledger.df.loc[mask, 'filename'].iloc[0]
        self.log_activity(f"Archived {engine.upper()} result for {filename}")
        messagebox.showinfo("Archived", f"{engine.upper()} result archived. File is now pending reprocessing.")
        
        self.refresh_display()
    
    def open_file_externally(self, filepath):
        """Open file with system default application"""
        import subprocess
        import platform
        import os
        
        try:
            if platform.system() == 'Windows':
                os.startfile(filepath)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', filepath])
            else:  # Linux
                subprocess.run(['xdg-open', filepath])
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to open file externally: {e}")
    
    def on_double_click(self, event):
        """Handle double-click on file to show document viewer"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            filename = item['values'][0]
            
            # Find the file in the ledger
            file_row = self.ledger.df[self.ledger.df['filename'] == filename]
            if not file_row.empty:
                filepath = file_row.iloc[0]['filepath']
                self.show_document_viewer(filepath)
    
    def show_document_viewer(self, filepath):
        """Show document in a viewer window"""
        viewer = tk.Toplevel(self.root)
        viewer.title(f"Document Viewer - {os.path.basename(filepath)}")
        viewer.geometry("900x700")
        
        file_ext = os.path.splitext(filepath)[1].lower()
        
        if file_ext == '.pdf':
            self.show_pdf_viewer(viewer, filepath)
        else:
            self.show_image_viewer(viewer, filepath)
    
    def show_image_viewer(self, parent, filepath):
        """Show image in viewer"""
        try:
            from PIL import Image, ImageTk
            img = Image.open(filepath)
            
            # Calculate display size
            display_width, display_height = 750, 550
            img_width, img_height = img.size
            
            scale_w = display_width / img_width
            scale_h = display_height / img_height
            scale = min(scale_w, scale_h, 1.0)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            
            label = ttk.Label(parent, image=photo)
            label.image = photo
            label.pack(expand=True)
            
        except Exception as e:
            ttk.Label(parent, text=f"Error loading image: {str(e)}").pack(expand=True)
    
    def show_pdf_viewer(self, parent, filepath):
        """Show PDF in viewer with page navigation"""
        try:
            import fitz
        except ImportError:
            ttk.Label(parent, text="PyMuPDF required for PDF viewing.\nInstall with: pip install PyMuPDF").pack(expand=True)
            return
        
        try:
            doc = fitz.open(filepath)
            
            main_frame = ttk.Frame(parent)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Navigation
            nav_frame = ttk.Frame(main_frame)
            nav_frame.pack(fill=tk.X, pady=(0, 10))
            
            current_page = [0]  # Use list for closure
            total_pages = len(doc)
            
            def change_page(direction):
                new_page = current_page[0] + direction
                if 0 <= new_page < total_pages:
                    current_page[0] = new_page
                    page_label.config(text=f"Page {current_page[0] + 1} of {total_pages}")
                    display_page()
            
            def display_page():
                try:
                    page = doc.load_page(current_page[0])
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    
                    from io import BytesIO
                    from PIL import Image, ImageTk
                    img_data = pix.tobytes("png")
                    img = Image.open(BytesIO(img_data))
                    
                    photo = ImageTk.PhotoImage(img)
                    
                    canvas.delete("all")
                    canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                    canvas.image = photo
                    canvas.configure(scrollregion=canvas.bbox("all"))
                    
                except Exception as e:
                    canvas.delete("all")
                    canvas.create_text(100, 100, text=f"Error: {str(e)}", anchor=tk.NW)
            
            ttk.Button(nav_frame, text="◀ Previous", command=lambda: change_page(-1)).pack(side=tk.LEFT, padx=5)
            
            page_label = ttk.Label(nav_frame, text=f"Page 1 of {total_pages}")
            page_label.pack(side=tk.LEFT, padx=20)
            
            ttk.Button(nav_frame, text="Next ▶", command=lambda: change_page(1)).pack(side=tk.LEFT, padx=5)
            
            # Canvas for PDF display
            canvas_frame = ttk.Frame(main_frame)
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            
            canvas = tk.Canvas(canvas_frame, bg='white')
            v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
            h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
            
            canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
            
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            
            display_page()
            
        except Exception as e:
            ttk.Label(parent, text=f"Error loading PDF: {str(e)}").pack(expand=True)
    
    def setup_timeline_analysis(self, parent_frame):
        """Setup timeline analysis interface"""
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(2, weight=1)
        
        # Add explanation header
        info_frame = ttk.LabelFrame(parent_frame, text="📅 Timeline Analysis Overview", padding="10")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = tk.Text(info_frame, height=3, wrap=tk.WORD, bg='#f8f8f8', font=("Arial", 9))
        info_text.pack(fill=tk.X)
        info_text.insert(1.0, 
            "Extract and visualize temporal patterns from your documents. Select files to analyze, choose OCR source, "
            "then extract timeline events. View chronological events, generate timeline charts, and analyze document "
            "frequency by decade. Double-click events to view source documents.")
        info_text.config(state=tk.DISABLED)
        
        # Controls
        controls_frame = ttk.Frame(parent_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # First row of controls
        controls_row1 = ttk.Frame(controls_frame)
        controls_row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(controls_row1, text="OCR Source:").pack(side=tk.LEFT, padx=5)
        self.timeline_ocr_var = tk.StringVar(value=self.ground_truth_engine or "easyocr")
        ocr_combo = ttk.Combobox(controls_row1, textvariable=self.timeline_ocr_var,
                                values=["easyocr", "tesseract", "pypdf2", "openai_ocr", "ollama_ocr"], width=12)
        ocr_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_row1, text="📂 Select Files", command=self.select_timeline_files).pack(side=tk.LEFT, padx=10)
        ttk.Button(controls_row1, text="📅 Extract Timeline", command=self.extract_timeline).pack(side=tk.LEFT, padx=5)
        
        # Second row of controls
        controls_row2 = ttk.Frame(controls_frame)
        controls_row2.pack(fill=tk.X, pady=2)
        
        ttk.Button(controls_row2, text="📊 Timeline Chart", command=self.show_timeline_chart).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_row2, text="📈 Document Frequency", command=self.show_document_frequency).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_row2, text="💾 Export Timeline", command=self.export_timeline_data).pack(side=tk.LEFT, padx=5)
        
        # Third row - Date range controls (initially hidden)
        self.date_range_frame = ttk.Frame(controls_frame)
        
        ttk.Label(self.date_range_frame, text="Date Range:").pack(side=tk.LEFT, padx=5)
        ttk.Label(self.date_range_frame, text="From:").pack(side=tk.LEFT, padx=(10,2))
        self.start_year_var = tk.StringVar()
        start_year_entry = ttk.Entry(self.date_range_frame, textvariable=self.start_year_var, width=8)
        start_year_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.date_range_frame, text="To:").pack(side=tk.LEFT, padx=(10,2))
        self.end_year_var = tk.StringVar()
        end_year_entry = ttk.Entry(self.date_range_frame, textvariable=self.end_year_var, width=8)
        end_year_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(self.date_range_frame, text="🔍 Filter", command=self.filter_timeline_by_date).pack(side=tk.LEFT, padx=10)
        ttk.Button(self.date_range_frame, text="🔄 Reset", command=self.reset_timeline_filter).pack(side=tk.LEFT, padx=2)
        
        # File selection status
        self.timeline_selection_var = tk.StringVar(value="All files selected")
        ttk.Label(controls_frame, textvariable=self.timeline_selection_var, font=("Arial", 9), foreground="blue").pack(anchor=tk.W, padx=5, pady=2)
        
        # Main paned window
        paned = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Timeline events list
        timeline_list_frame = ttk.LabelFrame(paned, text="Timeline Events")
        self.timeline_tree = ttk.Treeview(timeline_list_frame, columns=['year', 'confidence', 'type', 'document'], show='tree headings')
        self.timeline_tree.heading('#0', text='Date Text')
        self.timeline_tree.heading('year', text='Year')
        self.timeline_tree.heading('confidence', text='Conf')
        self.timeline_tree.heading('type', text='Type')
        self.timeline_tree.heading('document', text='Document')
        
        self.timeline_tree.column('#0', width=150)
        self.timeline_tree.column('year', width=60)
        self.timeline_tree.column('confidence', width=50)
        self.timeline_tree.column('type', width=80)
        self.timeline_tree.column('document', width=200)
        
        timeline_scroll = ttk.Scrollbar(timeline_list_frame, orient=tk.VERTICAL, command=self.timeline_tree.yview)
        self.timeline_tree.configure(yscrollcommand=timeline_scroll.set)
        
        self.timeline_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        timeline_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Bind double-click to open document viewer
        self.timeline_tree.bind('<Double-1>', self.on_timeline_double_click)
        
        # Statistics panel
        stats_frame = ttk.LabelFrame(paned, text="Timeline Statistics")
        self.timeline_stats_text = tk.Text(stats_frame, wrap=tk.WORD, font=("Consolas", 9), height=20)
        stats_scroll = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=self.timeline_stats_text.yview)
        self.timeline_stats_text.configure(yscrollcommand=stats_scroll.set)
        
        self.timeline_stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Add visualization frame
        viz_frame = ttk.LabelFrame(paned, text="Timeline Visualization")
        self.timeline_viz_frame = ttk.Frame(viz_frame)
        self.timeline_viz_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Default message
        ttk.Label(self.timeline_viz_frame, text="📊 Click visualization buttons to generate charts", 
                 font=("Arial", 12), foreground="gray").pack(expand=True)
        
        paned.add(timeline_list_frame, weight=1)
        paned.add(viz_frame, weight=1)
        paned.add(stats_frame, weight=1)
        
        # Store timeline data
        self.timeline_events = []
        self.filtered_timeline_events = []  # For date range filtering
        self.selected_timeline_files = []  # For subset selection
        
        # Store archival metadata
        self.archival_metadata = {}
    
    def on_timeline_double_click(self, event):
        """Handle double-click on timeline event to show document"""
        selection = self.timeline_tree.selection()
        if not selection:
            return
        
        item = self.timeline_tree.item(selection[0])
        values = item['values']
        if len(values) < 4:
            return
        
        filename = values[3]  # Document column
        
        # Find the file in the ledger
        matching_rows = self.ledger.df[self.ledger.df['filename'] == filename]
        if matching_rows.empty:
            messagebox.showwarning("File Not Found", f"Could not find file: {filename}")
            return
        
        filepath = matching_rows.iloc[0]['filepath']
        self.on_tree_double_click(None, filepath=filepath)
    
    def on_tree_double_click(self, event, filepath=None):
        """Handle double-click on tree item to show full OCR text with image preview"""
        if filepath:
            # Direct filepath provided (from timeline)
            matching_rows = self.ledger.df[self.ledger.df['filepath'] == filepath]
            if matching_rows.empty:
                return
            row = matching_rows.iloc[0]
            filename = row['filename']
        else:
            # From tree selection
            item = self.tree.selection()[0] if self.tree.selection() else None
            if not item:
                return
            
            values = self.tree.item(item)['values']
            filename = values[0]
            
            # Find the full OCR text and file path
            matching_rows = self.ledger.df[self.ledger.df['filename'] == filename]
            if matching_rows.empty:
                return
            
            row = matching_rows.iloc[0]
            filepath = row.get('filepath', '')
        
        # Get OCR results
        easyocr_text = str(row.get('easyocr_ocr', '') or '')
        tesseract_text = str(row.get('tesseract_ocr', '') or '')
        pypdf2_text = str(row.get('pypdf2_ocr', '') or '')
        openai_text = str(row.get('openai_ocr_ocr', '') or '')
        ollama_text = str(row.get('ollama_ocr_ocr', '') or '')
        
        # Show full text in dialog with image preview
        dialog = tk.Toplevel(self.root)
        dialog.title(f"OCR Results - {filename}")
        dialog.geometry("1200x700")
        dialog.transient(self.root)
        
        # Main container with paned window
        main_paned = ttk.PanedWindow(dialog, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side - OCR text tabs
        notebook = ttk.Notebook(main_paned)
        
        # Create OCR tabs
        ocr_data = [
            ("EasyOCR", easyocr_text, "easyocr"),
            ("Tesseract", tesseract_text, "tesseract"), 
            ("PyPDF2", pypdf2_text, "pypdf2"),
            ("OpenAI OCR", openai_text, "openai_ocr"),
            ("Ollama OCR", ollama_text, "ollama_ocr")
        ]
        
        for tab_name, text_content, engine_key in ocr_data:
            if text_content.strip():
                frame = ttk.Frame(notebook)
                notebook.add(frame, text=tab_name)
                
                # Add archive button at top of each tab
                button_frame = ttk.Frame(frame)
                button_frame.pack(fill=tk.X, pady=(0, 5))
                
                archive_btn = ttk.Button(button_frame, text=f"🗄️ Archive {tab_name}", 
                                       command=lambda e=engine_key: self.archive_ocr_result(row['file_id'], e))
                archive_btn.pack(side=tk.LEFT)
                
                # Text widget with scrollbar
                text_widget_frame = ttk.Frame(frame)
                text_widget_frame.pack(fill=tk.BOTH, expand=True)
                
                text_widget = tk.Text(text_widget_frame, wrap=tk.WORD, font=("Consolas", 9))
                scrollbar = ttk.Scrollbar(text_widget_frame, orient=tk.VERTICAL, command=text_widget.yview)
                text_widget.configure(yscrollcommand=scrollbar.set)
                
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                text_widget.insert(1.0, text_content)
                text_widget.config(state=tk.DISABLED)
        
        # Add NER results tab
        ner_entities = str(row.get('named_entities', '') or '')
        if ner_entities and ner_entities != 'nan' and ner_entities.strip():
            ner_frame = ttk.Frame(notebook)
            notebook.add(ner_frame, text="🏷️ Named Entities")
            
            # NER text widget with scrollbar
            ner_text_frame = ttk.Frame(ner_frame)
            ner_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            ner_text_widget = tk.Text(ner_text_frame, wrap=tk.WORD, font=("Consolas", 9))
            ner_scrollbar = ttk.Scrollbar(ner_text_frame, orient=tk.VERTICAL, command=ner_text_widget.yview)
            ner_text_widget.configure(yscrollcommand=ner_scrollbar.set)
            
            ner_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ner_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            ner_text_widget.insert(1.0, ner_entities)
            ner_text_widget.config(state=tk.DISABLED)
        
        main_paned.add(notebook, weight=1)
        
        # Right side - Document preview with open button
        preview_frame = ttk.LabelFrame(main_paned, text="Document Preview", padding="10")
        
        # Add open externally button for PDFs
        file_ext = os.path.splitext(filepath)[1].lower()
        if file_ext == '.pdf':
            button_frame = ttk.Frame(preview_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            ttk.Button(button_frame, text="📄 Open PDF Externally", 
                      command=lambda: self.open_file_externally(filepath)).pack()
        
        self._create_document_preview(preview_frame, filepath)
        main_paned.add(preview_frame, weight=1)
        
        # Close button
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack()
    
    def select_timeline_files(self):
        """Show dialog to select subset of files for timeline analysis"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Files for Timeline Analysis")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="📂 Select Files for Timeline Analysis", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Instructions
        inst_frame = ttk.Frame(dialog)
        inst_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(inst_frame, text="• Select multiple files with Ctrl+Click  • Check/uncheck selected files with buttons below", 
                 font=("Arial", 9), foreground="gray").pack()
        
        # File tree with archival structure
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview with archival grouping
        file_tree = ttk.Treeview(tree_frame, columns=['selected', 'filepath'], show='tree headings', selectmode='extended')
        file_tree.heading('#0', text='Archive Structure / File')
        file_tree.heading('selected', text='Selected')
        file_tree.heading('filepath', text='File Path')
        file_tree.column('#0', width=300)
        file_tree.column('selected', width=80)
        file_tree.column('filepath', width=300)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=file_tree.yview)
        file_tree.configure(yscrollcommand=scrollbar.set)
        
        file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Build archival structure like in Processing tab
        groups = {}
        file_items = {}  # Map file_id to tree item
        
        for _, row in self.ledger.df.iterrows():
            collection, box, folder = self.parse_archival_path(row['filepath'])
            group_key = f"{collection} > {box} > {folder}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(row)
        
        # Populate tree with groups and files
        for group_key, files in groups.items():
            # Insert group header
            group_item = file_tree.insert('', 'end', 
                text=f"📁 {group_key}",
                values=['', ''],
                tags=('group',),
                open=True)
            
            # Insert files under group
            for row in files:
                file_id = row['file_id']
                is_selected = file_id in self.selected_timeline_files if self.selected_timeline_files else True
                
                file_item = file_tree.insert(group_item, 'end', 
                    text=row['filename'],
                    values=['✓' if is_selected else '', row['filepath']],
                    tags=('file',))
                
                file_items[file_item] = {'file_id': file_id, 'filename': row['filename'], 'selected': is_selected}
        
        # Configure styling
        file_tree.tag_configure('group', background='#e8f4fd', font=('Arial', 9, 'bold'))
        file_tree.tag_configure('file', background='white')
        
        # Control buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def check_selected():
            """Check selected files"""
            selected_items = file_tree.selection()
            for item in selected_items:
                if item in file_items:
                    file_items[item]['selected'] = True
                    file_tree.item(item, values=['✓', file_tree.item(item)['values'][1]])
        
        def uncheck_selected():
            """Uncheck selected files"""
            selected_items = file_tree.selection()
            for item in selected_items:
                if item in file_items:
                    file_items[item]['selected'] = False
                    file_tree.item(item, values=['', file_tree.item(item)['values'][1]])
        
        def select_all_files():
            """Check all files"""
            for item in file_items:
                file_items[item]['selected'] = True
                file_tree.item(item, values=['✓', file_tree.item(item)['values'][1]])
        
        def select_no_files():
            """Uncheck all files"""
            for item in file_items:
                file_items[item]['selected'] = False
                file_tree.item(item, values=['', file_tree.item(item)['values'][1]])
        
        def apply_selection():
            """Apply the selection"""
            self.selected_timeline_files = [data['file_id'] for data in file_items.values() if data['selected']]
            count = len(self.selected_timeline_files)
            total = len(file_items)
            if count == total:
                self.timeline_selection_var.set("All files selected")
            else:
                self.timeline_selection_var.set(f"{count} of {total} files selected")
            dialog.destroy()
        
        # Button layout
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="✓ Check Selected", command=check_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="✗ Uncheck Selected", command=uncheck_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="📂 Expand All", command=lambda: self.expand_collapse_tree(file_tree, True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="📁 Collapse All", command=lambda: self.expand_collapse_tree(file_tree, False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Select All", command=select_all_files).pack(side=tk.LEFT, padx=10)
        ttk.Button(left_buttons, text="Select None", command=select_no_files).pack(side=tk.LEFT, padx=2)
        
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="Apply", command=apply_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_buttons, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def filter_timeline_by_date(self):
        """Filter timeline events by date range"""
        try:
            start_year = int(self.start_year_var.get()) if self.start_year_var.get() else None
            end_year = int(self.end_year_var.get()) if self.end_year_var.get() else None
            
            if start_year is None or end_year is None:
                messagebox.showwarning("Invalid Range", "Please enter both start and end years")
                return
            
            if start_year > end_year:
                messagebox.showwarning("Invalid Range", "Start year must be less than or equal to end year")
                return
            
            # Filter events
            self.filtered_timeline_events = [
                event for event in self.timeline_events 
                if event['year'] and start_year <= event['year'] <= end_year
            ]
            
            # Update displays
            self.refresh_filtered_timeline_display()
            
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid years (numbers only)")
    
    def reset_timeline_filter(self):
        """Reset timeline filter to show all events"""
        self.filtered_timeline_events = self.timeline_events.copy()
        if self.timeline_events:
            years = [event['year'] for event in self.timeline_events if event['year']]
            if years:
                self.start_year_var.set(str(min(years)))
                self.end_year_var.set(str(max(years)))
        self.refresh_filtered_timeline_display()
    
    def refresh_filtered_timeline_display(self):
        """Refresh timeline display with filtered events"""
        # Clear existing items
        for item in self.timeline_tree.get_children():
            self.timeline_tree.delete(item)
        
        events_to_show = self.filtered_timeline_events if self.filtered_timeline_events else self.timeline_events
        
        if not events_to_show:
            self.timeline_tree.insert('', 'end', text="No events in range", values=['', '', '', 'Adjust date range'])
        else:
            # Add filtered timeline events
            for event in events_to_show:
                self.timeline_tree.insert('', 'end', 
                                         text=event['date_text'],
                                         values=[event['year'], f"{event['confidence']:.2f}", 
                                               event['type'], event['filename']])
        
        # Update statistics with filtered data
        self.update_filtered_timeline_statistics()
    
    def update_filtered_timeline_statistics(self):
        """Update timeline statistics with filtered data"""
        events_to_analyze = self.filtered_timeline_events if self.filtered_timeline_events else self.timeline_events
        
        self.timeline_stats_text.config(state=tk.NORMAL)
        self.timeline_stats_text.delete(1.0, tk.END)
        
        if not events_to_analyze:
            self.timeline_stats_text.insert(tk.END, "No timeline events in selected range")
            self.timeline_stats_text.config(state=tk.DISABLED)
            return
        
        stats = self.timeline_extractor.get_timeline_statistics(events_to_analyze)
        
        report = f"FILTERED TIMELINE STATISTICS\n"
        report += f"=" * 30 + "\n\n"
        report += f"Events in Range: {len(events_to_analyze)}\n"
        report += f"Total Events: {len(self.timeline_events)}\n"
        report += f"Unique Years: {stats['unique_years']}\n"
        report += f"Year Range: {stats['year_range'][0]} - {stats['year_range'][1]}\n\n"
        
        report += f"TOP DECADES:\n"
        for decade, count in sorted(stats['decades'].items(), key=lambda x: x[1], reverse=True)[:5]:
            report += f"  {decade}s: {count} events\n"
        
        report += f"\nMOST REFERENCED YEARS:\n"
        for year, count in stats['most_common_years'][:10]:
            report += f"  {year}: {count} documents\n"
        
        self.timeline_stats_text.insert(1.0, report)
        self.timeline_stats_text.config(state=tk.DISABLED)
    
    def show_timeline_chart(self):
        """Show interactive timeline chart"""
        events_to_chart = self.filtered_timeline_events if self.filtered_timeline_events else self.timeline_events
        
        if not events_to_chart:
            messagebox.showwarning("No Timeline", "Extract timeline first or adjust date range")
            return
        
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Matplotlib Required", "Install matplotlib: pip install matplotlib")
            return
        
        # Clear existing visualization
        for widget in self.timeline_viz_frame.winfo_children():
            widget.destroy()
        
        # Create timeline chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extract years and document counts from filtered events
        years = [event['year'] for event in events_to_chart if event['year']]
        if not years:
            ttk.Label(self.timeline_viz_frame, text="No valid years found in timeline").pack(expand=True)
            return
        
        # Create scatter plot
        from collections import Counter
        year_counts = Counter(years)
        x_vals = list(year_counts.keys())
        y_vals = list(year_counts.values())
        
        ax.scatter(x_vals, y_vals, alpha=0.7, s=100)
        ax.set_xlabel('Year')
        ax.set_ylabel('Number of Documents')
        ax.set_title('Document Timeline')
        ax.grid(True, alpha=0.3)
        
        # Add labels for significant points
        for x, y in zip(x_vals, y_vals):
            if y > 1:
                ax.annotate(f'{y} docs', (x, y), xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.timeline_viz_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def show_document_frequency(self):
        """Show document frequency histogram"""
        events_to_chart = self.filtered_timeline_events if self.filtered_timeline_events else self.timeline_events
        
        if not events_to_chart:
            messagebox.showwarning("No Timeline", "Extract timeline first or adjust date range")
            return
        
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Matplotlib Required", "Install matplotlib: pip install matplotlib")
            return
        
        # Clear existing visualization
        for widget in self.timeline_viz_frame.winfo_children():
            widget.destroy()
        
        # Create frequency histogram
        fig, ax = plt.subplots(figsize=(10, 6))
        
        years = [event['year'] for event in events_to_chart if event['year']]
        if not years:
            ttk.Label(self.timeline_viz_frame, text="No valid years found in timeline").pack(expand=True)
            return
        
        # Create histogram by decade
        decades = [(year // 10) * 10 for year in years]
        from collections import Counter
        decade_counts = Counter(decades)
        
        x_vals = sorted(decade_counts.keys())
        y_vals = [decade_counts[x] for x in x_vals]
        
        bars = ax.bar(x_vals, y_vals, width=8, alpha=0.7)
        ax.set_xlabel('Decade')
        ax.set_ylabel('Number of Documents')
        ax.set_title('Document Frequency by Decade')
        
        # Add value labels on bars
        for bar, val in zip(bars, y_vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                   str(val), ha='center', va='bottom')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.timeline_viz_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def extract_timeline(self):
        """Extract timeline from documents"""
        ocr_source = self.timeline_ocr_var.get()
        
        def timeline_worker():
            try:
                # Update GUI on main thread
                self.root.after(0, lambda: self.status_var.set("Extracting timeline from documents..."))
                self.root.after(0, lambda: self.log_activity("Started timeline extraction"))
                
                # Use selected files or all files
                files_to_process = self.ledger.df
                if self.selected_timeline_files:
                    files_to_process = self.ledger.df[self.ledger.df['file_id'].isin(self.selected_timeline_files)]
                
                # Extract timeline
                self.timeline_events = self.timeline_extractor.extract_timeline_from_ledger(files_to_process, ocr_source)
                
                if not self.timeline_events:
                    self.root.after(0, lambda: self.status_var.set("No timeline events found"))
                    self.root.after(0, lambda: messagebox.showinfo("No Timeline", "No dates or temporal references found in documents"))
                    return
                
                self.root.after(0, lambda: self.log_activity(f"Found {len(self.timeline_events)} timeline events"))
                self.root.after(0, lambda: self.status_var.set(f"Timeline extraction completed - {len(self.timeline_events)} events found"))
                
                # Update display
                self.root.after(0, self.refresh_timeline_display)
                
            except Exception as e:
                self.root.after(0, lambda: self.log_activity(f"Timeline extraction error: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set(f"Timeline extraction failed: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Timeline Error", str(e)))
        
        self.progress.start()
        threading.Thread(target=timeline_worker, daemon=True).start()
    
    def refresh_timeline_display(self):
        """Refresh timeline display with results"""
        # Clear existing items
        for item in self.timeline_tree.get_children():
            self.timeline_tree.delete(item)
        
        if not self.timeline_events:
            self.timeline_tree.insert('', 'end', text="No events", values=['', '', '', 'Extract timeline first'])
        else:
            # Add timeline events
            for event in self.timeline_events:
                self.timeline_tree.insert('', 'end', 
                                         text=event['date_text'],
                                         values=[event['year'], f"{event['confidence']:.2f}", 
                                               event['type'], event['filename']])
        
        # Update statistics
        self.update_timeline_statistics()
        self.progress.stop()
        
        # Show date range controls if we have events with years
        if self.timeline_events:
            years = [event['year'] for event in self.timeline_events if event['year']]
            if years:
                self.date_range_frame.pack(fill=tk.X, pady=2)
                # Set default range to full span
                self.start_year_var.set(str(min(years)))
                self.end_year_var.set(str(max(years)))
                # Initialize filtered events to all events
                self.filtered_timeline_events = self.timeline_events.copy()
    
    def update_timeline_statistics(self):
        """Update timeline statistics display"""
        self.timeline_stats_text.config(state=tk.NORMAL)
        self.timeline_stats_text.delete(1.0, tk.END)
        
        if not self.timeline_events:
            self.timeline_stats_text.insert(tk.END, "No timeline events to analyze")
            self.timeline_stats_text.config(state=tk.DISABLED)
            return
        
        stats = self.timeline_extractor.get_timeline_statistics(self.timeline_events)
        
        report = f"TIMELINE STATISTICS\n"
        report += f"=" * 30 + "\n\n"
        report += f"Total Events: {stats['total_events']}\n"
        report += f"Unique Years: {stats['unique_years']}\n"
        report += f"Year Range: {stats['year_range'][0]} - {stats['year_range'][1]}\n\n"
        
        report += f"TOP DECADES:\n"
        for decade, count in sorted(stats['decades'].items(), key=lambda x: x[1], reverse=True)[:5]:
            report += f"  {decade}s: {count} events\n"
        
        report += f"\nMOST REFERENCED YEARS:\n"
        for year, count in stats['most_common_years'][:10]:
            report += f"  {year}: {count} documents\n"
        
        self.timeline_stats_text.insert(1.0, report)
        self.timeline_stats_text.config(state=tk.DISABLED)
    
    def export_timeline_data(self):
        """Export timeline data"""
        if not self.timeline_events:
            messagebox.showwarning("No Data", "Extract timeline first before exporting")
            return
        
        from tkinter import filedialog
        
        filepath = filedialog.asksaveasfilename(
            title="Export Timeline",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("TimelineJS", "*.json")]
        )
        
        if filepath:
            try:
                if 'timelinejs' in filepath.lower():
                    format_type = 'timeline_js'
                elif filepath.endswith('.json'):
                    format_type = 'json'
                else:
                    format_type = 'csv'
                
                base_path = filepath.rsplit('.', 1)[0]
                self.timeline_extractor.export_timeline(self.timeline_events, base_path, format_type)
                messagebox.showinfo("Export Complete", f"Timeline exported to {base_path}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export timeline: {e}")
    
    def setup_geographic_analysis(self, parent_frame):
        """Setup geographic analysis interface"""
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(2, weight=1)
        
        # Add explanation header
        info_frame = ttk.LabelFrame(parent_frame, text="🌍 Geographic Analysis Overview", padding="10")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = tk.Text(info_frame, height=3, wrap=tk.WORD, bg='#f8f8f8', font=("Arial", 9))
        info_text.pack(fill=tk.X)
        info_text.insert(1.0, 
            "Map geographic locations mentioned in your documents. Select files to analyze, choose map type (global or US), "
            "then generate interactive heat maps showing location frequency. Requires Named Entity Recognition to extract "
            "place names first. Export location data in various formats.")
        info_text.config(state=tk.DISABLED)
        
        # Controls
        controls_frame = ttk.Frame(parent_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # First row of controls
        controls_row1 = ttk.Frame(controls_frame)
        controls_row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(controls_row1, text="Map Type:").pack(side=tk.LEFT, padx=5)
        self.map_type_var = tk.StringVar(value="global")
        map_combo = ttk.Combobox(controls_row1, textvariable=self.map_type_var,
                                values=["global", "us_only"], width=10)
        map_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_row1, text="📂 Select Files", command=self.select_geo_files).pack(side=tk.LEFT, padx=10)
        ttk.Button(controls_row1, text="🌍 Generate Heat Map", command=self.generate_heat_map).pack(side=tk.LEFT, padx=5)
        
        # Second row of controls
        controls_row2 = ttk.Frame(controls_frame)
        controls_row2.pack(fill=tk.X, pady=2)
        
        ttk.Button(controls_row2, text="💾 Export Locations", command=self.export_geo_data).pack(side=tk.LEFT, padx=5)
        
        # File selection status
        self.geo_selection_var = tk.StringVar(value="All files selected")
        ttk.Label(controls_frame, textvariable=self.geo_selection_var, font=("Arial", 9), foreground="blue").pack(anchor=tk.W, padx=5, pady=2)
        
        # Main paned window
        paned = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Location list
        location_list_frame = ttk.LabelFrame(paned, text="Locations Found")
        self.location_tree = ttk.Treeview(location_list_frame, columns=['count', 'coords', 'type'], show='tree headings')
        self.location_tree.heading('#0', text='Location')
        self.location_tree.heading('count', text='Count')
        self.location_tree.heading('coords', text='Coordinates')
        self.location_tree.heading('type', text='Type')
        
        self.location_tree.column('#0', width=150)
        self.location_tree.column('count', width=60)
        self.location_tree.column('coords', width=120)
        self.location_tree.column('type', width=60)
        
        location_scroll = ttk.Scrollbar(location_list_frame, orient=tk.VERTICAL, command=self.location_tree.yview)
        self.location_tree.configure(yscrollcommand=location_scroll.set)
        
        self.location_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        location_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Statistics panel
        geo_stats_frame = ttk.LabelFrame(paned, text="Geographic Statistics")
        self.geo_stats_text = tk.Text(geo_stats_frame, wrap=tk.WORD, font=("Consolas", 9), height=20)
        geo_stats_scroll = ttk.Scrollbar(geo_stats_frame, orient=tk.VERTICAL, command=self.geo_stats_text.yview)
        self.geo_stats_text.configure(yscrollcommand=geo_stats_scroll.set)
        
        self.geo_stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        geo_stats_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        paned.add(location_list_frame, weight=2)
        paned.add(geo_stats_frame, weight=1)
        
        # Store location data
        self.location_data = []
        self.selected_geo_files = []  # For subset selection
    
    def select_geo_files(self):
        """Show dialog to select subset of files for geographic analysis"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Files for Geographic Analysis")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="🌍 Select Files for Geographic Analysis", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Instructions
        inst_frame = ttk.Frame(dialog)
        inst_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(inst_frame, text="• Select multiple files with Ctrl+Click  • Check/uncheck selected files with buttons below", 
                 font=("Arial", 9), foreground="gray").pack()
        
        # File tree with archival structure
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview with archival grouping
        file_tree = ttk.Treeview(tree_frame, columns=['selected', 'filepath'], show='tree headings', selectmode='extended')
        file_tree.heading('#0', text='Archive Structure / File')
        file_tree.heading('selected', text='Selected')
        file_tree.heading('filepath', text='File Path')
        file_tree.column('#0', width=300)
        file_tree.column('selected', width=80)
        file_tree.column('filepath', width=300)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=file_tree.yview)
        file_tree.configure(yscrollcommand=scrollbar.set)
        
        file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Build archival structure
        groups = {}
        file_items = {}  # Map file_id to tree item
        
        for _, row in self.ledger.df.iterrows():
            collection, box, folder = self.parse_archival_path(row['filepath'])
            group_key = f"{collection} > {box} > {folder}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(row)
        
        # Populate tree with groups and files
        for group_key, files in groups.items():
            # Insert group header
            group_item = file_tree.insert('', 'end', 
                text=f"📁 {group_key}",
                values=['', ''],
                tags=('group',),
                open=True)
            
            # Insert files under group
            for row in files:
                file_id = row['file_id']
                is_selected = file_id in self.selected_geo_files if self.selected_geo_files else True
                
                file_item = file_tree.insert(group_item, 'end', 
                    text=row['filename'],
                    values=['✓' if is_selected else '', row['filepath']],
                    tags=('file',))
                
                file_items[file_item] = {'file_id': file_id, 'filename': row['filename'], 'selected': is_selected}
        
        # Configure styling
        file_tree.tag_configure('group', background='#e8f4fd', font=('Arial', 9, 'bold'))
        file_tree.tag_configure('file', background='white')
        
        # Control buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def check_selected():
            selected_items = file_tree.selection()
            for item in selected_items:
                if item in file_items:
                    file_items[item]['selected'] = True
                    file_tree.item(item, values=['✓', file_tree.item(item)['values'][1]])
        
        def uncheck_selected():
            selected_items = file_tree.selection()
            for item in selected_items:
                if item in file_items:
                    file_items[item]['selected'] = False
                    file_tree.item(item, values=['', file_tree.item(item)['values'][1]])
        
        def select_all_files():
            for item in file_items:
                file_items[item]['selected'] = True
                file_tree.item(item, values=['✓', file_tree.item(item)['values'][1]])
        
        def select_no_files():
            for item in file_items:
                file_items[item]['selected'] = False
                file_tree.item(item, values=['', file_tree.item(item)['values'][1]])
        
        def apply_selection():
            self.selected_geo_files = [data['file_id'] for data in file_items.values() if data['selected']]
            count = len(self.selected_geo_files)
            total = len(file_items)
            if count == total:
                self.geo_selection_var.set("All files selected")
            else:
                self.geo_selection_var.set(f"{count} of {total} files selected")
            dialog.destroy()
        
        # Button layout
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="✓ Check Selected", command=check_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="✗ Uncheck Selected", command=uncheck_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="📂 Expand All", command=lambda: self.expand_collapse_tree(file_tree, True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="📁 Collapse All", command=lambda: self.expand_collapse_tree(file_tree, False)).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_buttons, text="Select All", command=select_all_files).pack(side=tk.LEFT, padx=10)
        ttk.Button(left_buttons, text="Select None", command=select_no_files).pack(side=tk.LEFT, padx=2)
        
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="Apply", command=apply_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_buttons, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def generate_heat_map(self):
        """Generate geographic heat map"""
        try:
            from src.geo_mapper import FOLIUM_AVAILABLE
            if not FOLIUM_AVAILABLE:
                messagebox.showerror("Missing Dependencies", 
                                   "Folium not available. Install with:\npip install folium")
                return
        except ImportError:
            messagebox.showerror("Import Error", "Geographic mapping module not available")
            return
        
        map_type = self.map_type_var.get()
        
        def geo_worker():
            self.status_var.set("Extracting locations from entities...")
            self.log_activity("Started geographic analysis")
            
            try:
                # Use selected files or all files
                files_to_process = self.ledger.df
                if self.selected_geo_files:
                    files_to_process = self.ledger.df[self.ledger.df['file_id'].isin(self.selected_geo_files)]
                
                # Extract entities first
                entities_by_type = self.entity_matcher.extract_entities_from_ledger(files_to_process)
                
                if 'GPE' not in entities_by_type or not entities_by_type['GPE']:
                    self.status_var.set("No location entities found")
                    messagebox.showinfo("No Locations", "No geographic entities found. Run NER first to extract locations.")
                    return
                
                # Extract and geocode locations
                self.location_data = self.geo_mapper.extract_locations_from_entities(entities_by_type)
                
                if not self.location_data:
                    self.status_var.set("No locations could be geocoded")
                    messagebox.showinfo("No Coordinates", "Found location names but could not determine coordinates")
                    return
                
                self.log_activity(f"Geocoded {len(self.location_data)} locations")
                
                # Create heat map
                focus_us = (map_type == "us_only")
                heat_map = self.geo_mapper.create_heat_map(self.location_data, focus_us)
                
                # Save map to file
                import tempfile
                import os
                import webbrowser
                
                temp_dir = tempfile.gettempdir()
                map_file = os.path.join(temp_dir, f"codebooks_heatmap_{map_type}.html")
                heat_map.save(map_file)
                
                self.log_activity(f"Heat map saved to {map_file}")
                self.status_var.set(f"Heat map generated - opening in browser")
                
                # Open in browser
                webbrowser.open(f"file://{map_file}")
                
                # Update display
                self.root.after(0, self.refresh_geo_display)
                
            except Exception as e:
                self.log_activity(f"Geographic analysis error: {str(e)}")
                self.status_var.set(f"Geographic analysis failed: {str(e)}")
                messagebox.showerror("Geographic Error", str(e))
        
        self.progress.start()
        threading.Thread(target=geo_worker, daemon=True).start()
    
    def refresh_geo_display(self):
        """Refresh geographic display with results"""
        # Clear existing items
        for item in self.location_tree.get_children():
            self.location_tree.delete(item)
        
        if not self.location_data:
            self.location_tree.insert('', 'end', text="No locations", values=['', '', 'Generate heat map first'])
        else:
            # Count locations
            from collections import Counter
            location_counts = Counter(loc['name'] for loc in self.location_data)
            
            # Add location entries
            for location_name, count in location_counts.most_common():
                # Find first occurrence for coordinates
                loc_data = next(loc for loc in self.location_data if loc['name'] == location_name)
                coords = f"{loc_data['latitude']:.3f}, {loc_data['longitude']:.3f}"
                loc_type = "US" if loc_data['is_us'] else "International"
                
                self.location_tree.insert('', 'end', 
                                         text=location_name,
                                         values=[count, coords, loc_type])
        
        # Update statistics
        self.update_geo_statistics()
        self.progress.stop()
    
    def update_geo_statistics(self):
        """Update geographic statistics display"""
        self.geo_stats_text.config(state=tk.NORMAL)
        self.geo_stats_text.delete(1.0, tk.END)
        
        if not self.location_data:
            self.geo_stats_text.insert(tk.END, "No location data to analyze")
            self.geo_stats_text.config(state=tk.DISABLED)
            return
        
        stats = self.geo_mapper.get_location_statistics(self.location_data)
        
        report = f"GEOGRAPHIC STATISTICS\n"
        report += f"=" * 30 + "\n\n"
        report += f"Total Mentions: {stats['total_locations']}\n"
        report += f"Unique Locations: {stats['unique_locations']}\n"
        report += f"US Locations: {stats['us_locations']}\n"
        report += f"International: {stats['international_locations']}\n\n"
        
        report += f"MOST MENTIONED LOCATIONS:\n"
        for location, count in stats['most_mentioned'][:10]:
            report += f"  {location}: {count} mentions\n"
        
        report += f"\nGEOGRAPHIC SPREAD:\n"
        spread = stats['geographic_spread']
        report += f"  Latitude: {spread['min_lat']:.2f} to {spread['max_lat']:.2f}\n"
        report += f"  Longitude: {spread['min_lon']:.2f} to {spread['max_lon']:.2f}\n"
        
        self.geo_stats_text.insert(1.0, report)
        self.geo_stats_text.config(state=tk.DISABLED)
    
    def export_geo_data(self):
        """Export geographic data"""
        if not self.location_data:
            messagebox.showwarning("No Data", "Generate heat map first before exporting")
            return
        
        from tkinter import filedialog
        
        filepath = filedialog.asksaveasfilename(
            title="Export Geographic Data",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("GeoJSON files", "*.geojson")]
        )
        
        if filepath:
            try:
                if filepath.endswith('.geojson'):
                    format_type = 'geojson'
                elif filepath.endswith('.json'):
                    format_type = 'json'
                else:
                    format_type = 'csv'
                
                base_path = filepath.rsplit('.', 1)[0]
                self.geo_mapper.export_locations(self.location_data, base_path, format_type)
                messagebox.showinfo("Export Complete", f"Geographic data exported to {base_path}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export geographic data: {e}")
    
    def batch_process_files(self):
        """Batch process N files with classification, OCR, and optional NER"""
        config = self.show_batch_process_dialog()
        if not config:
            return
        
        def batch_worker():
            import time
            
            self.status_var.set(f"Batch processing {config['num_files']} files...")
            self.log_activity(f"Started batch processing {config['num_files']} files")
            
            start_time = time.time()
            processed = 0
            
            try:
                # Get files to process based on selected operations
                files_to_process = self.get_files_for_batch_processing(
                    config['num_files'], 
                    config['ocr_engines'], 
                    config['include_ner'],
                    config['skip_pdfs']
                )
                
                if files_to_process.empty:
                    self.status_var.set("No files available for batch processing")
                    messagebox.showinfo("No Files", "No files available for batch processing")
                    return
                
                total_files = len(files_to_process)
                self.log_activity(f"Processing {total_files} files")
                
                # Track updates per file
                updates_by_file = {}
                
                for _, row in files_to_process.iterrows():
                    processed += 1
                    filename = row['filename']
                    file_id = row['file_id']
                    updates_by_file[filename] = []
                    
                    # DEBUG: Log file details
                    page_num = row.get('page_number', 0)
                    parent_id = row.get('parent_id', '')
                    filepath = row['filepath']
                    self.log_activity(f"DEBUG: Processing file_id={file_id}, filename={filename}, page={page_num}, parent={parent_id}, path={filepath}")
                    
                    self.status_var.set(f"Batch: {processed}/{total_files} - {filename}")
                    
                    # Step 1: Document classification (if needed and not PDF)
                    if (row.get('document_type_status') == 'pending' and 
                        row.get('file_type', '').lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']):
                        
                        if self.prompt_processor:
                            try:
                                self.log_activity(f"Classifying {filename}")
                                doc_type = self.prompt_processor.classify_document_type(row['filepath'])
                                if doc_type.startswith('error:'):
                                    self.ledger.update_document_type(file_id, doc_type, 'error')
                                    updates_by_file[filename].append(f"document_type: error")
                                else:
                                    self.ledger.update_document_type(file_id, doc_type, 'completed')
                                    updates_by_file[filename].append(f"document_type: {doc_type}")
                            except Exception as e:
                                self.ledger.update_document_type(file_id, f"Error: {e}", 'error')
                                updates_by_file[filename].append(f"document_type: error")
                    
                    # Step 2: OCR processing
                    for engine in config['ocr_engines']:
                        if row.get(f'{engine}_status') == 'pending':
                            try:
                                page_info = f" (Page {page_num})" if page_num > 0 else ""
                                self.log_activity(f"DEBUG: Running {engine.upper()} on {filename}{page_info} [file_id={file_id}]")
                                self.log_activity(f"Running {engine.upper()} on {filename}")
                                
                                # Use callback for OpenAI OCR when batching is enabled
                                if engine == 'openai_ocr' and hasattr(self.ocr, 'batching_enabled') and self.ocr.batching_enabled:
                                    def ocr_callback(fid, result, stat):
                                        self.ledger.update_ocr_result(fid, result, stat, 'openai_ocr')
                                        
                                        # Run NER after OpenAI OCR completes if requested
                                        if config['include_ner'] and stat == 'completed':
                                            try:
                                                entities = self.ner_processor.process_text(
                                                    str(result), 
                                                    config['ner_method'],
                                                    api_key=config.get('api_key'),
                                                    model=config.get('model')
                                                )
                                                if entities:
                                                    entities_display = self.ner_processor.format_entities_for_display(entities)
                                                    self.ledger.update_named_entities(fid, entities_display)
                                                else:
                                                    self.ledger.update_named_entities(fid, "No entities found")
                                            except Exception as e:
                                                self.ledger.update_named_entities(fid, f"Error: {e}")
                                        
                                        # Run metadata generation after OpenAI OCR completes if requested
                                        if config['include_metadata'] and stat == 'completed':
                                            try:
                                                metadata_result = self.prompt_processor.generate_multi_metadata(str(result))
                                                if isinstance(metadata_result, dict) and 'error' not in metadata_result:
                                                    for field, value in metadata_result.items():
                                                        if value and value != 'null':
                                                            self.ledger.update_dublin_core_field(fid, field, value)
                                            except Exception as e:
                                                pass  # Silent fail for batch callback
                                    
                                    text, status = self.ocr.process_image(
                                        row['filepath'], 
                                        engine,
                                        callback=ocr_callback,
                                        file_id=file_id,
                                        page_number=page_num if page_num > 0 else None
                                    )
                                else:
                                    # Pass page_number for PDF pages
                                    text, status = self.ocr.process_file(row['filepath'], engine, page_number=page_num if page_num > 0 else None)
                                
                                self.ledger.update_ocr_result(file_id, text, status, engine)
                                self.log_activity(f"DEBUG: Updated ledger for file_id={file_id}, engine={engine}, status={status}, text_length={len(str(text))}")
                                updates_by_file[filename].append(f"{engine}: {status}")
                            except Exception as e:
                                self.ledger.update_ocr_result(file_id, f"Error: {e}", 'error', engine)
                                updates_by_file[filename].append(f"{engine}: error")
                    
                    # Step 3: NER processing (if requested)
                    if config['include_ner']:
                        # Check if already has NER results
                        existing_entities = str(row.get('named_entities', ''))
                        if existing_entities and existing_entities != 'nan' and existing_entities.strip():
                            self.log_activity(f"Skipping NER for {filename} - already has entities")
                        else:
                            # Use ground truth OCR or best available
                            ocr_source = self.ground_truth_engine or config['ocr_engines'][0]
                            ocr_text = row.get(f'{ocr_source}_ocr', '')
                            
                            # Check if we just processed this OCR
                            if not ocr_text or str(ocr_text) == 'nan':
                                # Refresh row data from ledger
                                self.ledger.df = self.ledger.load_or_create_ledger()  # Reload from CSV
                                updated_row = self.ledger.df[self.ledger.df['file_id'] == file_id]
                                if not updated_row.empty:
                                    ocr_text = updated_row.iloc[0].get(f'{ocr_source}_ocr', '')
                            
                            if ocr_text and str(ocr_text) != 'nan' and str(ocr_text).strip():
                                try:
                                    self.log_activity(f"Extracting entities from {filename}")
                                    entities = self.ner_processor.process_text(
                                        str(ocr_text), 
                                        config['ner_method'],
                                        api_key=config.get('api_key'),
                                        model=config.get('model')
                                    )
                                    if entities:
                                        entities_display = self.ner_processor.format_entities_for_display(entities)
                                        self.ledger.update_named_entities(file_id, entities_display)
                                        entity_count = len(entities)
                                        updates_by_file[filename].append(f"NER: {entity_count} entities extracted")
                                    else:
                                        self.ledger.update_named_entities(file_id, "No entities found")
                                        updates_by_file[filename].append(f"NER: no entities found")
                                except Exception as e:
                                    self.ledger.update_named_entities(file_id, f"Error: {e}")
                                    updates_by_file[filename].append(f"NER: error")
                    
                    # Step 4: Metadata generation (if requested)
                    if config['include_metadata']:
                        self.log_activity(f"DEBUG METADATA: Checking metadata for {filename}, page_num={page_num}, processed={processed}/{total_files}")
                        # For PDFs, defer metadata generation until end of batch
                        if page_num > 0:
                            self.log_activity(f"DEBUG METADATA: PDF page detected - deferring metadata to end of batch")
                            updates_by_file[filename].append(f"Metadata: deferred (PDF processed at end)")
                        else:
                            # Regular image file - generate metadata normally
                            self.log_activity(f"DEBUG METADATA: Regular image file - generating metadata normally")
                            ocr_source = self.ground_truth_engine or config['ocr_engines'][0]
                            ocr_text = row.get(f'{ocr_source}_ocr', '')
                            
                            if not ocr_text or str(ocr_text) == 'nan':
                                self.ledger.df = self.ledger.load_or_create_ledger()
                                updated_row = self.ledger.df[self.ledger.df['file_id'] == file_id]
                                if not updated_row.empty:
                                    ocr_text = updated_row.iloc[0].get(f'{ocr_source}_ocr', '')
                            
                            if ocr_text and str(ocr_text) != 'nan' and str(ocr_text).strip():
                                try:
                                    self.log_activity(f"Generating metadata for {filename}")
                                    result = self.prompt_processor.generate_multi_metadata(str(ocr_text))
                                    
                                    if isinstance(result, dict) and 'error' not in result:
                                        field_count = 0
                                        for field, value in result.items():
                                            if value and value != 'null':
                                                self.ledger.update_dublin_core_field(file_id, field, value)
                                                field_count += 1
                                        updates_by_file[filename].append(f"Metadata: {field_count} fields generated")
                                    else:
                                        updates_by_file[filename].append(f"Metadata: error - {result.get('error', 'unknown')}")
                                except Exception as e:
                                    updates_by_file[filename].append(f"Metadata: error - {e}")
                
                total_time = time.time() - start_time
                
                # Step 5: Generate metadata for PDFs now that OCR is complete
                if config['include_metadata']:
                    self.log_activity("\n=== GENERATING PDF METADATA ===")
                    self.status_var.set("Generating metadata for PDFs...")
                    
                    # Find all unique PDFs that were processed
                    pdf_paths = set()
                    for _, row in files_to_process.iterrows():
                        if row.get('page_number', 0) > 0:
                            pdf_paths.add(row['filepath'])
                    
                    self.log_activity(f"DEBUG METADATA: Found {len(pdf_paths)} unique PDFs to process")
                    
                    ocr_source = self.ground_truth_engine or config['ocr_engines'][0]
                    
                    for pdf_path in pdf_paths:
                        self.log_activity(f"DEBUG METADATA: Processing PDF: {pdf_path}")
                        
                        # Reload ledger to get latest OCR results
                        self.ledger.df = self.ledger.load_or_create_ledger()
                        
                        # Get first 5 pages
                        pdf_pages = self.ledger.df[
                            (self.ledger.df['filepath'] == pdf_path) & 
                            (self.ledger.df['page_number'] > 0) & 
                            (self.ledger.df['page_number'] <= 5)
                        ].sort_values('page_number')
                        
                        self.log_activity(f"DEBUG METADATA: Found {len(pdf_pages)} pages (1-5)")
                        
                        # Check OCR status
                        for idx, p in pdf_pages.iterrows():
                            ocr_text = str(p.get(f'{ocr_source}_ocr', ''))
                            ocr_status = p.get(f'{ocr_source}_status', 'unknown')
                            has_text = ocr_text not in ['', 'nan'] and len(ocr_text.strip()) > 0
                            self.log_activity(f"DEBUG METADATA:   Page {p['page_number']}: status={ocr_status}, has_text={has_text}, text_len={len(ocr_text) if has_text else 0}")
                        
                        combined_text = '\n\n'.join([
                            str(p.get(f'{ocr_source}_ocr', '')) 
                            for _, p in pdf_pages.iterrows() 
                            if str(p.get(f'{ocr_source}_ocr', '')) not in ['', 'nan']
                        ])
                        
                        self.log_activity(f"DEBUG METADATA: Combined text length: {len(combined_text)} chars")
                        
                        if combined_text.strip():
                            try:
                                self.log_activity(f"DEBUG METADATA: ✅ Generating metadata for PDF")
                                result = self.prompt_processor.generate_multi_metadata(combined_text)
                                
                                if isinstance(result, dict) and 'error' not in result:
                                    all_pdf_pages = self.ledger.df[
                                        (self.ledger.df['filepath'] == pdf_path) & 
                                        (self.ledger.df['page_number'] > 0)
                                    ]
                                    self.log_activity(f"DEBUG METADATA: Applying to {len(all_pdf_pages)} pages")
                                    
                                    field_count = 0
                                    for field, value in result.items():
                                        if value and value != 'null':
                                            for _, pdf_page in all_pdf_pages.iterrows():
                                                self.ledger.update_dublin_core_field(pdf_page['file_id'], field, value)
                                            field_count += 1
                                    
                                    self.log_activity(f"DEBUG METADATA: ✅ Applied {field_count} fields to {len(all_pdf_pages)} pages")
                                    
                                    # Update summary for first page
                                    first_page_name = f"{os.path.basename(pdf_path)} (Page 1)"
                                    if first_page_name in updates_by_file:
                                        updates_by_file[first_page_name].append(f"Metadata: {field_count} fields generated for PDF")
                                else:
                                    self.log_activity(f"DEBUG METADATA: ❌ Error: {result.get('error', 'unknown')}")
                            except Exception as e:
                                self.log_activity(f"DEBUG METADATA: ❌ Exception: {e}")
                        else:
                            self.log_activity(f"DEBUG METADATA: ❌ No OCR text available for metadata generation")
                
                # Generate summary report
                summary = f"\n=== BATCH PROCESSING SUMMARY ===\n"
                summary += f"Processed {processed} files in {int(total_time//60)}m {int(total_time%60)}s\n\n"
                summary += "Updated ledger rows:\n"
                for filename, updates in updates_by_file.items():
                    if updates:
                        summary += f"  • {filename}:\n"
                        for update in updates:
                            summary += f"    - {update}\n"
                
                self.log_activity(summary)
                self.status_var.set(f"Batch processing completed in {int(total_time//60)}m {int(total_time%60)}s")
                self.root.after(0, self.refresh_display)
                
                # Show summary dialog
                self.root.after(0, lambda: messagebox.showinfo("Batch Complete", summary))
                
            except Exception as e:
                self.log_activity(f"Batch processing error: {str(e)}")
                self.status_var.set(f"Batch processing failed: {str(e)}")
                messagebox.showerror("Batch Processing Error", str(e))
        
        self.progress.start()
        threading.Thread(target=batch_worker, daemon=True).start()
    
    def get_files_for_batch_processing(self, num_files, selected_engines=None, include_ner=False, skip_pdfs=False):
        """Get files that need processing for batch operation based on selected operations"""
        all_files = self.ledger.df
        needs_processing = []
        
        for _, row in all_files.iterrows():
            # Skip PDFs if requested
            if skip_pdfs and row.get('file_type', '').lower() == '.pdf':
                continue
            
            # Check if THIS file needs ANY of the selected operations
            file_needs_work = False
            
            # Check document classification (for images only)
            if row.get('document_type_status') == 'pending' and row.get('file_type', '').lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                file_needs_work = True
            
            # Check each selected OCR engine individually
            if selected_engines and not file_needs_work:
                for engine in selected_engines:
                    # Check if THIS specific engine is pending for THIS file
                    engine_status = row.get(f'{engine}_status', 'pending')
                    engine_text = str(row.get(f'{engine}_ocr', '') if engine != 'openai_ocr' and engine != 'ollama_ocr' else row.get(f'{engine}_ocr', ''))
                    
                    # File needs work if engine is pending OR if it has no valid text
                    if engine_status == 'pending' or not engine_text or engine_text == 'nan' or not engine_text.strip():
                        file_needs_work = True
                        break
            
            # Check NER (only if requested and has OCR available)
            if include_ner and not file_needs_work:
                entities = str(row.get('named_entities', ''))
                if not entities or entities == 'nan' or not entities.strip():
                    # Check if any OCR is available
                    has_ocr_text = any(
                        row.get(f'{engine}_status') == 'completed' and 
                        str(row.get(f'{engine}_ocr' if engine not in ['openai_ocr', 'ollama_ocr'] else f'{engine}_ocr', '')).strip() and 
                        str(row.get(f'{engine}_ocr' if engine not in ['openai_ocr', 'ollama_ocr'] else f'{engine}_ocr', '')) != 'nan'
                        for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']
                    )
                    if has_ocr_text:
                        file_needs_work = True
            
            if file_needs_work:
                needs_processing.append(row)
                if len(needs_processing) >= num_files:
                    break
        
        import pandas as pd
        return pd.DataFrame(needs_processing)
    
    def show_batch_process_dialog(self):
        """Show batch processing configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Batch Process Files")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {}
        
        ttk.Label(dialog, text="⚡ Batch Process Configuration", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Number of files
        num_frame = ttk.LabelFrame(dialog, text="Number of Files")
        num_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(num_frame, text="Process N files:").pack(side=tk.LEFT, padx=10, pady=5)
        num_var = tk.StringVar(value="10")
        ttk.Entry(num_frame, textvariable=num_var, width=10).pack(side=tk.LEFT, padx=5, pady=5)
        
        # OCR engines selection
        ocr_frame = ttk.LabelFrame(dialog, text="OCR Engines")
        ocr_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ocr_config = self.config.get_section('ocr_engines')
        ocr_vars = {}
        
        engines = [
            ('easyocr', 'EasyOCR', ocr_config.get('easyocr_enabled', True)),
            ('tesseract', 'Tesseract', ocr_config.get('tesseract_enabled', True)),
            ('pypdf2', 'PyPDF2', ocr_config.get('pypdf2_enabled', True)),
            ('pymupdf', 'PyMuPDF', True),
            ('openai_ocr', 'OpenAI OCR', ocr_config.get('openai_ocr_enabled', False)),
            ('ollama_ocr', 'Ollama OCR', ocr_config.get('ollama_ocr_enabled', False))
        ]
        
        for engine_key, engine_name, default_enabled in engines:
            var = tk.BooleanVar(value=default_enabled and engine_key in self.ocr.models)
            ocr_vars[engine_key] = var
            cb = ttk.Checkbutton(ocr_frame, text=engine_name, variable=var)
            cb.pack(anchor=tk.W, padx=10, pady=2)
            if engine_key not in self.ocr.models:
                cb.configure(state='disabled')
        
        # File Type Options
        file_type_frame = ttk.LabelFrame(dialog, text="File Type Options")
        file_type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        include_classify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(file_type_frame, text="Include document classification", variable=include_classify_var).pack(anchor=tk.W, padx=10, pady=2)
        
        skip_pdfs_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(file_type_frame, text="Skip PDFs (process images only)", variable=skip_pdfs_var).pack(anchor=tk.W, padx=10, pady=2)
        
        # NER options
        ner_frame = ttk.LabelFrame(dialog, text="Named Entity Recognition (Optional)")
        ner_frame.pack(fill=tk.X, padx=10, pady=5)
        
        include_ner_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ner_frame, text="Include NER processing", variable=include_ner_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # Metadata options
        metadata_frame = ttk.LabelFrame(dialog, text="Metadata Generation (Optional)")
        metadata_frame.pack(fill=tk.X, padx=10, pady=5)
        
        include_metadata_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(metadata_frame, text="Generate metadata (Title, Creator, Subject, Date, Description)", variable=include_metadata_var).pack(anchor=tk.W, padx=10, pady=5)
        
        ner_method_var = tk.StringVar(value="spacy")
        ttk.Radiobutton(ner_frame, text="spaCy (Local)", variable=ner_method_var, value="spacy").pack(anchor=tk.W, padx=20, pady=2)
        
        ai_config = self.config.get_section('ai_models')
        if ai_config.get('openai_enabled'):
            ttk.Radiobutton(ner_frame, text="OpenAI (Cloud)", variable=ner_method_var, value="openai").pack(anchor=tk.W, padx=20, pady=2)
        
        if ai_config.get('ollama_enabled'):
            ttk.Radiobutton(ner_frame, text="Ollama (Local)", variable=ner_method_var, value="ollama").pack(anchor=tk.W, padx=20, pady=2)
        
        def on_ok():
            try:
                num_files = int(num_var.get())
                if num_files <= 0:
                    messagebox.showwarning("Invalid Input", "Number of files must be greater than 0")
                    return
            except ValueError:
                messagebox.showwarning("Invalid Input", "Please enter a valid number")
                return
            
            selected_engines = [key for key, var in ocr_vars.items() if var.get()]
            if not selected_engines:
                messagebox.showwarning("No Engines", "Please select at least one OCR engine")
                return
            
            result['num_files'] = num_files
            result['ocr_engines'] = selected_engines
            result['include_classify'] = include_classify_var.get()
            result['skip_pdfs'] = skip_pdfs_var.get()
            result['include_ner'] = include_ner_var.get()
            result['ner_method'] = ner_method_var.get()
            result['include_metadata'] = include_metadata_var.get()
            
            if result['include_ner']:
                if result['ner_method'] == 'openai':
                    result['api_key'] = ai_config.get('openai_api_key')
                elif result['ner_method'] == 'ollama':
                    result['model'] = ai_config.get('ollama_model', 'gemma3')
            
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="▶️ Start Batch Processing", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        return result
    
    def setup_topic_modeling(self, parent_frame):
        """Setup topic modeling interface"""
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(2, weight=1)
        
        # Add explanation header
        info_frame = ttk.LabelFrame(parent_frame, text="📊 Topic Modeling Overview", padding="10")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = tk.Text(info_frame, height=3, wrap=tk.WORD, bg='#f8f8f8', font=("Arial", 9))
        info_text.pack(fill=tk.X)
        info_text.insert(1.0, 
            "Discover hidden themes and topics in your document collection using machine learning. "
            "Select OCR source, set number of topics, and choose modeling method (LDA, NMF, or BERT). "
            "View topic keywords and see which documents belong to each topic.")
        info_text.config(state=tk.DISABLED)
        
        # Controls
        controls_frame = ttk.Frame(parent_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(controls_frame, text="OCR Source:").pack(side=tk.LEFT, padx=5)
        self.topic_ocr_var = tk.StringVar(value=self.ground_truth_engine or "easyocr")
        ocr_combo = ttk.Combobox(controls_frame, textvariable=self.topic_ocr_var,
                                values=["easyocr", "tesseract", "pypdf2", "openai_ocr", "ollama_ocr"], width=12)
        ocr_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls_frame, text="Topics:").pack(side=tk.LEFT, padx=(20,5))
        self.num_topics_var = tk.StringVar(value="10")
        topics_entry = ttk.Entry(controls_frame, textvariable=self.num_topics_var, width=5)
        topics_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls_frame, text="Method:").pack(side=tk.LEFT, padx=(20,5))
        self.topic_method_var = tk.StringVar(value="lda")
        method_combo = ttk.Combobox(controls_frame, textvariable=self.topic_method_var,
                                   values=["lda", "nmf", "bert_kmeans"], width=12)
        method_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_frame, text="📊 Generate Topics", command=self.generate_topics).pack(side=tk.LEFT, padx=10)
        ttk.Button(controls_frame, text="💾 Export Results", command=self.export_topics).pack(side=tk.LEFT, padx=5)
        
        # Main paned window
        paned = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Topic list
        topic_list_frame = ttk.LabelFrame(paned, text="Topics")
        self.topic_tree = ttk.Treeview(topic_list_frame, columns=['count', 'keywords'], show='tree headings')
        self.topic_tree.heading('#0', text='Topic')
        self.topic_tree.heading('count', text='Docs')
        self.topic_tree.heading('keywords', text='Keywords')
        self.topic_tree.column('#0', width=80)
        self.topic_tree.column('count', width=60)
        self.topic_tree.column('keywords', width=300)
        
        topic_scroll = ttk.Scrollbar(topic_list_frame, orient=tk.VERTICAL, command=self.topic_tree.yview)
        self.topic_tree.configure(yscrollcommand=topic_scroll.set)
        
        self.topic_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        topic_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Document list
        doc_list_frame = ttk.LabelFrame(paned, text="Documents in Selected Topic")
        self.topic_docs_tree = ttk.Treeview(doc_list_frame, columns=['probability', 'preview'], show='headings')
        self.topic_docs_tree.heading('probability', text='Prob')
        self.topic_docs_tree.heading('preview', text='Document Preview')
        self.topic_docs_tree.column('probability', width=60)
        self.topic_docs_tree.column('preview', width=400)
        
        topic_doc_scroll = ttk.Scrollbar(doc_list_frame, orient=tk.VERTICAL, command=self.topic_docs_tree.yview)
        self.topic_docs_tree.configure(yscrollcommand=topic_doc_scroll.set)
        
        self.topic_docs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        topic_doc_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        paned.add(topic_list_frame, weight=1)
        paned.add(doc_list_frame, weight=1)
        
        # Bind selection
        self.topic_tree.bind('<<TreeviewSelect>>', self.on_topic_select)
    
    def generate_topics(self):
        """Generate topics using BERTopic"""
        try:
            from src.topic_modeler import TOPIC_MODELING_AVAILABLE
            if not TOPIC_MODELING_AVAILABLE:
                messagebox.showerror("Missing Dependencies", 
                                   "Topic modeling not available. Install with:\npip install scikit-learn sentence-transformers")
                return
        except ImportError:
            messagebox.showerror("Import Error", "Topic modeling module not available")
            return
        
        ocr_source = self.topic_ocr_var.get()
        num_topics = int(self.num_topics_var.get())
        
        def topic_worker():
            self.status_var.set("Extracting documents for topic modeling...")
            self.log_activity("Started topic modeling")
            
            try:
                # Extract documents
                documents = self.topic_modeler.extract_documents_from_ledger(self.ledger.df, ocr_source)
                
                if len(documents) < 3:
                    self.status_var.set("Not enough documents for topic modeling")
                    messagebox.showwarning("Insufficient Data", "Need at least 3 documents with OCR text for topic modeling")
                    return
                
                self.log_activity(f"Processing {len(documents)} documents")
                self.status_var.set(f"Fitting topic model with {len(documents)} documents...")
                
                # Fit model
                method = self.topic_method_var.get()
                results = self.topic_modeler.fit_model(documents, num_topics, method)
                
                self.log_activity(f"Generated {results['num_topics']} topics")
                self.status_var.set(f"Topic modeling completed - {results['num_topics']} topics found")
                
                # Update UI
                self.root.after(0, self.refresh_topic_display)
                
            except Exception as e:
                self.log_activity(f"Topic modeling error: {str(e)}")
                self.status_var.set(f"Topic modeling failed: {str(e)}")
                messagebox.showerror("Topic Modeling Error", str(e))
        
        self.progress.start()
        threading.Thread(target=topic_worker, daemon=True).start()
    
    def refresh_topic_display(self):
        """Refresh topic display with results"""
        # Clear existing items
        for item in self.topic_tree.get_children():
            self.topic_tree.delete(item)
        
        for item in self.topic_docs_tree.get_children():
            self.topic_docs_tree.delete(item)
        
        if self.topic_modeler.model is None:
            self.topic_tree.insert('', 'end', text="No topics", values=['0', 'Run topic modeling first'])
            return
        
        # Get topic summary
        topic_summary = self.topic_modeler.get_topic_summary()
        
        for topic_id, info in topic_summary.items():
            self.topic_tree.insert('', 'end', text=f"Topic {topic_id}", 
                                 values=[info['count'], info['keywords']])
        
        self.progress.stop()
    
    def on_topic_select(self, event):
        """Handle topic selection"""
        selection = self.topic_tree.selection()
        
        # Clear document list
        for item in self.topic_docs_tree.get_children():
            self.topic_docs_tree.delete(item)
        
        if not selection:
            return
        
        # Get selected topic ID
        topic_text = self.topic_tree.item(selection[0])['text']
        if not topic_text.startswith('Topic '):
            return
        
        topic_id = int(topic_text.split()[1])
        
        # Get documents for this topic
        doc_topics = self.topic_modeler.get_document_topics()
        
        for doc_topic, preview, prob in doc_topics:
            if doc_topic == topic_id:
                self.topic_docs_tree.insert('', 'end', values=[f"{prob:.3f}", preview])
    
    def export_topics(self):
        """Export topic modeling results"""
        if self.topic_modeler.model is None:
            messagebox.showwarning("No Results", "Generate topics first before exporting")
            return
        
        from tkinter import filedialog
        
        filepath = filedialog.asksaveasfilename(
            title="Export Topic Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json")]
        )
        
        if filepath:
            try:
                format_type = 'json' if filepath.endswith('.json') else 'csv'
                base_path = filepath.rsplit('.', 1)[0]
                
                self.topic_modeler.export_results(base_path, format_type)
                messagebox.showinfo("Export Complete", f"Topic results exported to {base_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def check_batch_status(self):
        """Check status of batch requests and retrieve completed results"""
        # Check if any batching is configured
        has_prompt_batching = self.prompt_processor is not None
        has_ocr_batching = hasattr(self.ocr, 'batch_manager') and self.ocr.batch_manager is not None
        
        if not has_prompt_batching and not has_ocr_batching:
            messagebox.showinfo("No Batching Configured", 
                "Batch processing is not enabled.\n\n"
                "Enable it in AI Configuration > OpenAI > Use Batch API")
            return
        
        def batch_check_worker():
            self.status_var.set("Checking batch status...")
            self.log_activity("Checking OpenAI batch status")
            
            try:
                # First, submit any pending requests
                submitted_count = 0
                if has_prompt_batching:
                    batch_id = self.prompt_processor.submit_pending_batch()
                    if batch_id:
                        submitted_count += 1
                        self.log_activity(f"Submitted prompt batch: {batch_id}")
                
                if has_ocr_batching:
                    batch_id = self.ocr.batch_manager.submit_batch(force=True)
                    if batch_id:
                        submitted_count += 1
                        self.log_activity(f"Submitted OCR batch: {batch_id}")
                
                status_msg = "BATCH STATUS REPORT\n" + "="*40 + "\n\n"
                
                if submitted_count > 0:
                    status_msg += f"📤 Submitted {submitted_count} new batch(es) to OpenAI\n\n"
                
                total_active = 0
                total_pending = 0
                completed_count = 0
                
                # Check prompt processor batches
                if has_prompt_batching:
                    statuses = self.prompt_processor.check_batch_status()
                    batch_info = self.prompt_processor.get_batch_info()
                    
                    status_msg += "📝 PROMPT PROCESSING BATCHES:\n"
                    status_msg += f"  Pending Requests: {batch_info['pending_requests']}\n"
                    status_msg += f"  Active Batches: {batch_info['active_batches']}\n"
                    
                    if statuses:
                        for batch_id, status in statuses.items():
                            status_msg += f"  • Batch {batch_id[:8]}...: {status}\n"
                            if status == 'completed':
                                completed_count += 1
                    
                    total_active += batch_info['active_batches']
                    total_pending += batch_info['pending_requests']
                    status_msg += "\n"
                
                # Check OCR batches
                if has_ocr_batching:
                    ocr_statuses = self.ocr.batch_manager.check_all_batches()
                    ocr_pending = self.ocr.batch_manager.get_pending_count()
                    ocr_active = self.ocr.batch_manager.get_active_batch_count()
                    
                    status_msg += "🔍 OCR PROCESSING BATCHES:\n"
                    status_msg += f"  Pending Requests: {ocr_pending}\n"
                    status_msg += f"  Active Batches: {ocr_active}\n"
                    
                    if ocr_statuses:
                        for batch_id, status in ocr_statuses.items():
                            status_msg += f"  • Batch {batch_id[:8]}...: {status}\n"
                            if status == 'completed':
                                completed_count += 1
                    
                    total_active += ocr_active
                    total_pending += ocr_pending
                    status_msg += "\n"
                
                # Summary
                status_msg += "="*40 + "\n"
                status_msg += f"Total Active Batches: {total_active}\n"
                status_msg += f"Total Pending Requests: {total_pending}\n"
                
                if completed_count > 0:
                    status_msg += f"\n✅ {completed_count} batch(es) completed!\n"
                    status_msg += "Results have been retrieved and added to ledger.\n"
                
                if total_active == 0 and total_pending == 0:
                    status_msg = "No active batch requests found.\n\n"
                    status_msg += "Batch requests are queued when you:\n"
                    status_msg += "• Process files with OpenAI OCR (when batching enabled)\n"
                    status_msg += "• Generate metadata with OpenAI (when batching enabled)\n"
                
                self.root.after(0, lambda: messagebox.showinfo("Batch Status", status_msg))
                self.log_activity(f"Batch check: {total_active} active, {total_pending} pending, {completed_count} completed")
                self.status_var.set("Batch status checked")
                
                # Refresh display to update any completed batches
                if completed_count > 0:
                    self.root.after(0, self.refresh_display)
                
            except Exception as e:
                self.log_activity(f"Batch check error: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror("Batch Error", f"Failed to check batch status: {e}"))
        
        threading.Thread(target=batch_check_worker, daemon=True).start()
    
    def log_activity(self, message):
        """Log activity to the activity log widget"""
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Add to activity log list (keep last 20)
        self.activity_log.append(log_entry)
        if len(self.activity_log) > 20:
            self.activity_log.pop(0)
        
        # Update text widget
        self.activity_text.config(state=tk.NORMAL)
        self.activity_text.delete(1.0, tk.END)
        self.activity_text.insert(1.0, ''.join(self.activity_log))
        self.activity_text.see(tk.END)  # Auto-scroll to bottom
        self.activity_text.config(state=tk.DISABLED)
        
        # Force UI update
        self.root.update_idletasks()
    
    def extract_named_entities(self):
        """Extract named entities from OCR text"""
        # Show configuration dialog (includes OCR source selection)
        config = self.show_ner_config_dialog()
        if not config:
            return
        
        def ner_worker():
            import time
            import json
            
            self.start_processing()
            self.status_var.set("Extracting named entities...")
            self.log_activity(f"Started NER extraction using {config['method']} from {config['ocr_source'].upper()} transcripts")
            processed = 0
            
            start_time = time.time()
            operation_times = []
            total_files = len(config['files'])
            
            for _, row in config['files'].iterrows():
                # Check for stop request
                if self.stop_requested:
                    self.log_activity("NER processing stopped by user")
                    break
                
                # Skip if already has NER results
                existing_entities = str(row.get('named_entities', ''))
                if existing_entities and existing_entities != 'nan' and existing_entities.strip() and existing_entities != 'No entities found':
                    processed += 1
                    continue
                
                op_start = time.time()
                
                # Update time estimate every row
                if operation_times:
                    avg_time = sum(operation_times) / len(operation_times)
                    remaining_ops = total_files - processed
                    est_remaining = avg_time * remaining_ops
                    est_min = int(est_remaining // 60)
                    est_sec = int(est_remaining % 60)
                    time_str = f" (Est: {est_min}m {est_sec}s remaining)"
                else:
                    time_str = ""
                
                status_msg = f"NER: {processed + 1}/{total_files} - {row['filename']}{time_str}"
                self.status_var.set(status_msg)
                self.log_activity(f"Processing NER for {row['filename']}")
                
                ocr_text = row.get(f"{config['ocr_source']}_ocr", '')
                if not ocr_text or str(ocr_text).strip() == '' or str(ocr_text) == 'nan':
                    processed += 1
                    continue
                
                try:
                    entities = self.ner_processor.process_text(
                        str(ocr_text), 
                        config['method'],
                        api_key=config.get('api_key'),
                        model=config.get('model')
                    )
                    
                    entities_display = self.ner_processor.format_entities_for_display(entities)
                    self.ledger.update_named_entities(row['file_id'], entities_display)
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    self.ledger.update_named_entities(row['file_id'], error_msg)
                    print(f"NER error: {e}")
                
                op_time = time.time() - op_start
                operation_times.append(op_time)
                self.operation_times.append(op_time)
                
                if len(operation_times) > 20:
                    operation_times.pop(0)
                if len(self.operation_times) > 50:
                    self.operation_times.pop(0)
                
                processed += 1
            
            total_time = time.time() - start_time
            if self.stop_requested:
                self.status_var.set(f"Named entity extraction stopped after {int(total_time//60)}m {int(total_time%60)}s")
            else:
                self.status_var.set(f"Named entity extraction completed in {int(total_time//60)}m {int(total_time%60)}s")
            self.root.after(0, lambda: [self.finish_processing(), self.refresh_display()])
        
        self.progress.start()
        threading.Thread(target=ner_worker, daemon=True).start()
    
    def show_ner_config_dialog(self):
        """Show NER configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Configure Named Entity Recognition")
        dialog.geometry("700x550")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {}
        
        # Header
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="🏷️ Named Entity Recognition Setup", 
                 font=("Arial", 14, "bold")).pack()
        
        # Instructions
        inst_frame = ttk.LabelFrame(dialog, text="ℹ️ About NER", padding="10")
        inst_frame.pack(fill=tk.X, padx=10, pady=5)
        
        instructions = tk.Text(inst_frame, height=3, wrap=tk.WORD, bg='#f8f8f8')
        instructions.pack(fill=tk.X)
        instructions.insert(1.0,
            "Extract named entities (people, organizations, locations, dates, etc.) from OCR transcripts.\n"
            "Choose which OCR engine's transcript to use as the source, then select an extraction method.\n"
            "💡 Tip: OpenAI OCR transcripts typically produce the best entity extraction results.")
        instructions.config(state=tk.DISABLED)
        
        # OCR Source Selection with file counts
        ocr_frame = ttk.LabelFrame(dialog, text="1️⃣ Select OCR Source Transcript", padding="10")
        ocr_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Calculate file counts for each engine
        engine_stats = {}
        for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']:
            completed = len(self.ledger.get_files_by_status(engine, 'completed'))
            engine_stats[engine] = completed
        
        # Default to ground truth if set, otherwise openai_ocr, otherwise first available
        default_ocr = self.ground_truth_engine if self.ground_truth_engine else 'openai_ocr'
        if engine_stats.get(default_ocr, 0) == 0:
            # Find first engine with files
            for engine, count in engine_stats.items():
                if count > 0:
                    default_ocr = engine
                    break
        
        ocr_var = tk.StringVar(value=default_ocr)
        
        engine_display = {
            'easyocr': '🤖 EasyOCR (AI-powered)',
            'tesseract': '📄 Tesseract (Traditional OCR)',
            'pypdf2': '📋 PyPDF2 (Direct PDF text)',
            'openai_ocr': '🤖📄 OpenAI OCR (Recommended)',
            'ollama_ocr': '🏠🤖 Ollama OCR (Local LLM)'
        }
        
        for engine in ['easyocr', 'tesseract', 'pypdf2', 'openai_ocr', 'ollama_ocr']:
            count = engine_stats.get(engine, 0)
            label = engine_display.get(engine, engine.upper())
            
            if count > 0:
                label += f" ({count} files)"
                if engine == self.ground_truth_engine:
                    label += " ⭐ Ground Truth"
                
                rb = ttk.Radiobutton(ocr_frame, text=label, 
                                    variable=ocr_var, value=engine)
                rb.pack(anchor=tk.W, pady=2)
            else:
                # Show disabled if no files
                label += " (0 files - unavailable)"
                rb = ttk.Radiobutton(ocr_frame, text=label, 
                                    variable=ocr_var, value=engine, state='disabled')
                rb.pack(anchor=tk.W, pady=2)
        
        # NER Method Selection
        method_frame = ttk.LabelFrame(dialog, text="2️⃣ Select Extraction Method", padding="10")
        method_frame.pack(fill=tk.X, padx=10, pady=5)
        
        method_var = tk.StringVar(value="spacy")
        
        ttk.Radiobutton(method_frame, text="🔍 spaCy (Local, fast, free)", 
                       variable=method_var, value="spacy").pack(anchor=tk.W, pady=2)
        ttk.Label(method_frame, text="   Best for: Quick extraction, offline processing",
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=20)
        
        ai_config = self.config.get_section('ai_models')
        if ai_config.get('openai_enabled'):
            ttk.Radiobutton(method_frame, text="🤖 OpenAI (Cloud, high accuracy, costs API credits)", 
                           variable=method_var, value="openai").pack(anchor=tk.W, pady=2)
            ttk.Label(method_frame, text="   Best for: Maximum accuracy, complex entity types",
                     font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=20)
        
        if ai_config.get('ollama_enabled'):
            ttk.Radiobutton(method_frame, text="🏠 Ollama (Local, private, free)", 
                           variable=method_var, value="ollama").pack(anchor=tk.W, pady=2)
            ttk.Label(method_frame, text="   Best for: Privacy-sensitive data, offline processing",
                     font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=20)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(dialog, text="📊 Preview", padding="10")
        preview_frame.pack(fill=tk.X, padx=10, pady=5)
        
        preview_text = tk.Text(preview_frame, height=3, wrap=tk.WORD, bg='#f0f0f0')
        preview_text.pack(fill=tk.X)
        
        def update_preview(*args):
            ocr_source = ocr_var.get()
            method = method_var.get()
            
            all_files = self.ledger.get_files_by_status(ocr_source, 'completed')
            
            # Filter out files that already have NER results
            def needs_ner(row):
                entities = str(row.get('named_entities', ''))
                return not entities or entities == 'nan' or not entities.strip()
            
            files_needing_ner = all_files[all_files.apply(needs_ner, axis=1)] if not all_files.empty else all_files
            
            preview_text.config(state=tk.NORMAL)
            preview_text.delete(1.0, tk.END)
            
            if all_files.empty:
                preview_text.insert(1.0, f"❌ No files with completed {ocr_source.upper()} found.\nPlease select a different OCR source.")
            elif files_needing_ner.empty:
                preview_text.insert(1.0, f"✅ All {len(all_files)} files already have NER results.\nNo processing needed.")
            else:
                preview_text.insert(1.0, 
                    f"📄 Found {len(files_needing_ner)} files ready for NER extraction\n"
                    f"📊 Source: {ocr_source.upper()} transcripts\n"
                    f"🔧 Method: {method.upper()}")
            
            preview_text.config(state=tk.DISABLED)
        
        # Bind updates
        ocr_var.trace_add('write', update_preview)
        method_var.trace_add('write', update_preview)
        
        # Initial preview
        dialog.after(100, update_preview)
        
        def on_ok():
            ocr_source = ocr_var.get()
            method = method_var.get()
            
            # Get files with completed OCR that don't have NER yet
            all_files = self.ledger.get_files_by_status(ocr_source, 'completed')
            
            if all_files.empty:
                messagebox.showwarning("No Files", 
                    f"No files with completed {ocr_source.upper()} found.\n\n"
                    f"Please run {ocr_source.upper()} first or select a different OCR source.")
                return
            
            # Filter out files that already have NER results
            def needs_ner(row):
                entities = str(row.get('named_entities', ''))
                return not entities or entities == 'nan' or not entities.strip()
            
            files = all_files[all_files.apply(needs_ner, axis=1)]
            
            if files.empty:
                choice = messagebox.askyesno("NER Complete", 
                    f"All {len(all_files)} files with {ocr_source.upper()} already have NER results.\n\n"
                    f"Would you like to re-extract entities (overwrite existing)?")
                
                if choice:
                    files = all_files
                else:
                    return
            
            result['ocr_source'] = ocr_source
            result['method'] = method
            result['files'] = files
            
            if method == 'openai':
                result['api_key'] = ai_config.get('openai_api_key')
            elif method == 'ollama':
                result['model'] = ai_config.get('ollama_model', 'gemma3')
            
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="▶️ Start Extraction", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        return result
    
    def setup_entity_browser(self, parent_frame):
        """Setup entity browser interface"""
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(2, weight=1)
        
        # Add explanation header
        info_frame = ttk.LabelFrame(parent_frame, text="🏷️ Entity Browser Overview", padding="10")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = tk.Text(info_frame, height=3, wrap=tk.WORD, bg='#f8f8f8', font=("Arial", 9))
        info_text.pack(fill=tk.X)
        info_text.insert(1.0, 
            "Browse and manage named entities (people, organizations, places) extracted from your documents. "
            "Select entity types, merge similar entities, and get AI explanations of their historical significance. "
            "Requires Named Entity Recognition (NER) to be run first.")
        info_text.config(state=tk.DISABLED)
        
        # Controls
        controls_frame = ttk.Frame(parent_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(controls_frame, text="Entity Type:").pack(side=tk.LEFT, padx=5)
        self.entity_type_var = tk.StringVar(value="ORG")
        entity_combo = ttk.Combobox(controls_frame, textvariable=self.entity_type_var, 
                                   values=["PERSON", "ORG", "GPE", "DATE", "MONEY", "EVENT", "FAC", "PRODUCT"], width=12)
        entity_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_frame, text="🔍 Find & Merge Similar", command=self.find_similar_entities).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="🔗 Merge Selected", command=self.merge_selected_entities).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="🧠 Explain Entity", command=self.explain_selected_entity).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="⚙️ Settings", command=self.show_matching_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="🔄 Refresh", command=self.refresh_entity_browser).pack(side=tk.LEFT, padx=5)
        
        # Main paned window
        paned = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Entity list
        entity_list_frame = ttk.LabelFrame(paned, text="Entities")
        self.entity_tree = ttk.Treeview(entity_list_frame, columns=['count', 'alt_names'], show='tree headings', selectmode='extended')
        self.entity_tree.heading('#0', text='Entity')
        self.entity_tree.heading('count', text='Count')
        self.entity_tree.heading('alt_names', text='Alternative Names')
        self.entity_tree.column('count', width=60)
        self.entity_tree.column('alt_names', width=200)
        
        entity_scroll = ttk.Scrollbar(entity_list_frame, orient=tk.VERTICAL, command=self.entity_tree.yview)
        self.entity_tree.configure(yscrollcommand=entity_scroll.set)
        
        self.entity_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        entity_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Document list
        doc_list_frame = ttk.LabelFrame(paned, text="Documents Containing Selected Entity")
        self.entity_docs_tree = ttk.Treeview(doc_list_frame, columns=['filename'], show='headings')
        self.entity_docs_tree.heading('filename', text='Filename')
        
        doc_scroll = ttk.Scrollbar(doc_list_frame, orient=tk.VERTICAL, command=self.entity_docs_tree.yview)
        self.entity_docs_tree.configure(yscrollcommand=doc_scroll.set)
        
        self.entity_docs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        doc_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        paned.add(entity_list_frame, weight=1)
        paned.add(doc_list_frame, weight=1)
        
        # Bind selection and double-click
        self.entity_tree.bind('<<TreeviewSelect>>', self.on_entity_select)
        self.entity_docs_tree.bind('<Double-1>', self.on_entity_doc_double_click)
        entity_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_entity_browser())
        
        # Auto-refresh on tab creation
        parent_frame.after(100, self.refresh_entity_browser)
    
    def refresh_entity_browser(self):
        """Refresh entity browser with current data"""
        try:
            # Debug: Check if we have any named entities data
            has_entities = False
            for _, row in self.ledger.df.iterrows():
                entities_text = str(row.get('named_entities', ''))
                if entities_text and entities_text != 'nan' and entities_text.strip() and entities_text != 'No entities found':
                    has_entities = True
                    print(f"Found entities in {row['filename']}: {entities_text[:100]}...")
                    break
            
            if not has_entities:
                # Clear existing items
                for item in self.entity_tree.get_children():
                    self.entity_tree.delete(item)
                self.entity_tree.insert('', 'end', text="No entities extracted yet - run NER first", values=['0'])
                return
            
            entities_by_type = self.entity_matcher.extract_entities_from_ledger(self.ledger.df)
            stats = self.entity_matcher.get_entity_statistics(entities_by_type)
            
            # Clear existing items
            for item in self.entity_tree.get_children():
                self.entity_tree.delete(item)
            
            # Clear document list when refreshing
            for item in self.entity_docs_tree.get_children():
                self.entity_docs_tree.delete(item)
            self.entity_docs_tree.insert('', 'end', values=["← Select an entity to see documents"])
            
            selected_type = self.entity_type_var.get()
            if selected_type in stats and stats[selected_type]['entities']:
                # Sort entities by count (descending)
                sorted_entities = sorted(stats[selected_type]['entities'].items(), 
                                       key=lambda x: len(x[1]), reverse=True)
                for entity_text, occurrences in sorted_entities:
                    # Check for alternative names (stored in entity metadata)
                    alt_names = getattr(self, 'entity_alt_names', {}).get(entity_text, '')
                    self.entity_tree.insert('', 'end', text=entity_text, values=[len(occurrences), alt_names])
            else:
                # Show message if no entities found
                self.entity_tree.insert('', 'end', text=f"No {selected_type} entities found", values=['0', ''])
        except Exception as e:
            print(f"Entity browser refresh error: {e}")
            # Clear existing items
            for item in self.entity_tree.get_children():
                self.entity_tree.delete(item)
            self.entity_tree.insert('', 'end', text=f"Error: {str(e)}", values=['0'])
    
    def on_entity_select(self, event):
        """Handle entity selection"""
        selection = self.entity_tree.selection()
        
        # Clear document list
        for item in self.entity_docs_tree.get_children():
            self.entity_docs_tree.delete(item)
        
        if not selection:
            self.entity_docs_tree.insert('', 'end', values=["← Select an entity to see documents"])
            return
        
        entity_text = self.entity_tree.item(selection[0])['text']
        
        # Skip if it's a status message
        if entity_text.startswith('No ') or entity_text.startswith('Error'):
            return
        
        # Find documents containing this entity
        found_docs = []
        for _, row in self.ledger.df.iterrows():
            entities_text = str(row.get('named_entities', ''))
            if entity_text in entities_text:
                found_docs.append(row['filename'])
        
        if found_docs:
            for filename in found_docs:
                self.entity_docs_tree.insert('', 'end', values=[filename])
        else:
            self.entity_docs_tree.insert('', 'end', values=["No documents found"])
    
    def on_entity_doc_double_click(self, event):
        """Handle double-click on entity document to open OCR viewer"""
        selection = self.entity_docs_tree.selection()
        if not selection:
            return
        
        item = self.entity_docs_tree.item(selection[0])
        filename = item['values'][0]
        
        # Skip if it's a status message
        if filename in ["No documents found", "← Select an entity to see documents"]:
            return
        
        # Find the file in the ledger and open OCR viewer
        matching_rows = self.ledger.df[self.ledger.df['filename'] == filename]
        if not matching_rows.empty:
            filepath = matching_rows.iloc[0]['filepath']
            self.on_tree_double_click(None, filepath=filepath)
    
    def show_matching_settings(self):
        """Show entity matching configuration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Entity Matching Settings")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="🔧 Entity Matching Settings", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Similarity threshold
        threshold_frame = ttk.LabelFrame(dialog, text="Similarity Threshold")
        threshold_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(threshold_frame, text="Minimum similarity (0.0-1.0):").pack(anchor=tk.W, padx=10, pady=5)
        threshold_var = tk.StringVar(value=str(self.entity_matcher.similarity_threshold))
        ttk.Entry(threshold_frame, textvariable=threshold_var, width=10).pack(anchor=tk.W, padx=10, pady=2)
        
        ttk.Label(threshold_frame, text="Higher = stricter (0.85 recommended for people)", 
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=10)
        
        def apply_settings():
            try:
                new_threshold = float(threshold_var.get())
                if 0.0 <= new_threshold <= 1.0:
                    self.entity_matcher.similarity_threshold = new_threshold
                    messagebox.showinfo("Applied", f"Similarity threshold: {new_threshold}")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Must be between 0.0 and 1.0")
            except ValueError:
                messagebox.showerror("Error", "Enter a valid number")
        
        ttk.Button(dialog, text="✅ Apply", command=apply_settings).pack(pady=20)
        ttk.Button(dialog, text="❌ Cancel", command=dialog.destroy).pack()
    
    def merge_selected_entities(self):
        """Merge selected entities directly"""
        selected_items = self.entity_tree.selection()
        if len(selected_items) < 2:
            messagebox.showwarning("Selection Required", "Please select 2 or more entities to merge")
            return
        
        # Get selected entity names
        selected_entities = []
        for item in selected_items:
            entity_name = self.entity_tree.item(item)['text']
            if not entity_name.startswith('No '):
                selected_entities.append(entity_name)
        
        if len(selected_entities) < 2:
            messagebox.showwarning("Invalid Selection", "Please select valid entities to merge")
            return
        
        # Show merge dialog
        self.show_merge_dialog(selected_entities)
    
    def show_merge_dialog(self, entities):
        """Show dialog to configure entity merge"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Merge Entities")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="🔗 Merge Entities", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Primary entity selection
        primary_frame = ttk.LabelFrame(dialog, text="Select Primary Entity")
        primary_frame.pack(fill=tk.X, padx=10, pady=5)
        
        primary_var = tk.StringVar(value=entities[0])
        for entity in entities:
            ttk.Radiobutton(primary_frame, text=entity, variable=primary_var, value=entity).pack(anchor=tk.W, padx=10, pady=2)
        
        # Alternative names preview
        alt_frame = ttk.LabelFrame(dialog, text="Alternative Names (will be merged)")
        alt_frame.pack(fill=tk.X, padx=10, pady=5)
        
        alt_text = tk.Text(alt_frame, height=4, wrap=tk.WORD)
        alt_text.pack(fill=tk.X, padx=10, pady=5)
        alt_text.insert(1.0, ', '.join([e for e in entities if e != entities[0]]))
        
        def perform_merge():
            primary_entity = primary_var.get()
            alt_entities = [e for e in entities if e != primary_entity]
            
            # Store alternative names
            if not hasattr(self, 'entity_alt_names'):
                self.entity_alt_names = {}
            
            existing_alts = self.entity_alt_names.get(primary_entity, '')
            new_alts = ', '.join(alt_entities)
            if existing_alts:
                self.entity_alt_names[primary_entity] = f"{existing_alts}, {new_alts}"
            else:
                self.entity_alt_names[primary_entity] = new_alts
            
            # Update ledger entries
            self.apply_direct_entity_merge(primary_entity, alt_entities)
            
            messagebox.showinfo("Merge Complete", f"Merged {len(alt_entities)} entities into '{primary_entity}'")
            dialog.destroy()
            self.refresh_entity_browser()
        
        ttk.Button(dialog, text="✅ Merge", command=perform_merge).pack(pady=20)
        ttk.Button(dialog, text="❌ Cancel", command=dialog.destroy).pack()
    
    def explain_selected_entity(self):
        """Explain selected entity using AI"""
        selected_items = self.entity_tree.selection()
        if len(selected_items) != 1:
            messagebox.showwarning("Selection Required", "Please select exactly one entity to explain")
            return
        
        if not self.prompt_processor:
            messagebox.showwarning("AI Required", "Please configure AI models first")
            return
        
        entity_name = self.entity_tree.item(selected_items[0])['text']
        if entity_name.startswith('No '):
            return
        
        # Get OCR samples containing this entity
        ocr_samples = self.get_entity_ocr_samples(entity_name)
        if not ocr_samples:
            messagebox.showinfo("No Context", f"No OCR text found containing '{entity_name}'")
            return
        
        # Show explanation dialog
        self.show_entity_explanation_dialog(entity_name, ocr_samples)
    
    def get_entity_ocr_samples(self, entity_name, max_samples=5):
        """Get OCR text samples containing the entity"""
        samples = []
        ocr_source = self.ground_truth_engine or 'easyocr'
        
        for _, row in self.ledger.df.iterrows():
            entities_text = str(row.get('named_entities', ''))
            if entity_name in entities_text:
                ocr_text = str(row.get(f'{ocr_source}_ocr', '') or '')
                if ocr_text and ocr_text != 'nan' and entity_name.lower() in ocr_text.lower():
                    # Extract context around entity mention
                    words = ocr_text.split()
                    entity_words = entity_name.split()
                    
                    for i, word in enumerate(words):
                        if any(ew.lower() in word.lower() for ew in entity_words):
                            start = max(0, i-20)
                            end = min(len(words), i+20)
                            context = ' '.join(words[start:end])
                            samples.append({
                                'filename': row['filename'],
                                'context': context
                            })
                            break
                
                if len(samples) >= max_samples:
                    break
        
        return samples
    
    def show_entity_explanation_dialog(self, entity_name, ocr_samples):
        """Show AI explanation of entity"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Entity Analysis: {entity_name}")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text=f"🧠 AI Analysis: {entity_name}", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Create analysis text widget
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        analysis_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 9))
        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=analysis_text.yview)
        analysis_text.configure(yscrollcommand=scroll.set)
        
        analysis_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        analysis_text.insert(1.0, "Analyzing entity with AI...\n\nPlease wait...")
        
        def analyze_entity():
            try:
                # Prepare context for AI
                context_text = f"Entity: {entity_name}\n\nContext samples:\n"
                for i, sample in enumerate(ocr_samples, 1):
                    context_text += f"\n{i}. From {sample['filename']}:\n{sample['context']}\n"
                
                # Generate AI explanation with new document-focused prompt
                prompt = f"""Analyze this historical entity based on specific evidence from the archival documents provided. Focus on what the documents actually say rather than general historical knowledge.

Entity: {entity_name}

Document Evidence:
{context_text}

Please provide a document-focused analysis with specific citations:

1. DOCUMENTARY EVIDENCE: What do these specific documents tell us about {entity_name}? Quote key phrases and cite which documents they come from.

2. ROLES & ACTIVITIES: Based solely on these documents, what roles or activities is {entity_name} involved in? Reference specific documents for each claim.

3. RELATIONSHIPS & CONNECTIONS: What relationships or connections are mentioned in these documents? Cite the specific document for each relationship.

4. CHRONOLOGICAL CONTEXT: What dates or time periods are mentioned in relation to {entity_name} in these documents? List document sources.

5. RESEARCH RECOMMENDATIONS: Which of these specific documents contain the most information about {entity_name}? Rank them by relevance and explain why each is important.

Focus on evidence-based analysis using only what appears in these archival documents. Cite specific document names for every claim. Avoid general historical commentary not supported by the provided evidence."""
                
                # Use the existing generate method
                if self.prompt_processor.model_type == "openai":
                    explanation = self.prompt_processor._generate_openai(prompt)
                elif self.prompt_processor.model_type == "ollama":
                    explanation = self.prompt_processor._generate_ollama(prompt)
                else:
                    explanation = "Error: Unknown AI model type"
                
                # Update dialog
                analysis_text.delete(1.0, tk.END)
                analysis_text.insert(1.0, explanation)
                
            except Exception as e:
                analysis_text.delete(1.0, tk.END)
                analysis_text.insert(1.0, f"Error generating explanation: {str(e)}")
        
        # Start analysis in background
        threading.Thread(target=analyze_entity, daemon=True).start()
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def apply_direct_entity_merge(self, primary_entity, alt_entities):
        """Apply direct entity merge to ledger"""
        for alt_entity in alt_entities:
            # Update all occurrences in ledger
            for idx, row in self.ledger.df.iterrows():
                entities_text = str(row.get('named_entities', ''))
                if alt_entity in entities_text:
                    updated_entities = entities_text.replace(alt_entity, primary_entity)
                    self.ledger.df.at[idx, 'named_entities'] = updated_entities
        
        self.ledger.save_ledger()
    
    def expand_collapse_tree(self, tree_widget, expand=True):
        """Expand or collapse all items in a treeview"""
        def process_item(item):
            if expand:
                tree_widget.item(item, open=True)
            else:
                tree_widget.item(item, open=False)
            
            # Process children recursively
            for child in tree_widget.get_children(item):
                process_item(child)
        
        # Process all top-level items
        for item in tree_widget.get_children():
            process_item(item)
    
    def find_similar_entities(self):
        """Find and group similar entities"""
        entities_by_type = self.entity_matcher.extract_entities_from_ledger(self.ledger.df)
        selected_type = self.entity_type_var.get()
        
        if selected_type not in entities_by_type:
            messagebox.showinfo("No Entities", f"No {selected_type} entities found")
            return
        
        # Increase threshold for person matching to reduce false positives
        original_threshold = self.entity_matcher.similarity_threshold
        if selected_type == 'PERSON':
            self.entity_matcher.similarity_threshold = 0.85
        
        similar_groups = self.entity_matcher.find_similar_entities(
            entities_by_type[selected_type], selected_type)
        
        # Restore original threshold
        self.entity_matcher.similarity_threshold = original_threshold
        
        if not similar_groups:
            messagebox.showinfo("No Matches", "No similar entities found")
            return
        
        self.show_similar_entities_dialog(similar_groups, selected_type)
    
    def show_similar_entities_dialog(self, similar_groups, entity_type):
        """Show dialog with similar entity groups for approval - one group at a time"""
        if not similar_groups:
            return
        
        self.current_group_index = 0
        self.approved_merges = []
        
        def show_next_group():
            if self.current_group_index >= len(similar_groups):
                # All groups processed, apply merges
                if self.approved_merges:
                    self.apply_entity_merges(self.approved_merges, entity_type)
                    messagebox.showinfo("Merges Applied", f"Applied {len(self.approved_merges)} entity merges")
                    self.refresh_entity_browser()
                else:
                    messagebox.showinfo("No Merges", "No merges were approved")
                return
            
            group = similar_groups[self.current_group_index]
            
            dialog = tk.Toplevel(self.root)
            dialog.title(f"Merge {entity_type} Entities - Group {self.current_group_index + 1} of {len(similar_groups)}")
            dialog.geometry("1000x700")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Header
            header_frame = ttk.Frame(dialog)
            header_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Label(header_frame, text=f"🔍 Similar {entity_type} Entities Found", 
                     font=("Arial", 14, "bold")).pack()
            ttk.Label(header_frame, text=f"Group {self.current_group_index + 1} of {len(similar_groups)}", 
                     font=("Arial", 10), foreground="gray").pack()
            
            # Instructions
            inst_frame = ttk.LabelFrame(dialog, text="Instructions", padding="10")
            inst_frame.pack(fill=tk.X, padx=10, pady=5)
            
            instructions = tk.Text(inst_frame, height=3, wrap=tk.WORD, bg='#f8f8f8')
            instructions.pack(fill=tk.X)
            instructions.insert(1.0, 
                "✅ Check entities you want to merge together\n"
                "❌ Uncheck entities to exclude from merge\n"
                "📝 Selected entities will be merged into the first checked item")
            instructions.config(state=tk.DISABLED)
            
            # Main content with paned window
            main_paned = ttk.PanedWindow(dialog, orient=tk.HORIZONTAL)
            main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Left panel: Entity selection
            left_panel = ttk.LabelFrame(main_paned, text="Select Entities to Merge", padding="10")
            
            entity_vars = []
            canonical_var = tk.StringVar(value=group[0]['text'])  # Default to first entity
            
            for i, entity in enumerate(group):
                entity_frame = ttk.Frame(left_panel)
                entity_frame.pack(fill=tk.X, pady=2)
                
                # Checkbox for inclusion
                var = tk.BooleanVar(value=True)
                entity_vars.append((var, entity))
                
                cb = ttk.Checkbutton(entity_frame, variable=var)
                cb.pack(side=tk.LEFT)
                
                # Radio button for canonical name
                ttk.Radiobutton(entity_frame, text=f"{entity['text']} (in {entity['filename']})", 
                               variable=canonical_var, value=entity['text']).pack(side=tk.LEFT, padx=(5, 0))
                
                # View document button
                ttk.Button(entity_frame, text="👁️ View", 
                          command=lambda e=entity: self.view_entity_document(e)).pack(side=tk.RIGHT, padx=5)
            
            main_paned.add(left_panel, weight=1)
            
            # Right panel: Document preview
            preview_panel = ttk.LabelFrame(main_paned, text="Document Preview", padding="5")
            
            # Preview controls
            preview_controls = ttk.Frame(preview_panel)
            preview_controls.pack(fill=tk.X, pady=(0, 5))
            
            ttk.Label(preview_controls, text="Click 'View' buttons to see documents", 
                     font=("Arial", 9), foreground="gray").pack()
            
            # Preview area
            self.preview_frame = ttk.Frame(preview_panel)
            self.preview_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(self.preview_frame, text="📄 Document preview will appear here", 
                     font=("Arial", 12), foreground="gray").pack(expand=True)
            
            main_paned.add(preview_panel, weight=1)
            
            # Canonical name selection (move to bottom)
            canonical_frame = ttk.LabelFrame(dialog, text="Canonical Name", padding="10")
            canonical_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(canonical_frame, text="Selected entities will be renamed to:", 
                     font=("Arial", 9)).pack(anchor=tk.W)
            ttk.Label(canonical_frame, textvariable=canonical_var, 
                     font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W, padx=10)
            
            # Buttons
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def approve_merge():
                selected_entities = [entity for var, entity in entity_vars if var.get()]
                if len(selected_entities) >= 2:
                    # Create merge group with canonical name
                    canonical_name = canonical_var.get()
                    merge_group = []
                    for entity in selected_entities:
                        if entity['text'] != canonical_name:
                            merge_group.append(entity)
                    
                    if merge_group:  # Only add if there are entities to rename
                        # Add canonical entity first, then others
                        canonical_entity = next(e for e in selected_entities if e['text'] == canonical_name)
                        self.approved_merges.append([canonical_entity] + merge_group)
                
                self.current_group_index += 1
                dialog.destroy()
                show_next_group()
            
            def skip_group():
                self.current_group_index += 1
                dialog.destroy()
                show_next_group()
            
            def cancel_all():
                dialog.destroy()
            
            ttk.Button(button_frame, text="✅ Approve Merge", command=approve_merge).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="⏭️ Skip Group", command=skip_group).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="❌ Cancel All", command=cancel_all).pack(side=tk.LEFT, padx=5)
        
        show_next_group()
    
    def view_entity_document(self, entity):
        """View document containing the entity"""
        # Find the document in ledger
        matching_rows = self.ledger.df[self.ledger.df['filename'] == entity['filename']]
        if matching_rows.empty:
            return
        
        filepath = matching_rows.iloc[0]['filepath']
        
        # Clear preview frame
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Create document preview
        try:
            self._create_document_preview(self.preview_frame, filepath)
        except Exception as e:
            ttk.Label(self.preview_frame, text=f"Preview error: {str(e)}", 
                     foreground="red").pack(expand=True)
    
    def removed_import_metadata(self):
        """Import archival metadata from CSV or Excel file"""
        file_path = filedialog.askopenfilename(
            title="Select Metadata File",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")]
        )
        
        if not file_path:
            return
            
        try:
            import pandas as pd
            import os
            
            # Read file
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Auto-detect columns for Isabel Bevier Papers format
            matched_count = 0
            for _, row in df.iterrows():
                collection = str(row['Collection Title']).strip() if 'Collection Title' in df.columns and pd.notna(row['Collection Title']) else None
                box = str(row['Container']).strip() if 'Container' in df.columns and pd.notna(row['Container']) else None
                resource_id = str(row['Resource Identifier']).strip() if 'Resource Identifier' in df.columns and pd.notna(row['Resource Identifier']) else None
                
                if all([collection, box, resource_id]):
                    # Try to match with existing files using Resource Identifier
                    for file_path in self.ledger.df['filepath']:
                        if self.match_by_resource_id(file_path, collection, box, resource_id):
                            self.archival_metadata[file_path] = row.to_dict()
                            matched_count += 1
                            break
            
            messagebox.showinfo("Import Complete", f"Matched {matched_count} files with metadata")
            self.refresh_display()
            
            # Match with existing files using multiple strategies
            matched_count = 0
            folder_metadata = {}  # Store folder-level metadata
            
            # First pass: exact filename matches
            for file_path in self.ledger.df['filepath']:
                for constructed_path, archival_data in all_metadata.items():
                    if self.paths_match(file_path, constructed_path):
                        self.archival_metadata[file_path] = archival_data
                        matched_count += 1
                        
                        # Also store folder-level metadata for other files in same folder
                        folder_key = self.get_folder_key(file_path)
                        if folder_key not in folder_metadata:
                            folder_metadata[folder_key] = archival_data.copy()
                            folder_metadata[folder_key]['is_folder_level'] = True
                        break
            
            # Second pass: apply folder-level metadata to unmatched files
            for file_path in self.ledger.df['filepath']:
                if file_path not in self.archival_metadata:
                    folder_key = self.get_folder_key(file_path)
                    if folder_key in folder_metadata:
                        # Apply folder metadata but mark as inherited
                        inherited_metadata = folder_metadata[folder_key].copy()
                        inherited_metadata['Filename'] = os.path.basename(file_path)
                        inherited_metadata['match_type'] = 'folder_inherited'
                        self.archival_metadata[file_path] = inherited_metadata
                        matched_count += 1
            
            # Generate detailed report
            unmatched_files = []
            exact_matches = 0
            inherited_matches = 0
            
            for file_path in self.ledger.df['filepath']:
                if file_path in self.archival_metadata:
                    if self.archival_metadata[file_path].get('match_type') == 'folder_inherited':
                        inherited_matches += 1
                    else:
                        exact_matches += 1
                else:
                    unmatched_files.append(file_path)
            
            # Show detailed results
            result_msg = f"Imported {len(all_metadata)} metadata records\n\n"
            result_msg += f"✅ Matched {matched_count} files:\n"
            result_msg += f"   • {exact_matches} exact filename matches\n"
            result_msg += f"   • {inherited_matches} folder-level inherited\n\n"
            
            if unmatched_files:
                result_msg += f"❌ {len(unmatched_files)} unmatched files:\n"
                # Show first few unmatched files as examples
                for i, file_path in enumerate(unmatched_files[:5]):
                    filename = os.path.basename(file_path)
                    folder = os.path.basename(os.path.dirname(file_path))
                    result_msg += f"   • {filename} (in {folder})\n"
                
                if len(unmatched_files) > 5:
                    result_msg += f"   • ... and {len(unmatched_files) - 5} more\n"
                
                result_msg += f"\nCommon reasons for no match:\n"
                result_msg += f"• Files outside Collection/Box/Folder structure\n"
                result_msg += f"• Different collection not in metadata\n"
                result_msg += f"• Files in root directories or temp folders"
            
            messagebox.showinfo("Metadata Import Results", result_msg)
            
            # Refresh display to show updated metadata
            self.refresh_display()
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import metadata: {str(e)}")
            import traceback
            print(f"Metadata import error: {traceback.format_exc()}")
    
    def paths_match(self, actual_path, constructed_path):
        """Check if actual file path matches constructed metadata path using relative matching"""
        # Extract relative path components from actual file
        actual_parts = actual_path.replace('\\', '/').split('/')
        constructed_parts = constructed_path.replace('\\', '/').split('/')
        
        # Work backwards from filename to find matching pattern
        if len(actual_parts) < len(constructed_parts):
            return False
            
        # Check if the end of actual path matches constructed path
        actual_suffix = actual_parts[-len(constructed_parts):]
        
        for i, (actual, expected) in enumerate(zip(actual_suffix, constructed_parts)):
            if i == len(constructed_parts) - 1:  # Filename - exact match
                if actual.lower() != expected.lower():
                    return False
            else:  # Directory - flexible matching
                if not self.directory_match(actual.lower(), expected.lower()):
                    return False
        
        return True
    
    def directory_match(self, actual_dir, expected_dir):
        """Flexible directory matching"""
        # Exact match
        if actual_dir == expected_dir:
            return True
        # Box/Folder pattern matching
        if 'box' in expected_dir and 'box' in actual_dir:
            return True
        if 'folder' in expected_dir and 'folder' in actual_dir:
            return True
        # Partial name matching
        return expected_dir in actual_dir or actual_dir in expected_dir
    
    def get_folder_key(self, file_path):
        """Extract folder key for grouping files by folder"""
        path_parts = file_path.replace('\\', '/').split('/')
        
        # Work backwards to find collection/box/folder structure
        folder_parts = []
        for i in range(len(path_parts) - 1, 0, -1):  # Skip filename
            part = path_parts[i]
            folder_parts.insert(0, part)
            
            # Stop when we have enough context (3 levels: collection/box/folder)
            if len(folder_parts) >= 3:
                break
        
        return '/'.join(folder_parts).lower()
    
    def show_column_mapping_dialog(self, columns):
        """Show dialog to map CSV columns to required fields"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Map CSV Columns")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {}
        
        ttk.Label(dialog, text="Map your CSV columns to required fields:", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Collection mapping
        ttk.Label(dialog, text="Collection:").pack(anchor=tk.W, padx=20)
        collection_var = tk.StringVar()
        collection_combo = ttk.Combobox(dialog, textvariable=collection_var, values=columns, width=40)
        collection_combo.pack(padx=20, pady=2)
        
        # Box mapping
        ttk.Label(dialog, text="Box/Container:").pack(anchor=tk.W, padx=20, pady=(10,0))
        box_var = tk.StringVar()
        box_combo = ttk.Combobox(dialog, textvariable=box_var, values=columns, width=40)
        box_combo.pack(padx=20, pady=2)
        
        # Folder mapping
        ttk.Label(dialog, text="Folder/Title:").pack(anchor=tk.W, padx=20, pady=(10,0))
        folder_var = tk.StringVar()
        folder_combo = ttk.Combobox(dialog, textvariable=folder_var, values=columns, width=40)
        folder_combo.pack(padx=20, pady=2)
        
        # Filename mapping
        ttk.Label(dialog, text="Filename/Identifier:").pack(anchor=tk.W, padx=20, pady=(10,0))
        filename_var = tk.StringVar()
        filename_combo = ttk.Combobox(dialog, textvariable=filename_var, values=columns, width=40)
        filename_combo.pack(padx=20, pady=2)
        
        def on_ok():
            if all([collection_var.get(), box_var.get(), folder_var.get(), filename_var.get()]):
                result['collection'] = collection_var.get()
                result['box'] = box_var.get()
                result['folder'] = folder_var.get()
                result['filename'] = filename_var.get()
                dialog.destroy()
            else:
                messagebox.showwarning("Missing Selection", "Please select all four columns")
        
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=20)
        
        dialog.wait_window()
        return result
    
    def match_by_resource_id(self, file_path, collection, box, resource_id):
        """Match file using Resource Identifier as base filename"""
        # Extract actual filename without extension
        actual_base = os.path.splitext(os.path.basename(file_path))[0]
        
        # Direct match on Resource Identifier
        if actual_base.lower() == resource_id.lower():
            return True
        
        return False
    
    def import_csv_with_paths(self):
        """Import CSV file with file paths and metadata"""
        file_path = filedialog.askopenfilename(
            title="Select CSV with File Paths",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if not file_path:
            return
            
        try:
            import pandas as pd
            
            # Read CSV
            df = pd.read_csv(file_path)
            
            # Find filepath column
            filepath_col = self.find_filepath_column(df.columns.tolist())
            if not filepath_col:
                messagebox.showerror("No Filepath Column", "Could not find a column containing file paths")
                return
            
            # Collect all valid file paths first
            valid_paths = []
            for _, row in df.iterrows():
                filepath = str(row[filepath_col]).strip()
                if os.path.exists(filepath):
                    valid_paths.append(filepath)
            
            # Add all files at once
            if valid_paths:
                added_count = self.ledger.add_files(valid_paths)
            else:
                added_count = 0
            
            messagebox.showinfo("Import Complete", f"Imported {added_count} files with metadata from CSV")
            self.refresh_display()
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import CSV: {str(e)}")
    
    def find_filepath_column(self, columns):
        """Find column containing file paths"""
        filepath_indicators = ['filepath', 'file_path', 'path', 'filename', 'file']
        
        for col in columns:
            if any(indicator in col.lower() for indicator in filepath_indicators):
                return col
        return None
    
    def analyze_document_relationships(self):
        """Analyze PDF-image relationships in the dataset"""
        if not self.ground_truth_engine:
            messagebox.showwarning("Ground Truth Required", "Please set ground truth OCR engine first")
            return
        
        def analysis_worker():
            self.start_processing()
            self.status_var.set("Analyzing document relationships...")
            self.log_activity("Started document relationship analysis")
            
            try:
                relationships = self.detect_pdf_image_relationships()
                
                if not relationships:
                    self.status_var.set("No relationships found")
                    messagebox.showinfo("No Relationships", "No PDF-image relationships detected")
                    return
                
                self.log_activity(f"Found {len(relationships)} potential relationships")
                self.status_var.set(f"Analysis complete - {len(relationships)} relationships found")
                
                # Show review dialog
                self.root.after(0, lambda: self.show_relationship_review_dialog(relationships))
                
            except Exception as e:
                self.log_activity(f"Relationship analysis error: {str(e)}")
                self.status_var.set(f"Analysis failed: {str(e)}")
                messagebox.showerror("Analysis Error", str(e))
            finally:
                self.finish_processing()
        
        self.progress.start()
        threading.Thread(target=analysis_worker, daemon=True).start()
    
    def detect_pdf_image_relationships(self):
        """Detect relationships between PDFs and images"""
        relationships = []
        ocr_source = self.ground_truth_engine
        
        # Group files by directory
        directories = {}
        for _, row in self.ledger.df.iterrows():
            dir_path = os.path.dirname(row['filepath'])
            if dir_path not in directories:
                directories[dir_path] = {'pdfs': [], 'images': []}
            
            if row['file_type'] == '.pdf':
                directories[dir_path]['pdfs'].append(row)
            else:
                directories[dir_path]['images'].append(row)
        
        # Analyze each directory
        for dir_path, files in directories.items():
            if not files['pdfs'] or not files['images']:
                continue
            
            # Check for subdirectories with images
            for subdir in os.listdir(dir_path):
                subdir_path = os.path.join(dir_path, subdir)
                if os.path.isdir(subdir_path) and 'photo' in subdir.lower():
                    # Found potential source photos directory
                    subdir_images = [row for row in self.ledger.df.iterrows() 
                                   if os.path.dirname(row[1]['filepath']) == subdir_path]
                    
                    if subdir_images:
                        # Simple case: one PDF with matching image count
                        if len(files['pdfs']) == 1:
                            pdf_row = files['pdfs'][0]
                            pdf_pages = self.get_pdf_page_count(pdf_row['filepath'])
                            
                            if pdf_pages == len(subdir_images):
                                relationships.append({
                                    'pdf': pdf_row,
                                    'images': [img[1] for img in subdir_images],
                                    'confidence': 0.95,
                                    'method': 'page_count_match',
                                    'notes': f'PDF has {pdf_pages} pages, found {len(subdir_images)} images'
                                })
                        
                        # Complex case: multiple PDFs, use OCR similarity
                        else:
                            for pdf_row in files['pdfs']:
                                matches = self.match_pdf_to_images_by_ocr(pdf_row, subdir_images, ocr_source)
                                if matches['confidence'] > 0.7:
                                    relationships.append(matches)
        
        return relationships
    
    def get_pdf_page_count(self, pdf_path):
        """Get number of pages in PDF"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except:
            return 0
    
    def match_pdf_to_images_by_ocr(self, pdf_row, image_rows, ocr_source):
        """Match PDF to images using OCR text similarity"""
        from difflib import SequenceMatcher
        
        pdf_text = str(pdf_row.get(f'{ocr_source}_ocr', ''))
        if not pdf_text or pdf_text == 'nan':
            return {'confidence': 0.0}
        
        # Combine all image OCR text
        image_texts = []
        matched_images = []
        
        for img_tuple in image_rows:
            img_row = img_tuple[1]
            img_text = str(img_row.get(f'{ocr_source}_ocr', ''))
            if img_text and img_text != 'nan':
                image_texts.append(img_text)
                matched_images.append(img_row)
        
        if not image_texts:
            return {'confidence': 0.0}
        
        combined_image_text = ' '.join(image_texts)
        similarity = SequenceMatcher(None, pdf_text.lower(), combined_image_text.lower()).ratio()
        
        return {
            'pdf': pdf_row,
            'images': matched_images,
            'confidence': similarity,
            'method': 'ocr_similarity',
            'notes': f'OCR similarity: {similarity:.2%}'
        }
    
    def show_relationship_review_dialog(self, relationships):
        """Show dialog to review and approve relationships"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Review Document Relationships")
        dialog.geometry("1200x800")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="🔗 Document Relationship Analysis", 
                 font=("Arial", 14, "bold")).pack()
        ttk.Label(header_frame, text=f"Found {len(relationships)} potential relationships", 
                 font=("Arial", 10), foreground="gray").pack()
        
        # Main content
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Relationship list
        list_frame = ttk.LabelFrame(main_frame, text="Detected Relationships")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ['pdf', 'images', 'confidence', 'method', 'approved']
        tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        tree.heading('pdf', text='PDF Document')
        tree.heading('images', text='Matched Images')
        tree.heading('confidence', text='Confidence')
        tree.heading('method', text='Method')
        tree.heading('approved', text='Approved')
        
        tree.column('pdf', width=300)
        tree.column('images', width=200)
        tree.column('confidence', width=100)
        tree.column('method', width=150)
        tree.column('approved', width=80)
        
        # Populate tree
        approved_vars = {}
        for i, rel in enumerate(relationships):
            pdf_name = os.path.basename(rel['pdf']['filename'])
            image_count = len(rel['images'])
            confidence = f"{rel['confidence']:.1%}"
            method = rel['method'].replace('_', ' ').title()
            
            item_id = tree.insert('', 'end', values=[
                pdf_name, f"{image_count} images", confidence, method, "✅ Yes"
            ])
            approved_vars[item_id] = tk.BooleanVar(value=True)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def apply_relationships():
            approved_relationships = []
            for i, (item_id, var) in enumerate(approved_vars.items()):
                if var.get():
                    approved_relationships.append(relationships[i])
            
            if approved_relationships:
                self.store_approved_relationships(approved_relationships)
                messagebox.showinfo("Relationships Stored", 
                                   f"Stored {len(approved_relationships)} approved relationships")
            dialog.destroy()
        
        ttk.Button(button_frame, text="✅ Apply Approved", command=apply_relationships).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def store_approved_relationships(self, relationships):
        """Store approved relationships for export"""
        # Store in a simple format for now
        self.document_relationships = relationships
        self.log_activity(f"Stored {len(relationships)} document relationships")
    
    def apply_entity_merges(self, approved_groups, entity_type):
        """Apply approved entity merges to the data"""
        for group in approved_groups:
            # Use first entity as canonical name
            canonical_name = group[0]['text']
            
            # Replace all other variants with canonical name
            for entity in group[1:]:
                self.replace_entity_in_ledger(entity['text'], canonical_name)
    
    def replace_entity_in_ledger(self, old_entity, new_entity):
        """Replace entity name in all ledger entries"""
        for idx, row in self.ledger.df.iterrows():
            entities_text = str(row.get('named_entities', ''))
            if old_entity in entities_text:
                updated_text = entities_text.replace(old_entity, new_entity)
                self.ledger.df.at[idx, 'named_entities'] = updated_text
        
        # Save changes
        self.ledger.save_ledger()
    
    def stop_processing(self):
        """Stop current processing operation"""
        self.stop_requested = True
        self.stop_button.configure(state='disabled')
        self.status_var.set("Stopping processing...")
        self.log_activity("Stop requested by user")
    
    def start_processing(self):
        """Start processing and enable stop button"""
        self.stop_requested = False
        self.stop_button.configure(state='normal')
    
    def finish_processing(self):
        """Finish processing and disable stop button"""
        self.stop_requested = False
        self.stop_button.configure(state='disabled')
        self.progress.stop()
    
    def scan_directory_for_new_files(self):
        """Scan directory for new files not already in ledger"""
        directory = filedialog.askdirectory(title="Select directory to scan for new files")
        if not directory:
            return
        
        # Get all supported files in directory
        new_files = []
        existing_paths = set(self.ledger.df['filepath'].tolist())
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pdf']:
                    full_path = os.path.join(root, file)
                    if full_path not in existing_paths:
                        new_files.append(full_path)
        
        if new_files:
            added_count = self.ledger.add_files(new_files)
            messagebox.showinfo("New Files Added", 
                               f"Found {len(new_files)} new files\nAdded {added_count} to ledger")
            self.refresh_display()
        else:
            messagebox.showinfo("No New Files", "No new files found in directory")

def main():
    root = tk.Tk()
    app = CodebooksApp(root)
    # Make app globally accessible for OCR processor logging
    import __main__
    __main__.app = app
    root.mainloop()

if __name__ == "__main__":
    main()