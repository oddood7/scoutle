"""
Riot Games API Scraper for League of Legends
Provides comprehensive champion statistics using the official Riot Games API
"""

import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

@dataclass
class RiotChampionPerformance:
    """Champion performance data from Riot API"""
    champion_name: str
    champion_id: int
    games_played: int
    wins: int
    losses: int
    win_rate: float
    kills: float
    deaths: float
    assists: float
    kda: float
    cs_per_min: float
    queue_type: str

@dataclass
class RiotPlayerAccount:
    """Player account data from Riot API"""
    summoner_name: str
    summoner_id: str
    puuid: str
    region: str
    level: int
    soloq_rank: str
    flex_rank: str
    soloq_lp: int
    flex_lp: int
    champion_performances: List[RiotChampionPerformance]
    last_updated: str

class RiotApiScraper:
    """Scraper using Riot Games API for comprehensive League of Legends data"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_urls = {
            'euw': 'https://euw1.api.riotgames.com',
            'na': 'https://na1.api.riotgames.com',
            'kr': 'https://kr.api.riotgames.com',
            'eune': 'https://eun1.api.riotgames.com',
            'br': 'https://br1.api.riotgames.com',
            'jp': 'https://jp1.api.riotgames.com',
            'ru': 'https://ru.api.riotgames.com',
            'oce': 'https://oc1.api.riotgames.com',
            'tr': 'https://tr1.api.riotgames.com',
            'lan': 'https://la1.api.riotgames.com',
            'las': 'https://la2.api.riotgames.com'
        }
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'X-Riot-Token': self.api_key,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
    
    def get_summoner_by_name(self, summoner_name: str, region: str = "euw") -> Optional[Dict]:
        """Get summoner information by name"""
        if not self.api_key:
            print("❌ API key required for Riot API access")
            return None
        
        try:
            url = f"{self.base_urls[region]}/lol/summoner/v4/summoners/by-name/{summoner_name}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"❌ Summoner not found: {summoner_name}")
                return None
            elif response.status_code == 403:
                print("❌ Invalid API key")
                return None
            else:
                print(f"❌ API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting summoner: {e}")
            return None
    
    def get_summoner_ranked_info(self, summoner_id: str, region: str = "euw") -> Dict:
        """Get summoner's ranked information"""
        if not self.api_key:
            return {"soloq_rank": "API Key Required", "flex_rank": "API Key Required"}
        
        try:
            url = f"{self.base_urls[region]}/lol/league/v4/entries/by-summoner/{summoner_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                entries = response.json()
                ranked_info = {"soloq_rank": "Unranked", "flex_rank": "Unranked", "soloq_lp": 0, "flex_lp": 0}
                
                for entry in entries:
                    if entry['queueType'] == 'RANKED_SOLO_5x5':
                        ranked_info['soloq_rank'] = f"{entry['tier']} {entry['rank']}"
                        ranked_info['soloq_lp'] = entry['leaguePoints']
                    elif entry['queueType'] == 'RANKED_FLEX_SR':
                        ranked_info['flex_rank'] = f"{entry['tier']} {entry['rank']}"
                        ranked_info['flex_lp'] = entry['leaguePoints']
                
                return ranked_info
            else:
                return {"soloq_rank": "Unranked", "flex_rank": "Unranked", "soloq_lp": 0, "flex_lp": 0}
                
        except Exception as e:
            print(f"❌ Error getting ranked info: {e}")
            return {"soloq_rank": "Unranked", "flex_rank": "Unranked", "soloq_lp": 0, "flex_lp": 0}
    
    def get_champion_masteries(self, summoner_id: str, region: str = "euw") -> List[Dict]:
        """Get summoner's champion masteries"""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_urls[region]}/lol/champion-mastery/v4/champion-masteries/by-summoner/{summoner_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error getting champion masteries: {e}")
            return []
    
    def get_match_history(self, puuid: str, region: str = "euw", count: int = 100) -> List[str]:
        """Get summoner's match history"""
        if not self.api_key:
            return []
        
        try:
            # Use the regional routing value for match history
            routing_regions = {
                'euw': 'europe',
                'na': 'americas',
                'kr': 'asia',
                'eune': 'europe',
                'br': 'americas',
                'jp': 'asia',
                'ru': 'europe',
                'oce': 'americas',
                'tr': 'europe',
                'lan': 'americas',
                'las': 'americas'
            }
            
            routing_region = routing_regions.get(region, 'europe')
            url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
            
            params = {'count': count, 'queue': 420}  # 420 is Ranked Solo/Duo
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error getting match history: {e}")
            return []
    
    def get_match_details(self, match_id: str, region: str = "euw") -> Optional[Dict]:
        """Get detailed match information"""
        if not self.api_key:
            return None
        
        try:
            routing_regions = {
                'euw': 'europe',
                'na': 'americas',
                'kr': 'asia',
                'eune': 'europe',
                'br': 'americas',
                'jp': 'asia',
                'ru': 'europe',
                'oce': 'americas',
                'tr': 'europe',
                'lan': 'americas',
                'las': 'americas'
            }
            
            routing_region = routing_regions.get(region, 'europe')
            url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error getting match details: {e}")
            return None
    
    def get_champion_data(self) -> Dict[int, str]:
        """Get champion ID to name mapping from Data Dragon"""
        try:
            # Get the latest version
            versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            versions_response = requests.get(versions_url, timeout=10)
            
            if versions_response.status_code != 200:
                return {}
            
            latest_version = versions_response.json()[0]
            
            # Get champion data
            champions_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
            champions_response = requests.get(champions_url, timeout=10)
            
            if champions_response.status_code != 200:
                return {}
            
            champions_data = champions_response.json()
            champion_mapping = {}
            
            for champion_id, champion_info in champions_data['data'].items():
                champion_mapping[int(champion_info['key'])] = champion_info['name']
            
            return champion_mapping
            
        except Exception as e:
            print(f"❌ Error getting champion data: {e}")
            return {}
    
    def scrape_player_account(self, summoner_name: str, region: str = "euw") -> Optional[RiotPlayerAccount]:
        """Scrape comprehensive player account data using Riot API"""
        print(f"🔍 Scraping account using Riot API: {summoner_name} ({region})")
        
        if not self.api_key:
            print("❌ Riot API key required. Please get one from https://developer.riotgames.com/")
            print("💡 You can still use the OP.GG scraper as a fallback")
            return None
        
        # Get summoner information
        summoner_info = self.get_summoner_by_name(summoner_name, region)
        if not summoner_info:
            return None
        
        print(f"✅ Found summoner: {summoner_info['name']} (Level {summoner_info['summonerLevel']})")
        
        # Get ranked information
        ranked_info = self.get_summoner_ranked_info(summoner_info['id'], region)
        
        # Get champion masteries
        masteries = self.get_champion_masteries(summoner_info['id'], region)
        print(f"📊 Found {len(masteries)} champion masteries")
        
        # Get champion data mapping
        champion_mapping = self.get_champion_data()
        
        # Get match history for detailed statistics
        match_ids = self.get_match_history(summoner_info['puuid'], region, count=50)
        print(f"🎮 Found {len(match_ids)} recent matches")
        
        # Process matches to get detailed champion statistics
        champion_stats = {}
        
        for i, match_id in enumerate(match_ids[:20]):  # Process first 20 matches
            try:
                match_details = self.get_match_details(match_id, region)
                if not match_details:
                    continue
                
                # Find the player in the match
                participant_id = None
                for participant in match_details['info']['participants']:
                    if participant['puuid'] == summoner_info['puuid']:
                        participant_id = participant['participantId']
                        break
                
                if participant_id is None:
                    continue
                
                participant = match_details['info']['participants'][participant_id - 1]
                champion_id = participant['championId']
                champion_name = champion_mapping.get(champion_id, f"Champion_{champion_id}")
                
                # Initialize champion stats if not exists
                if champion_name not in champion_stats:
                    champion_stats[champion_name] = {
                        'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0, 'assists': 0, 'cs': 0, 'duration': 0
                    }
                
                # Update stats
                champion_stats[champion_name]['games'] += 1
                if participant['win']:
                    champion_stats[champion_name]['wins'] += 1
                
                champion_stats[champion_name]['kills'] += participant['kills']
                champion_stats[champion_name]['deaths'] += participant['deaths']
                champion_stats[champion_name]['assists'] += participant['assists']
                champion_stats[champion_name]['cs'] += participant['totalMinionsKilled'] + participant['neutralMinionsKilled']
                champion_stats[champion_name]['duration'] += match_details['info']['gameDuration']
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"⚠️ Error processing match {match_id}: {e}")
                continue
        
        # Convert to ChampionPerformance objects
        champion_performances = []
        for champion_name, stats in champion_stats.items():
            if stats['games'] > 0:
                win_rate = (stats['wins'] / stats['games']) * 100
                kda = (stats['kills'] + stats['assists']) / max(stats['deaths'], 1)
                cs_per_min = (stats['cs'] / stats['duration'] * 60) if stats['duration'] > 0 else 0
                
                performance = RiotChampionPerformance(
                    champion_name=champion_name,
                    champion_id=0,  # We'll need to map this
                    games_played=stats['games'],
                    wins=stats['wins'],
                    losses=stats['games'] - stats['wins'],
                    win_rate=win_rate,
                    kills=stats['kills'] / stats['games'],
                    deaths=stats['deaths'] / stats['games'],
                    assists=stats['assists'] / stats['games'],
                    kda=kda,
                    cs_per_min=cs_per_min,
                    queue_type="soloq"
                )
                champion_performances.append(performance)
        
        # Sort by games played
        champion_performances.sort(key=lambda x: x.games_played, reverse=True)
        
        return RiotPlayerAccount(
            summoner_name=summoner_info['name'],
            summoner_id=summoner_info['id'],
            puuid=summoner_info['puuid'],
            region=region,
            level=summoner_info['summonerLevel'],
            soloq_rank=ranked_info['soloq_rank'],
            flex_rank=ranked_info['flex_rank'],
            soloq_lp=ranked_info['soloq_lp'],
            flex_lp=ranked_info['flex_lp'],
            champion_performances=champion_performances,
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S")
        )

def main():
    """Test the Riot API scraper"""
    print("🧪 Testing Riot API Scraper...")
    
    # You need to get a Riot API key from https://developer.riotgames.com/
    api_key = None  # Replace with your actual API key
    
    scraper = RiotApiScraper(api_key)
    
    if not api_key:
        print("❌ No API key provided. Please get one from https://developer.riotgames.com/")
        print("💡 The scraper will return None without an API key")
        return
    
    # Test with your account
    result = scraper.scrape_player_account('Odd#kimmy', 'euw')
    
    if result:
        print(f"\n=== RIOT API RESULTS ===")
        print(f"Summoner: {result.summoner_name}")
        print(f"Region: {result.region}")
        print(f"Level: {result.level}")
        print(f"SoloQ Rank: {result.soloq_rank} ({result.soloq_lp} LP)")
        print(f"Flex Rank: {result.flex_rank} ({result.flex_lp} LP)")
        print(f"Champions Played: {len(result.champion_performances)}")
        
        print(f"\n=== CHAMPION PERFORMANCES ===")
        for i, champ in enumerate(result.champion_performances[:10], 1):
            print(f"{i:2d}. {champ.champion_name:12s}: {champ.games_played:2d} games, {champ.win_rate:5.1f}% win rate, {champ.kda:4.2f} KDA")
    else:
        print("❌ Failed to get account data")

if __name__ == "__main__":
    main()

