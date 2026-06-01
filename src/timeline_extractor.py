#!/usr/bin/env python3
"""
Timeline Extraction for Digital Humanities
Extracts and analyzes temporal information from documents
"""

import pandas as pd
import re
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

try:
    import dateutil.parser as date_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False

class TimelineExtractor:
    def __init__(self):
        self.date_patterns = [
            # Full dates
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            
            # Years only
            r'\b(?:19|20)\d{2}\b',
            
            # Decades
            r'\b\d{4}s\b',
            
            # Relative dates
            r'\b(?:early|mid|late)\s+(?:19|20)\d{2}s?\b',
            
            # Seasons with years
            r'\b(?:Spring|Summer|Fall|Autumn|Winter)\s+(?:19|20)\d{2}\b',
            
            # Month/Year combinations
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\b'
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.date_patterns]
        
        # Historical period keywords
        self.period_keywords = {
            'colonial': (1600, 1776),
            'revolutionary': (1775, 1783),
            'antebellum': (1815, 1861),
            'civil war': (1861, 1865),
            'reconstruction': (1865, 1877),
            'gilded age': (1870, 1900),
            'progressive era': (1890, 1920),
            'great depression': (1929, 1939),
            'world war': (1914, 1918, 1939, 1945),
            'postwar': (1945, 1960),
            'cold war': (1947, 1991)
        }
    
    def extract_dates_from_text(self, text: str) -> List[Dict]:
        """Extract date mentions from text"""
        if not text or str(text) == 'nan':
            return []
        
        text = str(text)
        dates_found = []
        
        # Extract using regex patterns
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            for match in matches:
                date_info = self.parse_date_string(match)
                if date_info:
                    dates_found.append({
                        'raw_text': match,
                        'parsed_date': date_info['date'],
                        'confidence': date_info['confidence'],
                        'type': date_info['type']
                    })
        
        # Extract historical periods
        for period, years in self.period_keywords.items():
            if period.lower() in text.lower():
                if len(years) == 2:  # Single period
                    dates_found.append({
                        'raw_text': period,
                        'parsed_date': years[0],
                        'confidence': 0.7,
                        'type': 'period'
                    })
                elif len(years) == 4:  # Multiple periods (like world wars)
                    dates_found.append({
                        'raw_text': f"{period} I",
                        'parsed_date': years[0],
                        'confidence': 0.7,
                        'type': 'period'
                    })
                    dates_found.append({
                        'raw_text': f"{period} II",
                        'parsed_date': years[2],
                        'confidence': 0.7,
                        'type': 'period'
                    })
        
        return dates_found
    
    def parse_date_string(self, date_str: str) -> Optional[Dict]:
        """Parse a date string into structured information"""
        date_str = date_str.strip()
        
        # Handle decades (e.g., "1920s")
        if date_str.endswith('s') and date_str[:-1].isdigit():
            year = int(date_str[:-1])
            return {
                'date': year,
                'confidence': 0.8,
                'type': 'decade'
            }
        
        # Handle relative dates (e.g., "early 1920s")
        relative_match = re.match(r'(early|mid|late)\s+(\d{4})s?', date_str, re.IGNORECASE)
        if relative_match:
            modifier, year = relative_match.groups()
            base_year = int(year)
            if modifier.lower() == 'early':
                year_offset = 2
            elif modifier.lower() == 'mid':
                year_offset = 5
            else:  # late
                year_offset = 8
            
            return {
                'date': base_year + year_offset,
                'confidence': 0.6,
                'type': 'relative'
            }
        
        # Handle seasons with years
        season_match = re.match(r'(Spring|Summer|Fall|Autumn|Winter)\s+(\d{4})', date_str, re.IGNORECASE)
        if season_match:
            season, year = season_match.groups()
            return {
                'date': int(year),
                'confidence': 0.9,
                'type': 'seasonal'
            }
        
        # Handle year-only dates
        if re.match(r'^\d{4}$', date_str):
            year = int(date_str)
            if 1000 <= year <= 2100:  # Reasonable year range
                return {
                    'date': year,
                    'confidence': 0.9,
                    'type': 'year'
                }
        
        # Handle full dates using dateutil if available
        if DATEUTIL_AVAILABLE:
            try:
                parsed_date = date_parser.parse(date_str, fuzzy=True)
                return {
                    'date': parsed_date.year,
                    'confidence': 0.95,
                    'type': 'full_date',
                    'month': parsed_date.month,
                    'day': parsed_date.day
                }
            except:
                pass
        
        # Fallback manual parsing for common formats
        # MM/DD/YYYY or DD/MM/YYYY
        date_match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
        if date_match:
            month, day, year = map(int, date_match.groups())
            if 1 <= month <= 12 and 1 <= day <= 31 and 1000 <= year <= 2100:
                return {
                    'date': year,
                    'confidence': 0.85,
                    'type': 'full_date',
                    'month': month,
                    'day': day
                }
        
        return None
    
    def extract_timeline_from_ledger(self, ledger_df: pd.DataFrame, ocr_source: str = 'easyocr') -> List[Dict]:
        """Extract timeline from all documents in ledger"""
        timeline_events = []
        
        for _, row in ledger_df.iterrows():
            # Get OCR text from specified source
            if ocr_source == 'openai_ocr':
                text = row.get('openai_ocr_ocr', '')
            elif ocr_source == 'ollama_ocr':
                text = row.get('ollama_ocr_ocr', '')
            else:
                text = row.get(f'{ocr_source}_ocr', '')
            
            # Extract dates from text
            dates = self.extract_dates_from_text(text)
            
            for date_info in dates:
                timeline_events.append({
                    'filename': row['filename'],
                    'file_id': row['file_id'],
                    'date_text': date_info['raw_text'],
                    'year': date_info['parsed_date'],
                    'confidence': date_info['confidence'],
                    'type': date_info['type'],
                    'month': date_info.get('month'),
                    'day': date_info.get('day')
                })
        
        # Sort by year
        timeline_events.sort(key=lambda x: x['year'])
        
        return timeline_events
    
    def get_timeline_statistics(self, timeline_events: List[Dict]) -> Dict:
        """Get statistics about the timeline"""
        if not timeline_events:
            return {}
        
        years = [event['year'] for event in timeline_events]
        
        # Group by decade
        decades = defaultdict(int)
        for year in years:
            decade = (year // 10) * 10
            decades[decade] += 1
        
        # Group by document
        docs_by_year = defaultdict(set)
        for event in timeline_events:
            docs_by_year[event['year']].add(event['filename'])
        
        return {
            'total_events': len(timeline_events),
            'unique_years': len(set(years)),
            'year_range': (min(years), max(years)),
            'decades': dict(decades),
            'documents_by_year': {year: len(docs) for year, docs in docs_by_year.items()},
            'most_common_years': sorted([(year, len(docs)) for year, docs in docs_by_year.items()], 
                                      key=lambda x: x[1], reverse=True)[:10]
        }
    
    def filter_timeline(self, timeline_events: List[Dict], 
                       start_year: Optional[int] = None, 
                       end_year: Optional[int] = None,
                       min_confidence: float = 0.5) -> List[Dict]:
        """Filter timeline events by criteria"""
        filtered = timeline_events
        
        if start_year:
            filtered = [e for e in filtered if e['year'] >= start_year]
        
        if end_year:
            filtered = [e for e in filtered if e['year'] <= end_year]
        
        if min_confidence:
            filtered = [e for e in filtered if e['confidence'] >= min_confidence]
        
        return filtered
    
    def export_timeline(self, timeline_events: List[Dict], filepath: str, format: str = 'csv'):
        """Export timeline to file"""
        if not timeline_events:
            raise ValueError("No timeline events to export")
        
        df = pd.DataFrame(timeline_events)
        
        if format == 'csv':
            df.to_csv(f"{filepath}_timeline.csv", index=False)
        elif format == 'json':
            df.to_json(f"{filepath}_timeline.json", orient='records', indent=2)
        elif format == 'timeline_js':
            # Export in TimelineJS format
            timeline_data = {
                "events": []
            }
            
            for event in timeline_events:
                timeline_entry = {
                    "start_date": {
                        "year": str(event['year'])
                    },
                    "text": {
                        "headline": event['date_text'],
                        "text": f"From document: {event['filename']}"
                    }
                }
                
                if event.get('month'):
                    timeline_entry["start_date"]["month"] = str(event['month'])
                if event.get('day'):
                    timeline_entry["start_date"]["day"] = str(event['day'])
                
                timeline_data["events"].append(timeline_entry)
            
            import json
            with open(f"{filepath}_timeline.json", 'w') as f:
                json.dump(timeline_data, f, indent=2)