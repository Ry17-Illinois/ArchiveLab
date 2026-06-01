#!/usr/bin/env python3
"""
OCR Evaluator - Standard metrics for OCR quality assessment
"""

import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

class OCREvaluator:
    """Evaluate OCR quality using standard metrics"""
    
    @staticmethod
    def calculate_cer(reference: str, hypothesis: str) -> float:
        """Calculate Character Error Rate"""
        if not reference:
            return 1.0 if hypothesis else 0.0
        
        # Simple edit distance calculation
        ref_chars = list(reference.lower())
        hyp_chars = list(hypothesis.lower())
        
        # Create distance matrix
        m, n = len(ref_chars), len(hyp_chars)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # Initialize
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # Fill matrix
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_chars[i-1] == hyp_chars[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[m][n] / len(ref_chars)
    
    @staticmethod
    def calculate_wer(reference: str, hypothesis: str) -> float:
        """Calculate Word Error Rate"""
        ref_words = reference.lower().split()
        hyp_words = hypothesis.lower().split()
        
        if not ref_words:
            return 1.0 if hyp_words else 0.0
        
        # Simple word-level edit distance
        m, n = len(ref_words), len(hyp_words)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_words[i-1] == hyp_words[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[m][n] / len(ref_words)
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate text similarity using SequenceMatcher"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    @staticmethod
    def quality_score(text: str) -> float:
        """Estimate OCR quality without ground truth"""
        if not text or not text.strip():
            return 0.0
        
        score = 1.0
        
        # Penalize for excessive special characters
        special_chars = len(re.findall(r'[^\w\s]', text))
        if len(text) > 0:
            special_ratio = special_chars / len(text)
            if special_ratio > 0.3:
                score -= 0.3
        
        # Penalize for excessive whitespace
        whitespace_ratio = len(re.findall(r'\s', text)) / len(text) if text else 0
        if whitespace_ratio > 0.5:
            score -= 0.2
        
        # Reward for readable words
        words = text.split()
        if words:
            readable_words = sum(1 for word in words if len(word) > 2 and word.isalpha())
            readable_ratio = readable_words / len(words)
            score = score * (0.5 + 0.5 * readable_ratio)
        
        return max(0.0, min(1.0, score))
    
    @staticmethod
    def quality_score_with_ground_truth(text: str, ground_truth: str) -> float:
        """Calculate quality score based on ground truth comparison"""
        if not text or not text.strip():
            return 0.0
        if not ground_truth or not ground_truth.strip():
            return OCREvaluator.quality_score(text)  # Fallback to heuristic
        
        # Calculate similarity-based quality (0.0 to 1.0)
        similarity = OCREvaluator.calculate_similarity(ground_truth, text)
        
        # Calculate error rates and convert to quality scores
        cer = OCREvaluator.calculate_cer(ground_truth, text)
        wer = OCREvaluator.calculate_wer(ground_truth, text)
        
        # Convert error rates to quality scores (capped at reasonable values)
        char_quality = max(0.0, 1.0 - min(cer, 2.0))  # Cap CER at 2.0
        word_quality = max(0.0, 1.0 - min(wer, 2.0))  # Cap WER at 2.0
        
        # Weighted combination: similarity (60%), character accuracy (25%), word accuracy (15%)
        quality = (0.6 * similarity) + (0.25 * char_quality) + (0.15 * word_quality)
        
        return max(0.0, min(1.0, quality))
    
    @classmethod
    def evaluate_ocr_engines(cls, ocr_results: Dict[str, str], ground_truth: Optional[str] = None) -> Dict:
        """Evaluate multiple OCR engines"""
        results = {}
        
        for engine, text in ocr_results.items():
            if not text or str(text).strip() == '' or str(text) == 'nan':
                results[engine] = {
                    'cer': 1.0,
                    'wer': 1.0,
                    'quality_score': 0.0,
                    'similarity_to_ground_truth': 0.0 if ground_truth else None,
                    'text_length': 0
                }
                continue
            
            text = str(text)
            engine_result = {
                'cer': None,
                'wer': None,
                'quality_score': cls.quality_score(text),
                'similarity_to_ground_truth': None,
                'text_length': len(text)
            }
            
            if ground_truth:
                engine_result['cer'] = cls.calculate_cer(ground_truth, text)
                engine_result['wer'] = cls.calculate_wer(ground_truth, text)
                engine_result['similarity_to_ground_truth'] = cls.calculate_similarity(ground_truth, text)
                engine_result['quality_score'] = cls.quality_score_with_ground_truth(text, ground_truth)
            
            results[engine] = engine_result
        
        # Cross-engine similarity if no ground truth
        if not ground_truth and len(ocr_results) > 1:
            engines = list(ocr_results.keys())
            for i, engine1 in enumerate(engines):
                text1 = str(ocr_results[engine1])
                similarities = []
                for j, engine2 in enumerate(engines):
                    if i != j:
                        text2 = str(ocr_results[engine2])
                        if text1 and text2 and text1 != 'nan' and text2 != 'nan':
                            similarities.append(cls.calculate_similarity(text1, text2))
                
                if similarities:
                    results[engine1]['avg_similarity_to_others'] = sum(similarities) / len(similarities)
                else:
                    results[engine1]['avg_similarity_to_others'] = 0.0
        
        return results