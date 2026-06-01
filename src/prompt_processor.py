#!/usr/bin/env python3
"""
Prompt-based AI Processor for extracting metadata
"""

import os
import json
from openai import OpenAI
from typing import List, Dict, Tuple, Optional, Any
from .batch_manager import BatchManager

try:
    import ollama
except ImportError:
    ollama = None

class PromptProcessor:
    """Handles AI-based metadata extraction using prompts"""
    
    def __init__(self, api_key: Optional[str] = None, model_type: str = "openai"):
        self.model_type = model_type
        self.prompts = self.load_prompts()
        
        if model_type == "openai":
            from .openai_client import initialize_openai_client, get_openai_client
            
            try:
                self.client = get_openai_client()
            except RuntimeError:
                self.client = initialize_openai_client(api_key)
            
            self.use_batching = False
        elif model_type == "ollama":
            if ollama is None:
                raise ImportError("Ollama not available")
            self.ollama_model = self._get_available_ollama_model()
            self.batch_manager = None
            self.use_batching = False
    
    def load_prompts(self) -> Dict[str, str]:
        """Load prompts from the prompts directory"""
        prompts = {}
        prompts_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        
        if os.path.exists(prompts_dir):
            for filename in os.listdir(prompts_dir):
                if filename.endswith('.txt'):
                    field_name = filename.replace('.txt', '')
                    with open(os.path.join(prompts_dir, filename), 'r', encoding='utf-8') as f:
                        prompts[field_name] = f.read().strip()
        
        return prompts
    
    def generate_multi_metadata(self, text: str, use_batch: bool = False, callback=None, metadata=None) -> Dict[str, Any]:
        """Generate multiple metadata fields at once using AI"""
        if 'multi_metadata' not in self.prompts:
            return {"error": "Multi-metadata prompt not found"}
        
        prompt = self.prompts['multi_metadata']
        full_prompt = f"{prompt}\n\nDocument text:\n{text[:2000]}..."
        
        try:
            if self.model_type == "openai":
                if use_batch and callback:
                    result = self._generate_openai(full_prompt, callback, metadata)
                else:
                    result = self._generate_openai(full_prompt)
            elif self.model_type == "ollama":
                result = self._generate_ollama(full_prompt)
            else:
                return {"error": f"Unknown model type: {self.model_type}"}
            
            # Parse JSON response
            import json
            try:
                metadata_dict = json.loads(result)
                return metadata_dict
            except json.JSONDecodeError:
                # Fallback: try to extract JSON from response
                import re
                json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
                if json_match:
                    try:
                        metadata_dict = json.loads(json_match.group())
                        return metadata_dict
                    except json.JSONDecodeError:
                        pass
                return {"error": "Could not parse JSON response", "raw_response": result}
                
        except Exception as e:
            return {"error": f"Error generating metadata: {str(e)}"}
    
    def generate_examples(self, text: str, field: str, num_examples: int = 3, use_batch: bool = False, callback=None, metadata=None) -> List[str]:
        """Generate examples for a Dublin Core field using AI"""
        if field not in self.prompts:
            return [f"No prompt available for field: {field}"]
        
        prompt = self.prompts[field]
        full_prompt = f"{prompt}\n\nDocument text:\n{text[:2000]}..."  # Limit text length
        
        try:
            if self.model_type == "openai":
                if use_batch and callback:
                    result = self._generate_openai(full_prompt, callback, metadata)
                else:
                    result = self._generate_openai(full_prompt)
            elif self.model_type == "ollama":
                result = self._generate_ollama(full_prompt)
            else:
                return [f"Unknown model type: {self.model_type}"]
            
            # Clean and parse the response
            examples = self._parse_clean_response(result, num_examples)
            return examples if examples else ["No examples generated"]
            
        except Exception as e:
            return [f"Error generating examples: {str(e)}"]
    
    def _generate_openai(self, prompt: str, callback=None, metadata=None) -> str:
        """Generate using OpenAI"""
        # Check if this is an entity analysis prompt (contains "DOCUMENTARY EVIDENCE")
        if "DOCUMENTARY EVIDENCE" in prompt:
            system_prompt = """You are a historical research expert. Analyze the provided historical entity based on the OCR text evidence. Write detailed, informative paragraphs for each requested section. Be thorough and reference the document evidence provided."""
            max_tokens = 800
            temperature = 0.7
        elif "return as JSON" in prompt.lower():
            # Multi-metadata extraction prompt
            system_prompt = """You are a metadata extraction expert. Extract metadata from the document and return as valid JSON only. No additional commentary."""
            max_tokens = 300
            temperature = 0.2
        else:
            # Original metadata extraction prompt
            system_prompt = """You are a metadata extraction expert. Extract ONLY the requested metadata values from the document text. 
Respond with exactly 3 options, one per line, with no commentary, explanations, or numbering. 
Just the clean metadata values."""
            max_tokens = 200
            temperature = 0.3
        
        # Prepare request parameters
        request_params = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add callback info if provided
        if callback and metadata:
            request_params['_callback'] = callback
            request_params['_metadata'] = metadata
        
        response = self.client.chat_completions_create(**request_params)
        return response.choices[0].message.content
    
    def set_batching_enabled(self, enabled: bool):
        """Enable or disable batch processing"""
        self.use_batching = enabled
        if hasattr(self.client, 'set_batching_enabled'):
            self.client.set_batching_enabled(enabled)
    
    def submit_pending_batch(self) -> Optional[str]:
        """Force submit any pending batch requests"""
        if hasattr(self.client, 'submit_pending_batch'):
            return self.client.submit_pending_batch()
        return None
    
    def check_batch_status(self) -> Dict[str, str]:
        """Check status of all active batches"""
        if hasattr(self.client, 'check_batch_status'):
            return self.client.check_batch_status()
        return {}
    
    def get_batch_info(self) -> Dict[str, int]:
        """Get batch queue information"""
        if hasattr(self.client, 'get_batch_info'):
            return self.client.get_batch_info()
        return {'pending_requests': 0, 'active_batches': 0}
    
    def _generate_ollama(self, prompt: str) -> str:
        """Generate using Ollama"""
        # Check if this is an entity analysis prompt
        if "DOCUMENTARY EVIDENCE" in prompt:
            system_prompt = """You are a historical research expert. Analyze the provided historical entity based on the OCR text evidence. Write detailed, informative paragraphs for each requested section. Be thorough and reference the document evidence provided."""
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            # Original metadata extraction prompt
            system_prompt = """You are a metadata extraction expert. Extract ONLY the requested metadata values from the document text. 
Respond with exactly 3 options, one per line, with no commentary, explanations, or numbering. 
Just the clean metadata values."""
            full_prompt = f"{system_prompt}\n\n{prompt}\n\nProvide exactly 3 clean metadata values, one per line:"
        
        response = ollama.generate(
            model=self.ollama_model,
            prompt=full_prompt
        )
        return response['response']
    
    def _parse_clean_response(self, result: str, num_examples: int) -> List[str]:
        """Parse AI response and extract clean metadata values"""
        examples = []
        lines = result.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip common AI commentary patterns
            skip_patterns = [
                'here are', 'options for', 'suggestions:', 'based on', 
                'the document', 'analysis', 'extracted', 'following'
            ]
            
            if any(pattern in line.lower() for pattern in skip_patterns):
                continue
                
            # Remove numbering and bullet points
            if line[0].isdigit() and '.' in line[:5]:
                line = line.split('.', 1)[1].strip()
            elif line.startswith(('- ', '• ', '* ')):
                line = line[2:].strip()
                
            # Skip if line is too short or contains common filler words
            if len(line) < 3 or line.lower() in ['n/a', 'none', 'unknown', 'not applicable']:
                continue
                
            examples.append(line)
            
            # Stop when we have enough examples
            if len(examples) >= num_examples:
                break
        
        # Ensure we have the requested number of examples
        while len(examples) < num_examples and examples:
            # Create variations of existing examples
            base = examples[-1]
            if ',' in base:
                # Try splitting compound entries
                parts = [p.strip() for p in base.split(',')]
                if len(parts) > 1:
                    examples.append(parts[0])
                else:
                    examples.append(f"{base} (alternative)")
            else:
                examples.append(f"{base} (variant)")
        
        return examples[:num_examples]
    
    def _get_available_ollama_model(self) -> str:
        """Get the first available Ollama model"""
        try:
            models = ollama.list()
            available_models = [m['name'] for m in models['models']]
            print(f"Available Ollama models: {available_models}")
            
            # Prefer these models in order
            preferred = ['gemma3', 'llama3.1', 'llama3', 'llama2', 'mistral']
            for model in preferred:
                for available in available_models:
                    if model in available:
                        print(f"Selected Ollama model: {available}")
                        return available
            
            # Return first available model if none of the preferred ones found
            if available_models:
                selected = available_models[0]
                print(f"Using first available model: {selected}")
                return selected
            else:
                raise Exception("No Ollama models found. Please install a model with: ollama pull gemma3")
                
        except Exception as e:
            # Try gemma3 directly as fallback
            print(f"Model detection failed, trying gemma3 directly: {e}")
            return "gemma3"
    
    def get_available_fields(self) -> List[str]:
        """Get list of available Dublin Core fields with prompts"""
        return list(self.prompts.keys())
    
    def classify_document_type(self, image_path: str) -> str:
        """Classify document as handwriting, typed, mixed-text, or image"""
        try:
            if self.model_type == "openai":
                return self._classify_openai(image_path)
            elif self.model_type == "ollama":
                return self._classify_ollama(image_path)
            else:
                return "error: unknown model type"
        except Exception as e:
            return f"error: {str(e)}"
    
    def _classify_openai(self, image_path: str) -> str:
        """Classify document using OpenAI vision model"""
        import base64
        from PIL import Image
        import io
        
        # Load and encode image
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        response = self.client.chat_completions_create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Classify this document as one of: 'handwriting', 'typed', 'mixed-text', or 'image'. Return only the classification word."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_str}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip().lower()
        valid_types = ['handwriting', 'typed', 'mixed-text', 'image']
        return result if result in valid_types else 'image'
    
    def _classify_ollama(self, image_path: str) -> str:
        """Classify document using Ollama vision model"""
        from PIL import Image
        import io
        
        # Load image
        with Image.open(image_path) as img:
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()
        
        response = ollama.generate(
            model=self.ollama_model,
            prompt="Classify this document as one of: 'handwriting', 'typed', 'mixed-text', or 'image'. Return only the classification word.",
            images=[img_bytes]
        )
        
        result = response['response'].strip().lower()
        valid_types = ['handwriting', 'typed', 'mixed-text', 'image']
        return result if result in valid_types else 'image'