#!/usr/bin/env python3
"""
Entity Matcher - Find similar named entities across documents
"""

from difflib import SequenceMatcher
from collections import defaultdict
import re

class EntityMatcher:
    def __init__(self):
        self.similarity_threshold = 0.8
        self.nickname_patterns = {
            'PERSON': [
                (r'\b(William|Bill|Billy)\b', 'William'),
                (r'\b(Robert|Bob|Bobby)\b', 'Robert'),
                (r'\b(Richard|Rick|Dick)\b', 'Richard'),
                (r'\b(James|Jim|Jimmy)\b', 'James'),
                (r'\b(Michael|Mike|Mickey)\b', 'Michael'),
                (r'\b(Elizabeth|Liz|Beth|Betty)\b', 'Elizabeth'),
                (r'\b(Margaret|Maggie|Peggy)\b', 'Margaret'),
                (r'\b(Catherine|Kate|Cathy)\b', 'Catherine')
            ]
        }
    
    def extract_entities_from_ledger(self, ledger_df):
        """Extract all entities from ledger data"""
        entities_by_type = defaultdict(list)
        
        for _, row in ledger_df.iterrows():
            entities_text = row.get('named_entities', '')
            if not entities_text or entities_text == 'nan' or str(entities_text) == 'nan':
                continue
            
            # Convert to string and parse entities
            entities_text = str(entities_text)
            
            # Handle emoji-formatted output: "🏢 Organizations: Company1, Company2"
            lines = entities_text.replace('\n', ' | ').split('|')
            
            for entity_group in lines:
                entity_group = entity_group.strip()
                if ':' in entity_group:
                    # Remove emoji and extract type and entities
                    parts = entity_group.split(':', 1)
                    entity_type_raw = parts[0].strip()
                    entities_raw = parts[1].strip()
                    
                    # Map display names to standard types
                    type_mapping = {
                        'Organizations': 'ORG',
                        'People': 'PERSON', 
                        'Locations': 'GPE',
                        'Dates': 'DATE',
                        'Money': 'MONEY'
                    }
                    
                    # Clean entity type (remove emojis and map to standard)
                    entity_type = entity_type_raw
                    for display_name, standard_type in type_mapping.items():
                        if display_name in entity_type_raw:
                            entity_type = standard_type
                            break
                    
                    # Extract individual entities
                    for entity in entities_raw.split(','):
                        entity = entity.strip()
                        if entity and entity != 'None found':
                            entities_by_type[entity_type].append({
                                'text': entity,
                                'file_id': row['file_id'],
                                'filename': row['filename']
                            })
        
        return entities_by_type
    
    def find_similar_entities(self, entities_list, entity_type='PERSON'):
        """Find similar entities using string similarity and nickname matching"""
        groups = []
        processed = set()
        
        for i, entity1 in enumerate(entities_list):
            if i in processed:
                continue
            
            group = [entity1]
            processed.add(i)
            
            for j, entity2 in enumerate(entities_list[i+1:], i+1):
                if j in processed:
                    continue
                
                if self._are_similar(entity1['text'], entity2['text'], entity_type):
                    group.append(entity2)
                    processed.add(j)
            
            if len(group) > 1:  # Only groups with matches
                groups.append(group)
        
        return groups
    
    def _are_similar(self, text1, text2, entity_type):
        """Check if two entity texts are similar"""
        # Exact match
        if text1.lower() == text2.lower():
            return True
        
        # Nickname matching for persons
        if entity_type == 'PERSON':
            if self._check_nicknames(text1, text2):
                return True
        
        # String similarity
        similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        return similarity >= self.similarity_threshold
    
    def _check_nicknames(self, name1, name2):
        """Check if names are nickname variants"""
        for pattern, canonical in self.nickname_patterns.get('PERSON', []):
            if re.search(pattern, name1, re.IGNORECASE) and re.search(pattern, name2, re.IGNORECASE):
                return True
        
        # Check if one name is contained in the other (e.g., "John" in "John Smith")
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        return bool(words1.intersection(words2))
    
    def get_entity_statistics(self, entities_by_type):
        """Get statistics about entities"""
        stats = {}
        
        for entity_type, entities in entities_by_type.items():
            unique_entities = {}
            for entity in entities:
                text = entity['text']
                if text not in unique_entities:
                    unique_entities[text] = []
                unique_entities[text].append(entity)
            
            stats[entity_type] = {
                'total_mentions': len(entities),
                'unique_entities': len(unique_entities),
                'entities': unique_entities
            }
        
        return stats