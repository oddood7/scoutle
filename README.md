# ScoutLE - Tournament Scouting Tool

A simple League of Legends player analysis tool for tournament scouting.

## Features

- ✅ **Player Verification** - Confirm players exist and get basic info
- ✅ **Summoner Level** - See player experience level
- ✅ **Basic Account Data** - Game name, tag, PUUID
- ⚠️ **Limited Ranked Stats** - Depends on API key permissions
- ❌ **Match History** - Requires production API key

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a Riot API key:**
   - Go to [Riot Developer Portal](https://developer.riotgames.com/)
   - Create a personal API key (free)

3. **Run ScoutLE:**
   ```bash
   python gui_clean.py
   ```

4. **Use the tool:**
   - Enter your API key
   - Enter a Riot ID (format: PlayerName#Tag)
   - Select region
   - Click "Analyze Player"

## What You'll See

- **Account Information** - Player's game name and tag
- **Summoner Level** - How experienced the player is
- **Ranked Statistics** - Current rank and LP (if available)
- **API Status** - What data is accessible

## API Limitations

Personal API keys have limited permissions:
- ✅ Account lookup works
- ✅ Summoner data works
- ❌ Match history requires production API key
- ❌ Champion analysis requires match history

## Files

- `gui_clean.py` - Main application (use this one)
- `api_client.py` - Riot API integration
- `config.py` - Configuration settings
- `models.py` - Data models
- `requirements.txt` - Dependencies

## For Full Features

To get champion analysis and match history:
1. Apply for a production API key
2. Use the full version with extended permissions
3. Or use this basic version for player verification

## Troubleshooting

- **"Player not found"** - Check Riot ID format and region
- **"API key invalid"** - Get a new key from Riot Developer Portal
- **"No ranked data"** - Normal for personal API keys
- **"Analysis stuck"** - Check internet connection
