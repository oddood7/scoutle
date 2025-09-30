"""
Hybrid Scraper for League of Legends
Combines OP.GG scraping with Riot Games API for comprehensive data
"""

from simple_account_scraper import SimpleAccountScraper, PlayerAccount, ChampionPerformance
from riot_api_scraper import RiotApiScraper, RiotPlayerAccount, RiotChampionPerformance
from typing import Optional, List, Dict
import time

class HybridScraper:
    """Hybrid scraper that uses both OP.GG and Riot API for comprehensive data"""
    
    def __init__(self, riot_api_key: Optional[str] = None):
        self.opgg_scraper = SimpleAccountScraper()
        self.riot_scraper = RiotApiScraper(riot_api_key)
        self.has_riot_api = riot_api_key is not None
    
    def scrape_player_account(self, summoner_name: str, region: str = "euw") -> Optional[PlayerAccount]:
        """Scrape player account using the best available method"""
        print(f"🔍 Hybrid scraping account: {summoner_name} ({region})")
        
        # Try Riot API first if available
        if self.has_riot_api:
            print("🚀 Using Riot API for comprehensive data...")
            riot_result = self.riot_scraper.scrape_player_account(summoner_name, region)
            
            if riot_result:
                # Convert Riot result to OP.GG format
                return self._convert_riot_to_opgg(riot_result)
            else:
                print("⚠️ Riot API failed, falling back to OP.GG...")
        
        # Fall back to OP.GG scraping
        print("🌐 Using OP.GG scraping...")
        return self.opgg_scraper.scrape_player_account(summoner_name, region)
    
    def _convert_riot_to_opgg(self, riot_account: RiotPlayerAccount) -> PlayerAccount:
        """Convert Riot API result to OP.GG format"""
        champion_performances = []
        
        for riot_champ in riot_account.champion_performances:
            opgg_champ = ChampionPerformance(
                champion_name=riot_champ.champion_name,
                games_played=riot_champ.games_played,
                wins=riot_champ.wins,
                losses=riot_champ.losses,
                win_rate=riot_champ.win_rate,
                kills=riot_champ.kills,
                deaths=riot_champ.deaths,
                assists=riot_champ.assists,
                kda=riot_champ.kda,
                cs_per_min=riot_champ.cs_per_min,
                queue_type=riot_champ.queue_type
            )
            champion_performances.append(opgg_champ)
        
        return PlayerAccount(
            summoner_name=riot_account.summoner_name,
            region=riot_account.region,
            level=riot_account.level,
            soloq_rank=riot_account.soloq_rank,
            flex_rank=riot_account.flex_rank,
            soloq_lp=riot_account.soloq_lp,
            flex_lp=riot_account.flex_lp,
            champion_performances=champion_performances,
            last_updated=riot_account.last_updated
        )
    
    def get_comprehensive_champion_data(self, summoner_name: str, region: str = "euw") -> Dict:
        """Get comprehensive champion data from multiple sources"""
        results = {
            'opgg_data': None,
            'riot_data': None,
            'combined_data': None
        }
        
        # Get OP.GG data
        print("🌐 Getting OP.GG data...")
        opgg_result = self.opgg_scraper.scrape_player_account(summoner_name, region)
        results['opgg_data'] = opgg_result
        
        # Get Riot API data if available
        if self.has_riot_api:
            print("🚀 Getting Riot API data...")
            riot_result = self.riot_scraper.scrape_player_account(summoner_name, region)
            results['riot_data'] = riot_result
            
            # Combine data if both are available
            if opgg_result and riot_result:
                results['combined_data'] = self._combine_data_sources(opgg_result, riot_result)
        
        return results
    
    def _combine_data_sources(self, opgg_data: PlayerAccount, riot_data: RiotPlayerAccount) -> PlayerAccount:
        """Combine data from OP.GG and Riot API for the most comprehensive result"""
        print("🔄 Combining data from multiple sources...")
        
        # Create a mapping of champion names to performances
        opgg_champions = {champ.champion_name: champ for champ in opgg_data.champion_performances}
        riot_champions = {champ.champion_name: champ for champ in riot_data.champion_performances}
        
        combined_champions = []
        
        # Add all OP.GG champions
        for champ_name, champ_data in opgg_champions.items():
            combined_champions.append(champ_data)
        
        # Add Riot API champions that aren't in OP.GG data
        for champ_name, champ_data in riot_champions.items():
            if champ_name not in opgg_champions:
                # Convert Riot format to OP.GG format
                opgg_champ = ChampionPerformance(
                    champion_name=champ_data.champion_name,
                    games_played=champ_data.games_played,
                    wins=champ_data.wins,
                    losses=champ_data.losses,
                    win_rate=champ_data.win_rate,
                    kills=champ_data.kills,
                    deaths=champ_data.deaths,
                    assists=champ_data.assists,
                    kda=champ_data.kda,
                    cs_per_min=champ_data.cs_per_min,
                    queue_type=champ_data.queue_type
                )
                combined_champions.append(opgg_champ)
                print(f"✅ Added missing champion from Riot API: {champ_name}")
        
        # Sort by games played
        combined_champions.sort(key=lambda x: x.games_played, reverse=True)
        
        # Use the most complete account data (prefer Riot API for basic info)
        if riot_data.level > opgg_data.level or len(riot_data.champion_performances) > len(opgg_data.champion_performances):
            base_data = riot_data
            print("📊 Using Riot API data as base (more complete)")
        else:
            base_data = opgg_data
            print("📊 Using OP.GG data as base")
        
        return PlayerAccount(
            summoner_name=base_data.summoner_name if hasattr(base_data, 'summoner_name') else opgg_data.summoner_name,
            region=base_data.region if hasattr(base_data, 'region') else opgg_data.region,
            level=base_data.level if hasattr(base_data, 'level') else opgg_data.level,
            soloq_rank=base_data.soloq_rank if hasattr(base_data, 'soloq_rank') else opgg_data.soloq_rank,
            flex_rank=base_data.flex_rank if hasattr(base_data, 'flex_rank') else opgg_data.flex_rank,
            soloq_lp=base_data.soloq_lp if hasattr(base_data, 'soloq_lp') else opgg_data.soloq_lp,
            flex_lp=base_data.flex_lp if hasattr(base_data, 'flex_lp') else opgg_data.flex_lp,
            champion_performances=combined_champions,
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S")
        )

def main():
    """Test the hybrid scraper"""
    print("🧪 Testing Hybrid Scraper...")
    
    # You can provide a Riot API key here if you have one
    riot_api_key = None  # Replace with your actual API key
    
    scraper = HybridScraper(riot_api_key)
    
    # Test with your account
    print("\n" + "="*50)
    print("Testing basic scraping...")
    result = scraper.scrape_player_account('Odd#kimmy', 'euw')
    
    if result:
        print(f"\n=== HYBRID SCRAPER RESULTS ===")
        print(f"Summoner: {result.summoner_name}")
        print(f"Region: {result.region}")
        print(f"Level: {result.level}")
        print(f"SoloQ Rank: {result.soloq_rank} ({result.soloq_lp} LP)")
        print(f"Flex Rank: {result.flex_rank} ({result.flex_lp} LP)")
        print(f"Champions Played: {len(result.champion_performances)}")
        
        print(f"\n=== CHAMPION PERFORMANCES ===")
        for i, champ in enumerate(result.champion_performances[:10], 1):
            print(f"{i:2d}. {champ.champion_name:12s}: {champ.games_played:2d} games, {champ.win_rate:5.1f}% win rate, {champ.kda:4.2f} KDA")
    
    # Test comprehensive data if Riot API is available
    if riot_api_key:
        print("\n" + "="*50)
        print("Testing comprehensive data collection...")
        comprehensive_data = scraper.get_comprehensive_champion_data('Odd#kimmy', 'euw')
        
        print(f"\n📊 Data Sources Results:")
        print(f"OP.GG Champions: {len(comprehensive_data['opgg_data'].champion_performances) if comprehensive_data['opgg_data'] else 0}")
        print(f"Riot API Champions: {len(comprehensive_data['riot_data'].champion_performances) if comprehensive_data['riot_data'] else 0}")
        print(f"Combined Champions: {len(comprehensive_data['combined_data'].champion_performances) if comprehensive_data['combined_data'] else 0}")
    else:
        print("\n💡 To get more comprehensive data, get a Riot API key from https://developer.riotgames.com/")
        print("   The hybrid scraper will automatically use both sources when available")

if __name__ == "__main__":
    main()

