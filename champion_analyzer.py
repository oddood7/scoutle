"""
Champion Analysis Engine for ScoutLE
Analyzes player performance by champion with detailed statistics
"""

from typing import Dict, List, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass
import statistics

@dataclass
class ChampionStats:
    """Statistics for a specific champion"""
    champion_name: str
    games_played: int
    wins: int
    losses: int
    win_rate: float
    avg_kda: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_cs_per_min: float
    avg_gold_per_min: float
    avg_damage_per_min: float
    most_common_role: str
    performance_trend: str  # "improving", "declining", "stable"

class ChampionAnalyzer:
    """Analyzes player performance by champion"""
    
    def __init__(self):
        self.champion_data = {}
    
    def analyze_matches(self, matches: List[Dict], player_puuid: str) -> Dict[str, ChampionStats]:
        """Analyze all matches and return champion statistics"""
        champion_stats = defaultdict(lambda: {
            'games': [],
            'wins': 0,
            'losses': 0,
            'roles': Counter(),
            'kdas': [],
            'kills': [],
            'deaths': [],
            'assists': [],
            'cs_per_min': [],
            'gold_per_min': [],
            'damage_per_min': []
        })
        
        # Process each match
        for match in matches:
            player_data = self._extract_player_data(match, player_puuid)
            if not player_data:
                continue
            
            champion = player_data.get('championName', 'Unknown')
            stats = champion_stats[champion]
            
            # Basic match data
            stats['games'].append(match)
            if player_data.get('win', False):
                stats['wins'] += 1
            else:
                stats['losses'] += 1
            
            # Role tracking
            role = player_data.get('teamPosition', 'Unknown')
            if role != 'Unknown':
                stats['roles'][role] += 1
            
            # Performance metrics
            kills = player_data.get('kills', 0)
            deaths = player_data.get('deaths', 0)
            assists = player_data.get('assists', 0)
            
            stats['kills'].append(kills)
            stats['deaths'].append(deaths)
            stats['assists'].append(assists)
            
            # Calculate KDA
            kda = (kills + assists) / deaths if deaths > 0 else kills + assists
            stats['kdas'].append(kda)
            
            # CS per minute
            total_cs = player_data.get('totalMinionsKilled', 0) + player_data.get('neutralMinionsKilled', 0)
            game_duration_minutes = match.get('info', {}).get('gameDuration', 0) / 60
            cs_per_min = total_cs / game_duration_minutes if game_duration_minutes > 0 else 0
            stats['cs_per_min'].append(cs_per_min)
            
            # Gold per minute
            gold_earned = player_data.get('goldEarned', 0)
            gold_per_min = gold_earned / game_duration_minutes if game_duration_minutes > 0 else 0
            stats['gold_per_min'].append(gold_per_min)
            
            # Damage per minute
            total_damage = player_data.get('totalDamageDealtToChampions', 0)
            damage_per_min = total_damage / game_duration_minutes if game_duration_minutes > 0 else 0
            stats['damage_per_min'].append(damage_per_min)
        
        # Convert to ChampionStats objects
        result = {}
        for champion, stats in champion_stats.items():
            if not stats['games']:  # Skip champions with no games
                continue
                
            games_played = len(stats['games'])
            wins = stats['wins']
            losses = stats['losses']
            win_rate = (wins / games_played) * 100 if games_played > 0 else 0
            
            # Calculate averages
            avg_kda = statistics.mean(stats['kdas']) if stats['kdas'] else 0
            avg_kills = statistics.mean(stats['kills']) if stats['kills'] else 0
            avg_deaths = statistics.mean(stats['deaths']) if stats['deaths'] else 0
            avg_assists = statistics.mean(stats['assists']) if stats['assists'] else 0
            avg_cs_per_min = statistics.mean(stats['cs_per_min']) if stats['cs_per_min'] else 0
            avg_gold_per_min = statistics.mean(stats['gold_per_min']) if stats['gold_per_min'] else 0
            avg_damage_per_min = statistics.mean(stats['damage_per_min']) if stats['damage_per_min'] else 0
            
            # Most common role
            most_common_role = stats['roles'].most_common(1)[0][0] if stats['roles'] else 'Unknown'
            
            # Performance trend (simplified - compare first half vs second half)
            performance_trend = self._calculate_performance_trend(stats['kdas'])
            
            result[champion] = ChampionStats(
                champion_name=champion,
                games_played=games_played,
                wins=wins,
                losses=losses,
                win_rate=win_rate,
                avg_kda=avg_kda,
                avg_kills=avg_kills,
                avg_deaths=avg_deaths,
                avg_assists=avg_assists,
                avg_cs_per_min=avg_cs_per_min,
                avg_gold_per_min=avg_gold_per_min,
                avg_damage_per_min=avg_damage_per_min,
                most_common_role=most_common_role,
                performance_trend=performance_trend
            )
        
        return result
    
    def _extract_player_data(self, match: Dict, player_puuid: str) -> Dict:
        """Extract player data from match"""
        for participant in match.get('info', {}).get('participants', []):
            if participant.get('puuid') == player_puuid:
                return participant
        return {}
    
    def _calculate_performance_trend(self, kdas: List[float]) -> str:
        """Calculate if performance is improving, declining, or stable"""
        if len(kdas) < 4:
            return "stable"
        
        # Split into first half and second half
        mid_point = len(kdas) // 2
        first_half = kdas[:mid_point]
        second_half = kdas[mid_point:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        if second_avg > first_avg * 1.1:  # 10% improvement
            return "improving"
        elif second_avg < first_avg * 0.9:  # 10% decline
            return "declining"
        else:
            return "stable"
    
    def get_top_champions(self, champion_stats: Dict[str, ChampionStats], limit: int = 5) -> List[ChampionStats]:
        """Get top played champions sorted by games played"""
        return sorted(champion_stats.values(), key=lambda x: x.games_played, reverse=True)[:limit]
    
    def get_best_performing_champions(self, champion_stats: Dict[str, ChampionStats], min_games: int = 3) -> List[ChampionStats]:
        """Get best performing champions by win rate (minimum games required)"""
        filtered = [stats for stats in champion_stats.values() if stats.games_played >= min_games]
        return sorted(filtered, key=lambda x: x.win_rate, reverse=True)
