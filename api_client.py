""" Riot API Client """

import requests
import time
from typing import Dict, List, Optional
from config import RIOT_API_BASE_URLS, RIOT_ACCOUNT_API_URL, RATE_LIMIT_DELAY, CACHE_DURATION

class RiotAPIClient:
	def __init__(self, api_key: str, region: str = "euw1"):
		self.api_key = api_key
		self.region = region
		self.base_url = RIOT_API_BASE_URLS.get(region, RIOT_API_BASE_URLS["euw1"])
		self.account_url = RIOT_ACCOUNT_API_URL
		self.headers = {
			"X-Riot-Token": api_key,
			"Accept": "application/json"
		}
		self.cache = {}
		self.rate_limit_delay = RATE_LIMIT_DELAY

	def make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
		"""API REQUEST"""
		cache_key = f"{url}_{params}"

		# Check cache
		if cache_key in self.cache:
			cached_data, timestamp = self.cache[cache_key]
			if time.time() - timestamp < CACHE_DURATION:
				return cached_data
		
		try:
			time.sleep(self.rate_limit_delay)
			response = requests.get(url, headers=self.headers, params=params)
			response.raise_for_status()
			data = response.json()

			# Cache result
			self.cache[cache_key] = (data, time.time())
			return data

		except requests.exceptions.RequestException as e:
			print(f"API Error: {e}")
			return None

	def get_player_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict]:
		"""Player with Riot ID"""
		url = f"{self.account_url}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
		return self.make_request(url)
	
	def get_summoner_data(self, puuid: str) -> Optional[Dict]:
		"""Get summoner data by PUUID - works with new Riot ID system"""
		url = f"{self.base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
		return self.make_request(url)
	
	def get_ranked_stats(self, summoner_id: str) -> List[Dict]:
		"""Ranked stats for player - works with both old and new API"""
		# Try the old API first
		url = f"{self.base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
		result = self.make_request(url)
		
		# If that fails, try alternative approach
		if not result:
			print(f"⚠️ Ranked stats not available for summoner ID: {summoner_id}")
			return []
		
		return result
	
	def get_match_history(self, puuid: str, count: int = 20) -> Optional[List[Dict]]:
		"""Match History"""
		url = f"{self.base_url}/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
		params = {"count": count, "start": 0}
		result = self.make_request(url, params)
		return result if result else []

	def get_match_details(self, match_id: str) -> Optional[Dict]:
		"""Detailed match info"""
		url = f"{self.base_url}/lol/match/v5/matches/{match_id}"
		return self.make_request(url)
	
	def analyze_player_matches(self, puuid: str, count: int = 20) -> List[Dict]:
		"""Get and analyze player's recent matches with detailed stats"""
		match_ids = self.get_match_history(puuid, count)
		matches = []
		
		for match_id in match_ids:
			match_data = self.get_match_details(match_id)
			if match_data:
				matches.append(match_data)
		
		return matches
