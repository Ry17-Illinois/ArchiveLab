#!/usr/bin/env python3
"""
BERT-based Topic Modeling for Digital Humanities
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import re

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation, NMF
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    TOPIC_MODELING_AVAILABLE = True
except ImportError:
    TOPIC_MODELING_AVAILABLE = False

class TopicModeler:
    def __init__(self):
        self.model = None
        self.topics = None
        self.probabilities = None
        self.documents = None
        
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for topic modeling"""
        if not text or str(text) == 'nan':
            return ""
        
        # Convert to string and clean
        text = str(text)
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove very short texts (less than 10 characters)
        if len(text.strip()) < 10:
            return ""
        
        return text.strip()
    
    def extract_documents_from_ledger(self, ledger_df: pd.DataFrame, ocr_source: str = 'easyocr') -> List[str]:
        """Extract and preprocess documents from ledger"""
        documents = []
        
        for _, row in ledger_df.iterrows():
            # Get OCR text from specified source
            if ocr_source == 'openai_ocr':
                text = row.get('openai_ocr_ocr', '')
            elif ocr_source == 'ollama_ocr':
                text = row.get('ollama_ocr_ocr', '')
            else:
                text = row.get(f'{ocr_source}_ocr', '')
            
            # Preprocess text
            clean_text = self.preprocess_text(text)
            if clean_text:
                documents.append(clean_text)
        
        return documents
    
    def fit_model(self, documents: List[str], num_topics: int = 10, method: str = 'lda') -> Dict:
        """Fit topic model to documents using LDA, NMF, or BERT+KMeans"""
        if not TOPIC_MODELING_AVAILABLE:
            raise ImportError("Topic modeling dependencies not available. Install with: pip install scikit-learn sentence-transformers")
        
        if len(documents) < 3:
            raise ValueError("Need at least 3 documents for topic modeling")
        
        # Filter out empty documents
        documents = [doc for doc in documents if doc.strip()]
        self.documents = documents
        
        if len(documents) < 3:
            raise ValueError("Not enough valid documents after preprocessing")
        
        if method == 'bert_kmeans':
            return self._fit_bert_kmeans(documents, num_topics)
        elif method == 'nmf':
            return self._fit_nmf(documents, num_topics)
        else:  # Default to LDA
            return self._fit_lda(documents, num_topics)
    
    def _fit_lda(self, documents: List[str], num_topics: int) -> Dict:
        """Fit LDA topic model"""
        # Vectorize documents
        self.vectorizer = CountVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        doc_term_matrix = self.vectorizer.fit_transform(documents)
        
        # Fit LDA model
        self.model = LatentDirichletAllocation(
            n_components=num_topics,
            random_state=42,
            max_iter=10,
            learning_method='online'
        )
        
        self.topics = self.model.fit_transform(doc_term_matrix)
        
        # Get topic assignments (highest probability topic for each doc)
        self.topic_assignments = np.argmax(self.topics, axis=1)
        
        return {
            'num_topics': num_topics,
            'method': 'LDA',
            'documents_processed': len(documents)
        }
    
    def _fit_nmf(self, documents: List[str], num_topics: int) -> Dict:
        """Fit NMF topic model"""
        # Vectorize documents with TF-IDF
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        doc_term_matrix = self.vectorizer.fit_transform(documents)
        
        # Fit NMF model
        self.model = NMF(
            n_components=num_topics,
            random_state=42,
            max_iter=100
        )
        
        self.topics = self.model.fit_transform(doc_term_matrix)
        
        # Get topic assignments
        self.topic_assignments = np.argmax(self.topics, axis=1)
        
        return {
            'num_topics': num_topics,
            'method': 'NMF',
            'documents_processed': len(documents)
        }
    
    def _fit_bert_kmeans(self, documents: List[str], num_topics: int) -> Dict:
        """Fit BERT embeddings + KMeans clustering"""
        # Generate BERT embeddings
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = embedding_model.encode(documents)
        
        # Cluster embeddings
        self.model = KMeans(n_clusters=num_topics, random_state=42, n_init=10)
        self.topic_assignments = self.model.fit_predict(embeddings)
        
        # Create topic probabilities (distance-based)
        distances = self.model.transform(embeddings)
        self.topics = 1 / (1 + distances)  # Convert distances to similarities
        
        # Vectorize for keyword extraction
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.vectorizer.fit(documents)
        
        return {
            'num_topics': num_topics,
            'method': 'BERT+KMeans',
            'documents_processed': len(documents)
        }
    
    def get_topic_keywords(self, topic_id: int, num_words: int = 10) -> List[Tuple[str, float]]:
        """Get keywords for a specific topic"""
        if self.model is None or self.vectorizer is None:
            return []
        
        try:
            if hasattr(self.model, 'components_'):  # LDA or NMF
                feature_names = self.vectorizer.get_feature_names_out()
                topic_words = self.model.components_[topic_id]
                top_indices = topic_words.argsort()[-num_words:][::-1]
                return [(feature_names[i], topic_words[i]) for i in top_indices]
            else:  # BERT+KMeans
                # Get documents in this topic
                topic_docs = [self.documents[i] for i, t in enumerate(self.topic_assignments) if t == topic_id]
                if not topic_docs:
                    return []
                
                # Vectorize topic documents
                topic_matrix = self.vectorizer.transform(topic_docs)
                topic_scores = np.mean(topic_matrix.toarray(), axis=0)
                
                feature_names = self.vectorizer.get_feature_names_out()
                top_indices = topic_scores.argsort()[-num_words:][::-1]
                return [(feature_names[i], topic_scores[i]) for i in top_indices]
        except Exception:
            return []
    
    def get_document_topics(self) -> List[Tuple[int, str, float]]:
        """Get topic assignments for all documents"""
        if self.model is None or self.topic_assignments is None:
            return []
        
        results = []
        for i, topic_id in enumerate(self.topic_assignments):
            doc_preview = self.documents[i][:100] + "..." if len(self.documents[i]) > 100 else self.documents[i]
            # Get probability for assigned topic
            prob = self.topics[i][topic_id] if hasattr(self.topics, 'shape') and len(self.topics.shape) > 1 else 1.0
            results.append((topic_id, doc_preview, float(prob)))
        
        return results
    
    def get_topic_summary(self) -> Dict:
        """Get summary of all topics"""
        if self.model is None or self.topic_assignments is None:
            return {}
        
        summary = {}
        unique_topics = np.unique(self.topic_assignments)
        
        for topic_id in unique_topics:
            keywords = self.get_topic_keywords(topic_id, 5)
            keyword_str = ", ".join([word for word, _ in keywords])
            count = np.sum(self.topic_assignments == topic_id)
            
            summary[int(topic_id)] = {
                'keywords': keyword_str,
                'count': int(count),
                'name': f'Topic {topic_id}'
            }
        
        return summary
    
    def search_topics_by_keywords(self, query: str) -> List[Tuple[int, str, float]]:
        """Search topics by keyword similarity"""
        if self.model is None or self.vectorizer is None:
            return []
        
        try:
            # Vectorize query
            query_vec = self.vectorizer.transform([query])
            
            results = []
            topic_summary = self.get_topic_summary()
            
            for topic_id in topic_summary.keys():
                # Get topic documents
                topic_docs = [self.documents[i] for i, t in enumerate(self.topic_assignments) if t == topic_id]
                if topic_docs:
                    # Calculate similarity
                    topic_vecs = self.vectorizer.transform(topic_docs)
                    similarities = cosine_similarity(query_vec, topic_vecs)
                    avg_similarity = np.mean(similarities)
                    
                    keywords = topic_summary[topic_id]['keywords']
                    results.append((topic_id, keywords, float(avg_similarity)))
            
            # Sort by similarity
            results.sort(key=lambda x: x[2], reverse=True)
            return results[:5]
        except Exception:
            return []
    
    def export_results(self, filepath: str, format: str = 'csv'):
        """Export topic modeling results"""
        if self.model is None:
            raise ValueError("No model fitted yet")
        
        if format == 'csv':
            # Export topic info
            topic_info = self.model.get_topic_info()
            topic_info.to_csv(f"{filepath}_topics.csv", index=False)
            
            # Export document-topic assignments
            doc_topics = []
            for i, (topic, prob) in enumerate(zip(self.topics, self.probabilities)):
                doc_topics.append({
                    'document_id': i,
                    'topic': topic,
                    'probability': prob,
                    'text_preview': self.documents[i][:200]
                })
            
            pd.DataFrame(doc_topics).to_csv(f"{filepath}_document_topics.csv", index=False)
            
        elif format == 'json':
            import json
            
            results = {
                'topic_summary': self.get_topic_summary(),
                'document_topics': self.get_document_topics(),
                'model_info': {
                    'num_documents': len(self.documents),
                    'num_topics': len(self.get_topic_summary())
                }
            }
            
            with open(f"{filepath}_topics.json", 'w') as f:
                json.dump(results, f, indent=2, default=str)