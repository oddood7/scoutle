"""
Storage system for manually added matches
Allows tracking custom games, tournament games, or specific matches
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class ManualMatch:
    """Represents a manually added match"""
    match_id: str
    summoner_name: str
    champion_name: str
    result: str  # "WIN" or "LOSS"
    kills: float
    deaths: float
    assists: float
    cs: float
    game_duration: int  # in minutes
    queue_type: str  # "custom", "tournament", "soloq", "flex", etc.
    date: str
    notes: str = ""
    
    @property
    def kda(self):
        """Calculate KDA"""
        if self.deaths == 0:
            return self.kills + self.assists
        return (self.kills + self.assists) / self.deaths
    
    @property
    def cs_per_min(self):
        """Calculate CS per minute"""
        if self.game_duration == 0:
            return 0
        return self.cs / self.game_duration

class ManualMatchStorage:
    """Manages storage and retrieval of manual matches"""
    
    def __init__(self, storage_file: str = "manual_matches.json"):
        self.storage_file = storage_file
        self.matches: List[ManualMatch] = []
        self.load_matches()
    
    def load_matches(self):
        """Load matches from JSON file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.matches = [ManualMatch(**match) for match in data]
                print(f"✅ Loaded {len(self.matches)} manual matches from {self.storage_file}")
            except Exception as e:
                print(f"⚠️ Error loading manual matches: {e}")
                self.matches = []
        else:
            self.matches = []
    
    def save_matches(self):
        """Save matches to JSON file"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                data = [asdict(match) for match in self.matches]
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(self.matches)} manual matches to {self.storage_file}")
        except Exception as e:
            print(f"⚠️ Error saving manual matches: {e}")
    
    def add_match(self, match: ManualMatch):
        """Add a new manual match"""
        # Check if match ID already exists
        if any(m.match_id == match.match_id for m in self.matches):
            print(f"⚠️ Match ID {match.match_id} already exists")
            return False
        
        self.matches.append(match)
        self.save_matches()
        print(f"✅ Added manual match: {match.champion_name} ({match.result})")
        return True
    
    def remove_match(self, match_id: str):
        """Remove a match by ID"""
        original_count = len(self.matches)
        self.matches = [m for m in self.matches if m.match_id != match_id]
        
        if len(self.matches) < original_count:
            self.save_matches()
            print(f"✅ Removed match {match_id}")
            return True
        else:
            print(f"⚠️ Match ID {match_id} not found")
            return False
    
    def get_matches_for_summoner(self, summoner_name: str) -> List[ManualMatch]:
        """Get all matches for a specific summoner"""
        return [m for m in self.matches if m.summoner_name.lower() == summoner_name.lower()]
    
    def get_champion_stats(self, summoner_name: str, champion_name: str) -> Dict:
        """Get aggregated stats for a champion"""
        matches = [m for m in self.matches 
                  if m.summoner_name.lower() == summoner_name.lower() 
                  and m.champion_name.lower() == champion_name.lower()]
        
        if not matches:
            return None
        
        games = len(matches)
        wins = sum(1 for m in matches if m.result == "WIN")
        losses = games - wins
        win_rate = (wins / games * 100) if games > 0 else 0
        
        total_kills = sum(m.kills for m in matches)
        total_deaths = sum(m.deaths for m in matches)
        total_assists = sum(m.assists for m in matches)
        total_cs = sum(m.cs for m in matches)
        total_duration = sum(m.game_duration for m in matches)
        
        avg_kills = total_kills / games
        avg_deaths = total_deaths / games
        avg_assists = total_assists / games
        avg_kda = (total_kills + total_assists) / total_deaths if total_deaths > 0 else total_kills + total_assists
        avg_cs_per_min = total_cs / total_duration if total_duration > 0 else 0
        
        return {
            'champion_name': champion_name,
            'games_played': games,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'kills': avg_kills,
            'deaths': avg_deaths,
            'assists': avg_assists,
            'kda': avg_kda,
            'cs_per_min': avg_cs_per_min
        }
    
    def get_all_champion_stats(self, summoner_name: str) -> List[Dict]:
        """Get stats for all champions played"""
        matches = self.get_matches_for_summoner(summoner_name)
        
        # Group by champion
        champions = set(m.champion_name for m in matches)
        
        stats = []
        for champion in champions:
            champion_stats = self.get_champion_stats(summoner_name, champion)
            if champion_stats:
                stats.append(champion_stats)
        
        # Sort by games played
        stats.sort(key=lambda x: x['games_played'], reverse=True)
        
        return stats
    
    def clear_all_matches(self):
        """Clear all matches"""
        self.matches = []
        self.save_matches()
        print("✅ Cleared all manual matches")

# Example usage
if __name__ == "__main__":
    storage = ManualMatchStorage()
    
    # Add a test match
    test_match = ManualMatch(
        match_id="MANUAL_001",
        summoner_name="TestPlayer",
        champion_name="Ahri",
        result="WIN",
        kills=10.0,
        deaths=3.0,
        assists=8.0,
        cs=180.0,
        game_duration=25,
        queue_type="tournament",
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        notes="Tournament finals"
    )
    
    storage.add_match(test_match)
    
    # Get stats
    stats = storage.get_all_champion_stats("TestPlayer")
    print(f"\nChampion stats: {stats}")
