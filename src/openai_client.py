#!/usr/bin/env python3
"""
Unified OpenAI Client - Handles all OpenAI requests with optional batching
"""

import os
from typing import Dict, Any, Optional, Callable
from openai import OpenAI
from .batch_manager import BatchManager

class UnifiedOpenAIClient:
    """Wrapper for OpenAI client that handles batching automatically"""
    
    def __init__(self, api_key: str = None):
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        self.client = OpenAI()
        self.batch_manager = BatchManager(self.client)
        self.batching_enabled = False
    
    def set_batching_enabled(self, enabled: bool):
        """Enable or disable batch processing"""
        self.batching_enabled = enabled
    
    def chat_completions_create(self, **kwargs) -> Any:
        """Create chat completion with optional batching"""
        
        # Check if this should be batched
        if self.batching_enabled and self._should_batch_request(**kwargs):
            # Extract callback info if provided
            callback = kwargs.pop('_callback', None)
            metadata = kwargs.pop('_metadata', {})
            
            if callback:
                # Convert to batch format
                prompt = self._extract_prompt_from_messages(kwargs.get('messages', []))
                request_id = self.batch_manager.add_request(prompt, callback, metadata)
                
                # Return a placeholder response
                class BatchResponse:
                    def __init__(self, request_id):
                        self.request_id = request_id
                        self.choices = [type('obj', (object,), {
                            'message': type('obj', (object,), {
                                'content': f'BATCH_QUEUED:{request_id}'
                            })()
                        })()]
                
                return BatchResponse(request_id)
        
        # Process immediately
        return self.client.chat.completions.create(**kwargs)
    
    def _should_batch_request(self, **kwargs) -> bool:
        """Determine if request should be batched"""
        # Don't batch image requests (OpenAI batch API doesn't support images well)
        messages = kwargs.get('messages', [])
        for message in messages:
            if isinstance(message.get('content'), list):
                for content_item in message['content']:
                    if content_item.get('type') == 'image_url':
                        return False
        
        # Don't batch if no callback provided
        if '_callback' not in kwargs:
            return False
        
        return True
    
    def _extract_prompt_from_messages(self, messages) -> str:
        """Extract prompt text from messages for batching"""
        prompt_parts = []
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if isinstance(content, str):
                prompt_parts.append(f"{role}: {content}")
            elif isinstance(content, list):
                # Handle complex content (text + images)
                text_parts = [item.get('text', '') for item in content if item.get('type') == 'text']
                if text_parts:
                    prompt_parts.append(f"{role}: {' '.join(text_parts)}")
        
        return '\n'.join(prompt_parts)
    
    def submit_pending_batch(self) -> Optional[str]:
        """Submit pending batch requests"""
        return self.batch_manager.submit_batch(force=True)
    
    def check_batch_status(self) -> Dict[str, str]:
        """Check status of active batches"""
        return self.batch_manager.check_all_batches()
    
    def get_batch_info(self) -> Dict[str, int]:
        """Get batch queue information"""
        return {
            'pending_requests': self.batch_manager.get_pending_count(),
            'active_batches': self.batch_manager.get_active_batch_count()
        }

# Global instance
_global_client = None

def get_openai_client() -> UnifiedOpenAIClient:
    """Get the global OpenAI client instance"""
    global _global_client
    if _global_client is None:
        raise RuntimeError("OpenAI client not initialized. Call initialize_openai_client() first.")
    return _global_client

def initialize_openai_client(api_key: str = None) -> UnifiedOpenAIClient:
    """Initialize the global OpenAI client"""
    global _global_client
    _global_client = UnifiedOpenAIClient(api_key)
    return _global_client

def set_batching_enabled(enabled: bool):
    """Enable/disable batching globally"""
    client = get_openai_client()
    client.set_batching_enabled(enabled)