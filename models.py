""" Data models for player profiles """

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

@dataclass
class RankedStats:
	"""Solo Queue stats"""
	queue_type: str
	tier: str
	rank: str
	lp: int
	wins: int
	losses: int
	win_rate: float

	@property
	def total_games(self) -> int:
		return self.wins + self.losses


@dataclass
class MatchPerformance:
    """Represents a single match performance"""
    match_id: str
    champion: str
    role: str
    kills: int
    deaths: int
    assists: int
    win: bool
    game_duration: int
    game_mode: str
    
    @property
    def kda(self) -> float:
        if self.deaths == 0:
            return float(self.kills + self.assists)
        return (self.kills + self.assists) / self.deaths


@dataclass
class PlayerProfile:
	""" Player Profile"""
	riot_id: str
	puuid: str
	summoner_id: str
	summoner_level: str
	region: str

	# Ranked Stats
	ranked_stats: List[RankedStats]

	# Ranked Performance
	recent_matches: List[MatchPerformance]

	# Analysis 
	champion_pool: Dict[str, int]
	role_preference: Dict[str, float]
	performance_trends: Dict[str, float]

	# Metadata
	last_update: datetime

	@property
	def most_played_champions(self) -> List[str]:
		if not self.champion_pool:
			return "No Data"
		return max(self.champion_pool.items(), key=lambda x: x[1])[0]

	@property
	def preferred_roles(self) -> List[str]:
		if not self.role_preference:
			return "No Data"
		return max(self.role_preference.items(), key=lambda x: x[1])[0]
	
	@property
	def recent_win_rate(self) -> float:
		if not self.recent_matches:
			return 0.0
		wins = sum(1 for match in self.recent_matches if match.win)
		return (wins / len(self.recent_matches)) * 100

	@property
	def average_kda(self) -> float:
		if not self.recent_matches:
			return 0.0
		total_kda = sum(match.kda for match in self.recent_matches)
		return total_kda / len(self.recent_matches)
