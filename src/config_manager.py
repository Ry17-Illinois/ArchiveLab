#!/usr/bin/env python3
"""
Configuration Manager for persistent settings
"""

import json
import os
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "ai_models": {
                "openai_enabled": False,
                "openai_api_key": "",
                "ollama_enabled": False,
                "ollama_model": "gemma3",
                "openai_batch_enabled": False
            },
            "ocr_engines": {
                "easyocr_enabled": True,
                "tesseract_enabled": True,
                "pypdf2_enabled": True,
                "openai_ocr_enabled": False,
                "ollama_ocr_enabled": False
            },
            "ui_settings": {
                "window_geometry": "1000x700",
                "last_directory": ""
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to handle new settings
                for section, settings in default_config.items():
                    if section not in loaded_config:
                        loaded_config[section] = settings
                    else:
                        for key, value in settings.items():
                            if key not in loaded_config[section]:
                                loaded_config[section][key] = value
                return loaded_config
            except:
                return default_config
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def get(self, section: str, key: str, default=None):
        """Get configuration value"""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.config.get(section, {})