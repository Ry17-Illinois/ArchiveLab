#!/usr/bin/env python3
"""
Batch Manager - Handle OpenAI batch processing for cost optimization
"""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from pathlib import Path
import openai

class BatchRequest:
    def __init__(self, request_id: str, prompt: str, callback: Callable, metadata: Dict = None):
        self.request_id = request_id
        self.prompt = prompt
        self.callback = callback
        self.metadata = metadata or {}
        self.created_at = datetime.now()

class BatchManager:
    def __init__(self, client: openai.OpenAI, batch_size: int = 50, max_wait_hours: int = 24):
        self.client = client
        self.batch_size = batch_size
        self.max_wait_hours = max_wait_hours
        
        # Storage
        self.pending_requests: List[BatchRequest] = []
        self.active_batches: Dict[str, Dict] = {}  # batch_id -> batch_info
        self.batch_storage = Path("batch_data")
        self.batch_storage.mkdir(exist_ok=True)
        
        # Load existing batches
        self._load_active_batches()
    
    def add_request(self, prompt: str, callback: Callable, metadata: Dict = None) -> str:
        """Add a request to the batch queue"""
        request_id = str(uuid.uuid4())
        batch_request = BatchRequest(request_id, prompt, callback, metadata)
        self.pending_requests.append(batch_request)
        
        # Auto-submit if batch is full
        if len(self.pending_requests) >= self.batch_size:
            self.submit_batch()
        
        return request_id
    
    def submit_batch(self, force: bool = False) -> Optional[str]:
        """Submit current batch to OpenAI"""
        if not self.pending_requests:
            return None
        
        if len(self.pending_requests) < self.batch_size and not force:
            return None
        
        # Prepare batch file
        batch_id = str(uuid.uuid4())
        batch_file_path = self.batch_storage / f"batch_{batch_id}.jsonl"
        
        # Create JSONL file for batch
        with open(batch_file_path, 'w') as f:
            for i, req in enumerate(self.pending_requests):
                # Parse prompt to extract base64 image if present
                if "data:image/jpeg;base64," in req.prompt:
                    # Extract text and image from prompt
                    parts = req.prompt.split("Image: data:image/jpeg;base64,")
                    text_prompt = parts[0].strip()
                    image_b64 = parts[1].strip() if len(parts) > 1 else ""
                    
                    batch_item = {
                        "custom_id": req.request_id,
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": "gpt-4o-mini",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": text_prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/jpeg;base64,{image_b64}",
                                                "detail": "low"
                                            }
                                        }
                                    ]
                                }
                            ],
                            "max_tokens": 800
                        }
                    }
                else:
                    # Text-only request
                    batch_item = {
                        "custom_id": req.request_id,
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": "You are a historical research expert."},
                                {"role": "user", "content": req.prompt}
                            ],
                            "max_tokens": 800,
                            "temperature": 0.7
                        }
                    }
                f.write(json.dumps(batch_item) + '\n')
        
        try:
            # Upload batch file
            with open(batch_file_path, 'rb') as f:
                batch_input_file = self.client.files.create(file=f, purpose="batch")
            
            # Create batch
            batch = self.client.batches.create(
                input_file_id=batch_input_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            
            # Store batch info
            batch_info = {
                'batch_id': batch.id,
                'openai_batch_id': batch.id,
                'status': 'submitted',
                'created_at': datetime.now().isoformat(),
                'requests': {req.request_id: {'callback': req.callback, 'metadata': req.metadata} 
                           for req in self.pending_requests},
                'file_path': str(batch_file_path),
                'input_file_id': batch_input_file.id
            }
            
            self.active_batches[batch_id] = batch_info
            self._save_batch_info(batch_id, batch_info)
            
            # Clear pending requests
            self.pending_requests.clear()
            
            return batch_id
            
        except Exception as e:
            print(f"Error submitting batch: {e}")
            return None
    
    def check_batch_status(self, batch_id: str) -> Optional[str]:
        """Check status of a specific batch"""
        if batch_id not in self.active_batches:
            return None
        
        batch_info = self.active_batches[batch_id]
        
        try:
            batch = self.client.batches.retrieve(batch_info['openai_batch_id'])
            batch_info['status'] = batch.status
            
            if batch.status == 'completed':
                self._process_completed_batch(batch_id, batch)
            elif batch.status == 'failed':
                print(f"Batch {batch_id} failed: {batch.errors}")
            
            return batch.status
            
        except Exception as e:
            print(f"Error checking batch status: {e}")
            return None
    
    def check_all_batches(self) -> Dict[str, str]:
        """Check status of all active batches"""
        statuses = {}
        completed_batches = []
        
        for batch_id in list(self.active_batches.keys()):
            status = self.check_batch_status(batch_id)
            if status:
                statuses[batch_id] = status
                if status in ['completed', 'failed', 'cancelled']:
                    completed_batches.append(batch_id)
        
        # Clean up completed batches
        for batch_id in completed_batches:
            if batch_id in self.active_batches:
                del self.active_batches[batch_id]
        
        return statuses
    
    def _process_completed_batch(self, batch_id: str, batch: object):
        """Process completed batch results"""
        batch_info = self.active_batches[batch_id]
        
        try:
            # Check for errors first
            if batch.error_file_id:
                print(f"\n⚠️ Batch {batch_id} has errors. Downloading error file...")
                error_result = self.client.files.content(batch.error_file_id)
                print(f"Error details:\n{error_result.text}")
                return
            
            # Download results
            output_file_id = getattr(batch, 'output_file_id', None)
            if not output_file_id:
                print(f"Batch {batch_id} completed but has no output file.")
                print(f"Request counts: {batch.request_counts}")
                return
            
            result = self.client.files.content(batch.output_file_id)
            
            # Process each result
            for line in result.text.strip().split('\n'):
                if line:
                    result_item = json.loads(line)
                    custom_id = result_item['custom_id']
                    
                    if custom_id in batch_info['requests']:
                        request_info = batch_info['requests'][custom_id]
                        
                        # Extract response
                        if result_item.get('response') and result_item['response'].get('body'):
                            response_body = result_item['response']['body']
                            if response_body.get('choices'):
                                content = response_body['choices'][0]['message']['content']
                                
                                # Execute callback with result and metadata
                                try:
                                    callback = request_info.get('callback')
                                    metadata = request_info.get('metadata', {})
                                    if callback:
                                        callback(content, metadata)
                                    else:
                                        print(f"No callback for request {custom_id}")
                                except Exception as e:
                                    print(f"Error executing callback for {custom_id}: {e}")
                        elif result_item.get('error'):
                            print(f"Request {custom_id} failed: {result_item['error']}")
        
        except Exception as e:
            print(f"Error processing completed batch {batch_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_batch_info(self, batch_id: str, batch_info: Dict):
        """Save batch info to disk"""
        # Remove callback functions for serialization
        serializable_info = batch_info.copy()
        serializable_info['requests'] = {
            req_id: {'metadata': req_data['metadata']} 
            for req_id, req_data in batch_info['requests'].items()
        }
        
        with open(self.batch_storage / f"{batch_id}.json", 'w') as f:
            json.dump(serializable_info, f, indent=2)
    
    def _load_active_batches(self):
        """Load active batches from disk"""
        for batch_file in self.batch_storage.glob("*.json"):
            try:
                with open(batch_file, 'r') as f:
                    batch_info = json.load(f)
                
                batch_id = batch_file.stem
                
                # Skip old batches
                created_at = datetime.fromisoformat(batch_info['created_at'])
                if datetime.now() - created_at > timedelta(hours=self.max_wait_hours):
                    batch_file.unlink()  # Delete old batch file
                    continue
                
                # Only load if still active
                if batch_info['status'] not in ['completed', 'failed', 'cancelled']:
                    # Reconstruct callbacks from metadata
                    for req_id, req_data in batch_info['requests'].items():
                        req_data['callback'] = self._create_callback_from_metadata(req_data['metadata'])
                    
                    self.active_batches[batch_id] = batch_info
                    
            except Exception as e:
                print(f"Error loading batch file {batch_file}: {e}")
    
    def _create_callback_from_metadata(self, metadata: Dict) -> Callable:
        """Create a callback function from saved metadata"""
        def callback(result, meta):
            # This will be called when batch completes
            # The actual ledger update will be handled by the application
            file_id = meta.get('file_id')
            if file_id:
                # Import here to avoid circular dependency
                try:
                    import __main__
                    if hasattr(__main__, 'app'):
                        __main__.app.ledger.update_ocr_result(file_id, result, 'completed', 'openai_ocr')
                        __main__.app.root.after(0, __main__.app.refresh_display)
                except Exception as e:
                    print(f"Error in reconstructed callback: {e}")
        
        return callback
    
    def get_pending_count(self) -> int:
        """Get number of pending requests"""
        return len(self.pending_requests)
    
    def get_active_batch_count(self) -> int:
        """Get number of active batches"""
        return len(self.active_batches)
    
    def force_submit_pending(self) -> Optional[str]:
        """Force submit pending requests even if batch isn't full"""
        return self.submit_batch(force=True)