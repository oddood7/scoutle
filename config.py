""" Config for scoutle"""

import os
from typing import Dict

# RIOT APIS
RIOT_API_BASE_URLS = {
	"euw1": "https://euw1.api.riotgames.com",
	"na1": "https://na1.api.riotgames.com",
	"eun1": "https://eun1.api.riotgames.com",
	"kr": "https://kr.api.riotgames.com",
	"br1": "https://br1.api.riotgames.com",
	"jp1": "https://jp1.api.riotgames.com",
	"oc1": "https://oc1.api.riotgames.com",
	"ru": "https://ru.api.riotgames.com",
	"tr1": "https://tr1.api.riotgames.com",
	"la1": "https://la1.api.riotgames.com",
	"la2": "https://la2.api.riotgames.com",
}

RIOT_ACCOUNT_API_URL = "https://europe.api.riotgames.com"

# Limiting
RATE_LIMIT_DELAY = 0.1
CACHE_DURATION = 300

DEFAULT_MATCH_COUNT = 20
MAX_MATCHES_ANALYZE = 10

# Supported Regions
REGION_NAMES = {
	"euw1": "Europe West",
	"eun1": "Europe Nordic & East",
    "na1": "North America", 
    "kr": "Korea",
    "br1": "Brazil",
    "jp1": "Japan",
    "ru": "Russia",
    "oc1": "Oceania",
    "tr1": "Turkey",
    "la1": "Latin America North",
    "la2": "Latin America South"
}

# Queue type
QUEUE_NAMES = {
	"RANKED_SOLO_5x5": "Solo Queue",
	"RANKED_FLEX_SR": "Flex 5v5",
	"RANKED_TFT": "TFT"
}

# Roles
ROLE_NAMES = {
	"TOP": "Top",
	"JUNGLE": "Jungle",
	"MIDDLE": "Mid",
	"BOTTOM": "Bot Lane",
	"UTILITY": "Support"
}