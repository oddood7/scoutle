"""
ScoutLE Discord Bot
Comprehensive Discord bot for League of Legends stats tracking
- Show most played champions and their stats
- Add games manually
- Combine ranked + manual stats
- Champion-specific features
"""

import discord
from discord.ext import commands
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from riot_api_scraper import RiotApiScraper
from manual_matches_storage import ManualMatchStorage, ManualMatch
from champion_stats_scraper import ChampionStatsScraper

load_dotenv()

class ScoutLEBot:
    """Discord bot for ScoutLE - League of Legends stats tracking"""
    
    def __init__(self):
        self.token = os.getenv('DISCORD_BOT_TOKEN')
        self.riot_api_key = os.getenv('RIOT_API_KEY')
        
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
        
        # Initialize scrapers and storage
        self.riot_scraper = RiotApiScraper(self.riot_api_key)
        self.manual_storage = ManualMatchStorage()
        self.champion_scraper = ChampionStatsScraper()
        
        self.team_data_file = "team_data.json"
        self.load_team_data()
        
        self.setup_events()
        self.setup_commands()
    
    def load_team_data(self):
        """Load team data from file (multi-server support)"""
        if os.path.exists(self.team_data_file):
            with open(self.team_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Migration: Convert old single-server format to multi-server
                if "players" in data and "servers" not in data:
                    print("🔄 Migrating to multi-server format...")
                    self.team_data = {
                        "servers": {
                            "default": {  # Old data goes to "default" server
                                "players": data.get("players", {}),
                                "teams": data.get("teams", {}),
                                "settings": data.get("settings", {})
                            }
                        }
                    }
                    self.save_team_data()
                    print("✅ Migration complete! Old data available as 'default' server")
                else:
                    self.team_data = data
        else:
            self.team_data = {
                "servers": {}  # Server-specific data
            }
            self.save_team_data()
    
    def save_team_data(self):
        """Save team data to file"""
        with open(self.team_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.team_data, f, indent=2, ensure_ascii=False)
    
    def get_server_data(self, guild_id: int):
        """Get or create server-specific data"""
        if guild_id is None:
            # DM or no guild context, use default
            guild_key = "default"
        else:
            guild_key = str(guild_id)
        
        if "servers" not in self.team_data:
            self.team_data["servers"] = {}
        
        if guild_key not in self.team_data["servers"]:
            self.team_data["servers"][guild_key] = {
                "players": {},
                "teams": {},
                "settings": {
                    "auto_updates": True,
                    "update_interval": 3600,
                }
            }
            self.save_team_data()
        
        return self.team_data["servers"][guild_key]
    
    def setup_events(self):
        """Setup Discord event handlers"""
        
        @self.bot.event
        async def on_ready():
            print(f'🤖 ScoutLE Bot is ready! Logged in as {self.bot.user}')
            print(f'📊 Connected to {len(self.bot.guilds)} server(s)')
            
            activity = discord.Activity(
                type=discord.ActivityType.watching, 
                name="League stats | !help"
            )
            await self.bot.change_presence(activity=activity)
        
        @self.bot.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.CommandNotFound):
                await ctx.send("❌ Unknown command. Use `!help` to see available commands.")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ Missing argument: {error.param}. Use `!help <command>` for more info.")
            else:
                await ctx.send(f"❌ Error: {str(error)}")
                print(f"Error: {error}")
    
    def setup_commands(self):
        """Setup Discord commands"""
        
        @self.bot.command(name='help')
        async def help_command(ctx, command_name: str = None):
            """Display help for commands"""
            if command_name:
                # Show help for specific command
                command = self.bot.get_command(command_name)
                if command:
                    embed = discord.Embed(
                        title=f"📖 Help: !{command_name}",
                        description=command.help or "No description available",
                        color=0x3498db
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ Command `{command_name}` not found!")
                return
            
            embed = discord.Embed(
                title="🤖 ScoutLE Bot - All Commands",
                description="**34 Commands** | League of Legends Stats Tracker\n"
                           "✨ NEW: Team sync, space support, champion icons!\n"
                           "Use `!help <command>` for detailed help on a specific command",
                color=0x00ff00
            )
            
            embed.add_field(
                name="📊 Player Stats & Registration (5 commands)",
                value="""**`!register <riot_id> <region> [ranked_count] [custom_count]`** ⭐ AUTO!
Registers player AND auto-fetches all stats!
Example: `!register Odd#kimmy euw` (default: 50 ranked, 100 custom)
Custom: `!register Odd#kimmy euw 100 200` (heavy scan)

**`!update <riot_id>`** - Manually update ranked stats
**`!stats <riot_id>`** - View complete stats (3 sections!)
**`!ranked <riot_id>`** - View only ranked stats
**`!manual <riot_id>`** - View only manual games""",
                inline=False
            )
            
            embed.add_field(
                name="🚀 Auto-Import Features (6 commands)",
                value="""**`!sync <riot_id> [count]`** - Auto-import ranked games
Example: `!sync Odd#kimmy 20` (imports last 20 ranked games)

**`!synccustom <riot_id> [count]`** - Auto-import custom/tournament games ⭐
Example: `!synccustom Odd#kimmy 50` (scans last 50 for custom games)

**`!importtournament <code> [region]`** - Import by tournament code
Example: `!importtournament EUW1234-CODE euw`

**`!lastgame <riot_id>`** - Detailed last game analysis
Example: `!lastgame Odd#kimmy`

**`!mastery <riot_id> [champion]`** - Champion mastery levels
Example: `!mastery Odd#kimmy` or `!mastery Odd#kimmy Zeri`

**`!live <riot_id>`** - Check if player is in game (temporarily unavailable)""",
                inline=False
            )
            
            embed.add_field(
                name="➕ Manual Game Management (4 commands)",
                value="""**`!addgame <riot_id> <champ> <result> <k> <d> <a> <cs> <dur> [type]`**
Add game with full stats
Example: `!addgame Odd#kimmy Zeri WIN 12 1 7 274 31 custom`

**`!addgameid <riot_id> <game_id>`** - Import by game ID
Example: `!addgameid Odd#kimmy EUW1_1234567890`

**`!listgames <riot_id>`** - List all manual games
**`!removegame <match_id>`** - Remove a specific game""",
                inline=False
            )
            
            embed.add_field(
                name="🏆 Champion Meta & Analysis (3 commands)",
                value="""**`!champion <name>`** - Detailed champion stats (Diamond+)
Shows: Win/Pick/Ban rates, Tier, Builds, Runes, Matchups
Example: `!champion Zeri`

**`!matchup <champ1> <champ2>`** - Compare champions
Example: `!matchup Zeri Jinx`

**`!tier <champion>`** - Quick tier check
Example: `!tier Zeri`""",
                inline=False
            )
            
            embed.add_field(
                name="👥 Player Management (3 commands)",
                value="""**`!players`** - List all registered players
**`!remove <riot_id>`** - Remove a player
**`!clearstats <riot_id>`** - Clear a player's stats (keeps registration)""",
                inline=False
            )
            
            embed.add_field(
                name="🏆 Team System (7 commands)",
                value="""**`!createteam <name>`** - Create a new team
**`!addtoteam <team> <riot_id>`** - Add player to team
**`!removefromteam <team> <riot_id>`** - Remove player from team
**`!viewteam <name>`** - View team roster & **combined** stats (Ranked + Custom)
**`!teams`** - List all teams
**`!syncteam <team> [ranked] [custom]`** ⭐ - Sync entire team at once!
Example: `!syncteam MainRoster` (default: 30 ranked, 50 custom)
Custom: `!syncteam MainRoster 50 100` (sync all players!)
**`!deleteteam <name>`** - Delete a team""",
                inline=False
            )
            
            embed.add_field(
                name="🗑️ Clear Data (3 commands)",
                value="""**`!clearstats <riot_id>`** - Clear one player's stats
**`!clearall confirm`** - Clear ALL stats (use !clearall first for warning)
**`!unregisterall confirm`** - Unregister ALL players and delete ALL data""",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ Help & Debug (4 commands)",
                value="""**`!help`** - Show all commands (this message)
**`!help <command>`** - Detailed help for specific command
**`!debug <riot_id>`** - Show data sources for troubleshooting
**`!matchhistory <riot_id> [count]`** - View match history with dates""",
                inline=False
            )
            
            embed.add_field(
                name="💡 Quick Start Guide",
                value="""1️⃣ Register: `!register YourName#TAG euw`
2️⃣ Fetch stats: `!update YourName#TAG`
3️⃣ Or add manually: `!addgame YourName#TAG Zeri WIN 12 1 7 274 31`
4️⃣ View stats: `!stats YourName#TAG`
5️⃣ Check meta: `!champion Zeri`""",
                inline=False
            )
            
            embed.set_footer(text="📝 Riot ID format: Name#TAG | Regions: euw, na, kr, eune, br, jp, ru, oce, tr, lan, las")
            await ctx.send(embed=embed)
        
        @self.bot.command(name='register')
        async def register_player(ctx, *, args: str):
            """Register a new player and auto-fetch all stats. Example: !register Odd#kimmy euw or !register Player Name#TAG euw"""
            # Parse arguments (riot_id is required, rest are optional)
            parts = args.split()
            if len(parts) < 1:
                await ctx.send("❌ Usage: !register <riot_id> [region] [ranked_games] [custom_games]")
                return
            
            # Find the riot_id (contains #)
            riot_id_parts = []
            remaining_parts = []
            found_tag = False
            
            for part in parts:
                if not found_tag:
                    riot_id_parts.append(part)
                    if '#' in part:
                        found_tag = True
                else:
                    remaining_parts.append(part)
            
            riot_id = ' '.join(riot_id_parts)
            region = remaining_parts[0] if len(remaining_parts) > 0 else "euw"
            ranked_games = int(remaining_parts[1]) if len(remaining_parts) > 1 else 50
            custom_games = int(remaining_parts[2]) if len(remaining_parts) > 2 else 100
            region = region.lower()
            
            if riot_id in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} is already registered!")
                return
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`\nExample: `Odd#kimmy`")
                return
            
            # Initial registration
            await ctx.send(f"🔍 Registering {riot_id} on {region.upper()}...")
            
            self.team_data["players"][riot_id] = {
                "region": region,
                "discord_id": ctx.author.id,
                "registered_by": ctx.author.name,
                "registered_at": datetime.now().isoformat(),
                "last_updated": None,
                "ranked_stats": None
            }
            self.save_team_data()
            
            # Auto-fetch stats
            status_msg = await ctx.send(f"⏳ **Step 1/3:** Fetching ranked stats from Riot API...")
            
            # Initialize counters at the start
            synced = 0
            custom_imported = 0
            
            try:
                # Step 1: Update ranked stats
                account = self.riot_scraper.scrape_player_account(riot_id, region)
                
                if account:
                    ranked_stats = {
                        "summoner_name": account.summoner_name,
                        "level": account.level,
                        "rank": {
                            "soloq": account.soloq_rank,
                            "flex": account.flex_rank,
                            "soloq_lp": account.soloq_lp,
                            "flex_lp": account.flex_lp
                        },
                        "champions": []
                    }
                    
                    for perf in account.champion_performances:
                        ranked_stats["champions"].append({
                            "name": perf.champion_name,
                            "games": perf.games_played,
                            "wins": perf.wins,
                            "losses": perf.losses,
                            "win_rate": perf.win_rate,
                            "kda": perf.kda,
                            "kills": perf.kills,
                            "deaths": perf.deaths,
                            "assists": perf.assists,
                            "cs_per_min": perf.cs_per_min
                        })
                    
                    self.team_data["players"][riot_id]["ranked_stats"] = ranked_stats
                    self.team_data["players"][riot_id]["last_updated"] = datetime.now().isoformat()
                    self.save_team_data()
                    
                    try:
                        await status_msg.edit(content=f"✅ **Step 1/3:** Ranked stats fetched!\n⏳ **Step 2/3:** Importing last {ranked_games} ranked games...")
                    except:
                        await ctx.send(f"✅ **Step 1/3:** Ranked stats fetched!\n⏳ **Step 2/3:** Importing last {ranked_games} ranked games...")
                else:
                    try:
                        await status_msg.edit(content=f"⚠️ **Step 1/3:** Could not fetch ranked stats (continuing anyway)\n⏳ **Step 2/3:** Importing ranked games...")
                    except:
                        await ctx.send(f"⚠️ **Step 1/3:** Could not fetch ranked stats (continuing anyway)\n⏳ **Step 2/3:** Importing ranked games...")
                
                # Step 2: Sync ranked games
                summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
                if summoner_info:
                    match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, ranked_games, queue=420)
                    
                    if match_ids:
                        champion_mapping = self.riot_scraper.get_champion_data()
                        synced = 0
                        
                        for match_id in match_ids[:ranked_games]:
                            # Add small async delay to prevent blocking
                            if synced > 0 and synced % 10 == 0:
                                await asyncio.sleep(0.1)
                            
                            match_details = self.riot_scraper.get_match_details(match_id, region)
                            if not match_details:
                                continue
                            
                            # Auto-add for all registered players in game
                            for p in match_details['info']['participants']:
                                if p['puuid'] == summoner_info['puuid']:
                                    manual_match_id = f"SYNC_{match_id}"
                                    if not any(m.match_id == manual_match_id for m in self.manual_storage.matches):
                                        champion_name = champion_mapping.get(p['championId'], "Unknown")
                                        match = ManualMatch(
                                            match_id=manual_match_id,
                                            summoner_name=riot_id,
                                            champion_name=champion_name,
                                            result="WIN" if p['win'] else "LOSS",
                                            kills=float(p['kills']),
                                            deaths=float(p['deaths']),
                                            assists=float(p['assists']),
                                            cs=float(p['totalMinionsKilled'] + p['neutralMinionsKilled']),
                                            game_duration=int(match_details['info']['gameDuration'] / 60),
                                            queue_type="ranked",
                                            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            notes=f"Auto-synced during registration"
                                        )
                                        if self.manual_storage.add_match(match):
                                            synced += 1
                                    break
                        
                        try:
                            await status_msg.edit(content=f"✅ **Step 1/3:** Ranked stats fetched!\n✅ **Step 2/3:** {synced} ranked games imported!\n⏳ **Step 3/3:** Scanning for custom/tournament games...")
                        except:
                            await ctx.send(f"✅ **Step 2/3:** {synced} ranked games imported!\n⏳ **Step 3/3:** Scanning for custom games...")
                    else:
                        try:
                            await status_msg.edit(content=f"✅ **Step 1/3:** Ranked stats fetched!\n⚠️ **Step 2/3:** No ranked games found\n⏳ **Step 3/3:** Scanning for custom games...")
                        except:
                            await ctx.send(f"⚠️ **Step 2/3:** No ranked games found\n⏳ **Step 3/3:** Scanning for custom games...")
                
                # Step 3: Scan custom games
                if summoner_info:
                    all_match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, custom_games)
                    custom_found = 0
                    
                    if all_match_ids:
                        champion_mapping = self.riot_scraper.get_champion_data()
                        
                        for match_id in all_match_ids:
                            # Add async delay every 10 games to prevent blocking
                            if custom_found > 0 and custom_found % 10 == 0:
                                await asyncio.sleep(0.1)
                            
                            match_details = self.riot_scraper.get_match_details(match_id, region)
                            if not match_details:
                                continue
                            
                            queue_id = match_details['info']['queueId']
                            # ONLY detect true custom/tournament games
                            # Queue 0 = Custom games (5v5 Draft/Blind)
                            # Queue 2000-2020 = Tournament code games
                            # NOTE: Excludes Clash (700), Arena (1700/3100), ARURF (900), etc.
                            if queue_id != 0 and not (2000 <= queue_id <= 2020):
                                continue
                            
                            custom_found += 1
                            
                            # Auto-add for all registered players
                            for p in match_details['info']['participants']:
                                p_game_name = p.get('riotIdGameName', p.get('summonerName', ''))
                                p_tag = p.get('riotIdTagline', '')
                                p_riot_id = f"{p_game_name}#{p_tag}" if p_tag else p_game_name
                                
                                is_registered = p_riot_id in self.team_data["players"]
                                if not is_registered:
                                    for registered_id in self.team_data["players"].keys():
                                        if registered_id.split('#')[0].lower() == p_game_name.lower():
                                            p_riot_id = registered_id
                                            is_registered = True
                                            break
                                
                                if is_registered:
                                    p_match_id = f"CUSTOM_{match_id}_{p_riot_id}"
                                    if not any(m.match_id == p_match_id for m in self.manual_storage.matches):
                                        p_champion = champion_mapping.get(p['championId'], "Unknown")
                                        
                                        # Determine game type based on queue ID
                                        if queue_id == 0:
                                            game_type = "custom"
                                        elif 2000 <= queue_id <= 2020:
                                            game_type = "tournament"
                                        else:
                                            game_type = "custom"  # Fallback
                                        
                                        match = ManualMatch(
                                            match_id=p_match_id,
                                            summoner_name=p_riot_id,
                                            champion_name=p_champion,
                                            result="WIN" if p['win'] else "LOSS",
                                            kills=float(p['kills']),
                                            deaths=float(p['deaths']),
                                            assists=float(p['assists']),
                                            cs=float(p['totalMinionsKilled'] + p['neutralMinionsKilled']),
                                            game_duration=int(match_details['info']['gameDuration'] / 60),
                                            queue_type=game_type,
                                            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            notes=f"Auto-imported during registration"
                                        )
                                        if self.manual_storage.add_match(match):
                                            if p_riot_id == riot_id:  # Only count for the player being registered
                                                custom_imported += 1
                
                try:
                    await status_msg.delete()
                except:
                    pass
                
                # Final result
                embed = discord.Embed(
                    title="🎉 Player Registered & Stats Loaded!",
                    description=f"**{riot_id}** is ready to go!",
                    color=0x00ff00
                )
                
                if account:
                    embed.add_field(name="Level", value=str(account.level), inline=True)
                    embed.add_field(name="Rank", value=account.soloq_rank, inline=True)
                    embed.add_field(name="Region", value=region.upper(), inline=True)
                
                embed.add_field(name="✅ Ranked Stats", value="Fetched from API" if account else "Not available", inline=True)
                embed.add_field(name="✅ Ranked Games", value=f"{synced} imported", inline=True)
                embed.add_field(name="✅ Custom/Tournament", value=f"{custom_imported} imported", inline=True)
                
                embed.add_field(
                    name="🎮 Ready to Use",
                    value=f"Use `!stats {riot_id}` to view complete statistics!",
                    inline=False
                )
                
                embed.set_footer(text=f"Registered by {ctx.author.name} | Auto-scanned {ranked_games} ranked + {custom_games} total games")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"✅ Player registered but auto-scan failed: {str(e)}\nUse `!update {riot_id}` and `!sync {riot_id}` manually.")
                print(f"❌ Registration auto-scan error: {e}")
        
        @self.bot.command(name='update')
        async def update_player(ctx, *, riot_id: str):
            """Update ranked stats from Riot API. Example: !update Faker#KR1 or !update Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered! Use `!register {riot_id} <region>`")
                return
            
            # Validate Riot ID format
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`\nExample: `Odd#kimmy`")
                return
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            await ctx.send(f"🔄 Fetching ranked stats for {riot_id}...")
            
            # Fetch from Riot API
            account = self.riot_scraper.scrape_player_account(riot_id, region)
            
            if not account:
                await ctx.send(f"❌ Could not fetch data for {riot_id}. Make sure the Riot ID is correct and API key is set.")
                return
            
            # Store ranked stats
            ranked_stats = {
                "summoner_name": account.summoner_name,
                "level": account.level,
                "rank": {
                    "soloq": account.soloq_rank,
                    "flex": account.flex_rank,
                    "soloq_lp": account.soloq_lp,
                    "flex_lp": account.flex_lp
                },
                "champions": []
            }
            
            for perf in account.champion_performances:
                ranked_stats["champions"].append({
                    "name": perf.champion_name,
                    "games": perf.games_played,
                    "wins": perf.wins,
                    "losses": perf.losses,
                    "win_rate": perf.win_rate,
                    "kda": perf.kda,
                    "kills": perf.kills,
                    "deaths": perf.deaths,
                    "assists": perf.assists,
                    "cs_per_min": perf.cs_per_min
                })
            
            self.team_data["players"][riot_id]["ranked_stats"] = ranked_stats
            self.team_data["players"][riot_id]["last_updated"] = datetime.now().isoformat()
            self.save_team_data()
            
            embed = discord.Embed(
                title="✅ Stats Updated",
                description=f"**{account.summoner_name}** (Level {account.level})",
                color=0x00ff00
            )
            embed.add_field(name="SoloQ", value=f"{account.soloq_rank} ({account.soloq_lp} LP)", inline=True)
            embed.add_field(name="Flex", value=f"{account.flex_rank} ({account.flex_lp} LP)", inline=True)
            embed.add_field(name="Champions Tracked", value=str(len(ranked_stats["champions"])), inline=True)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='stats')
        async def show_stats(ctx, *, riot_id: str):
            """Show comprehensive stats (ranked + manual + combined). Example: !stats Faker#KR1 or !stats Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered! Use `!register {riot_id} <region>`")
                return
            
            player_data = self.team_data["players"][riot_id]
            ranked_stats = player_data.get("ranked_stats")
            manual_matches = self.manual_storage.get_matches_for_summoner(riot_id)
            
            if not ranked_stats and not manual_matches:
                await ctx.send(f"❌ No data for {riot_id}. Use `!update {riot_id}` to fetch ranked stats or `!addgame` to add manual games.")
                return
            
            # Separate manual matches by type
            ranked_manual_matches = [m for m in manual_matches if m.queue_type in ['ranked', 'other']]
            custom_matches = [m for m in manual_matches if m.queue_type in ['custom', 'tournament', 'tournament_draft', 'scrim', 'clash', 'arena']]
            
            # Calculate stats for each category
            # Ranked stats = ranked_stats from API + ranked games from manual storage
            ranked_stats_combined = self._combine_stats(ranked_stats, ranked_manual_matches)
            
            # Custom stats = only custom/tournament games
            custom_stats = self._get_stats_from_matches(custom_matches)
            
            # Combined = everything
            combined_stats = self._combine_stats(ranked_stats, manual_matches)
            
            # Create main embed
            embed = discord.Embed(
                title=f"📊 Complete Stats - {riot_id}",
                description=f"Region: {player_data['region'].upper()}",
                color=0x0099ff
            )
            
            # Show rank if available
            if ranked_stats:
                embed.add_field(
                    name="👑 Current Rank",
                    value=f"SoloQ: **{ranked_stats['rank']['soloq']}** ({ranked_stats['rank']['soloq_lp']} LP)\n"
                          f"Flex: **{ranked_stats['rank']['flex']}** ({ranked_stats['rank']['flex_lp']} LP)",
                    inline=False
                )
            
            # SECTION 1: Ranked Stats (includes API ranked + synced ranked games)
            if ranked_stats_combined:
                total_ranked_games = sum(c['games'] for c in ranked_stats_combined)
                total_ranked_wins = sum(c['wins'] for c in ranked_stats_combined)
                ranked_wr = (total_ranked_wins / total_ranked_games * 100) if total_ranked_games > 0 else 0
                
                # Add champion icon for top champion
                if ranked_stats_combined:
                    top_champ = ranked_stats_combined[0]['name']
                    icon_url = self.champion_scraper.get_champion_icon_url(top_champ)
                    if icon_url:
                        embed.set_thumbnail(url=icon_url)
                    
                    # Add second champion as author icon if exists
                    if len(ranked_stats_combined) > 1:
                        second_champ = ranked_stats_combined[1]['name']
                        second_icon_url = self.champion_scraper.get_champion_icon_url(second_champ)
                        if second_icon_url:
                            embed.set_author(name=f"Most Played: {top_champ} & {second_champ}", icon_url=second_icon_url)
                
                ranked_text = f"**Overall:** {total_ranked_games}g | {ranked_wr:.1f}% WR | **{total_ranked_wins}W** {total_ranked_games - total_ranked_wins}L\n\n"
                
                for i, champ in enumerate(ranked_stats_combined[:5], 1):
                    # Add visual indicators
                    wr_emoji = "🟢" if champ['win_rate'] >= 50 else "🔴"
                    kda_emoji = "⭐" if champ['kda'] >= 3.0 else ("✨" if champ['kda'] >= 2.0 else "")
                    
                    # Add clickable champion icon link
                    champ_icon = self.champion_scraper.get_champion_icon_url(champ['name'])
                    champ_name_display = f"[{champ['name']}]({champ_icon})" if champ_icon else f"**{champ['name']}**"
                    
                    ranked_text += f"{wr_emoji} {i}. {champ_name_display} - {champ['games']}g | {champ['win_rate']:.1f}% WR | {champ['kda']:.2f} KDA {kda_emoji}\n"
                
                embed.add_field(
                    name="🎮 Ranked Games",
                    value=ranked_text,
                    inline=False
                )
            
            # SECTION 2: Custom/Tournament Stats
            if custom_stats:
                total_custom_games = sum(c['games'] for c in custom_stats)
                total_custom_wins = sum(c['wins'] for c in custom_stats)
                custom_wr = (total_custom_wins / total_custom_games * 100) if total_custom_games > 0 else 0
                
                custom_text = f"**Overall:** {total_custom_games}g | {custom_wr:.1f}% WR | **{total_custom_wins}W** {total_custom_games - total_custom_wins}L\n\n"
                
                for i, champ in enumerate(custom_stats[:5], 1):
                    # Add visual indicators
                    wr_emoji = "🟢" if champ['win_rate'] >= 50 else "🔴"
                    kda_emoji = "⭐" if champ['kda'] >= 3.0 else ("✨" if champ['kda'] >= 2.0 else "")
                    
                    # Add clickable champion icon link
                    champ_icon = self.champion_scraper.get_champion_icon_url(champ['name'])
                    champ_name_display = f"[{champ['name']}]({champ_icon})" if champ_icon else f"**{champ['name']}**"
                    
                    custom_text += f"{wr_emoji} {i}. {champ_name_display} - {champ['games']}g | {champ['win_rate']:.1f}% WR | {champ['kda']:.2f} KDA {kda_emoji}\n"
                
                embed.add_field(
                    name="🏆 Custom/Tournament Games",
                    value=custom_text,
                    inline=False
                )
            
            # SECTION 3: Combined Stats
            if combined_stats:
                total_games = sum(c['games'] for c in combined_stats)
                total_wins = sum(c['wins'] for c in combined_stats)
                combined_wr = (total_wins / total_games * 100) if total_games > 0 else 0
                
                combined_text = f"**Overall:** {total_games}g | {combined_wr:.1f}% WR | **{total_wins}W** {total_games - total_wins}L\n\n"
                
                for i, champ in enumerate(combined_stats[:5], 1):
                    # Add visual indicators
                    wr_emoji = "🟢" if champ['win_rate'] >= 50 else "🔴"
                    kda_emoji = "⭐" if champ['kda'] >= 3.0 else ("✨" if champ['kda'] >= 2.0 else "")
                    
                    # Add clickable champion icon link
                    champ_icon = self.champion_scraper.get_champion_icon_url(champ['name'])
                    champ_name_display = f"[{champ['name']}]({champ_icon})" if champ_icon else f"**{champ['name']}**"
                    
                    combined_text += f"{wr_emoji} {i}. {champ_name_display} - {champ['games']}g | {champ['win_rate']:.1f}% WR | {champ['kda']:.2f} KDA {kda_emoji}\n"
                
                embed.add_field(
                    name="⭐ Combined Stats (All Games)",
                    value=combined_text,
                    inline=False
                )
            
            # Footer with data sources
            if player_data["last_updated"]:
                last_update = datetime.fromisoformat(player_data["last_updated"])
                embed.set_footer(text=f"Last updated: {last_update.strftime('%d/%m/%Y %H:%M')} | Use !ranked or !manual for detailed views")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='ranked')
        async def show_ranked_stats(ctx, *, riot_id: str):
            """Show only ranked stats. Example: !ranked Faker#KR1 or !ranked Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            player_data = self.team_data["players"][riot_id]
            ranked_stats = player_data.get("ranked_stats")
            
            if not ranked_stats:
                await ctx.send(f"❌ No ranked stats for {riot_id}. Use `!update {riot_id}` to fetch.")
                return
            
            embed = discord.Embed(
                title=f"🎮 Ranked Stats: {riot_id}",
                description=f"Level {ranked_stats['level']} | {player_data['region'].upper()}",
                color=0xffd700
            )
            
            embed.add_field(
                name="👑 Ranks",
                value=f"SoloQ: **{ranked_stats['rank']['soloq']}** ({ranked_stats['rank']['soloq_lp']} LP)\n"
                      f"Flex: **{ranked_stats['rank']['flex']}** ({ranked_stats['rank']['flex_lp']} LP)",
                inline=False
            )
            
            if ranked_stats["champions"]:
                champ_text = ""
                for i, champ in enumerate(ranked_stats["champions"][:8], 1):
                    champ_text += f"{i}. **{champ['name']}** - {champ['games']}g ({champ['win_rate']:.1f}% WR)\n"
                    champ_text += f"   KDA: {champ['kda']:.2f} | CS/min: {champ['cs_per_min']:.1f}\n"
                
                embed.add_field(
                    name="🏆 Champion Pool",
                    value=champ_text,
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='manual')
        async def show_manual_stats(ctx, *, riot_id: str):
            """Show only manual games. Example: !manual Faker#KR1 or !manual Player Name#TAG"""
            manual_matches = self.manual_storage.get_matches_for_summoner(riot_id)
            
            if not manual_matches:
                await ctx.send(f"❌ No manual games for {riot_id}. Use `!addgame` to add some!")
                return
            
            # Get aggregated stats
            all_stats = self.manual_storage.get_all_champion_stats(riot_id)
            
            embed = discord.Embed(
                title=f"📝 Manual Games: {riot_id}",
                description=f"Total: {len(manual_matches)} games",
                color=0x9b59b6
            )
            
            if all_stats:
                champ_text = ""
                for i, champ in enumerate(all_stats[:8], 1):
                    champ_text += f"{i}. **{champ['champion_name']}** - {champ['games_played']}g ({champ['win_rate']:.1f}% WR)\n"
                    champ_text += f"   KDA: {champ['kda']:.2f} | CS/min: {champ['cs_per_min']:.1f}\n"
                
                embed.add_field(
                    name="🏆 Champions",
                    value=champ_text,
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='addgame')
        async def add_game(ctx, riot_id: str, champion: str, result: str, kills: float, 
                          deaths: float, assists: float, cs: float, duration: int, queue_type: str = "custom"):
            """Add a game manually. Example: !addgame Faker#KR1 Zeri WIN 12 1 7 274 31 custom"""
            result = result.upper()
            if result not in ["WIN", "LOSS"]:
                await ctx.send("❌ Result must be WIN or LOSS")
                return
            
            # Generate unique match ID
            match_id = f"MANUAL_{riot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            match = ManualMatch(
                match_id=match_id,
                summoner_name=riot_id,
                champion_name=champion,
                result=result,
                kills=kills,
                deaths=deaths,
                assists=assists,
                cs=cs,
                game_duration=duration,
                queue_type=queue_type,
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                notes=f"Added by {ctx.author.name}"
            )
            
            success = self.manual_storage.add_match(match)
            
            if success:
                embed = discord.Embed(
                    title="✅ Game Added",
                    description=f"**{champion}** - {result}",
                    color=0x00ff00
                )
                embed.add_field(name="Player", value=riot_id, inline=True)
                embed.add_field(name="KDA", value=f"{kills}/{deaths}/{assists} ({match.kda:.2f})", inline=True)
                embed.add_field(name="CS", value=f"{cs} ({match.cs_per_min:.1f}/min)", inline=True)
                embed.add_field(name="Match ID", value=match_id, inline=False)
                embed.set_footer(text=f"Added by {ctx.author.name}")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to add game (match ID already exists)")
        
        @self.bot.command(name='addgameid')
        async def add_game_by_id(ctx, riot_id: str, game_id: str):
            """Add a game by fetching it from Riot API. Example: !addgameid Faker#KR1 EUW1_1234567890"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            await ctx.send(f"🔍 Fetching game {game_id}...")
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            # Fetch match details
            match_details = self.riot_scraper.get_match_details(game_id, region)
            
            if not match_details:
                await ctx.send("❌ Could not fetch game. Make sure the game ID is correct.")
                return
            
            # Find player in match
            summoner_name = riot_id.split('#')[0] if '#' in riot_id else riot_id
            
            # Get player's puuid if we have ranked stats
            puuid = None
            if player_data.get("ranked_stats"):
                # We need to fetch puuid from Riot API first
                summoner_info = self.riot_scraper.get_summoner_by_name(summoner_name, region)
                if summoner_info:
                    puuid = summoner_info['puuid']
            
            participant = None
            if puuid:
                for p in match_details['info']['participants']:
                    if p['puuid'] == puuid:
                        participant = p
                        break
            
            if not participant:
                await ctx.send(f"❌ Could not find {riot_id} in this game!")
                return
            
            # Extract stats and AUTO-ADD FOR ALL REGISTERED PLAYERS
            champion_mapping = self.riot_scraper.get_champion_data()
            
            queue_id = match_details['info']['queueId']
            queue_type = "ranked" if queue_id == 420 else ("custom" if queue_id == 0 else "other")
            
            players_added = 0
            players_list = []
            
            # Check all participants and add for registered players
            for p in match_details['info']['participants']:
                # Try to match participant to registered players
                p_game_name = p.get('riotIdGameName', p.get('summonerName', ''))
                p_tag = p.get('riotIdTagline', '')
                p_riot_id = f"{p_game_name}#{p_tag}" if p_tag else p_game_name
                
                # Check if this participant is registered
                is_registered = p_riot_id in self.team_data["players"]
                
                # Also check without tag variations
                if not is_registered:
                    for registered_id in self.team_data["players"].keys():
                        if registered_id.split('#')[0].lower() == p_game_name.lower():
                            p_riot_id = registered_id
                            is_registered = True
                            break
                
                if is_registered:
                    # Create match for this player
                    p_match_id = f"GAME_{game_id}_{p_riot_id}"
                    
                    # Skip if already added
                    if any(m.match_id == p_match_id for m in self.manual_storage.matches):
                        continue
                    
                    p_champion = champion_mapping.get(p['championId'], f"Champion_{p['championId']}")
                    
                    p_match = ManualMatch(
                        match_id=p_match_id,
                        summoner_name=p_riot_id,
                        champion_name=p_champion,
                        result="WIN" if p['win'] else "LOSS",
                        kills=float(p['kills']),
                        deaths=float(p['deaths']),
                        assists=float(p['assists']),
                        cs=float(p['totalMinionsKilled'] + p['neutralMinionsKilled']),
                        game_duration=int(match_details['info']['gameDuration'] / 60),
                        queue_type=queue_type,
                        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        notes=f"Imported from game ID {game_id} by {ctx.author.name}"
                    )
                    
                    if self.manual_storage.add_match(p_match):
                        players_added += 1
                        result_emoji = "✅" if p_match.result == "WIN" else "❌"
                        players_list.append(f"{result_emoji} **{p_riot_id}** ({p_champion})")
            
            if players_added > 0:
                embed = discord.Embed(
                    title="✅ Game Imported for All Players",
                    description=f"Game ID: `{game_id}`",
                    color=0x00ff00
                )
                embed.add_field(name="Players Updated", value=str(players_added), inline=True)
                embed.add_field(name="Queue Type", value=queue_type.capitalize(), inline=True)
                
                if players_list:
                    embed.add_field(
                        name="🎮 Players in Game",
                        value="\n".join(players_list[:10]),
                        inline=False
                    )
                
                embed.set_footer(text="Use !stats <player> to view updated statistics")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Game already imported for all registered players in this match")
        
        @self.bot.command(name='listgames')
        async def list_games(ctx, *, riot_id: str):
            """List all manual games for a player. Example: !listgames Faker#KR1 or !listgames Player Name#TAG"""
            matches = self.manual_storage.get_matches_for_summoner(riot_id)
            
            if not matches:
                await ctx.send(f"❌ No manual games for {riot_id}")
                return
            
            # Show in pages of 10
            page_size = 10
            total_pages = (len(matches) + page_size - 1) // page_size
            
            embed = discord.Embed(
                title=f"📝 Manual Games: {riot_id}",
                description=f"Total: {len(matches)} games (Page 1/{total_pages})",
                color=0x3498db
            )
            
            for i, match in enumerate(matches[:page_size], 1):
                status = "✅" if match.result == "WIN" else "❌"
                embed.add_field(
                    name=f"{status} {match.champion_name}",
                    value=f"KDA: {match.kills:.0f}/{match.deaths:.0f}/{match.assists:.0f} | CS: {match.cs:.0f}\n"
                          f"ID: `{match.match_id}`\n"
                          f"Date: {match.date}",
                    inline=False
                )
            
            embed.set_footer(text="Use !removegame <match_id> to remove a game")
            await ctx.send(embed=embed)
        
        @self.bot.command(name='removegame')
        async def remove_game(ctx, match_id: str):
            """Remove a manual game. Example: !removegame MANUAL_12345"""
            success = self.manual_storage.remove_match(match_id)
            
            if success:
                await ctx.send(f"✅ Removed game: `{match_id}`")
            else:
                await ctx.send(f"❌ Game not found: `{match_id}`")
        
        @self.bot.command(name='champion')
        async def champion_stats(ctx, *, champion_name: str):
            """Show detailed champion stats from Lolalytics. Example: !champion Zeri or !champion Lee Sin"""
            await ctx.send(f"🔍 Fetching data for {champion_name}...")
            
            stats = self.champion_scraper.get_champion_stats(champion_name)
            
            if not stats:
                await ctx.send(f"❌ Could not find stats for {champion_name}")
                return
            
            embed = discord.Embed(
                title=f"🏆 {stats.champion_name} - {stats.role}",
                description=f"**{stats.tier} Tier** | Patch {stats.patch}",
                color=self._tier_color(stats.tier)
            )
            
            embed.add_field(
                name="📊 Overall Stats",
                value=f"Win Rate: **{stats.win_rate:.1f}%**\n"
                      f"Pick Rate: **{stats.pick_rate:.1f}%**\n"
                      f"Ban Rate: **{stats.ban_rate:.1f}%**",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Runes",
                value=f"Primary: **{stats.primary_rune}**\n"
                      f"Secondary: **{stats.secondary_rune}**",
                inline=True
            )
            
            if stats.most_popular_items:
                items_text = "\n".join([f"• {item}" for item in stats.most_popular_items[:3]])
                embed.add_field(
                    name="📦 Most Popular Build",
                    value=items_text,
                    inline=False
                )
            
            if stats.highest_winrate_items:
                items_text = "\n".join([f"• {item}" for item in stats.highest_winrate_items[:3]])
                embed.add_field(
                    name="🏅 Highest Win Rate Build",
                    value=items_text,
                    inline=False
                )
            
            if stats.best_matchups:
                matchups = "\n".join([f"• {m.opponent_name} ({m.win_rate:.1f}%)" for m in stats.best_matchups[:3]])
                embed.add_field(
                    name="✅ Best Matchups",
                    value=matchups,
                    inline=True
                )
            
            if stats.worst_matchups:
                matchups = "\n".join([f"• {m.opponent_name} ({m.win_rate:.1f}%)" for m in stats.worst_matchups[:3]])
                embed.add_field(
                    name="❌ Worst Matchups",
                    value=matchups,
                    inline=True
                )
            
            embed.set_footer(text="Data from Lolalytics (Diamond+ ranked)")
            
            # Try to add champion icon
            icon_url = self.champion_scraper.get_champion_icon_url(champion_name)
            if icon_url:
                embed.set_thumbnail(url=icon_url)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='matchup')
        async def matchup_compare(ctx, champion1: str, champion2: str):
            """Compare two champions in a matchup. Example: !matchup Zeri Jinx"""
            await ctx.send(f"⚔️ Analyzing {champion1} vs {champion2}...")
            
            comparison = self.champion_scraper.compare_champions(champion1, champion2)
            
            if not comparison:
                await ctx.send("❌ Could not fetch matchup data")
                return
            
            stats1 = comparison['champion1']
            stats2 = comparison['champion2']
            matchup_wr = comparison['matchup_winrate']
            difficulty = comparison['difficulty']
            
            embed = discord.Embed(
                title=f"⚔️ {stats1.champion_name} vs {stats2.champion_name}",
                description=f"**{stats1.champion_name}** has **{matchup_wr:.1f}%** win rate\n"
                           f"Difficulty: **{difficulty}**",
                color=self._matchup_color(matchup_wr)
            )
            
            embed.add_field(
                name=f"🔵 {stats1.champion_name}",
                value=f"Tier: **{stats1.tier}**\n"
                      f"Win Rate: **{stats1.win_rate:.1f}%**\n"
                      f"Pick Rate: **{stats1.pick_rate:.1f}%**",
                inline=True
            )
            
            embed.add_field(
                name=f"🔴 {stats2.champion_name}",
                value=f"Tier: **{stats2.tier}**\n"
                      f"Win Rate: **{stats2.win_rate:.1f}%**\n"
                      f"Pick Rate: **{stats2.pick_rate:.1f}%**",
                inline=True
            )
            
            embed.set_footer(text="Data from Lolalytics (Diamond+ ranked)")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='tier')
        async def tier_rating(ctx, champion_name: str):
            """Quick tier check for a champion. Example: !tier Zeri"""
            stats = self.champion_scraper.get_champion_stats(champion_name)
            
            if not stats:
                await ctx.send(f"❌ Could not find {champion_name}")
                return
            
            tier_emoji = {"S": "🏆", "A": "⭐", "B": "👍", "C": "👌", "D": "👎"}.get(stats.tier[0], "❓")
            
            embed = discord.Embed(
                title=f"{tier_emoji} {stats.champion_name} - {stats.tier} Tier",
                description=f"**{stats.role}** | {stats.win_rate:.1f}% Win Rate",
                color=self._tier_color(stats.tier)
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='players')
        async def list_players(ctx):
            """List all registered players"""
            if not self.team_data["players"]:
                await ctx.send("❌ No players registered! Use `!register <riot_id> <region>`")
                return
            
            embed = discord.Embed(
                title="👥 Registered Players",
                color=0x9b59b6
            )
            
            for riot_id, data in self.team_data["players"].items():
                status = "✅" if data["ranked_stats"] else "⏳"
                manual_count = len(self.manual_storage.get_matches_for_summoner(riot_id))
                
                embed.add_field(
                    name=f"{status} {riot_id}",
                    value=f"Region: {data['region'].upper()}\n"
                          f"Manual games: {manual_count}",
                    inline=True
                )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='remove', aliases=['unregister'])
        async def remove_player(ctx, *, riot_id: str):
            """Unregister a player completely (removes player and all their data). Example: !remove Faker#KR1 or !unregister Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            # Count what will be removed
            manual_matches = self.manual_storage.get_matches_for_summoner(riot_id)
            manual_count = len(manual_matches)
            has_ranked = self.team_data["players"][riot_id].get("ranked_stats") is not None
            
            # Remove from manual storage
            self.manual_storage.matches = [m for m in self.manual_storage.matches if m.summoner_name != riot_id]
            self.manual_storage.save_matches()
            
            # Remove from all teams
            teams_removed_from = []
            for team_name, team in self.team_data.get("teams", {}).items():
                if riot_id in team["players"]:
                    team["players"].remove(riot_id)
                    teams_removed_from.append(team_name)
            
            # Remove from players
            del self.team_data["players"][riot_id]
            self.save_team_data()
            
            embed = discord.Embed(
                title="🗑️ Player Unregistered",
                description=f"**{riot_id}** has been completely removed",
                color=0xff6b35
            )
            embed.add_field(name="Manual games deleted", value=str(manual_count), inline=True)
            embed.add_field(name="Ranked stats deleted", value="Yes" if has_ranked else "No", inline=True)
            
            if teams_removed_from:
                embed.add_field(
                    name="Removed from teams",
                    value=", ".join(teams_removed_from),
                    inline=False
                )
            
            embed.set_footer(text="All data for this player has been permanently deleted")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='unregisterall')
        async def unregister_all_players(ctx, confirmation: str = None):
            """Unregister ALL players (removes everything). Example: !unregisterall confirm"""
            if confirmation != 'confirm':
                # Show warning
                total_players = len(self.team_data["players"])
                total_manual = len(self.manual_storage.matches)
                total_teams = len(self.team_data.get("teams", {}))
                
                embed = discord.Embed(
                    title="⚠️ WARNING - Unregister All Players",
                    description="This will **permanently delete EVERYTHING**!",
                    color=0xe74c3c
                )
                
                embed.add_field(
                    name="🗑️ What Will Be Deleted",
                    value=f"• **{total_players}** player registrations\n"
                          f"• **{total_manual}** manual games\n"
                          f"• All ranked stats\n"
                          f"• **{total_teams}** teams",
                    inline=False
                )
                
                embed.add_field(
                    name="⚠️ This Is Permanent!",
                    value="Everything will be deleted. You'll need to re-register all players.",
                    inline=False
                )
                
                embed.add_field(
                    name="🔄 To Proceed",
                    value="Type: `!unregisterall confirm`",
                    inline=False
                )
                
                embed.set_footer(text="⛔ THIS CANNOT BE UNDONE!")
                
                await ctx.send(embed=embed)
                return
            
            # Confirmation received
            total_players = len(self.team_data["players"])
            total_manual = len(self.manual_storage.matches)
            total_teams = len(self.team_data.get("teams", {}))
            
            # Clear everything
            self.manual_storage.clear_all_matches()
            self.team_data["players"] = {}
            self.team_data["teams"] = {}
            self.save_team_data()
            
            embed = discord.Embed(
                title="🗑️ Everything Deleted",
                description="⚠️ All players and data have been permanently removed",
                color=0xe74c3c
            )
            embed.add_field(name="Players unregistered", value=str(total_players), inline=True)
            embed.add_field(name="Games deleted", value=str(total_manual), inline=True)
            embed.add_field(name="Teams deleted", value=str(total_teams), inline=True)
            
            embed.set_footer(text="Fresh start! Use !register to add players again")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='team')
        async def team_overview(ctx):
            """Show team overview"""
            if not self.team_data["players"]:
                await ctx.send("❌ No players registered!")
                return
            
            embed = discord.Embed(
                title="👥 Team Overview",
                description=f"**{len(self.team_data['players'])}** players registered",
                color=0xff6b35
            )
            
            total_manual = 0
            players_with_ranked = 0
            
            for riot_id, data in self.team_data["players"].items():
                manual_count = len(self.manual_storage.get_matches_for_summoner(riot_id))
                total_manual += manual_count
                if data.get("ranked_stats"):
                    players_with_ranked += 1
            
            embed.add_field(
                name="📊 Stats",
                value=f"Players with ranked data: **{players_with_ranked}**\n"
                      f"Total manual games: **{total_manual}**",
                inline=False
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='sync')
        async def sync_recent_games(ctx, *, args: str):
            """Auto-import recent games from Riot API. Example: !sync Faker#KR1 20 or !sync Player Name#TAG 50"""
            # Parse riot_id and count
            parts = args.split()
            riot_id_parts = []
            found_tag = False
            count = 20
            
            for part in parts:
                if not found_tag:
                    riot_id_parts.append(part)
                    if '#' in part:
                        found_tag = True
                elif part.isdigit():
                    count = int(part)
                    break
            
            riot_id = ' '.join(riot_id_parts)
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered! Use `!register {riot_id} <region>`")
                return
            
            # Limit to reasonable amount
            if count > 500:
                await ctx.send(f"⚠️ Maximum 500 games allowed. Setting count to 500.")
                count = 500
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`")
                return
            
            if count > 100:
                await ctx.send(f"🔄 Fetching {count} ranked games (this may take a minute)...")
            else:
                await ctx.send(f"🔄 Fetching last {count} ranked games for {riot_id}...")
            
            # Get summoner info
            summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
            if not summoner_info:
                await ctx.send(f"❌ Could not find summoner {riot_id}")
                return
            
            # Get match history (only ranked games for !sync)
            try:
                match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, count, queue=420)
            except Exception as e:
                await ctx.send(f"❌ Error fetching match history: {str(e)}")
                return
                
            if not match_ids:
                await ctx.send(f"❌ No recent ranked games found")
                return
            
            # Import each match
            champion_mapping = self.riot_scraper.get_champion_data()
            imported = 0
            skipped = 0
            errors = 0
            
            # Show progress for large imports
            if count > 50:
                status_msg = await ctx.send(f"⏳ Importing {len(match_ids)} ranked games... (0% complete)")
            
            for i, match_id in enumerate(match_ids):
                try:
                    # Add async delay every 10 games to prevent blocking
                    if i > 0 and i % 10 == 0:
                        await asyncio.sleep(0.1)
                    
                    # Update progress for large imports
                    if count > 50 and i > 0 and i % 20 == 0:
                        percent = int((i / len(match_ids)) * 100)
                        try:
                            await status_msg.edit(content=f"⏳ Imported {i}/{len(match_ids)} games ({percent}%)...")
                        except:
                            pass  # Ignore connection errors
                    
                    match_details = self.riot_scraper.get_match_details(match_id, region)
                    if not match_details:
                        errors += 1
                        continue
                    
                    # Find player in match
                    participant = None
                    for p in match_details['info']['participants']:
                        if p['puuid'] == summoner_info['puuid']:
                            participant = p
                            break
                    
                    if not participant:
                        continue
                    
                    # Check if already imported
                    manual_match_id = f"SYNC_{match_id}"
                    if any(m.match_id == manual_match_id for m in self.manual_storage.matches):
                        skipped += 1
                        continue
                    
                    # Create manual match
                    champion_name = champion_mapping.get(participant['championId'], f"Champion_{participant['championId']}")
                    match = ManualMatch(
                        match_id=manual_match_id,
                        summoner_name=riot_id,
                        champion_name=champion_name,
                        result="WIN" if participant['win'] else "LOSS",
                        kills=float(participant['kills']),
                        deaths=float(participant['deaths']),
                        assists=float(participant['assists']),
                        cs=float(participant['totalMinionsKilled'] + participant['neutralMinionsKilled']),
                        game_duration=int(match_details['info']['gameDuration'] / 60),
                        queue_type="ranked" if match_details['info']['queueId'] == 420 else "other",
                        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        notes=f"Auto-synced by {ctx.author.name}"
                    )
                    
                    if self.manual_storage.add_match(match):
                        imported += 1
                        
                except Exception as e:
                    errors += 1
                    print(f"❌ Error processing match {match_id}: {e}")
                    continue
            
            # Delete progress message if it exists
            if count > 50:
                try:
                    await status_msg.delete()
                except:
                    pass
            
            embed = discord.Embed(
                title="✅ Ranked Games Synced",
                description=f"Imported ranked games for **{riot_id}**",
                color=0x00ff00
            )
            embed.add_field(name="Imported", value=str(imported), inline=True)
            embed.add_field(name="Skipped (already imported)", value=str(skipped), inline=True)
            embed.add_field(name="Total checked", value=str(len(match_ids)), inline=True)
            
            if errors > 0:
                embed.add_field(
                    name="⚠️ Errors",
                    value=f"{errors} games failed to process",
                    inline=False
                )
            
            embed.set_footer(text="Use !stats to view updated statistics")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='importtournament')
        async def import_tournament(ctx, tournament_code: str, region: str = "euw"):
            """Import games from tournament code. Example: !importtournament EUW1234-CODE euw"""
            await ctx.send(f"🔍 Fetching games from tournament code...")
            
            # Get match IDs from tournament code
            match_ids = self.riot_scraper.get_tournament_matches(tournament_code, region)
            
            if not match_ids:
                await ctx.send(f"❌ No games found for tournament code `{tournament_code}`")
                return
            
            await ctx.send(f"✅ Found {len(match_ids)} games! Importing...")
            
            champion_mapping = self.riot_scraper.get_champion_data()
            imported = 0
            games_info = []
            
            for match_id in match_ids:
                match_details = self.riot_scraper.get_match_details(match_id, region)
                if not match_details:
                    continue
                
                # Import for each participant
                for participant in match_details['info']['participants']:
                    # Find riot_id from participant
                    summoner_name = participant['riotIdGameName'] if 'riotIdGameName' in participant else participant['summonerName']
                    riot_id = summoner_name  # Simplified, could be enhanced
                    
                    # Check if already imported
                    manual_match_id = f"TOURNAMENT_{match_id}_{participant['participantId']}"
                    if any(m.match_id == manual_match_id for m in self.manual_storage.matches):
                        continue
                    
                    champion_name = champion_mapping.get(participant['championId'], f"Champion_{participant['championId']}")
                    match = ManualMatch(
                        match_id=manual_match_id,
                        summoner_name=riot_id,
                        champion_name=champion_name,
                        result="WIN" if participant['win'] else "LOSS",
                        kills=float(participant['kills']),
                        deaths=float(participant['deaths']),
                        assists=float(participant['assists']),
                        cs=float(participant['totalMinionsKilled'] + participant['neutralMinionsKilled']),
                        game_duration=int(match_details['info']['gameDuration'] / 60),
                        queue_type="tournament",
                        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        notes=f"Tournament: {tournament_code}"
                    )
                    
                    if self.manual_storage.add_match(match):
                        imported += 1
                        result_emoji = "✅" if match.result == "WIN" else "❌"
                        games_info.append(f"{result_emoji} {champion_name} ({riot_id}) - {match.result}")
            
            embed = discord.Embed(
                title="🏆 Tournament Games Imported",
                description=f"Tournament Code: `{tournament_code}`",
                color=0xffd700
            )
            embed.add_field(name="Games imported", value=str(imported), inline=True)
            embed.add_field(name="Total games", value=str(len(match_ids)), inline=True)
            
            if games_info[:10]:  # Show first 10
                embed.add_field(
                    name="Games",
                    value="\n".join(games_info[:10]),
                    inline=False
                )
            
            embed.set_footer(text="Use !stats to view updated statistics")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='synccustom')
        async def sync_custom_games(ctx, *, args: str):
            """Auto-import custom/tournament games from match history. Example: !synccustom Odd#kimmy 50 or !synccustom Player Name#TAG 100"""
            # Parse riot_id and count
            parts = args.split()
            riot_id_parts = []
            found_tag = False
            count = 50
            
            for part in parts:
                if not found_tag:
                    riot_id_parts.append(part)
                    if '#' in part:
                        found_tag = True
                elif part.isdigit():
                    count = int(part)
                    break
            
            riot_id = ' '.join(riot_id_parts)
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered! Use `!register {riot_id} <region>`")
                return
            
            # Limit to reasonable amount
            if count > 500:
                await ctx.send(f"⚠️ Maximum 500 games allowed. Setting count to 500.")
                count = 500
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`")
                return
            
            if count > 100:
                await ctx.send(f"🔍 Scanning last {count} games for custom/tournament games (this may take a few minutes)...")
            else:
                await ctx.send(f"🔍 Scanning last {count} games for custom/tournament games...")
            
            # Get summoner info
            summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
            if not summoner_info:
                await ctx.send(f"❌ Could not find summoner {riot_id}")
                return
            
            # Get match history (ALL games, not just ranked)
            try:
                match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, count)
            except Exception as e:
                await ctx.send(f"❌ Error fetching match history: {str(e)}")
                return
                
            if not match_ids:
                await ctx.send(f"❌ No recent games found")
                return
            
            # Scan for custom games
            champion_mapping = self.riot_scraper.get_champion_data()
            imported = 0
            skipped = 0
            custom_found = 0
            errors = 0
            
            status_msg = await ctx.send(f"⏳ Checking {len(match_ids)} games... (0% complete)")
            
            for i, match_id in enumerate(match_ids):
                try:
                    # Add async delay every 10 games to prevent blocking
                    if i > 0 and i % 10 == 0:
                        await asyncio.sleep(0.1)
                        percent = int((i / len(match_ids)) * 100)
                        try:
                            await status_msg.edit(content=f"⏳ Checked {i}/{len(match_ids)} games ({percent}%)... Found {custom_found} custom games")
                        except:
                            pass  # Ignore connection errors during progress updates
                    
                    match_details = self.riot_scraper.get_match_details(match_id, region)
                    if not match_details:
                        errors += 1
                        continue
                    
                    # Check if it's a custom game
                    # Queue ID 0 = Custom games (including tournament draft)
                    # Only detect true custom/tournament games
                    queue_id = match_details['info']['queueId']
                    
                    # Queue 0 = Custom games (5v5 Draft/Blind)
                    # Queue 2000-2020 = Tournament code games
                    # Excludes: Clash (700), Arena (1700/3100), ARURF (900), ARAM (450), etc.
                    if queue_id != 0 and not (2000 <= queue_id <= 2020):
                        continue
                    
                    custom_found += 1
                    
                    # Find player in match
                    participant = None
                    for p in match_details['info']['participants']:
                        if p['puuid'] == summoner_info['puuid']:
                            participant = p
                            break
                    
                    if not participant:
                        continue
                    
                    # Check if already imported for this player
                    manual_match_id = f"CUSTOM_{match_id}_{riot_id}"
                    if any(m.match_id == manual_match_id for m in self.manual_storage.matches):
                        skipped += 1
                        continue
                    
                    # Determine game type based on queue
                    if queue_id == 0:
                        game_type = "custom"
                    elif 2000 <= queue_id <= 2020:
                        game_type = "tournament"
                    else:
                        game_type = "tournament"
                    
                    # AUTO-ADD FOR ALL REGISTERED PLAYERS IN THE GAME
                    players_added = 0
                    for p in match_details['info']['participants']:
                        # Try to match participant to registered players
                        p_game_name = p.get('riotIdGameName', p.get('summonerName', ''))
                        p_tag = p.get('riotIdTagline', '')
                        p_riot_id = f"{p_game_name}#{p_tag}" if p_tag else p_game_name
                        
                        # Check if this participant is registered
                        is_registered = p_riot_id in self.team_data["players"]
                        
                        # Also check without tag variations
                        if not is_registered:
                            for registered_id in self.team_data["players"].keys():
                                if registered_id.split('#')[0].lower() == p_game_name.lower():
                                    p_riot_id = registered_id
                                    is_registered = True
                                    break
                        
                        if is_registered:
                            # Create match for this player
                            p_match_id = f"CUSTOM_{match_id}_{p_riot_id}"
                            
                            # Skip if already added
                            if any(m.match_id == p_match_id for m in self.manual_storage.matches):
                                continue
                            
                            p_champion = champion_mapping.get(p['championId'], f"Champion_{p['championId']}")
                            
                            p_match = ManualMatch(
                                match_id=p_match_id,
                                summoner_name=p_riot_id,
                                champion_name=p_champion,
                                result="WIN" if p['win'] else "LOSS",
                                kills=float(p['kills']),
                                deaths=float(p['deaths']),
                                assists=float(p['assists']),
                                cs=float(p['totalMinionsKilled'] + p['neutralMinionsKilled']),
                                game_duration=int(match_details['info']['gameDuration'] / 60),
                                queue_type=game_type,
                                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                notes=f"Auto-imported (found {p_riot_id} in game)"
                            )
                            
                            if self.manual_storage.add_match(p_match):
                                players_added += 1
                    
                    if players_added > 0:
                        imported += players_added
                        
                except Exception as e:
                    errors += 1
                    print(f"❌ Error processing match {match_id}: {e}")
                    continue
            
            # Final result
            embed = discord.Embed(
                title="✅ Custom Games Scan Complete",
                description=f"Scanned match history for **{riot_id}**",
                color=0x00ff00
            )
            embed.add_field(name="Games Scanned", value=str(len(match_ids)), inline=True)
            embed.add_field(name="Custom Games Found", value=str(custom_found), inline=True)
            embed.add_field(name="Stats Imported", value=f"{imported} (all registered players)", inline=True)
            embed.add_field(name="Already Imported", value=str(skipped), inline=True)
            
            if errors > 0:
                embed.add_field(
                    name="⚠️ Errors",
                    value=f"{errors} games failed to process (rate limit or network issues)",
                    inline=False
                )
            
            if imported > 0:
                embed.add_field(
                    name="💡 Next Step",
                    value="Use `!stats` to view updated statistics!",
                    inline=False
                )
            elif custom_found == 0:
                embed.add_field(
                    name="ℹ️ Note",
                    value="No custom games found in recent match history.\n"
                          "Custom games include: Tournament Draft, Custom lobbies, Practice games.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="ℹ️ Note",
                    value="All custom games were already imported previously.",
                    inline=False
                )
            
            embed.set_footer(text="Custom games include tournament games with codes")
            
            try:
                await status_msg.delete()
            except:
                pass
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='lastgame')
        async def last_game(ctx, *, riot_id: str):
            """Show detailed last game analysis. Example: !lastgame Faker#KR1 or !lastgame Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`")
                return
            
            await ctx.send(f"🔍 Fetching last game for {riot_id}...")
            
            # Get summoner info
            summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
            if not summoner_info:
                await ctx.send(f"❌ Could not find summoner")
                return
            
            # Get last game
            match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, 1)
            if not match_ids:
                await ctx.send(f"❌ No recent games found")
                return
            
            match_details = self.riot_scraper.get_match_details(match_ids[0], region)
            if not match_details:
                await ctx.send(f"❌ Could not fetch game details")
                return
            
            # Find player
            participant = None
            for p in match_details['info']['participants']:
                if p['puuid'] == summoner_info['puuid']:
                    participant = p
                    break
            
            if not participant:
                await ctx.send(f"❌ Player not found in match")
                return
            
            # Create detailed embed
            champion_mapping = self.riot_scraper.get_champion_data()
            champion_name = champion_mapping.get(participant['championId'], "Unknown")
            result = "VICTORY" if participant['win'] else "DEFEAT"
            color = 0x00ff00 if participant['win'] else 0xff0000
            
            # Add result emoji
            result_emoji = "✅" if participant['win'] else "❌"
            
            embed = discord.Embed(
                title=f"{result_emoji} Last Game - {riot_id}",
                description=f"**{champion_name}** - {result}",
                color=color
            )
            
            # Add champion icon
            icon_url = self.champion_scraper.get_champion_icon_url(champion_name)
            if icon_url:
                embed.set_thumbnail(url=icon_url)
            
            # KDA
            kda = (participant['kills'] + participant['assists']) / max(participant['deaths'], 1)
            embed.add_field(
                name="📊 KDA",
                value=f"{participant['kills']}/{participant['deaths']}/{participant['assists']}\n"
                      f"**{kda:.2f}** KDA",
                inline=True
            )
            
            # CS
            cs = participant['totalMinionsKilled'] + participant['neutralMinionsKilled']
            duration_min = match_details['info']['gameDuration'] / 60
            cs_per_min = cs / duration_min if duration_min > 0 else 0
            embed.add_field(
                name="🌾 CS",
                value=f"{cs} CS\n**{cs_per_min:.1f}** CS/min",
                inline=True
            )
            
            # Damage
            embed.add_field(
                name="⚔️ Damage",
                value=f"{participant['totalDamageDealtToChampions']:,} to champions\n"
                      f"{participant['totalDamageTaken']:,} taken",
                inline=True
            )
            
            # Gold & Vision
            embed.add_field(
                name="💰 Gold",
                value=f"{participant['goldEarned']:,}",
                inline=True
            )
            embed.add_field(
                name="👁️ Vision",
                value=f"{participant['visionScore']} score\n"
                      f"{participant['wardsPlaced']} wards placed",
                inline=True
            )
            
            # Duration
            duration_str = f"{int(duration_min)}:{int((duration_min % 1) * 60):02d}"
            embed.add_field(
                name="⏱️ Duration",
                value=duration_str,
                inline=True
            )
            
            # Items
            items = []
            for i in range(7):
                item_id = participant.get(f'item{i}', 0)
                if item_id > 0:
                    items.append(str(item_id))
            if items:
                embed.add_field(
                    name="📦 Items",
                    value=" | ".join(items) if items else "No items",
                    inline=False
                )
            
            embed.set_footer(text=f"Match ID: {match_ids[0]}")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='live')
        async def check_live(ctx, *, riot_id: str):
            """Check if player is in game. Example: !live Faker#KR1 or !live Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`")
                return
            
            # Get summoner info
            summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
            if not summoner_info:
                await ctx.send(f"❌ Could not find summoner")
                return
            
            # Check current game (using PUUID)
            # Note: Spectator endpoint might not be available with Personal API keys
            await ctx.send(f"⚠️ Live game detection temporarily unavailable due to API changes. Feature coming soon!")
            return
            
            current_game = self.riot_scraper.get_current_game(summoner_info['puuid'], region)
            
            if not current_game:
                embed = discord.Embed(
                    title=f"💤 {riot_id}",
                    description="Not currently in game",
                    color=0x95a5a6
                )
                await ctx.send(embed=embed)
                return
            
            # Parse game data
            champion_mapping = self.riot_scraper.get_champion_data()
            
            # Find player's champion
            player_champion = None
            for participant in current_game['participants']:
                if participant['summonerId'] == summoner_info['id']:
                    player_champion = champion_mapping.get(participant['championId'], "Unknown")
                    break
            
            game_length = current_game['gameLength']
            game_duration = f"{game_length // 60}:{game_length % 60:02d}"
            
            queue_types = {
                420: "Ranked Solo/Duo",
                440: "Ranked Flex",
                450: "ARAM",
                400: "Normal Draft",
                430: "Normal Blind"
            }
            queue_name = queue_types.get(current_game['gameQueueConfigId'], "Custom/Other")
            
            embed = discord.Embed(
                title=f"🎮 {riot_id} is IN GAME!",
                description=f"Playing **{player_champion}**",
                color=0x00ff00
            )
            
            embed.add_field(name="Queue", value=queue_name, inline=True)
            embed.add_field(name="Duration", value=game_duration, inline=True)
            embed.add_field(name="Map", value=current_game.get('mapId', 'Unknown'), inline=True)
            
            # Team compositions
            team_100 = []
            team_200 = []
            for participant in current_game['participants']:
                champ = champion_mapping.get(participant['championId'], "Unknown")
                if participant['teamId'] == 100:
                    team_100.append(champ)
                else:
                    team_200.append(champ)
            
            embed.add_field(
                name="🔵 Blue Team",
                value="\n".join(team_100),
                inline=True
            )
            embed.add_field(
                name="🔴 Red Team",
                value="\n".join(team_200),
                inline=True
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='mastery')
        async def check_mastery(ctx, *, args: str):
            """Show champion mastery. Example: !mastery Faker#KR1 or !mastery Player Name#TAG Zeri"""
            # Parse riot_id and optional champion_name
            parts = args.split()
            riot_id_parts = []
            found_tag = False
            champion_name = None
            
            for i, part in enumerate(parts):
                if not found_tag:
                    riot_id_parts.append(part)
                    if '#' in part:
                        found_tag = True
                else:
                    # Rest is champion name
                    champion_name = ' '.join(parts[i:])
                    break
            
            riot_id = ' '.join(riot_id_parts)
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`")
                return
            
            # Get summoner info
            summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
            if not summoner_info:
                await ctx.send(f"❌ Could not find summoner")
                return
            
            # Get masteries
            masteries = self.riot_scraper.get_champion_masteries(summoner_info['puuid'], region)
            if not masteries:
                await ctx.send(f"❌ Could not fetch champion masteries")
                return
            
            champion_mapping = self.riot_scraper.get_champion_data()
            id_to_name = champion_mapping
            name_to_id = {v.lower(): k for k, v in champion_mapping.items()}
            
            if champion_name:
                # Show specific champion
                champ_id = name_to_id.get(champion_name.lower())
                if not champ_id:
                    await ctx.send(f"❌ Champion {champion_name} not found")
                    return
                
                mastery = next((m for m in masteries if m['championId'] == champ_id), None)
                if not mastery:
                    await ctx.send(f"❌ No mastery data for {champion_name}")
                    return
                
                embed = discord.Embed(
                    title=f"🏆 {champion_name} Mastery",
                    description=f"Player: **{riot_id}**",
                    color=0x00ff00
                )
                embed.add_field(name="Level", value=str(mastery['championLevel']), inline=True)
                embed.add_field(name="Points", value=f"{mastery['championPoints']:,}", inline=True)
                embed.add_field(name="Chest", value="✅" if mastery['chestGranted'] else "❌", inline=True)
                
            else:
                # Show top masteries
                embed = discord.Embed(
                    title=f"🏆 Top Champion Masteries",
                    description=f"Player: **{riot_id}**",
                    color=0x00ff00
                )
                
                for i, mastery in enumerate(masteries[:10], 1):
                    champ_name = id_to_name.get(mastery['championId'], "Unknown")
                    chest = "✅" if mastery['chestGranted'] else "❌"
                    embed.add_field(
                        name=f"{i}. {champ_name}",
                        value=f"Level {mastery['championLevel']} | {mastery['championPoints']:,} pts | Chest: {chest}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='debug')
        async def debug_stats(ctx, *, riot_id: str):
            """Debug stats sources for troubleshooting. Example: !debug Odd#kimmy or !debug Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            player_data = self.team_data["players"][riot_id]
            ranked_stats = player_data.get("ranked_stats")
            manual_matches = self.manual_storage.get_matches_for_summoner(riot_id)
            
            embed = discord.Embed(
                title=f"🔍 Debug Info - {riot_id}",
                description="Data source breakdown",
                color=0x3498db
            )
            
            # Ranked stats from API
            if ranked_stats and ranked_stats.get("champions"):
                ranked_text = f"**Champions from !update:** {len(ranked_stats['champions'])}\n"
                for champ in ranked_stats['champions'][:10]:
                    ranked_text += f"• {champ['name']}: {champ['games']}g, {champ['wins']}W {champ['losses']}L\n"
                embed.add_field(
                    name="📊 Ranked Stats (from API)",
                    value=ranked_text,
                    inline=False
                )
            
            # Manual matches breakdown
            if manual_matches:
                ranked_manual = [m for m in manual_matches if m.queue_type in ['ranked', 'other']]
                custom_manual = [m for m in manual_matches if m.queue_type in ['custom', 'tournament', 'tournament_draft', 'scrim']]
                
                manual_text = f"**Total manual games:** {len(manual_matches)}\n"
                manual_text += f"• Ranked (from !sync): {len(ranked_manual)}\n"
                manual_text += f"• Custom/Tournament: {len(custom_manual)}\n"
                
                # Show champions in manual
                from collections import Counter
                champ_counts = Counter([m.champion_name for m in manual_matches])
                manual_text += f"\n**Champion breakdown:**\n"
                for champ, count in champ_counts.most_common(10):
                    queue_types = [m.queue_type for m in manual_matches if m.champion_name == champ]
                    queue_counts = Counter(queue_types)
                    manual_text += f"• {champ}: {count}g {dict(queue_counts)}\n"
                
                embed.add_field(
                    name="📝 Manual Matches",
                    value=manual_text,
                    inline=False
                )
            
            embed.set_footer(text="Use this to verify data sources")
            await ctx.send(embed=embed)
        
        @self.bot.command(name='matchhistory')
        async def match_history(ctx, *, args: str):
            """Show actual match history with dates. Example: !matchhistory Odd#kimmy 10 or !matchhistory Player Name#TAG 15"""
            # Parse riot_id and count
            parts = args.split()
            riot_id_parts = []
            found_tag = False
            count = 10
            
            for part in parts:
                if not found_tag:
                    riot_id_parts.append(part)
                    if '#' in part:
                        found_tag = True
                elif part.isdigit():
                    count = int(part)
                    break
            
            riot_id = ' '.join(riot_id_parts)
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format! Must include tag: `Name#TAG`")
                return
            
            if count > 20:
                count = 20
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            await ctx.send(f"🔍 Fetching last {count} matches for {riot_id}...")
            
            # Get summoner info
            summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
            if not summoner_info:
                await ctx.send(f"❌ Could not find summoner")
                return
            
            # Get match history
            match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, count, queue=420)
            if not match_ids:
                await ctx.send(f"❌ No recent ranked games found")
                return
            
            champion_mapping = self.riot_scraper.get_champion_data()
            
            embed = discord.Embed(
                title=f"📜 Match History - {riot_id}",
                description=f"Last {len(match_ids)} ranked games",
                color=0x3498db
            )
            
            # Get details for each match
            for i, match_id in enumerate(match_ids[:count], 1):
                match_details = self.riot_scraper.get_match_details(match_id, region)
                if not match_details:
                    continue
                
                # Find player
                participant = None
                for p in match_details['info']['participants']:
                    if p['puuid'] == summoner_info['puuid']:
                        participant = p
                        break
                
                if not participant:
                    continue
                
                champion_name = champion_mapping.get(participant['championId'], "Unknown")
                result = "✅ WIN" if participant['win'] else "❌ LOSS"
                kda = f"{participant['kills']}/{participant['deaths']}/{participant['assists']}"
                
                # Get game date from timestamp
                game_creation = match_details['info']['gameCreation']
                game_date = datetime.fromtimestamp(game_creation / 1000).strftime('%Y-%m-%d %H:%M')
                
                embed.add_field(
                    name=f"{i}. {result} - {champion_name}",
                    value=f"KDA: {kda} | Date: {game_date}\nMatch ID: `{match_id[-10:]}`",
                    inline=False
                )
            
            embed.set_footer(text="Use this to verify which games were counted")
            await ctx.send(embed=embed)
        
        @self.bot.command(name='scanqueues')
        async def scan_queue_types(ctx, *, args: str):
            """Debug: Show queue types in match history. Example: !scanqueues Odd#kimmy 50 or !scanqueues Player Name#TAG 100"""
            # Parse riot_id and count
            parts = args.split()
            riot_id_parts = []
            found_tag = False
            count = 50
            
            for part in parts:
                if not found_tag:
                    riot_id_parts.append(part)
                    if '#' in part:
                        found_tag = True
                elif part.isdigit():
                    count = int(part)
                    break
            
            riot_id = ' '.join(riot_id_parts)
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            if '#' not in riot_id:
                await ctx.send(f"❌ Invalid Riot ID format!")
                return
            
            player_data = self.team_data["players"][riot_id]
            region = player_data["region"]
            
            await ctx.send(f"🔍 Scanning queue types in last {count} games...")
            
            summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
            if not summoner_info:
                await ctx.send(f"❌ Could not find summoner")
                return
            
            # Get ALL games (no queue filter)
            match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, count)
            if not match_ids:
                await ctx.send(f"❌ No games found")
                return
            
            champion_mapping = self.riot_scraper.get_champion_data()
            queue_breakdown = {}
            game_details = []
            
            for i, match_id in enumerate(match_ids[:count]):
                if i > 0 and i % 10 == 0:
                    await asyncio.sleep(0.1)
                
                match_details = self.riot_scraper.get_match_details(match_id, region)
                if not match_details:
                    continue
                
                queue_id = match_details['info']['queueId']
                queue_breakdown[queue_id] = queue_breakdown.get(queue_id, 0) + 1
                
                # Get champion and date for custom/tournament games
                if queue_id in [0, 700, 1700, 2000, 2010, 2020, 3100]:
                    for p in match_details['info']['participants']:
                        if p['puuid'] == summoner_info['puuid']:
                            champ = champion_mapping.get(p['championId'], "Unknown")
                            game_date = datetime.fromtimestamp(match_details['info']['gameCreation'] / 1000).strftime('%Y-%m-%d')
                            result = "WIN" if p['win'] else "LOSS"
                            queue_name = queue_names.get(queue_id, f"ID {queue_id}")
                            game_details.append(f"• {queue_name}: {champ} ({result}) - {game_date}")
                            break
            
            embed = discord.Embed(
                title=f"🔍 Queue Type Analysis - {riot_id}",
                description=f"Scanned {len(match_ids)} games",
                color=0x3498db
            )
            
            # Queue ID reference
            queue_names = {
                0: "Custom",
                420: "Ranked Solo/Duo",
                440: "Ranked Flex",
                450: "ARAM",
                400: "Normal Draft",
                430: "Normal Blind",
                700: "Clash",
                1700: "Tournament Draft / Arena",
                2000: "Tutorial 1",
                2010: "Tutorial 2",
                2020: "Tutorial 3",
                3100: "Cherry (Arena 2v2v2v2)"
            }
            
            breakdown_text = ""
            custom_queue_ids = [0, 700, 1700, 2000, 2010, 2020, 3100]
            
            for queue_id in sorted(queue_breakdown.keys()):
                count_games = queue_breakdown[queue_id]
                queue_name = queue_names.get(queue_id, f"Unknown ({queue_id})")
                
                # Mark which queues are imported by !synccustom
                if queue_id in custom_queue_ids:
                    breakdown_text += f"✅ **{queue_name}** (ID: {queue_id}): {count_games} games ← Imported by !synccustom\n"
                else:
                    breakdown_text += f"**{queue_name}** (ID: {queue_id}): {count_games} games\n"
            
            embed.add_field(
                name="📊 Queue Breakdown",
                value=breakdown_text if breakdown_text else "No games found",
                inline=False
            )
            
            if game_details:
                custom_text = "\n".join(game_details[:10])
                embed.add_field(
                    name="🎮 Custom Games Found",
                    value=custom_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ Custom Games",
                    value="No custom games found in this range!",
                    inline=False
                )
            
            embed.set_footer(text="Custom/Tournament games: 0 (Custom), 700 (Clash), 1700 (Tournament Draft), 3100 (Arena)")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='clearstats')
        async def clear_player_stats(ctx, *, riot_id: str):
            """Clear all stats for a specific player. Example: !clearstats Odd#kimmy or !clearstats Player Name#TAG"""
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered!")
                return
            
            # Count games before clearing
            manual_matches = self.manual_storage.get_matches_for_summoner(riot_id)
            manual_count = len(manual_matches)
            
            # Remove from manual storage
            original_count = len(self.manual_storage.matches)
            self.manual_storage.matches = [m for m in self.manual_storage.matches if m.summoner_name != riot_id]
            self.manual_storage.save_matches()
            
            # Clear ranked stats
            self.team_data["players"][riot_id]["ranked_stats"] = None
            self.team_data["players"][riot_id]["last_updated"] = None
            self.save_team_data()
            
            embed = discord.Embed(
                title="🗑️ Stats Cleared",
                description=f"All stats cleared for **{riot_id}**",
                color=0xff6b35
            )
            embed.add_field(name="Manual games removed", value=str(manual_count), inline=True)
            embed.add_field(name="Ranked stats", value="Cleared", inline=True)
            embed.set_footer(text="Use !update or !sync to rebuild stats")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='clearall')
        async def clear_all_stats(ctx, confirmation: str = None):
            """Clear ALL stats for ALL players. Example: !clearall confirm"""
            if confirmation != 'confirm':
                # Show warning
                embed = discord.Embed(
                    title="⚠️ WARNING - Clear All Stats",
                    description="This will **permanently delete ALL stats** for ALL players!",
                    color=0xe74c3c
                )
                
                total_manual = len(self.manual_storage.matches)
                total_players = len(self.team_data["players"])
                
                embed.add_field(
                    name="📊 What Will Be Deleted",
                    value=f"• **{total_manual}** manual games\n"
                          f"• Ranked stats for **{total_players}** players\n"
                          f"• All imported game data",
                    inline=False
                )
                
                embed.add_field(
                    name="✅ What Will Be Kept",
                    value="• Player registrations\n• Team rosters\n• Bot settings",
                    inline=False
                )
                
                embed.add_field(
                    name="🔄 To Proceed",
                    value="Type: `!clearall confirm`",
                    inline=False
                )
                
                embed.set_footer(text="⚠️ This action cannot be undone!")
                
                await ctx.send(embed=embed)
                return
            
            # Confirmation received - clear everything
            total_manual = len(self.manual_storage.matches)
            total_players = len(self.team_data["players"])
            
            # Clear all manual matches
            self.manual_storage.clear_all_matches()
            
            # Clear all ranked stats
            for riot_id in self.team_data["players"]:
                self.team_data["players"][riot_id]["ranked_stats"] = None
                self.team_data["players"][riot_id]["last_updated"] = None
            self.save_team_data()
            
            embed = discord.Embed(
                title="🗑️ All Stats Cleared",
                description="⚠️ All statistics have been permanently deleted",
                color=0xe74c3c
            )
            embed.add_field(name="Manual games removed", value=str(total_manual), inline=True)
            embed.add_field(name="Players affected", value=str(total_players), inline=True)
            
            embed.add_field(
                name="✅ Kept",
                value=f"• Player registrations: {total_players}\n• Team rosters: {len(self.team_data.get('teams', {}))}",
                inline=False
            )
            
            embed.set_footer(text="Players are still registered. Use !sync to rebuild stats")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='createteam')
        async def create_team(ctx, team_name: str):
            """Create a new team. Example: !createteam MainRoster"""
            if team_name in self.team_data.get("teams", {}):
                await ctx.send(f"❌ Team `{team_name}` already exists!")
                return
            
            if "teams" not in self.team_data:
                self.team_data["teams"] = {}
            
            self.team_data["teams"][team_name] = {
                "name": team_name,
                "players": [],
                "created_by": ctx.author.name,
                "created_at": datetime.now().isoformat()
            }
            self.save_team_data()
            
            embed = discord.Embed(
                title="✅ Team Created",
                description=f"Team **{team_name}** has been created!",
                color=0x00ff00
            )
            embed.add_field(name="Created by", value=ctx.author.name, inline=True)
            embed.set_footer(text="Use !addtoteam to add players")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='addtoteam')
        async def add_to_team(ctx, team_name: str, riot_id: str):
            """Add a player to a team. Example: !addtoteam MainRoster Odd#kimmy"""
            if team_name not in self.team_data.get("teams", {}):
                await ctx.send(f"❌ Team `{team_name}` doesn't exist! Use `!createteam {team_name}` first")
                return
            
            if riot_id not in self.team_data["players"]:
                await ctx.send(f"❌ {riot_id} not registered! Use `!register {riot_id} <region>` first")
                return
            
            if riot_id in self.team_data["teams"][team_name]["players"]:
                await ctx.send(f"❌ {riot_id} is already in team `{team_name}`")
                return
            
            self.team_data["teams"][team_name]["players"].append(riot_id)
            self.save_team_data()
            
            embed = discord.Embed(
                title="✅ Player Added to Team",
                description=f"**{riot_id}** → Team **{team_name}**",
                color=0x00ff00
            )
            embed.add_field(name="Team Size", value=str(len(self.team_data["teams"][team_name]["players"])), inline=True)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='removefromteam')
        async def remove_from_team(ctx, team_name: str, riot_id: str):
            """Remove a player from a team. Example: !removefromteam MainRoster Odd#kimmy"""
            if team_name not in self.team_data.get("teams", {}):
                await ctx.send(f"❌ Team `{team_name}` doesn't exist!")
                return
            
            if riot_id not in self.team_data["teams"][team_name]["players"]:
                await ctx.send(f"❌ {riot_id} is not in team `{team_name}`")
                return
            
            self.team_data["teams"][team_name]["players"].remove(riot_id)
            self.save_team_data()
            
            await ctx.send(f"✅ Removed **{riot_id}** from team **{team_name}**")
        
        @self.bot.command(name='viewteam')
        async def view_team(ctx, *, team_name: str):
            """View a team's roster and stats (Combined: Ranked + Custom). Example: !viewteam MainRoster"""
            if team_name not in self.team_data.get("teams", {}):
                await ctx.send(f"❌ Team `{team_name}` doesn't exist!")
                return
            
            team = self.team_data["teams"][team_name]
            
            if not team["players"]:
                await ctx.send(f"❌ Team `{team_name}` has no players! Use `!addtoteam {team_name} <riot_id>`")
                return
            
            embed = discord.Embed(
                title=f"👥 Team: {team_name}",
                description=f"**{len(team['players'])}** players in roster\n"
                           f"📊 *Showing: **Combined Stats** (Ranked + Custom/Tournament)*",
                color=0x3498db
            )
            
            # Calculate team stats (combined)
            total_games = 0
            total_wins = 0
            total_ranked_games = 0
            total_custom_games = 0
            
            roster_text = ""
            for riot_id in team["players"]:
                if riot_id in self.team_data["players"]:
                    player_data = self.team_data["players"][riot_id]
                    manual_matches = self.manual_storage.get_matches_for_summoner(riot_id)
                    
                    # Count ranked games
                    ranked_game_count = 0
                    if player_data.get("ranked_stats") and player_data["ranked_stats"].get("champions"):
                        for champ in player_data["ranked_stats"]["champions"]:
                            ranked_game_count += champ.get("games", 0)
                    
                    # Count custom/tournament games
                    custom_game_count = len([m for m in manual_matches if m.queue_type in ['custom', 'tournament', 'tournament_draft', 'clash']])
                    
                    # Get combined stats
                    combined = self._combine_stats(player_data.get("ranked_stats"), manual_matches)
                    
                    if combined:
                        player_games = sum(c['games'] for c in combined)
                        player_wins = sum(c['wins'] for c in combined)
                        player_wr = (player_wins / player_games * 100) if player_games > 0 else 0
                        
                        total_games += player_games
                        total_wins += player_wins
                        total_ranked_games += ranked_game_count
                        total_custom_games += custom_game_count
                        
                        # Show breakdown for each player
                        wr_indicator = "🟢" if player_wr >= 50 else "🔴"
                        roster_text += f"{wr_indicator} **{riot_id}**\n"
                        roster_text += f"   └ {player_games}g total | {player_wr:.1f}% WR\n"
                        roster_text += f"   └ {ranked_game_count} ranked + {custom_game_count} custom\n"
                    else:
                        roster_text += f"⚪ **{riot_id}** - No stats\n"
            
            embed.add_field(
                name="📊 Combined Team Stats",
                value=f"**Total games:** {total_games}\n"
                      f"**Ranked games:** {total_ranked_games}\n"
                      f"**Custom/Tournament:** {total_custom_games}\n"
                      f"**Total wins:** {total_wins}\n"
                      f"**Team WR:** {(total_wins/total_games*100 if total_games > 0 else 0):.1f}%",
                inline=False
            )
            
            embed.add_field(
                name="👥 Player Breakdown",
                value=roster_text if roster_text else "No players",
                inline=False
            )
            
            embed.set_footer(text=f"Created by {team['created_by']}")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='teams')
        async def list_teams(ctx):
            """List all teams. Example: !teams"""
            teams = self.team_data.get("teams", {})
            
            if not teams:
                await ctx.send("❌ No teams created! Use `!createteam <name>` to create one")
                return
            
            embed = discord.Embed(
                title="🏆 All Teams",
                description=f"**{len(teams)}** teams created",
                color=0x9b59b6
            )
            
            for team_name, team in teams.items():
                player_count = len(team["players"])
                embed.add_field(
                    name=f"👥 {team_name}",
                    value=f"Players: {player_count}\nCreated by: {team['created_by']}",
                    inline=True
                )
            
            embed.set_footer(text="Use !viewteam <name> to see roster")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='deleteteam')
        async def delete_team(ctx, *, team_name: str):
            """Delete a team. Example: !deleteteam MainRoster or !deleteteam Team Name"""
            if team_name not in self.team_data.get("teams", {}):
                await ctx.send(f"❌ Team `{team_name}` doesn't exist!")
                return
            
            player_count = len(self.team_data["teams"][team_name]["players"])
            
            del self.team_data["teams"][team_name]
            self.save_team_data()
            
            embed = discord.Embed(
                title="🗑️ Team Deleted",
                description=f"Team **{team_name}** has been deleted",
                color=0xff6b35
            )
            embed.add_field(name="Players removed from team", value=str(player_count), inline=True)
            embed.set_footer(text="Players are still registered individually")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='syncteam')
        async def sync_team(ctx, *, args: str):
            """Sync all players in a team at once! Example: !syncteam MainRoster 50 100"""
            # Parse team_name, ranked_count, custom_count
            parts = args.split()
            if len(parts) < 1:
                await ctx.send("❌ Usage: !syncteam <team_name> [ranked_count] [custom_count]")
                return
            
            # Everything up to first number is team name
            team_name_parts = []
            ranked_count = 30  # Reduced default for smoother team sync
            custom_count = 50  # Reduced default for smoother team sync
            
            for i, part in enumerate(parts):
                if part.isdigit():
                    ranked_count = int(part)
                    if i + 1 < len(parts) and parts[i + 1].isdigit():
                        custom_count = int(parts[i + 1])
                    break
                else:
                    team_name_parts.append(part)
            
            team_name = ' '.join(team_name_parts) if team_name_parts else parts[0]
            
            if team_name not in self.team_data.get("teams", {}):
                await ctx.send(f"❌ Team `{team_name}` doesn't exist! Use `!createteam {team_name}` first")
                return
            
            team = self.team_data["teams"][team_name]
            
            if not team["players"]:
                await ctx.send(f"❌ Team `{team_name}` has no players!")
                return
            
            total_players = len(team["players"])
            
            embed = discord.Embed(
                title=f"🔄 Syncing Team: {team_name}",
                description=f"Auto-importing games for **{total_players}** players...",
                color=0x3498db
            )
            embed.add_field(name="Ranked games per player", value=str(ranked_count), inline=True)
            embed.add_field(name="Custom games scan", value=str(custom_count), inline=True)
            embed.set_footer(text="This may take a few minutes...")
            
            await ctx.send(embed=embed)
            
            # Sync each player
            total_ranked_imported = 0
            total_custom_imported = 0
            players_updated = 0
            errors_encountered = []
            
            for player_idx, riot_id in enumerate(team["players"], 1):
                status_msg = None
                try:
                    status_msg = await ctx.send(f"⏳ Syncing player {player_idx}/{total_players}: {riot_id}...")
                    
                    if riot_id not in self.team_data["players"]:
                        try:
                            await status_msg.edit(content=f"⚠️ Skipping {riot_id} (not registered)")
                        except:
                            await ctx.send(f"⚠️ Skipping {riot_id} (not registered)")
                        continue
                    
                    player_data = self.team_data["players"][riot_id]
                    region = player_data["region"]
                    
                    # Get summoner info
                    summoner_info = self.riot_scraper.get_summoner_by_name(riot_id, region)
                    if not summoner_info:
                        try:
                            await status_msg.edit(content=f"⚠️ Could not find {riot_id}")
                        except:
                            await ctx.send(f"⚠️ Could not find {riot_id}")
                        continue
                    
                    await asyncio.sleep(0.1)  # Prevent event loop blocking
                    
                    # Sync ranked games
                    match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, ranked_count, queue=420)
                    ranked_synced = 0
                    
                    await asyncio.sleep(0.1)  # Prevent event loop blocking
                    
                    if match_ids:
                        champion_mapping = self.riot_scraper.get_champion_data()
                        for idx, match_id in enumerate(match_ids):
                            match_details = self.riot_scraper.get_match_details(match_id, region)
                            if not match_details:
                                continue
                            
                            # Async sleep every 10 matches to prevent blocking
                            if idx % 10 == 0:
                                await asyncio.sleep(0.1)
                            
                            for p in match_details['info']['participants']:
                                if p['puuid'] == summoner_info['puuid']:
                                    manual_match_id = f"SYNC_{match_id}"
                                    if not any(m.match_id == manual_match_id for m in self.manual_storage.matches):
                                        champion_name = champion_mapping.get(p['championId'], "Unknown")
                                        match = ManualMatch(
                                            match_id=manual_match_id,
                                            summoner_name=riot_id,
                                            champion_name=champion_name,
                                            result="WIN" if p['win'] else "LOSS",
                                            kills=float(p['kills']),
                                            deaths=float(p['deaths']),
                                            assists=float(p['assists']),
                                            cs=float(p['totalMinionsKilled'] + p['neutralMinionsKilled']),
                                            game_duration=int(match_details['info']['gameDuration'] / 60),
                                            queue_type="ranked",
                                            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            notes=f"Team sync"
                                        )
                                        if self.manual_storage.add_match(match):
                                            ranked_synced += 1
                                    break
                    
                    total_ranked_imported += ranked_synced
                    
                    await asyncio.sleep(0.1)  # Prevent event loop blocking
                    
                    # Scan custom games (simplified, don't import all to save time)
                    custom_match_ids = self.riot_scraper.get_match_history(summoner_info['puuid'], region, min(custom_count, 100))
                    custom_synced = 0
                    
                    await asyncio.sleep(0.1)  # Prevent event loop blocking
                    
                    if custom_match_ids:
                        for c_idx, match_id in enumerate(custom_match_ids[:50]):  # Limit to 50 for team sync
                            match_details = self.riot_scraper.get_match_details(match_id, region)
                            if not match_details:
                                continue
                            
                            # Async sleep every 10 matches to prevent blocking
                            if c_idx % 10 == 0:
                                await asyncio.sleep(0.1)
                            
                            queue_id = match_details['info']['queueId']
                            # ONLY detect true custom/tournament games
                            # Queue 0 = Custom, Queue 2000-2020 = Tournament codes
                            # Excludes Clash, Arena, ARURF, and other RGMs
                            if queue_id != 0 and not (2000 <= queue_id <= 2020):
                                continue
                            
                            # Auto-add for all registered players in game
                            for p in match_details['info']['participants']:
                                p_game_name = p.get('riotIdGameName', p.get('summonerName', ''))
                                p_tag = p.get('riotIdTagline', '')
                                p_riot_id = f"{p_game_name}#{p_tag}" if p_tag else p_game_name
                                
                                is_registered = p_riot_id in self.team_data["players"]
                                if not is_registered:
                                    for registered_id in self.team_data["players"].keys():
                                        if registered_id.split('#')[0].lower() == p_game_name.lower():
                                            p_riot_id = registered_id
                                            is_registered = True
                                            break
                                
                                if is_registered:
                                    p_match_id = f"CUSTOM_{match_id}_{p_riot_id}"
                                    if not any(m.match_id == p_match_id for m in self.manual_storage.matches):
                                        p_champion = champion_mapping.get(p['championId'], "Unknown")
                                        
                                        if queue_id == 0:
                                            game_type = "custom"
                                        elif 2000 <= queue_id <= 2020:
                                            game_type = "tournament"
                                        else:
                                            game_type = "custom"  # Fallback
                                        
                                        match = ManualMatch(
                                            match_id=p_match_id,
                                            summoner_name=p_riot_id,
                                            champion_name=p_champion,
                                            result="WIN" if p['win'] else "LOSS",
                                            kills=float(p['kills']),
                                            deaths=float(p['deaths']),
                                            assists=float(p['assists']),
                                            cs=float(p['totalMinionsKilled'] + p['neutralMinionsKilled']),
                                            game_duration=int(match_details['info']['gameDuration'] / 60),
                                            queue_type=game_type,
                                            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            notes=f"Team sync"
                                        )
                                        if self.manual_storage.add_match(match):
                                            if p_riot_id == riot_id:
                                                custom_synced += 1
                    
                    total_custom_imported += custom_synced
                    players_updated += 1
                    
                    # Send success message (try edit first, fallback to new message)
                    success_msg = f"✅ {riot_id}: {ranked_synced} ranked + {custom_synced} custom games"
                    if status_msg:
                        try:
                            await status_msg.edit(content=success_msg)
                        except Exception as edit_error:
                            # Connection reset, send new message instead
                            try:
                                await ctx.send(success_msg)
                            except:
                                pass  # Discord is having issues, continue anyway
                    
                    # Add delay between players to prevent rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    error_msg = str(e)[:100]
                    errors_encountered.append(f"{riot_id}: {error_msg}")
                    
                    # Try to send error message
                    error_display = f"❌ Error syncing {riot_id}"
                    if status_msg:
                        try:
                            await status_msg.edit(content=error_display)
                        except:
                            try:
                                await ctx.send(error_display)
                            except:
                                pass  # Connection issues, continue to next player
            
            # Final summary - always send this, even if connection was reset
            try:
                final_embed = discord.Embed(
                    title=f"✅ Team Sync Complete: {team_name}",
                    description=f"Synced **{players_updated}** of **{total_players}** players",
                    color=0x00ff00
                )
                final_embed.add_field(name="Players updated", value=str(players_updated), inline=True)
                final_embed.add_field(name="Total ranked imported", value=str(total_ranked_imported), inline=True)
                final_embed.add_field(name="Total custom imported", value=str(total_custom_imported), inline=True)
                
                if errors_encountered:
                    final_embed.add_field(
                        name="⚠️ Errors",
                        value="\n".join(errors_encountered[:5]),
                        inline=False
                    )
                
                final_embed.set_footer(text=f"Use !viewteam {team_name} to see updated stats")
                
                await ctx.send(embed=final_embed)
            except Exception as e:
                # Fallback to simple text message if embed fails
                try:
                    summary = f"✅ **Team Sync Complete: {team_name}**\n"
                    summary += f"Players: {players_updated}/{total_players} | "
                    summary += f"Ranked: {total_ranked_imported} | Custom: {total_custom_imported}"
                    if errors_encountered:
                        summary += f"\n⚠️ {len(errors_encountered)} errors occurred"
                    await ctx.send(summary)
                except:
                    pass  # Discord connection completely lost, data is saved anyway
    
    def _combine_stats(self, ranked_stats, manual_matches):
        """Combine ranked and manual stats per champion"""
        combined = {}
        
        # Add ranked stats
        if ranked_stats and ranked_stats.get("champions"):
            for champ in ranked_stats["champions"]:
                combined[champ["name"]] = {
                    "name": champ["name"],
                    "games": champ["games"],
                    "wins": champ["wins"],
                    "losses": champ["losses"],
                    "kills": champ["kills"] * champ["games"],
                    "deaths": champ["deaths"] * champ["games"],
                    "assists": champ["assists"] * champ["games"],
                    "total_cs": champ["cs_per_min"] * champ["games"] * 25  # Approximate
                }
        
        # Add manual stats
        for match in manual_matches:
            champ_name = match.champion_name
            if champ_name not in combined:
                combined[champ_name] = {
                    "name": champ_name,
                    "games": 0,
                    "wins": 0,
                    "losses": 0,
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "total_cs": 0
                }
            
            combined[champ_name]["games"] += 1
            if match.result == "WIN":
                combined[champ_name]["wins"] += 1
            else:
                combined[champ_name]["losses"] += 1
            combined[champ_name]["kills"] += match.kills
            combined[champ_name]["deaths"] += match.deaths
            combined[champ_name]["assists"] += match.assists
            combined[champ_name]["total_cs"] += match.cs
        
        # Calculate averages and win rates
        result = []
        for champ_name, data in combined.items():
            games = data["games"]
            if games > 0:
                avg_kills = data["kills"] / games
                avg_deaths = data["deaths"] / games
                avg_assists = data["assists"] / games
                kda = (data["kills"] + data["assists"]) / max(data["deaths"], 1)
                win_rate = (data["wins"] / games) * 100
                
                result.append({
                    "name": champ_name,
                    "games": games,
                    "wins": data["wins"],
                    "losses": data["losses"],
                    "win_rate": win_rate,
                    "kda": kda,
                    "kills": avg_kills,
                    "deaths": avg_deaths,
                    "assists": avg_assists
                })
        
        # Sort by games played
        result.sort(key=lambda x: x["games"], reverse=True)
        return result
    
    def _get_stats_from_matches(self, matches):
        """Calculate stats from a list of matches"""
        if not matches:
            return []
        
        champions = {}
        
        for match in matches:
            champ_name = match.champion_name
            if champ_name not in champions:
                champions[champ_name] = {
                    "name": champ_name,
                    "games": 0,
                    "wins": 0,
                    "losses": 0,
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "total_cs": 0
                }
            
            champions[champ_name]["games"] += 1
            if match.result == "WIN":
                champions[champ_name]["wins"] += 1
            else:
                champions[champ_name]["losses"] += 1
            champions[champ_name]["kills"] += match.kills
            champions[champ_name]["deaths"] += match.deaths
            champions[champ_name]["assists"] += match.assists
            champions[champ_name]["total_cs"] += match.cs
        
        # Calculate averages
        result = []
        for champ_name, data in champions.items():
            games = data["games"]
            if games > 0:
                kda = (data["kills"] + data["assists"]) / max(data["deaths"], 1)
                win_rate = (data["wins"] / games) * 100
                
                result.append({
                    "name": champ_name,
                    "games": games,
                    "wins": data["wins"],
                    "losses": data["losses"],
                    "win_rate": win_rate,
                    "kda": kda,
                    "kills": data["kills"] / games,
                    "deaths": data["deaths"] / games,
                    "assists": data["assists"] / games
                })
        
        # Sort by games played
        result.sort(key=lambda x: x["games"], reverse=True)
        return result
    
    def _tier_color(self, tier: str):
        """Get color based on tier"""
        colors = {
            "S": 0xffd700,  # Gold
            "A": 0x00ff00,  # Green
            "B": 0x3498db,  # Blue
            "C": 0xff6b35,  # Orange
            "D": 0xe74c3c   # Red
        }
        return colors.get(tier[0], 0x95a5a6)
    
    def _matchup_color(self, win_rate: float):
        """Get color based on matchup win rate"""
        if win_rate >= 55:
            return 0x00ff00  # Green
        elif win_rate >= 50:
            return 0x3498db  # Blue
        elif win_rate >= 45:
            return 0xff6b35  # Orange
        else:
            return 0xe74c3c  # Red
    
    def run(self):
        """Run the Discord bot"""
        if not self.token:
            print("❌ DISCORD_BOT_TOKEN not found in environment variables!")
            print("Create a .env file with: DISCORD_BOT_TOKEN=your_bot_token")
            return
        
        print("🚀 Starting ScoutLE Discord Bot...")
        print(f"📊 Riot API Key: {'✅ Set' if self.riot_api_key else '❌ Not set'}")
        print(f"📝 Manual matches loaded: {len(self.manual_storage.matches)}")
        self.bot.run(self.token)

if __name__ == "__main__":
    bot = ScoutLEBot()
    bot.run()
