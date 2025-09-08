"""
Tournament Game Scraper for ScoutLE
Detects and analyzes tournament games from op.gg match history
"""

import requests
import re
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from dataclasses import dataclass
from urllib.parse import quote
from datetime import datetime

@dataclass
class TournamentGame:
    """Tournament game data"""
    game_id: str
    game_type: str  # "CUSTOM", "TOURNAMENT", "OFFICIAL"
    tournament_code: str
    date: str
    duration: int  # in seconds
    result: str  # "WIN" or "LOSS"
    champion: str
    role: str
    kills: int
    deaths: int
    assists: int
    kda: float
    cs: int
    gold: int
    damage: int
    vision_score: int
    team_composition: List[str]
    enemy_composition: List[str]

@dataclass
class TournamentStats:
    """Tournament statistics summary"""
    total_tournament_games: int
    tournament_wins: int
    tournament_losses: int
    tournament_win_rate: float
    most_played_champion: str
    best_performing_champion: str
    average_kda: float
    average_cs: float
    average_damage: float
    tournament_codes: List[str]
    recent_tournaments: List[TournamentGame]

class TournamentScraper:
    """Scraper for tournament games from op.gg"""
    
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def scrape_tournament_games(self, summoner_name: str, region: str = "euw") -> Optional[TournamentStats]:
        """Scrape tournament games from op.gg match history"""
        try:
            # Handle Riot ID format
            if '#' in summoner_name:
                name, tag = summoner_name.split('#', 1)
                clean_name = f"{name}-{tag}"
            else:
                clean_name = summoner_name
            
            # URL encode the summoner name
            encoded_name = quote(clean_name, safe='+-')
            
            # Try to access match history page
            match_history_url = f"https://op.gg/lol/summoners/{region}/{encoded_name}/matches"
            
            print(f"🔍 Scraping tournament games for: {summoner_name} ({region})")
            print(f"   URL: {match_history_url}")
            
            response = self.session.get(match_history_url, timeout=15)
            
            if response.status_code == 200:
                print(f"   ✅ Successfully accessed match history")
                return self._parse_tournament_games(response.content, summoner_name, region)
            else:
                print(f"   ❌ Failed to access match history: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error scraping tournament games for {summoner_name}: {e}")
            return None
    
    def _parse_tournament_games(self, html_content: bytes, summoner_name: str, region: str) -> TournamentStats:
        """Parse tournament games from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        page_text = soup.get_text()
        
        tournament_games = []
        tournament_codes = set()
        
        try:
            # Look for CUSTOM games and tournament indicators
            # Tournament games often have specific patterns in op.gg
            
            # Method 1: Look for "CUSTOM" game type indicators
            custom_games = self._find_custom_games(soup, page_text)
            tournament_games.extend(custom_games)
            
            # Method 2: Look for tournament codes in game data
            tournament_codes_found = self._find_tournament_codes(page_text)
            tournament_codes.update(tournament_codes_found)
            
            # Method 3: Look for official tournament indicators
            official_games = self._find_official_tournament_games(soup, page_text)
            tournament_games.extend(official_games)
            
            # Remove duplicates
            unique_games = {}
            for game in tournament_games:
                if game.game_id not in unique_games:
                    unique_games[game.game_id] = game
            
            tournament_games = list(unique_games.values())
            
            print(f"   📊 Found {len(tournament_games)} tournament games")
            print(f"   🏆 Found {len(tournament_codes)} unique tournament codes")
            
            # Calculate tournament statistics
            return self._calculate_tournament_stats(tournament_games, list(tournament_codes))
            
        except Exception as e:
            print(f"⚠️ Error parsing tournament games: {e}")
            return self._create_empty_tournament_stats()
    
    def _find_custom_games(self, soup: BeautifulSoup, page_text: str) -> List[TournamentGame]:
        """Find CUSTOM games that might be tournaments"""
        custom_games = []
        
        try:
            # Look for "CUSTOM" text in the page
            custom_indicators = re.findall(r'CUSTOM.*?(\d{4}-\d{2}-\d{2})', page_text, re.IGNORECASE)
            
            for i, date in enumerate(custom_indicators):
                # Create a basic tournament game entry
                game = TournamentGame(
                    game_id=f"custom_{i}_{date}",
                    game_type="CUSTOM",
                    tournament_code=f"CUSTOM_{date}",
                    date=date,
                    duration=0,
                    result="UNKNOWN",
                    champion="Unknown",
                    role="Unknown",
                    kills=0,
                    deaths=0,
                    assists=0,
                    kda=0.0,
                    cs=0,
                    gold=0,
                    damage=0,
                    vision_score=0,
                    team_composition=[],
                    enemy_composition=[]
                )
                custom_games.append(game)
                
        except Exception as e:
            print(f"⚠️ Error finding custom games: {e}")
        
        return custom_games
    
    def _find_tournament_codes(self, page_text: str) -> List[str]:
        """Find tournament codes in the page"""
        tournament_codes = []
        
        try:
            # Look for tournament code patterns
            # Tournament codes often follow patterns like "TOURNAMENT_XXXXXX" or similar
            code_patterns = [
                r'TOURNAMENT[_-]?([A-Z0-9]{6,})',
                r'CUSTOM[_-]?([A-Z0-9]{6,})',
                r'OFFICIAL[_-]?([A-Z0-9]{6,})',
                r'([A-Z]{2,}\d{4,})',  # Pattern like "EUW2024" or similar
            ]
            
            for pattern in code_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                tournament_codes.extend(matches)
            
            # Remove duplicates and clean up
            tournament_codes = list(set(tournament_codes))
            
        except Exception as e:
            print(f"⚠️ Error finding tournament codes: {e}")
        
        return tournament_codes
    
    def _find_official_tournament_games(self, soup: BeautifulSoup, page_text: str) -> List[TournamentGame]:
        """Find official tournament games"""
        official_games = []
        
        try:
            # Look for official tournament indicators
            official_indicators = [
                'OFFICIAL',
                'TOURNAMENT',
                'COMPETITIVE',
                'PRO',
                'LCS',
                'LEC',
                'LCK',
                'LPL',
                'WORLDS',
                'MSI'
            ]
            
            for indicator in official_indicators:
                if indicator.lower() in page_text.lower():
                    # Create a basic official tournament game entry
                    game = TournamentGame(
                        game_id=f"official_{indicator.lower()}",
                        game_type="OFFICIAL",
                        tournament_code=indicator,
                        date=datetime.now().strftime("%Y-%m-%d"),
                        duration=0,
                        result="UNKNOWN",
                        champion="Unknown",
                        role="Unknown",
                        kills=0,
                        deaths=0,
                        assists=0,
                        kda=0.0,
                        cs=0,
                        gold=0,
                        damage=0,
                        vision_score=0,
                        team_composition=[],
                        enemy_composition=[]
                    )
                    official_games.append(game)
                    
        except Exception as e:
            print(f"⚠️ Error finding official tournament games: {e}")
        
        return official_games
    
    def _calculate_tournament_stats(self, tournament_games: List[TournamentGame], tournament_codes: List[str]) -> TournamentStats:
        """Calculate tournament statistics"""
        if not tournament_games:
            return self._create_empty_tournament_stats()
        
        total_games = len(tournament_games)
        wins = sum(1 for game in tournament_games if game.result == "WIN")
        losses = sum(1 for game in tournament_games if game.result == "LOSS")
        win_rate = (wins / total_games * 100) if total_games > 0 else 0.0
        
        # Calculate averages
        total_kda = sum(game.kda for game in tournament_games if game.kda > 0)
        total_cs = sum(game.cs for game in tournament_games if game.cs > 0)
        total_damage = sum(game.damage for game in tournament_games if game.damage > 0)
        
        avg_kda = total_kda / total_games if total_games > 0 else 0.0
        avg_cs = total_cs / total_games if total_games > 0 else 0.0
        avg_damage = total_damage / total_games if total_games > 0 else 0.0
        
        # Find most played and best performing champions
        champion_stats = {}
        for game in tournament_games:
            if game.champion != "Unknown":
                if game.champion not in champion_stats:
                    champion_stats[game.champion] = {'games': 0, 'wins': 0, 'kda': 0.0}
                
                champion_stats[game.champion]['games'] += 1
                if game.result == "WIN":
                    champion_stats[game.champion]['wins'] += 1
                champion_stats[game.champion]['kda'] += game.kda
        
        most_played = max(champion_stats.keys(), key=lambda x: champion_stats[x]['games']) if champion_stats else "Unknown"
        best_performing = max(champion_stats.keys(), key=lambda x: champion_stats[x]['kda']) if champion_stats else "Unknown"
        
        # Get recent tournaments (last 10)
        recent_tournaments = sorted(tournament_games, key=lambda x: x.date, reverse=True)[:10]
        
        return TournamentStats(
            total_tournament_games=total_games,
            tournament_wins=wins,
            tournament_losses=losses,
            tournament_win_rate=win_rate,
            most_played_champion=most_played,
            best_performing_champion=best_performing,
            average_kda=avg_kda,
            average_cs=avg_cs,
            average_damage=avg_damage,
            tournament_codes=tournament_codes,
            recent_tournaments=recent_tournaments
        )
    
    def _create_empty_tournament_stats(self) -> TournamentStats:
        """Create empty tournament stats when no data is found"""
        return TournamentStats(
            total_tournament_games=0,
            tournament_wins=0,
            tournament_losses=0,
            tournament_win_rate=0.0,
            most_played_champion="None",
            best_performing_champion="None",
            average_kda=0.0,
            average_cs=0.0,
            average_damage=0.0,
            tournament_codes=[],
            recent_tournaments=[]
        )

def main():
    """Test the tournament scraper"""
    print("🧪 Testing Tournament Scraper...")
    
    scraper = TournamentScraper()
    
    # Test with your account
    test_summoner = "Odd#kimmy"
    test_region = "euw"
    
    tournament_stats = scraper.scrape_tournament_games(test_summoner, test_region)
    
    if tournament_stats:
        print(f"\n✅ Tournament stats retrieved for {test_summoner}")
        print(f"   Total Tournament Games: {tournament_stats.total_tournament_games}")
        print(f"   Tournament Win Rate: {tournament_stats.tournament_win_rate:.1f}%")
        print(f"   Most Played Champion: {tournament_stats.most_played_champion}")
        print(f"   Best Performing Champion: {tournament_stats.best_performing_champion}")
        print(f"   Average KDA: {tournament_stats.average_kda:.2f}")
        print(f"   Tournament Codes Found: {len(tournament_stats.tournament_codes)}")
        
        if tournament_stats.tournament_codes:
            print(f"   Codes: {', '.join(tournament_stats.tournament_codes[:5])}")
        
        if tournament_stats.recent_tournaments:
            print(f"\n📊 Recent Tournament Games:")
            for game in tournament_stats.recent_tournaments[:3]:
                print(f"   {game.date}: {game.champion} ({game.result}) - {game.game_type}")
    else:
        print(f"❌ Failed to retrieve tournament stats for {test_summoner}")

if __name__ == "__main__":
    main()
