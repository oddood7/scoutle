"""
Champion Icons and Visual Elements for ScoutLE
Fetches and manages champion icons from Riot's Data Dragon
"""

import requests
import os
from typing import Dict, Optional
from PIL import Image, ImageTk
import tkinter as tk

class ChampionIconManager:
    """Manages champion icons and visual elements"""
    
    def __init__(self, cache_dir: str = "champion_icons"):
        self.cache_dir = cache_dir
        self.base_url = "https://ddragon.leagueoflegends.com/cdn"
        self.version = None
        self.champion_data = {}
        self.icon_cache = {}
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize with latest version
        self._get_latest_version()
    
    def _get_latest_version(self):
        """Get the latest Data Dragon version"""
        try:
            response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
            if response.status_code == 200:
                versions = response.json()
                self.version = versions[0]  # Latest version
                print(f"✅ Using Data Dragon version: {self.version}")
            else:
                self.version = "13.24.1"  # Fallback version
                print(f"⚠️ Using fallback version: {self.version}")
        except Exception as e:
            self.version = "13.24.1"
            print(f"⚠️ Error fetching version, using fallback: {e}")
    
    def get_champion_icon_url(self, champion_name: str) -> str:
        """Get the URL for a champion's icon"""
        # Clean champion name (remove spaces, special characters)
        clean_name = champion_name.replace(" ", "").replace("'", "").replace(".", "")
        
        # Handle special cases
        special_cases = {
            "Wukong": "MonkeyKing",
            "Kha'Zix": "Khazix",
            "Kai'Sa": "Kaisa",
            "Vel'Koz": "Velkoz",
            "Cho'Gath": "Chogath",
            "Kog'Maw": "Kogmaw",
            "Rek'Sai": "RekSai",
            "Kha'Zix": "Khazix"
        }
        
        icon_name = special_cases.get(champion_name, clean_name)
        return f"{self.base_url}/{self.version}/img/champion/{icon_name}.png"
    
    def download_champion_icon(self, champion_name: str) -> Optional[str]:
        """Download and cache a champion icon"""
        if champion_name in self.icon_cache:
            return self.icon_cache[champion_name]
        
        icon_url = self.get_champion_icon_url(champion_name)
        filename = f"{champion_name.replace(' ', '_').replace("'", '')}.png"
        filepath = os.path.join(self.cache_dir, filename)
        
        # Check if already cached
        if os.path.exists(filepath):
            self.icon_cache[champion_name] = filepath
            return filepath
        
        try:
            response = requests.get(icon_url, timeout=10)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                self.icon_cache[champion_name] = filepath
                print(f"✅ Downloaded icon for {champion_name}")
                return filepath
            else:
                print(f"❌ Failed to download icon for {champion_name}: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error downloading icon for {champion_name}: {e}")
            return None
    
    def get_tkinter_icon(self, champion_name: str, size: tuple = (32, 32)) -> Optional[ImageTk.PhotoImage]:
        """Get a Tkinter-compatible icon for a champion"""
        icon_path = self.download_champion_icon(champion_name)
        if not icon_path:
            return None
        
        try:
            # Load and resize image
            image = Image.open(icon_path)
            image = image.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception as e:
            print(f"❌ Error creating Tkinter icon for {champion_name}: {e}")
            return None
    
    def get_champion_name_from_key(self, champion_key: str) -> str:
        """Convert champion key to display name"""
        # This would ideally use the champion data from Data Dragon
        # For now, return the key as-is
        return champion_key
    
    def create_champion_stat_display(self, champion_stats, parent_widget, icon_size: tuple = (48, 48)):
        """Create a visual display for champion statistics"""
        frame = tk.Frame(parent_widget, relief=tk.RAISED, bd=1)
        
        # Champion icon
        icon = self.get_tkinter_icon(champion_stats.champion_name, icon_size)
        if icon:
            icon_label = tk.Label(frame, image=icon)
            icon_label.image = icon  # Keep a reference
            icon_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Champion name
        name_label = tk.Label(frame, text=champion_stats.champion_name, font=("Arial", 12, "bold"))
        name_label.pack(side=tk.LEFT, padx=5)
        
        # Statistics
        stats_text = f"""Games: {champion_stats.games_played} | Win Rate: {champion_stats.win_rate:.1f}%
KDA: {champion_stats.avg_kda:.2f} | CS/min: {champion_stats.avg_cs_per_min:.1f}
Role: {champion_stats.most_common_role} | Trend: {champion_stats.performance_trend}"""
        
        stats_label = tk.Label(frame, text=stats_text, font=("Arial", 9), justify=tk.LEFT)
        stats_label.pack(side=tk.LEFT, padx=10)
        
        return frame
