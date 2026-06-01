#!/usr/bin/env python3
"""
Named Entity Recognition Processor
Extracts entities from OCR text using spaCy or OpenAI/Ollama
"""

import json
from typing import Dict, List, Any, Optional

class NERProcessor:
    def __init__(self):
        self.spacy_model = None
        self.openai_client = None
        self.ollama_available = False
        self._load_spacy()
    
    def _load_spacy(self):
        """Load spaCy model if available"""
        try:
            import spacy
            self.spacy_model = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            print("spaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")
    
    def extract_entities_spacy(self, text: str) -> Dict[str, List[str]]:
        """Extract entities using spaCy"""
        if not self.spacy_model or not text:
            return {}
        
        doc = self.spacy_model(text)
        entities = {
            'PERSON': [],
            'ORG': [],
            'GPE': [],  # Geopolitical entities (countries, cities, states)
            'DATE': [],
            'MONEY': [],
            'CARDINAL': [],  # Numbers
            'EVENT': [],
            'FAC': [],  # Facilities
            'LAW': [],
            'PRODUCT': [],
            'WORK_OF_ART': []
        }
        
        for ent in doc.ents:
            if ent.label_ in entities:
                entity_text = ent.text.strip()
                if entity_text and entity_text not in entities[ent.label_]:
                    entities[ent.label_].append(entity_text)
        
        # Remove empty categories
        return {k: v for k, v in entities.items() if v}
    
    def extract_entities_openai(self, text: str, api_key: str) -> Dict[str, List[str]]:
        """Extract entities using OpenAI"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            prompt = f"""Extract named entities from the following text. Return ONLY a valid JSON object with these categories:
- PERSON: People's names
- ORG: Organizations, companies, institutions
- GPE: Geographic locations (cities, states, countries)
- DATE: Dates and time expressions
- MONEY: Monetary values
- EVENT: Named events
- PRODUCT: Products, brands
- WORK_OF_ART: Titles of books, articles, reports

Text: {text[:2000]}

IMPORTANT: Return ONLY the JSON object, no markdown, no code blocks, no explanations."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            return {k: v for k, v in result.items() if v}
            
        except json.JSONDecodeError as e:
            print(f"OpenAI NER JSON error: {e}")
            print(f"Response content: {response.choices[0].message.content[:200]}")
            return {}
        except Exception as e:
            print(f"OpenAI NER error: {e}")
            return {}
    
    def extract_entities_ollama(self, text: str, model: str = "gemma3") -> Dict[str, List[str]]:
        """Extract entities using Ollama"""
        try:
            import requests
            
            prompt = f"""Extract named entities from this text and return as JSON:

Categories:
- PERSON: People's names
- ORG: Organizations
- GPE: Geographic locations
- DATE: Dates
- MONEY: Money amounts
- EVENT: Events
- PRODUCT: Products

Text: {text[:1500]}

Return only JSON format with arrays."""

            response = requests.post('http://localhost:11434/api/generate',
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'format': 'json'
                })
            
            if response.status_code == 200:
                result = json.loads(response.json()['response'])
                return {k: v for k, v in result.items() if v}
            
        except Exception as e:
            print(f"Ollama NER error: {e}")
        
        return {}
    
    def process_text(self, text: str, method: str = "spacy", **kwargs) -> Dict[str, List[str]]:
        """Process text with specified NER method"""
        if not text or not text.strip():
            return {}
        
        if method == "spacy":
            return self.extract_entities_spacy(text)
        elif method == "openai":
            api_key = kwargs.get('api_key')
            if api_key:
                return self.extract_entities_openai(text, api_key)
        elif method == "ollama":
            model = kwargs.get('model', 'gemma3')
            return self.extract_entities_ollama(text, model)
        
        return {}
    
    def format_entities_for_display(self, entities: Dict[str, List[str]]) -> str:
        """Format entities for display"""
        if not entities:
            return "No entities found"
        
        formatted = []
        entity_labels = {
            'PERSON': '👤 People',
            'ORG': '🏢 Organizations', 
            'GPE': '🌍 Locations',
            'DATE': '📅 Dates',
            'MONEY': '💰 Money',
            'CARDINAL': '🔢 Numbers',
            'EVENT': '🎯 Events',
            'FAC': '🏗️ Facilities',
            'LAW': '⚖️ Laws',
            'PRODUCT': '📦 Products',
            'WORK_OF_ART': '🎨 Works'
        }
        
        for category, items in entities.items():
            if items:
                label = entity_labels.get(category, category)
                formatted.append(f"{label}: {', '.join(items[:10])}")  # Limit to 10 items
        
        return '\n'.join(formatted)