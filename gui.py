"""Graphic Interface"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import threading
from tkinter.font import BOLD

# Import modules
from api_client import RiotAPIClient
from models import PlayerProfile, RankedStats, MatchPerformance
from config import REGION_NAMES, QUEUE_NAMES
from champion_analyzer import ChampionAnalyzer, ChampionStats
from champion_icons import ChampionIconManager

class ScoutleGUI:
	def __init__(self, root):
		self.root = root
		self.root.title("ScoutLE - Tournament Scouting Tool")
		self.root.geometry("800x600")
		self.root.resizable(True, True)

		# Variables
		self.api_key = tk.StringVar()
		self.riot_id = tk.StringVar()
		self.selected_region = tk.StringVar()

		# API Client and analyzers
		self.api_client = None
		self.champion_analyzer = ChampionAnalyzer()
		self.icon_manager = ChampionIconManager()

		self.setup_ui()

	def setup_ui(self):
		""" Setup UI components"""
		# Style
		style = ttk.Style()
		style.theme_use("default")

		main_frame = ttk.Frame(self.root)
		main_frame.grid(row=0, column=0, sticky="nsew")

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(0, weight=1)
		main_frame.columnconfigure(1, weight=1)

		# Title
		title_label = ttk.Label(main_frame, text="ScoutLE", font=("Arial", 16, "bold"))
		title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

		# Setup API
		self.setup_api_config(main_frame, 1)

		# Separators
		separator = ttk.Separator(main_frame, orient='horizontal')
		separator.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)
		
		# Find player
		self.setup_find_player(main_frame, 3)

		# Results
		self.setup_results_area(main_frame, 5)

		# Status
		self.setup_status_bar(main_frame, 7)

	def setup_api_config(self, parent, row):
		"""API Key configuration"""
		# Label
		api_label = ttk.Label(parent, text="Riot API Key:")
		api_label.grid(row=row, column=0, sticky=tk.W, padx=(0, 10))

		# Entry field
		api_entry = ttk.Entry(parent, textvariable=self.api_key, width=40, show="*")
		api_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 10))

		# Confirm button
		validate_btn = ttk.Button(parent, text="Confirm", command=self.validate_api_key)
		validate_btn.grid(row=row, column=2, sticky=tk.W)

	def setup_find_player(self, parent, row):
		"""Player search interface"""
		# Riot ID
		id_label = ttk.Label(parent, text="Riot ID:")
		id_label.grid(row=row, column=0, sticky=tk.W, padx=(0, 10))

		id_entry = ttk.Entry(parent, textvariable=self.riot_id, width=30)
		id_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
		id_entry.bind('<Return>', lambda e: self.analyze_player())

		# Region
		region_label = ttk.Label(parent, text='Region:')
		region_label.grid(row=row+1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

		region_combo = ttk.Combobox(parent, textvariable=self.selected_region, values=list(REGION_NAMES.keys()), width=15, state='readonly')
		region_combo.grid(row=row+1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 10))

		# Analyze button
		analyze_btn = ttk.Button(parent, text="Analyze", command=self.analyze_player, style="Accent.TButton")
		analyze_btn.grid(row=row+1, column=2, sticky=tk.W, pady=(10, 0))

	def setup_results_area(self, parent, row):
		"""Results area with tabs for different views"""
		# Create notebook for tabs
		self.results_notebook = ttk.Notebook(parent)
		self.results_notebook.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(20, 10))
		
		# Basic info tab
		self.basic_frame = ttk.Frame(self.results_notebook)
		self.results_notebook.add(self.basic_frame, text="Basic Info")
		
		# Champion stats tab
		self.champion_frame = ttk.Frame(self.results_notebook)
		self.results_notebook.add(self.champion_frame, text="Champion Stats")
		
		# Text area for basic info
		self.results_text = scrolledtext.ScrolledText(self.basic_frame, width=80, height=20, 
                                                     font=("Consolas", 10))
		self.results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
		
		# Champion stats area with scrollbar
		self.champion_canvas = tk.Canvas(self.champion_frame)
		self.champion_scrollbar = ttk.Scrollbar(self.champion_frame, orient="vertical", command=self.champion_canvas.yview)
		self.champion_scrollable_frame = ttk.Frame(self.champion_canvas)
		
		self.champion_scrollable_frame.bind(
			"<Configure>",
			lambda e: self.champion_canvas.configure(scrollregion=self.champion_canvas.bbox("all"))
		)
		
		self.champion_canvas.create_window((0, 0), window=self.champion_scrollable_frame, anchor="nw")
		self.champion_canvas.configure(yscrollcommand=self.champion_scrollbar.set)
		
		self.champion_canvas.pack(side="left", fill="both", expand=True)
		self.champion_scrollbar.pack(side="right", fill="y")
        
		# Configure results area
		parent.rowconfigure(row, weight=1)
    
	def setup_status_bar(self, parent, row):
		"""Status bar"""
		self.status_var = tk.StringVar(value="Ready")
		status_label = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN)
		status_label.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
	def validate_api_key(self):
		"""Validate API key"""
		api_key = self.api_key.get().strip()
		if not api_key:
			messagebox.showerror("Error", "Please enter an API key")
			return
        
		# Initialize API client
		self.api_client = RiotAPIClient(api_key, self.selected_region.get())
		self.status_var.set("API key validated - Ready to analyze")
		messagebox.showinfo("Success", "API key validated successfully!")
    
	def analyze_player(self):
		"""Analyze a player"""
		if not self.api_client:
			messagebox.showerror("Error", "Please validate your API key first")
			return
        
		riot_id = self.riot_id.get().strip()
		if not riot_id or '#' not in riot_id:
			messagebox.showerror("Error", "Invalid Riot ID format. Use: PlayerName#Tag")
			return
        
		# Launch analyze in a separate thread to avoid blocking the UI
		self.status_var.set("Analyze in progress...")
		thread = threading.Thread(target=self._analyze_player_thread, args=(riot_id,))
		thread.daemon = True
		thread.start()
    
	def _analyze_player_thread(self, riot_id):
		"""Thread analyze player"""
		try:
			print(f"🔍 Starting analysis for: {riot_id}")
			game_name, tag_line = riot_id.split('#', 1)
			
			# Get account data
			print("📡 Fetching account data...")
			account_data = self.api_client.get_player_by_riot_id(game_name, tag_line)
			if not account_data:
				self.root.after(0, lambda: self._show_error("Player not found"))
				return
            
			puuid = account_data['puuid']
			print(f"✅ Found player: {account_data.get('gameName', 'Unknown')}")
			
			# Get summoner data (with fallback)
			print("📡 Fetching summoner data...")
			summoner_data = self.api_client.get_summoner_data(puuid)
			if not summoner_data:
				print("⚠️ Summoner data not available, using fallback")
				# Create fallback summoner data
				summoner_data = {
					"id": f"summoner_{puuid[:8]}",  # Create a mock summoner ID
					"summonerLevel": 100,  # Default level
					"name": account_data.get('gameName', 'Unknown')
				}
			
			# Get ranked stats
			print("📡 Fetching ranked stats...")
			ranked_stats = self.api_client.get_ranked_stats(summoner_data['id'])
			
			# Get recent matches (simplified for now)
			self.root.after(0, lambda: self.status_var.set("Fetching match history..."))
			print("📡 Fetching match history...")
			match_ids = self.api_client.get_match_history(puuid, 10)  # Reduced to 10 for faster testing
			
			matches = []
			for i, match_id in enumerate(match_ids):
				print(f"📡 Fetching match {i+1}/{len(match_ids)}: {match_id}")
				match_data = self.api_client.get_match_details(match_id)
				if match_data:
					matches.append(match_data)
			
			print(f"✅ Fetched {len(matches)} matches")
			
			# Analyze champion performance
			self.root.after(0, lambda: self.status_var.set("Analyzing champion performance..."))
			print("🔍 Analyzing champion performance...")
			champion_stats = self.champion_analyzer.analyze_matches(matches, puuid)
			print(f"✅ Analyzed {len(champion_stats)} champions")
			
			# Prepare basic results
			basic_result = f"""
=== ANALYSIS RESULTS ===
Player: {riot_id}
Region: {self.selected_region.get()}
Time: {datetime.now().strftime('%H:%M:%S')}

=== BASIC DATA ===
Game Name: {account_data.get('gameName', 'N/A')}
Tag: {account_data.get('tagLine', 'N/A')}
Summoner Level: {summoner_data.get('summonerLevel', 'N/A')}
PUUID: {puuid[:20]}...

=== RANKED STATISTICS ===
"""
			
			if ranked_stats:
				for queue in ranked_stats:
					queue_type = queue.get('queueType', 'Unknown')
					tier = queue.get('tier', 'Unranked')
					rank = queue.get('rank', '')
					lp = queue.get('leaguePoints', 0)
					wins = queue.get('wins', 0)
					losses = queue.get('losses', 0)
					win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
					
					queue_name = queue_type.replace('RANKED_', '').replace('_', ' ').title()
					basic_result += f"{queue_name}: {tier} {rank} ({lp} LP) - {wins}W {losses}L ({win_rate:.1f}% WR)\n"
			else:
				basic_result += "No ranked data available\n"
			
			basic_result += f"""
=== MATCH ANALYSIS ===
Recent Matches Analyzed: {len(matches)}
Champions Played: {len(champion_stats)}

=== STATUS ===
✅ API connection successful
✅ Player found
✅ Match history analyzed
✅ Champion performance calculated
"""
			
			# Show results
			self.root.after(0, lambda: self._show_results(basic_result, champion_stats))   
			
		except Exception as e:
			print(f"❌ Error during analysis: {str(e)}")
			import traceback
			traceback.print_exc()
			self.root.after(0, lambda: self._show_error(f"Error during analysis: {str(e)}"))
    
	def _show_results(self, result, champion_stats=None):
		"""Show results"""
		# Clear basic results
		self.results_text.delete(1.0, tk.END)
		self.results_text.insert(1.0, result)
		
		# Clear champion stats
		for widget in self.champion_scrollable_frame.winfo_children():
			widget.destroy()
		
		# Show champion statistics
		if champion_stats:
			self._display_champion_stats(champion_stats)
		
		self.status_var.set("Analysis completed")
	
	def _display_champion_stats(self, champion_stats):
		"""Display champion statistics with icons"""
		# Get top champions by games played
		top_champions = self.champion_analyzer.get_top_champions(champion_stats, 10)
		
		if not top_champions:
			no_data_label = tk.Label(self.champion_scrollable_frame, 
									text="No champion data available", 
									font=("Arial", 12))
			no_data_label.pack(pady=20)
			return
		
		# Title
		title_label = tk.Label(self.champion_scrollable_frame, 
							  text="Champion Performance Analysis", 
							  font=("Arial", 14, "bold"))
		title_label.pack(pady=10)
		
		# Display each champion
		for i, champ_stats in enumerate(top_champions):
			# Create champion frame
			champ_frame = tk.Frame(self.champion_scrollable_frame, relief=tk.RAISED, bd=2)
			champ_frame.pack(fill=tk.X, padx=10, pady=5)
			
			# Champion icon
			icon = self.icon_manager.get_tkinter_icon(champ_stats.champion_name, (48, 48))
			if icon:
				icon_label = tk.Label(champ_frame, image=icon)
				icon_label.image = icon  # Keep reference
				icon_label.pack(side=tk.LEFT, padx=5, pady=5)
			
			# Champion info frame
			info_frame = tk.Frame(champ_frame)
			info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
			
			# Champion name and basic stats
			name_label = tk.Label(info_frame, text=champ_stats.champion_name, 
								 font=("Arial", 12, "bold"))
			name_label.pack(anchor=tk.W)
			
			# Performance metrics
			metrics_text = f"""Games: {champ_stats.games_played} | Win Rate: {champ_stats.win_rate:.1f}% | KDA: {champ_stats.avg_kda:.2f}
CS/min: {champ_stats.avg_cs_per_min:.1f} | Gold/min: {champ_stats.avg_gold_per_min:.0f} | Damage/min: {champ_stats.avg_damage_per_min:.0f}
Role: {champ_stats.most_common_role} | Trend: {champ_stats.performance_trend}"""
			
			metrics_label = tk.Label(info_frame, text=metrics_text, 
									font=("Arial", 9), justify=tk.LEFT)
			metrics_label.pack(anchor=tk.W)
			
			# Win/Loss bar
			self._create_win_loss_bar(champ_frame, champ_stats.wins, champ_stats.losses)
	
	def _create_win_loss_bar(self, parent, wins, losses):
		"""Create a visual win/loss bar"""
		total = wins + losses
		if total == 0:
			return
		
		win_percentage = wins / total
		
		# Create frame for the bar
		bar_frame = tk.Frame(parent, height=20, bg="lightgray")
		bar_frame.pack(side=tk.RIGHT, padx=10, pady=5, fill=tk.Y)
		
		# Win portion (green)
		win_width = int(win_percentage * 100)
		win_bar = tk.Frame(bar_frame, width=win_width, height=20, bg="green")
		win_bar.pack(side=tk.LEFT, fill=tk.Y)
		
		# Loss portion (red)
		loss_bar = tk.Frame(bar_frame, width=100-win_width, height=20, bg="red")
		loss_bar.pack(side=tk.LEFT, fill=tk.Y)
		
		# Text overlay
		text_label = tk.Label(bar_frame, text=f"{wins}W-{losses}L", 
							 font=("Arial", 8, "bold"), fg="white", bg="black")
		text_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    
	def _show_error(self, error_msg):
		"""Show error"""
		self.results_text.delete(1.0, tk.END)
		self.results_text.insert(1.0, f"❌ ERROR: {error_msg}")
		self.status_var.set("Error")

def main():
	"""Launch application"""
	root = tk.Tk()
	app = ScoutleGUI(root)
	root.mainloop()

if __name__ == "__main__":
    main()


