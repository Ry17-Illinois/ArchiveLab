#!/usr/bin/env python3
"""
Geographic Mapping for Digital Humanities
Creates heat maps from location entities in documents
"""

import pandas as pd
import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
import json

try:
    import folium
    from folium.plugins import HeatMap
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class GeoMapper:
    def __init__(self):
        self.location_cache = {}
        self.us_states = {
            'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
            'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
            'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
            'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
            'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
            'new hampshire', 'new jersey', 'new mexico', 'new york',
            'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
            'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
            'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
            'west virginia', 'wisconsin', 'wyoming'
        }
        
        # Major US cities with coordinates
        self.us_cities = {
            'new york': (40.7128, -74.0060),
            'los angeles': (34.0522, -118.2437),
            'chicago': (41.8781, -87.6298),
            'houston': (29.7604, -95.3698),
            'philadelphia': (39.9526, -75.1652),
            'phoenix': (33.4484, -112.0740),
            'san antonio': (29.4241, -98.4936),
            'san diego': (32.7157, -117.1611),
            'dallas': (32.7767, -96.7970),
            'san jose': (37.3382, -121.8863),
            'austin': (30.2672, -97.7431),
            'jacksonville': (30.3322, -81.6557),
            'fort worth': (32.7555, -97.3308),
            'columbus': (39.9612, -82.9988),
            'charlotte': (35.2271, -80.8431),
            'san francisco': (37.7749, -122.4194),
            'indianapolis': (39.7684, -86.1581),
            'seattle': (47.6062, -122.3321),
            'denver': (39.7392, -104.9903),
            'washington': (38.9072, -77.0369),
            'boston': (42.3601, -71.0589),
            'el paso': (31.7619, -106.4850),
            'detroit': (42.3314, -83.0458),
            'nashville': (36.1627, -86.7816),
            'memphis': (35.1495, -90.0490),
            'portland': (45.5152, -122.6784),
            'oklahoma city': (35.4676, -97.5164),
            'las vegas': (36.1699, -115.1398),
            'baltimore': (39.2904, -76.6122),
            'milwaukee': (43.0389, -87.9065),
            'albuquerque': (35.0844, -106.6504),
            'tucson': (32.2226, -110.9747),
            'fresno': (36.7378, -119.7871),
            'sacramento': (38.5816, -121.4944),
            'kansas city': (39.0997, -94.5786),
            'mesa': (33.4152, -111.8315),
            'atlanta': (33.7490, -84.3880),
            'omaha': (41.2565, -95.9345),
            'colorado springs': (38.8339, -104.8214),
            'raleigh': (35.7796, -78.6382),
            'miami': (25.7617, -80.1918),
            'virginia beach': (36.8529, -75.9780),
            'oakland': (37.8044, -122.2711),
            'minneapolis': (44.9778, -93.2650),
            'tulsa': (36.1540, -95.9928),
            'arlington': (32.7357, -97.1081),
            'new orleans': (29.9511, -90.0715),
            'wichita': (37.6872, -97.3301)
        }
        
        # World countries/cities with coordinates
        self.world_locations = {
            'london': (51.5074, -0.1278),
            'paris': (48.8566, 2.3522),
            'berlin': (52.5200, 13.4050),
            'rome': (41.9028, 12.4964),
            'madrid': (40.4168, -3.7038),
            'moscow': (55.7558, 37.6176),
            'tokyo': (35.6762, 139.6503),
            'beijing': (39.9042, 116.4074),
            'sydney': (-33.8688, 151.2093),
            'toronto': (43.6532, -79.3832),
            'mexico city': (19.4326, -99.1332),
            'cairo': (30.0444, 31.2357),
            'mumbai': (19.0760, 72.8777),
            'istanbul': (41.0082, 28.9784),
            'buenos aires': (-34.6118, -58.3960),
            'rio de janeiro': (-22.9068, -43.1729),
            'lagos': (6.5244, 3.3792),
            'bangkok': (13.7563, 100.5018),
            'singapore': (1.3521, 103.8198),
            'hong kong': (22.3193, 114.1694),
            'dubai': (25.2048, 55.2708),
            'johannesburg': (-26.2041, 28.0473),
            'stockholm': (59.3293, 18.0686),
            'amsterdam': (52.3676, 4.9041),
            'vienna': (48.2082, 16.3738),
            'zurich': (47.3769, 8.5417),
            'brussels': (50.8503, 4.3517),
            'copenhagen': (55.6761, 12.5683),
            'oslo': (59.9139, 10.7522),
            'helsinki': (60.1699, 24.9384)
        }
    
    def extract_locations_from_entities(self, entities_by_type: Dict) -> List[Dict]:
        """Extract location entities and attempt geocoding"""
        locations = []
        
        if 'GPE' not in entities_by_type:
            return locations
        
        for entity in entities_by_type['GPE']:
            location_name = entity['text'].lower().strip()
            
            # Skip very short or generic terms
            if len(location_name) < 3 or location_name in ['usa', 'us', 'america']:
                continue
            
            coords = self.geocode_location(location_name)
            if coords:
                locations.append({
                    'name': entity['text'],
                    'normalized_name': location_name,
                    'latitude': coords[0],
                    'longitude': coords[1],
                    'filename': entity['filename'],
                    'file_id': entity['file_id'],
                    'is_us': self.is_us_location(location_name)
                })
        
        return locations
    
    def geocode_location(self, location_name: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a location name"""
        location_name = location_name.lower().strip()
        
        # Check cache first
        if location_name in self.location_cache:
            return self.location_cache[location_name]
        
        # Check US cities
        if location_name in self.us_cities:
            coords = self.us_cities[location_name]
            self.location_cache[location_name] = coords
            return coords
        
        # Check world locations
        if location_name in self.world_locations:
            coords = self.world_locations[location_name]
            self.location_cache[location_name] = coords
            return coords
        
        # Check US states (use approximate center coordinates)
        if location_name in self.us_states:
            coords = self.get_state_coordinates(location_name)
            if coords:
                self.location_cache[location_name] = coords
                return coords
        
        # Try online geocoding as fallback (if available)
        if REQUESTS_AVAILABLE:
            coords = self.online_geocode(location_name)
            if coords:
                self.location_cache[location_name] = coords
                return coords
        
        return None
    
    def get_state_coordinates(self, state_name: str) -> Optional[Tuple[float, float]]:
        """Get approximate center coordinates for US states"""
        state_coords = {
            'alabama': (32.806671, -86.791130),
            'alaska': (61.370716, -152.404419),
            'arizona': (33.729759, -111.431221),
            'arkansas': (34.969704, -92.373123),
            'california': (36.116203, -119.681564),
            'colorado': (39.059811, -105.311104),
            'connecticut': (41.597782, -72.755371),
            'delaware': (39.318523, -75.507141),
            'florida': (27.766279, -81.686783),
            'georgia': (33.040619, -83.643074),
            'hawaii': (21.094318, -157.498337),
            'idaho': (44.240459, -114.478828),
            'illinois': (40.349457, -88.986137),
            'indiana': (39.849426, -86.258278),
            'iowa': (42.011539, -93.210526),
            'kansas': (38.526600, -96.726486),
            'kentucky': (37.668140, -84.670067),
            'louisiana': (31.169546, -91.867805),
            'maine': (44.693947, -69.381927),
            'maryland': (39.063946, -76.802101),
            'massachusetts': (42.230171, -71.530106),
            'michigan': (43.326618, -84.536095),
            'minnesota': (45.694454, -93.900192),
            'mississippi': (32.741646, -89.678696),
            'missouri': (38.456085, -92.288368),
            'montana': (47.042418, -109.633835),
            'nebraska': (41.125370, -98.268082),
            'nevada': (38.313515, -117.055374),
            'new hampshire': (43.452492, -71.563896),
            'new jersey': (40.298904, -74.521011),
            'new mexico': (34.840515, -106.248482),
            'new york': (42.165726, -74.948051),
            'north carolina': (35.630066, -79.806419),
            'north dakota': (47.528912, -99.784012),
            'ohio': (40.388783, -82.764915),
            'oklahoma': (35.565342, -96.928917),
            'oregon': (44.572021, -122.070938),
            'pennsylvania': (40.590752, -77.209755),
            'rhode island': (41.680893, -71.511780),
            'south carolina': (33.856892, -80.945007),
            'south dakota': (44.299782, -99.438828),
            'tennessee': (35.747845, -86.692345),
            'texas': (31.054487, -97.563461),
            'utah': (40.150032, -111.862434),
            'vermont': (44.045876, -72.710686),
            'virginia': (37.769337, -78.169968),
            'washington': (47.400902, -121.490494),
            'west virginia': (38.491226, -80.954570),
            'wisconsin': (44.268543, -89.616508),
            'wyoming': (42.755966, -107.302490)
        }
        return state_coords.get(state_name)
    
    def online_geocode(self, location_name: str) -> Optional[Tuple[float, float]]:
        """Attempt online geocoding using Nominatim (OpenStreetMap)"""
        try:
            url = f"https://nominatim.openstreetmap.org/search"
            params = {
                'q': location_name,
                'format': 'json',
                'limit': 1
            }
            headers = {'User-Agent': 'DigitalHumanitiesToolkit/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return (float(data[0]['lat']), float(data[0]['lon']))
        except Exception:
            pass
        
        return None
    
    def is_us_location(self, location_name: str) -> bool:
        """Check if location is in the US"""
        location_name = location_name.lower()
        return (location_name in self.us_cities or 
                location_name in self.us_states or
                any(state in location_name for state in self.us_states))
    
    def create_heat_map(self, locations: List[Dict], focus_us: bool = False) -> str:
        """Create a heat map from location data"""
        if not FOLIUM_AVAILABLE:
            raise ImportError("Folium not available. Install with: pip install folium")
        
        if not locations:
            raise ValueError("No locations to map")
        
        # Filter locations if focusing on US
        if focus_us:
            locations = [loc for loc in locations if loc['is_us']]
            if not locations:
                raise ValueError("No US locations found")
        
        # Count occurrences of each location
        location_counts = Counter()
        for loc in locations:
            key = (loc['latitude'], loc['longitude'])
            location_counts[key] += 1
        
        # Prepare heat map data
        heat_data = []
        for (lat, lon), count in location_counts.items():
            heat_data.append([lat, lon, count])
        
        # Set map center and zoom based on focus
        if focus_us:
            center_lat, center_lon = 39.8283, -98.5795  # Geographic center of US
            zoom_start = 4
            map_title = "US Geographic Heat Map"
        else:
            # Calculate center from all locations
            center_lat = sum(loc['latitude'] for loc in locations) / len(locations)
            center_lon = sum(loc['longitude'] for loc in locations) / len(locations)
            zoom_start = 2
            map_title = "Global Geographic Heat Map"
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles='OpenStreetMap'
        )
        
        # Add heat map layer
        HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)
        
        # Add markers for top locations
        top_locations = location_counts.most_common(10)
        for (lat, lon), count in top_locations:
            # Find location name
            location_name = "Unknown"
            for loc in locations:
                if loc['latitude'] == lat and loc['longitude'] == lon:
                    location_name = loc['name']
                    break
            
            folium.Marker(
                [lat, lon],
                popup=f"{location_name}: {count} mentions",
                tooltip=f"{location_name} ({count})"
            ).add_to(m)
        
        return m
    
    def get_location_statistics(self, locations: List[Dict]) -> Dict:
        """Get statistics about locations"""
        if not locations:
            return {}
        
        us_locations = [loc for loc in locations if loc['is_us']]
        international_locations = [loc for loc in locations if not loc['is_us']]
        
        # Count by location name
        location_counts = Counter(loc['name'] for loc in locations)
        
        # Count by document
        docs_by_location = defaultdict(set)
        for loc in locations:
            docs_by_location[loc['name']].add(loc['filename'])
        
        return {
            'total_locations': len(locations),
            'unique_locations': len(set(loc['name'] for loc in locations)),
            'us_locations': len(us_locations),
            'international_locations': len(international_locations),
            'most_mentioned': location_counts.most_common(10),
            'documents_by_location': {name: len(docs) for name, docs in docs_by_location.items()},
            'geographic_spread': {
                'min_lat': min(loc['latitude'] for loc in locations),
                'max_lat': max(loc['latitude'] for loc in locations),
                'min_lon': min(loc['longitude'] for loc in locations),
                'max_lon': max(loc['longitude'] for loc in locations)
            }
        }
    
    def export_locations(self, locations: List[Dict], filepath: str, format: str = 'csv'):
        """Export location data"""
        if not locations:
            raise ValueError("No locations to export")
        
        df = pd.DataFrame(locations)
        
        if format == 'csv':
            df.to_csv(f"{filepath}_locations.csv", index=False)
        elif format == 'json':
            df.to_json(f"{filepath}_locations.json", orient='records', indent=2)
        elif format == 'geojson':
            # Create GeoJSON format
            features = []
            for loc in locations:
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [loc['longitude'], loc['latitude']]
                    },
                    "properties": {
                        "name": loc['name'],
                        "filename": loc['filename'],
                        "is_us": loc['is_us']
                    }
                }
                features.append(feature)
            
            geojson_data = {
                "type": "FeatureCollection",
                "features": features
            }
            
            with open(f"{filepath}_locations.geojson", 'w') as f:
                json.dump(geojson_data, f, indent=2)