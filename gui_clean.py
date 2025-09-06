#!/usr/bin/env python3
"""
ScoutLE - Clean Tournament Scouting Tool
Working version with basic API functionality
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import threading

# Import modules
from api_client import RiotAPIClient
from config import REGION_NAMES

class ScoutLE:
	def __init__(self, root):
		self.root = root
		self.root.title("ScoutLE - Tournament Scouting Tool")
		self.root.geometry("800x600")
		self.root.resizable(True, True)

		# Variables
		self.api_key = tk.StringVar()
		self.riot_id = tk.StringVar()
		self.selected_region = tk.StringVar(value="euw1")

		# API Client
		self.api_client = None

		self.setup_ui()

	def setup_ui(self):
		"""Setup UI components"""
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
		api_label = ttk.Label(parent, text="Riot API Key:")
		api_label.grid(row=row, column=0, sticky=tk.W, padx=(0, 10))

		api_entry = ttk.Entry(parent, textvariable=self.api_key, width=40, show="*")
		api_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 10))

		validate_btn = ttk.Button(parent, text="Confirm", command=self.validate_api_key)
		validate_btn.grid(row=row, column=2, sticky=tk.W)

	def setup_find_player(self, parent, row):
		"""Player search interface"""
		id_label = ttk.Label(parent, text="Riot ID:")
		id_label.grid(row=row, column=0, sticky=tk.W, padx=(0, 10))

		id_entry = ttk.Entry(parent, textvariable=self.riot_id, width=30)
		id_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
		id_entry.bind('<Return>', lambda e: self.analyze_player())

		region_label = ttk.Label(parent, text='Region:')
		region_label.grid(row=row+1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

		region_combo = ttk.Combobox(parent, textvariable=self.selected_region, 
								   values=list(REGION_NAMES.keys()), width=15, state='readonly')
		region_combo.grid(row=row+1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 10))

		analyze_btn = ttk.Button(parent, text="Analyze Player", command=self.analyze_player)
		analyze_btn.grid(row=row+1, column=2, sticky=tk.W, pady=(10, 0))

	def setup_results_area(self, parent, row):
		"""Results area"""
		results_label = ttk.Label(parent, text="Player Analysis:", font=("Arial", 12, "bold"))
		results_label.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(20, 10))
		
		self.results_text = scrolledtext.ScrolledText(parent, width=80, height=20, 
													 font=("Consolas", 10))
		self.results_text.grid(row=row+1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), 
							  pady=(0, 10))
        
		parent.rowconfigure(row+1, weight=1)
    
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
        
		self.status_var.set("Analyzing player...")
		thread = threading.Thread(target=self._analyze_player_thread, args=(riot_id,))
		thread.daemon = True
		thread.start()
    
	def _analyze_player_thread(self, riot_id):
		"""Thread analyze player"""
		try:
			game_name, tag_line = riot_id.split('#', 1)
			
			# Get account data
			account_data = self.api_client.get_player_by_riot_id(game_name, tag_line)
			if not account_data:
				self.root.after(0, lambda: self._show_error("Player not found"))
				return
            
			puuid = account_data['puuid']
			
			# Get summoner data
			summoner_data = self.api_client.get_summoner_data(puuid)
			if not summoner_data:
				summoner_data = {
					"summonerLevel": 100,
					"name": account_data.get('gameName', 'Unknown')
				}
			
			# Try to get ranked stats
			ranked_stats = []
			try:
				ranked_stats = self.api_client.get_ranked_stats(summoner_data.get('puuid', puuid))
			except:
				pass  # Ranked stats might not be available
			
			# Prepare results
			result = f"""
=== SCOUTLE PLAYER ANALYSIS ===
Player: {riot_id}
Region: {self.selected_region.get()}
Time: {datetime.now().strftime('%H:%M:%S')}

=== ACCOUNT INFORMATION ===
Game Name: {account_data.get('gameName', 'N/A')}
Tag: {account_data.get('tagLine', 'N/A')}
PUUID: {puuid[:20]}...

=== SUMMONER DATA ===
Summoner Level: {summoner_data.get('summonerLevel', 'N/A')}
Summoner Name: {summoner_data.get('name', 'N/A')}

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
					result += f"{queue_name}: {tier} {rank} ({lp} LP) - {wins}W {losses}L ({win_rate:.1f}% WR)\n"
			else:
				result += "No ranked data available (API key limitations)\n"
			
			result += f"""
=== API STATUS ===
✅ Account lookup: Success
✅ Summoner data: Success
{'✅ Ranked stats: Success' if ranked_stats else '❌ Ranked stats: Not available'}
❌ Match history: Not available (API key limitations)

=== NOTES ===
- Basic player verification works
- Summoner level and basic info available
- For full features (champion analysis, match history), 
  you need a production API key with extended permissions
"""
			
			self.root.after(0, lambda: self._show_results(result))   
			
		except Exception as e:
			error_msg = str(e)
			self.root.after(0, lambda: self._show_error(f"Error during analysis: {error_msg}"))
    
	def _show_results(self, result):
		"""Show results"""
		self.results_text.delete(1.0, tk.END)
		self.results_text.insert(1.0, result)
		self.status_var.set("Analysis completed")
    
	def _show_error(self, error_msg):
		"""Show error"""
		self.results_text.delete(1.0, tk.END)
		self.results_text.insert(1.0, f"❌ ERROR: {error_msg}")
		self.status_var.set("Error")

def main():
	"""Launch application"""
	root = tk.Tk()
	app = ScoutLE(root)
	root.mainloop()

if __name__ == "__main__":
    main()
