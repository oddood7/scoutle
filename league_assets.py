"""
League of Legends Asset Manager
Downloads and caches champion, item, and rune icons from Data Dragon
"""

import requests
import json
from PIL import Image, ImageTk
from io import BytesIO
from typing import Optional, Dict
import os

class LeagueAssets:
    """Manages League of Legends assets from Data Dragon"""
    
    def __init__(self):
        self.version = "15.1.1"
        self.base_url = f"https://ddragon.leagueoflegends.com/cdn/{self.version}"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://www.leagueoflegends.com/'
        })
        
        # Cache for images
        self.image_cache: Dict[str, ImageTk.PhotoImage] = {}
        
        # Load item and rune mappings
        self.items: Dict[str, str] = {}  # name -> id
        self.runes: Dict[str, str] = {}  # name -> icon path
        self.champions: Dict[str, str] = {}  # lowercase name -> correct ID
        self._load_champion_data()
        self._load_item_data()
        self._load_rune_data()
    
    def _load_champion_data(self):
        """Load champion name mappings"""
        try:
            url = f"{self.base_url}/data/en_US/champion.json"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            # Create mapping: various forms of name -> Data Dragon ID
            for champ_id, champ_data in data['data'].items():
                name = champ_data['name']
                # Store: "kai'sa" -> "Kaisa", "kaisa" -> "Kaisa", etc.
                self.champions[name.lower().replace("'", "").replace(" ", "")] = champ_id
            
            print(f"✅ Loaded {len(self.champions)} champions")
        except Exception as e:
            print(f"⚠️ Could not load champion data: {e}")
    
    def _load_item_data(self):
        """Load item name to ID mapping"""
        try:
            url = f"{self.base_url}/data/en_US/item.json"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            for item_id, item_data in data['data'].items():
                name = item_data['name']
                self.items[name] = item_id
            
            print(f"✅ Loaded {len(self.items)} items")
        except Exception as e:
            print(f"⚠️ Could not load item data: {e}")
    
    def _load_rune_data(self):
        """Load rune name to icon path mapping"""
        try:
            url = f"https://ddragon.leagueoflegends.com/cdn/{self.version}/data/en_US/runesReforged.json"
            response = self.session.get(url, timeout=10)
            runes_data = response.json()
            
            for tree in runes_data:
                for slot in tree['slots']:
                    for rune in slot['runes']:
                        # Icon path relative to CDN
                        icon_path = rune['icon']
                        self.runes[rune['name']] = icon_path
            
            print(f"✅ Loaded {len(self.runes)} runes")
        except Exception as e:
            print(f"⚠️ Could not load rune data: {e}")
    
    def get_champion_icon(self, champion_name: str, size: int = 48) -> Optional[ImageTk.PhotoImage]:
        """Get champion icon as PhotoImage"""
        cache_key = f"champ_{champion_name}_{size}"
        
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        try:
            # Look up correct champion ID from mapping
            lookup_name = champion_name.lower().replace("'", "").replace(" ", "")
            champ_id = self.champions.get(lookup_name)
            
            if not champ_id:
                print(f"⚠️ Champion '{champion_name}' not found in Data Dragon")
                return None
            
            url = f"{self.base_url}/img/champion/{champ_id}.png"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_cache[cache_key] = photo
                return photo
        except Exception as e:
            print(f"⚠️ Could not load champion icon for {champion_name}: {e}")
        
        return None
    
    def get_item_icon(self, item_name: str, size: int = 32) -> Optional[ImageTk.PhotoImage]:
        """Get item icon as PhotoImage"""
        cache_key = f"item_{item_name}_{size}"
        
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        try:
            # Find item ID
            item_id = self.items.get(item_name)
            if not item_id:
                # Try partial match
                for name, id_ in self.items.items():
                    if item_name.lower() in name.lower():
                        item_id = id_
                        break
            
            if not item_id:
                return None
            
            url = f"{self.base_url}/img/item/{item_id}.png"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_cache[cache_key] = photo
                return photo
        except Exception as e:
            print(f"⚠️ Could not load item icon for {item_name}: {e}")
        
        return None
    
    def get_rune_icon(self, rune_name: str, size: int = 32) -> Optional[ImageTk.PhotoImage]:
        """Get rune icon as PhotoImage"""
        cache_key = f"rune_{rune_name}_{size}"
        
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        
        try:
            # Find rune icon path
            icon_path = self.runes.get(rune_name)
            if not icon_path:
                # Try partial match
                for name, path in self.runes.items():
                    if rune_name.lower() in name.lower():
                        icon_path = path
                        break
            
            if not icon_path:
                return None
            
            url = f"https://ddragon.leagueoflegends.com/cdn/img/{icon_path}"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_cache[cache_key] = photo
                return photo
        except Exception as e:
            print(f"⚠️ Could not load rune icon for {rune_name}: {e}")
        
        return None


# Test if run directly
if __name__ == "__main__":
    assets = LeagueAssets()
    
    print("\n🧪 Testing Asset Manager:")
    print(f"  • Items loaded: {len(assets.items)}")
    print(f"  • Runes loaded: {len(assets.runes)}")
    print(f"  • Infinity Edge ID: {assets.items.get('Infinity Edge')}")
    print(f"  • Lethal Tempo path: {assets.runes.get('Lethal Tempo')}")
