"""
ScoutLE - League of Legends Account Analysis Tool
- Account Stats from OP.GG (ranked SoloQ and Flex)
- Champion Meta from Lolalytics
- Manual Match Tracking (custom games, tournaments)
- Combined Statistics Analysis
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
from datetime import datetime
from typing import Dict
import threading
import json
import os
import requests
from PIL import Image, ImageTk
from io import BytesIO
from tkinter.font import BOLD

# Import modules
from simple_account_scraper import SimpleAccountScraper, LolalyticsScraper, ChampionPerformance
from hybrid_scraper import HybridScraper
from manual_matches_storage import ManualMatchStorage, ManualMatch
from champion_stats_scraper import ChampionStatsScraper, DetailedChampionStats
from league_assets import LeagueAssets

class AccountGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ScoutLE - League of Legends Scout Tool")
        
        # Initialize League assets manager
        print("🎨 Loading League of Legends assets...")
        self.assets = LeagueAssets()
        self.root.geometry("1400x850")  # Slightly larger for better visibility
        self.root.resizable(True, True)

        # Load configuration
        self.config = self.load_config()
        self.riot_api_key = self.config.get("riot_api_key", "")

        # Variables
        self.summoner_name = tk.StringVar()
        self.region = tk.StringVar(value=self.config.get("default_region", "euw"))
        self.champion_name = tk.StringVar()
        self.use_mock_data = tk.BooleanVar(value=True)
        self.champions_to_display = self.config.get("champions_to_display", 10)

        # Scraper instances - initialize with API key if available
        self.account_scraper = SimpleAccountScraper()
        self.hybrid_scraper = HybridScraper(self.riot_api_key if self.riot_api_key else None)
        self.lolalytics_scraper = LolalyticsScraper()
        self.champion_stats_scraper = ChampionStatsScraper()
        self.manual_match_storage = ManualMatchStorage()
        self.current_account_data = None
        self.current_champion_data = None
        self.current_champion_comparison = None

        self.setup_ui()
        
        # Show API key status on startup
        if self.riot_api_key:
            print(f"🔑 Riot API key loaded from config.json")
            self.status_var.set(f"Ready - Riot API key loaded ({len(self.riot_api_key)} chars)")
        else:
            print(f"ℹ️ No Riot API key found in config.json - using OP.GG scraping only")
            self.status_var.set("Ready - No API key (using OP.GG scraping only)")

    def load_config(self):
        """Load configuration from config.json file"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        default_config = {
            "riot_api_key": "",
            "default_region": "euw",
            "auto_load_api_key": True,
            "champions_to_display": 10
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"✅ Loaded config from {config_path}")
                    return {**default_config, **config}  # Merge with defaults
            else:
                print(f"ℹ️ Config file not found, creating default config at {config_path}")
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
            return default_config

    def save_config(self):
        """Save current configuration to config.json"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            print(f"✅ Saved config to {config_path}")
        except Exception as e:
            print(f"⚠️ Error saving config: {e}")

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

        # Title - Compact
        title_label = ttk.Label(main_frame, text="ScoutLE - League Scout Tool", 
                               font=("Segoe UI", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(5, 15))

        # Account analysis section
        self.setup_account_section(main_frame, 1)

        # Separator - Thinner
        separator1 = ttk.Separator(main_frame, orient='horizontal')
        separator1.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        # Champion analysis section
        self.setup_champion_section(main_frame, 3)

        # Separator - Thinner
        separator2 = ttk.Separator(main_frame, orient='horizontal')
        separator2.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        # Results area
        self.setup_results_area(main_frame, 5)

        # Status bar
        self.setup_status_bar(main_frame, 7)

    def setup_account_section(self, parent, row):
        """Account analysis section"""
        account_frame = ttk.LabelFrame(parent, text="Account Analysis", padding=10)
        account_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        account_frame.columnconfigure(1, weight=1)

        # Summoner name
        ttk.Label(account_frame, text="Summoner Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        summoner_entry = ttk.Entry(account_frame, textvariable=self.summoner_name, width=30)
        summoner_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        summoner_entry.bind('<Return>', lambda e: self.analyze_account())

        # Region
        ttk.Label(account_frame, text="Region:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        region_combo = ttk.Combobox(account_frame, textvariable=self.region, 
                                   values=["euw", "na", "kr", "eune", "br", "jp", "oce", "tr", "ru", "lan", "las"], 
                                   width=10, state='readonly')
        region_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))

        # API Key status (loaded from config.json)
        ttk.Label(account_frame, text="API Key Status:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        api_status = f"✅ Loaded from config.json ({len(self.riot_api_key)} chars)" if self.riot_api_key else "❌ Not configured"
        self.api_status_label = ttk.Label(account_frame, text=api_status, foreground="green" if self.riot_api_key else "gray")
        self.api_status_label.grid(row=1, column=1, sticky=tk.W, padx=(0, 10))
        
        # Button to configure API key
        config_btn = ttk.Button(account_frame, text="Configure API Key", command=self.configure_api_key)
        config_btn.grid(row=1, column=2, sticky=tk.W)

        # Options
        options_frame = ttk.Frame(account_frame)
        options_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Checkbutton(options_frame, text="Use Mock Data (for demo)", variable=self.use_mock_data).pack(side=tk.LEFT, padx=(0, 20))

        # Buttons
        button_frame = ttk.Frame(account_frame)
        button_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        analyze_btn = ttk.Button(button_frame, text="Analyze Account (OP.GG)", 
                                command=self.analyze_account, style="Accent.TButton")
        analyze_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        hybrid_btn = ttk.Button(button_frame, text="Analyze Account (Hybrid)", 
                               command=self.analyze_account_hybrid, style="Accent.TButton")
        hybrid_btn.pack(side=tk.LEFT, padx=(0, 10))

        export_btn = ttk.Button(button_frame, text="Export Account Data", 
                               command=self.export_account_data)
        export_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = ttk.Button(button_frame, text="Clear Results", 
                              command=self.clear_results)
        clear_btn.pack(side=tk.LEFT)

    def setup_champion_section(self, parent, row):
        """Champion analysis section - Clean layout"""
        champion_frame = ttk.Frame(parent, padding=10)
        champion_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        champion_frame.columnconfigure(1, weight=1)
        champion_frame.columnconfigure(3, weight=1)

        # Header
        tk.Label(champion_frame, text="📊 Champion Meta Analysis", 
                font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 8))

        # Input row: Champion 1 + Champion 2 + Buttons
        ttk.Label(champion_frame, text="Champion:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        champion_entry = ttk.Entry(champion_frame, textvariable=self.champion_name, width=20, font=("Segoe UI", 10))
        champion_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        champion_entry.bind('<Return>', lambda e: self.analyze_champion())
        
        ttk.Label(champion_frame, text="vs:", font=("Segoe UI", 10)).grid(row=1, column=2, sticky=tk.W, padx=(0, 5))
        self.champion_name_2 = tk.StringVar()
        champion_entry_2 = ttk.Entry(champion_frame, textvariable=self.champion_name_2, width=20, font=("Segoe UI", 10))
        champion_entry_2.grid(row=1, column=3, sticky=(tk.W, tk.E), padx=(0, 10))

        analyze_champ_btn = ttk.Button(champion_frame, text="📈 Analyze", 
                                      command=self.analyze_champion, style="Accent.TButton")
        analyze_champ_btn.grid(row=1, column=4, sticky=tk.W, padx=(0, 5))
        
        compare_btn = ttk.Button(champion_frame, text="⚔️ Compare", 
                                command=self.compare_champions)
        compare_btn.grid(row=1, column=5, sticky=tk.W)

    def setup_results_area(self, parent, row):
        """Results area with tabs"""
        # Create notebook for tabs
        self.results_notebook = ttk.Notebook(parent)
        self.results_notebook.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Account stats tab
        self.account_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.account_frame, text="Account Stats")

        # Champion stats tab
        self.champion_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.champion_frame, text="Champion Stats")

        # Manual matches tab (standalone)
        self.manual_matches_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.manual_matches_frame, text="Manual Matches")

        # Combined analysis tab
        self.combined_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.combined_frame, text="Combined Analysis")

        # Setup tab contents
        self.setup_account_tab()
        self.setup_champion_tab()
        self.setup_manual_matches_tab()
        self.setup_combined_tab()

        # Configure results area
        parent.rowconfigure(row, weight=1)

    def setup_account_tab(self):
        """Setup account stats tab with modern layout"""
        # Canvas with scrollbar for account view (like champion tab)
        self.account_canvas = tk.Canvas(self.account_frame)
        self.account_scrollbar = ttk.Scrollbar(self.account_frame, orient="vertical", 
                                              command=self.account_canvas.yview)
        self.account_scrollable_frame = ttk.Frame(self.account_canvas)

        self.account_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.account_canvas.configure(scrollregion=self.account_canvas.bbox("all"))
        )

        self.account_canvas.create_window((0, 0), window=self.account_scrollable_frame, anchor="nw")
        self.account_canvas.configure(yscrollcommand=self.account_scrollbar.set)

        self.account_canvas.pack(side="left", fill="both", expand=True)
        self.account_scrollbar.pack(side="right", fill="y")

    def setup_champion_tab(self):
        """Setup champion stats tab"""
        # Canvas with scrollbar for champion view
        self.champion_canvas = tk.Canvas(self.champion_frame)
        self.champion_scrollbar = ttk.Scrollbar(self.champion_frame, orient="vertical", 
                                               command=self.champion_canvas.yview)
        self.champion_scrollable_frame = ttk.Frame(self.champion_canvas)

        self.champion_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.champion_canvas.configure(scrollregion=self.champion_canvas.bbox("all"))
        )

        self.champion_canvas.create_window((0, 0), window=self.champion_scrollable_frame, anchor="nw")
        self.champion_canvas.configure(yscrollcommand=self.champion_scrollbar.set)

        self.champion_canvas.pack(side="left", fill="both", expand=True)
        self.champion_scrollbar.pack(side="right", fill="y")

    def setup_combined_tab(self):
        """Setup combined analysis tab"""
        # Text area for combined analysis
        self.combined_text = scrolledtext.ScrolledText(self.combined_frame, width=100, height=25,
                                                      font=("Consolas", 10))
        self.combined_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def setup_manual_matches_tab(self):
        """Setup manual matches tab - Standalone view for manually tracked games"""
        # Top frame for title and buttons
        top_frame = ttk.Frame(self.manual_matches_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Manual Match Tracking", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Button(top_frame, text="➕ Add Match", command=self.add_manual_match).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="📊 View Matches", command=self.view_manual_matches).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="📈 Show Stats", command=self.show_manual_stats_summary).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="🗑️ Clear All", command=self.clear_manual_matches).pack(side=tk.LEFT, padx=5)
        
        # Info label
        info_label = ttk.Label(self.manual_matches_frame, 
                              text="Track custom games, tournament matches, and other games not shown in ranked stats",
                              font=("Segoe UI", 9), foreground="gray")
        info_label.pack(padx=10, pady=(0, 10))
        
        # Scrolled text area for displaying matches
        self.manual_matches_text = scrolledtext.ScrolledText(self.manual_matches_frame, width=100, height=25,
                                                             font=("Consolas", 10))
        self.manual_matches_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Show initial message
        self.manual_matches_text.insert(1.0, "Welcome to Manual Match Tracking!\n\n"
                                             "Click 'Add Match' to track your first game.\n"
                                             "Click 'Show Stats' to see champion statistics from your manual matches.\n"
                                             "Go to 'Combined Analysis' tab to merge with ranked stats.")

    def setup_status_bar(self, parent, row):
        """Status bar"""
        self.status_var = tk.StringVar(value="Ready - Enter summoner name and champion to analyze")
        status_label = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

    def analyze_account(self):
        """Analyze account using OP.GG scraper"""
        summoner_name = self.summoner_name.get().strip()
        region = self.region.get()
        if not summoner_name:
            messagebox.showerror("Error", "Please enter a summoner name")
            return

        # Launch analysis in a separate thread
        self.status_var.set(f"Analyzing account: {summoner_name}...")
        thread = threading.Thread(target=self._analyze_account_thread, args=(summoner_name, region))
        thread.daemon = True
        thread.start()
    
    def configure_api_key(self):
        """Configure Riot API key and save to config"""
        current_key = self.riot_api_key if self.riot_api_key else ""
        new_key = simpledialog.askstring("Configure API Key", 
                                         "Enter your Riot API key:\n(Leave empty to remove)",
                                         initialvalue=current_key,
                                         show="*")
        
        if new_key is not None:  # User didn't cancel
            self.riot_api_key = new_key.strip()
            self.config["riot_api_key"] = self.riot_api_key
            self.save_config()
            
            # Update hybrid scraper with new key
            self.hybrid_scraper = HybridScraper(self.riot_api_key if self.riot_api_key else None)
            
            # Update status label
            if self.riot_api_key:
                api_status = f"✅ Configured ({len(self.riot_api_key)} chars)"
                self.api_status_label.config(text=api_status, foreground="green")
                messagebox.showinfo("Success", "API key saved to config.json")
            else:
                api_status = "❌ Not configured"
                self.api_status_label.config(text=api_status, foreground="gray")
                messagebox.showinfo("Info", "API key removed from config.json")
    
    def analyze_account_hybrid(self):
        """Analyze account using hybrid scraper (OP.GG + Riot API)"""
        summoner_name = self.summoner_name.get().strip()
        region = self.region.get()
        
        if not summoner_name:
            messagebox.showerror("Error", "Please enter a summoner name")
            return
        
        # Use the API key from config (already loaded)
        if self.riot_api_key:
            print(f"🔑 Using Riot API key from config for comprehensive data")
        else:
            print(f"🌐 Using OP.GG scraping only (no API key configured)")
        
        # Launch analysis in a separate thread
        self.status_var.set(f"Analyzing account (Hybrid): {summoner_name}...")
        thread = threading.Thread(target=self._analyze_account_hybrid_thread, args=(summoner_name, region))
        thread.daemon = True
        thread.start()

    def _analyze_account_thread(self, summoner_name, region):
        """Thread for account analysis using OP.GG scraper"""
        try:
            # Clear previous results first
            self.root.after(0, self.clear_results)
            
            if self.use_mock_data.get():
                # Use mock data for demonstration
                self.current_account_data = self._create_mock_account_data(summoner_name)
                self.root.after(0, lambda: self._show_account_results(self.current_account_data))
            else:
                # Try real scraping
                account_data = self.account_scraper.scrape_player_account(summoner_name, self.region.get())
                if account_data:
                    self.current_account_data = account_data
                    self.root.after(0, lambda: self._show_account_results(account_data))
                else:
                    self.root.after(0, lambda: self._show_error("Failed to retrieve account data. Try using mock data for demonstration."))
            
        except Exception as e:
            print(f"❌ Error during account analysis: {str(e)}")
            self.root.after(0, lambda: self._show_error(f"Error during account analysis: {str(e)}"))

    def _analyze_account_hybrid_thread(self, summoner_name, region):
        """Thread for account analysis using hybrid scraper"""
        try:
            # Clear previous results first
            self.root.after(0, self.clear_results)
            
            if self.use_mock_data.get():
                # Use mock data for demonstration
                self.current_account_data = self._create_mock_account_data(summoner_name)
                self.root.after(0, lambda: self._show_account_results(self.current_account_data))
            else:
                # Try hybrid scraping
                account_data = self.hybrid_scraper.scrape_player_account(summoner_name, region)
                if account_data:
                    self.current_account_data = account_data
                    self.root.after(0, lambda: self._show_account_results(account_data))
                else:
                    self.root.after(0, lambda: self._show_error("Failed to retrieve account data with hybrid scraper. Try using mock data for demonstration."))
            
        except Exception as e:
            print(f"❌ Error during hybrid account analysis: {str(e)}")
            self.root.after(0, lambda: self._show_error(f"Error during hybrid account analysis: {str(e)}"))

    def _create_mock_account_data(self, summoner_name):
        """Create mock account data for demonstration"""
        from simple_account_scraper import PlayerAccount, ChampionPerformance
        
        # Mock champion performances
        mock_performances = [
            ChampionPerformance("Ahri", 45, 28, 17, 62.2, 7.2, 4.1, 6.8, 3.4, 6.8, "soloq"),
            ChampionPerformance("Yasuo", 32, 18, 14, 56.3, 8.1, 5.2, 5.9, 2.7, 7.2, "soloq"),
            ChampionPerformance("Lux", 28, 16, 12, 57.1, 6.8, 3.9, 7.1, 3.6, 6.5, "soloq"),
            ChampionPerformance("Zed", 25, 13, 12, 52.0, 9.2, 4.8, 4.5, 2.9, 7.8, "soloq"),
            ChampionPerformance("Jinx", 22, 12, 10, 54.5, 8.5, 3.2, 6.1, 4.6, 8.1, "soloq"),
        ]
        
        return PlayerAccount(
            summoner_name=summoner_name,
            region=self.region.get(),
            level=156,
            soloq_rank="Diamond II",
            flex_rank="Platinum I",
            soloq_lp=45,
            flex_lp=78,
            champion_performances=mock_performances,
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    def _show_account_results(self, account_data):
        """Show account analysis results with icons"""
        try:
            # Clear existing widgets
            for widget in self.account_scrollable_frame.winfo_children():
                widget.destroy()
            
            # Separate overall stats from champion stats
            overall_stats = None
            champion_stats = []
            
            for champ in account_data.champion_performances:
                if champ.champion_name == "Overall Season":
                    overall_stats = champ
                else:
                    champion_stats.append(champ)
            
            # Title section - More compact
            title_label = tk.Label(self.account_scrollable_frame, 
                                  text=f"{account_data.summoner_name} ({account_data.region.upper()})",
                                  font=("Segoe UI", 18, "bold"),
                                  fg="#1e40af")
            title_label.pack(pady=(10, 5))
            
            # Basic info section - Clean cards without borders
            info_container = ttk.Frame(self.account_scrollable_frame)
            info_container.pack(fill=tk.X, padx=10, pady=(5, 10))
            
            # Rank card - Light background
            rank_bg = "#dbeafe" if "Diamond" in account_data.soloq_rank or "Master" in account_data.soloq_rank else "#e0e7ff"
            rank_frame = tk.Frame(info_container, bg=rank_bg, padx=15, pady=12)
            rank_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
            
            tk.Label(rank_frame, text="⭐ Ranked Solo/Duo", font=("Segoe UI", 10), foreground="#475569", bg=rank_bg).pack()
            rank_color = "#1e40af" if "Diamond" in account_data.soloq_rank or "Master" in account_data.soloq_rank else "#4f46e5"
            tk.Label(rank_frame, text=account_data.soloq_rank, 
                    font=("Segoe UI", 18, "bold"), foreground=rank_color, bg=rank_bg).pack(pady=(3, 0))
            tk.Label(rank_frame, text=f"{account_data.soloq_lp} LP", 
                    font=("Segoe UI", 13), foreground="#64748b", bg=rank_bg).pack()
            
            # Quick stats - Light background
            stats_frame = tk.Frame(info_container, bg="#fef3c7", padx=15, pady=12)
            stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            tk.Label(stats_frame, text="📋 Account Info", font=("Segoe UI", 10), foreground="#92400e", bg="#fef3c7").pack()
            tk.Label(stats_frame, text=f"Level {account_data.level}", 
                    font=("Segoe UI", 14, "bold"), foreground="#78350f", bg="#fef3c7").pack(pady=(3, 0))
            tk.Label(stats_frame, text=f"Updated: {account_data.last_updated.split()[0]}", 
                    font=("Segoe UI", 10), foreground="#92400e", bg="#fef3c7").pack(pady=(2, 0))
            
            # Overall statistics - Horizontal layout, more compact
            if overall_stats:
                total_games = overall_stats.games_played
                total_wins = overall_stats.wins
                overall_win_rate = overall_stats.win_rate
            else:
                total_games = sum(champ.games_played for champ in champion_stats)
                total_wins = sum(champ.wins for champ in champion_stats)
                overall_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
            
            overall_frame = ttk.Frame(self.account_scrollable_frame)
            overall_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # Three stats cards - Light backgrounds instead of borders
            games_card = tk.Frame(overall_frame, bg="#dbeafe", padx=12, pady=10)
            games_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            tk.Label(games_card, text="Total Games", font=("Segoe UI", 10), foreground="#1e40af", bg="#dbeafe").pack()
            tk.Label(games_card, text=str(total_games), font=("Segoe UI", 20, "bold"), foreground="#1e3a8a", bg="#dbeafe").pack()
            
            wins_card = tk.Frame(overall_frame, bg="#dcfce7", padx=12, pady=10)
            wins_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            tk.Label(wins_card, text="Wins", font=("Segoe UI", 10), foreground="#15803d", bg="#dcfce7").pack()
            tk.Label(wins_card, text=str(total_wins), font=("Segoe UI", 20, "bold"), foreground="#166534", bg="#dcfce7").pack()
            
            wr_card_bg = "#dcfce7" if overall_win_rate >= 50 else "#fee2e2"
            wr_card = tk.Frame(overall_frame, bg=wr_card_bg, padx=12, pady=10)
            wr_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            wr_label_color = "#15803d" if overall_win_rate >= 50 else "#991b1b"
            tk.Label(wr_card, text="Win Rate", font=("Segoe UI", 10), foreground=wr_label_color, bg=wr_card_bg).pack()
            wr_color = "#166534" if overall_win_rate >= 50 else "#dc2626"
            tk.Label(wr_card, text=f"{overall_win_rate:.1f}%", font=("Segoe UI", 20, "bold"), foreground=wr_color, bg=wr_card_bg).pack()
            
            # Champion performances header - More compact
            champ_title = tk.Label(self.account_scrollable_frame,
                                   text=f"📌 Top Champions ({len(champion_stats)})",
                                   font=("Segoe UI", 14, "bold"))
            champ_title.pack(pady=(10, 8))
            
            # Sort champions by games played
            sorted_champions = sorted(champion_stats, key=lambda x: x.games_played, reverse=True)
            
            # Display champions in more compact grid (2 per row)
            sorted_champions = sorted(champion_stats, key=lambda x: x.games_played, reverse=True)
            
            for row_idx in range(0, len(sorted_champions), 2):
                row_container = ttk.Frame(self.account_scrollable_frame)
                row_container.pack(fill=tk.X, padx=10, pady=3)
                
                # Process up to 2 champions per row
                for col_idx in range(2):
                    champ_idx = row_idx + col_idx
                    if champ_idx >= len(sorted_champions):
                        break
                    
                    champ = sorted_champions[champ_idx]
                    i = champ_idx + 1
                    
                    # Champion card - Very clean, light background instead of border
                    champ_frame = tk.Frame(row_container, bg="#f8fafc", padx=12, pady=10)
                    champ_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8) if col_idx == 0 else (0, 0))
                    
                    # Horizontal layout: Icon + Stats
                    content_row = tk.Frame(champ_frame, bg="#f8fafc")
                    content_row.pack(fill=tk.X)
                    
                    # Champion icon (smaller)
                    champ_icon = self.assets.get_champion_icon(champ.champion_name, size=40)
                    if champ_icon:
                        icon_label = tk.Label(content_row, image=champ_icon, bg="#f8fafc")
                        icon_label.image = champ_icon
                        icon_label.pack(side=tk.LEFT, padx=(0, 10))
                    
                    # Stats column
                    stats_col = tk.Frame(content_row, bg="#f8fafc")
                    stats_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    
                    # Champion name + rank badge  
                    name_label = tk.Label(stats_col, text=f"#{i} {champ.champion_name}", 
                                         font=("Segoe UI", 13, "bold"), bg="#f8fafc")
                    name_label.pack(anchor=tk.W)
                    
                    # Stats in one line with CS/min - Colorful
                    stats_line = tk.Frame(stats_col, bg="#f8fafc")
                    stats_line.pack(anchor=tk.W, pady=(2, 0))
                    
                    tk.Label(stats_line, text=f"{champ.games_played} Games", 
                            font=("Segoe UI", 10), foreground="#3b82f6", bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 10))
                    
                    wr_color = "#16a34a" if champ.win_rate >= 50 else "#dc2626"
                    tk.Label(stats_line, text=f"{champ.win_rate:.0f}% WR", 
                            font=("Segoe UI", 10, "bold"), foreground=wr_color, bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 10))
                    
                    kda_color = "#16a34a" if champ.kda >= 3.0 else "#f59e0b" if champ.kda >= 2.0 else "#dc2626"
                    tk.Label(stats_line, text=f"{champ.kda:.1f} KDA", 
                            font=("Segoe UI", 10), foreground=kda_color, bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 10))
                    
                    tk.Label(stats_line, text=f"{champ.cs_per_min:.1f} CS/min", 
                            font=("Segoe UI", 10), foreground="#0891b2", bg="#f8fafc").pack(side=tk.LEFT)
                    
                    # Queue type badge
                    tk.Label(stats_col, text=champ.queue_type.upper(), 
                            font=("Segoe UI", 8), foreground="#9ca3af", bg="#f8fafc").pack(anchor=tk.W, pady=(2, 0))
            
            # Note about OP.GG limitations
            note_label = tk.Label(self.account_scrollable_frame,
                                 text="📊 Data from OP.GG - Showing most played champions from ranked games",
                                 font=("Segoe UI", 8), fg="gray")
            note_label.pack(pady=10)
            
            self.status_var.set(f"Account analysis completed for {account_data.summoner_name}")
            
        except Exception as e:
            print(f"❌ Error showing account results: {str(e)}")
            self._show_error(f"Error displaying account results: {str(e)}")

    def show_manual_stats_summary(self):
        """Show aggregated stats from manual matches only"""
        summoner = self.summoner_name.get().strip()
        if not summoner:
            # Show all manual matches regardless of summoner
            all_stats = {}
            for match in self.manual_match_storage.matches:
                champ = match.champion_name
                if champ not in all_stats:
                    all_stats[champ] = []
                all_stats[champ].append(match)
            
            if not all_stats:
                self.manual_matches_text.delete(1.0, tk.END)
                self.manual_matches_text.insert(1.0, "No manual matches found. Add some matches first!")
                return
            
            # Show stats for all summoners
            summoners = set(m.summoner_name for m in self.manual_match_storage.matches)
            output = f"=== MANUAL MATCHES STATISTICS (ALL SUMMONERS) ===\n"
            output += f"Total Matches: {len(self.manual_match_storage.matches)}\n"
            output += f"Summoners: {', '.join(summoners)}\n\n"
        else:
            manual_stats = self.manual_match_storage.get_all_champion_stats(summoner)
            
            if not manual_stats:
                self.manual_matches_text.delete(1.0, tk.END)
                self.manual_matches_text.insert(1.0, f"No manual matches found for {summoner}.\n\nAdd some matches first!")
                return
            
            output = f"=== MANUAL MATCHES STATISTICS ===\n"
            output += f"Summoner: {summoner}\n"
            output += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            output += "=== CHAMPION PERFORMANCE (MANUAL MATCHES ONLY) ===\n\n"
            
            for i, champ_stats in enumerate(manual_stats, 1):
                output += f"{i}. {champ_stats['champion_name']}\n"
                output += f"   Games: {champ_stats['games_played']} | Win Rate: {champ_stats['win_rate']:.1f}% "
                output += f"({champ_stats['wins']}W {champ_stats['losses']}L)\n"
                output += f"   KDA: {champ_stats['kda']:.2f} | K/D/A: {champ_stats['kills']:.1f}/{champ_stats['deaths']:.1f}/{champ_stats['assists']:.1f}\n"
                output += f"   CS/min: {champ_stats['cs_per_min']:.1f}\n\n"
        
        self.manual_matches_text.delete(1.0, tk.END)
        self.manual_matches_text.insert(1.0, output)
        self.status_var.set(f"Manual match statistics displayed")

    def analyze_champion(self):
        """Analyze champion with detailed stats"""
        champion_name = self.champion_name.get().strip()
        if not champion_name:
            messagebox.showerror("Error", "Please enter a champion name")
            return

        # Launch analysis in a separate thread
        self.status_var.set(f"Analyzing champion: {champion_name}...")
        thread = threading.Thread(target=self._analyze_champion_thread, args=(champion_name,))
        thread.daemon = True
        thread.start()

    def _analyze_champion_thread(self, champion_name):
        """Thread for champion analysis with enhanced data"""
        try:
            # Use enhanced scraper
            champion_data = self.champion_stats_scraper.get_champion_stats(champion_name)
            
            if champion_data:
                self.current_champion_data = champion_data
                self.root.after(0, lambda: self._show_detailed_champion_results(champion_data))
            else:
                self.root.after(0, lambda: self._show_error(f"Failed to retrieve data for {champion_name}"))
            
        except Exception as e:
            print(f"❌ Error during champion analysis: {str(e)}")
            self.root.after(0, lambda: self._show_error(f"Error during champion analysis: {str(e)}"))
    
    def compare_champions(self):
        """Compare two champions"""
        champ1 = self.champion_name.get().strip()
        champ2 = self.champion_name_2.get().strip()
        
        if not champ1 or not champ2:
            messagebox.showerror("Error", "Please enter both champion names to compare")
            return
        
        self.status_var.set(f"Comparing {champ1} vs {champ2}...")
        thread = threading.Thread(target=self._compare_champions_thread, args=(champ1, champ2))
        thread.daemon = True
        thread.start()
    
    def _compare_champions_thread(self, champ1, champ2):
        """Thread for champion comparison"""
        try:
            comparison = self.champion_stats_scraper.compare_champions(champ1, champ2)
            
            if comparison:
                self.current_champion_comparison = comparison
                self.root.after(0, lambda: self._show_champion_comparison(comparison))
            else:
                self.root.after(0, lambda: self._show_error(f"Failed to compare {champ1} vs {champ2}"))
            
        except Exception as e:
            print(f"❌ Error during champion comparison: {str(e)}")
            self.root.after(0, lambda: self._show_error(f"Error during comparison: {str(e)}"))


    def _show_detailed_champion_results(self, champion_data: DetailedChampionStats):
        """Show detailed champion analysis results"""
        try:
            # Clear existing widgets
            for widget in self.champion_scrollable_frame.winfo_children():
                widget.destroy()

            # Title with champion icon
            title_frame = ttk.Frame(self.champion_scrollable_frame)
            title_frame.pack(pady=10)
            
            # Download and display champion icon
            icon_url = self.champion_stats_scraper.get_champion_icon_url(champion_data.champion_name)
            if icon_url:
                try:
                    response = requests.get(icon_url, timeout=5)
                    if response.status_code == 200:
                        image_data = Image.open(BytesIO(response.content))
                        # Resize to 64x64 for display
                        image_data = image_data.resize((64, 64), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(image_data)
                        
                        icon_label = tk.Label(title_frame, image=photo)
                        icon_label.image = photo  # Keep reference
                        icon_label.pack()
                except Exception as e:
                    print(f"Failed to load icon: {e}")
            
            title_label = tk.Label(title_frame, 
                                  text=f"{champion_data.champion_name} - {champion_data.role}",
                                  font=("Segoe UI", 20, "bold"))
            title_label.pack()

            # Tier and rates in one row
            stats_container = ttk.Frame(self.champion_scrollable_frame)
            stats_container.pack(fill=tk.X, padx=10, pady=5)
            
            # Basic stats frame
            basic_frame = ttk.LabelFrame(stats_container, text="Meta Statistics", padding=10)
            basic_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            stats_text = f"""Tier: {champion_data.tier}
Win Rate: {champion_data.win_rate:.1f}%
Pick Rate: {champion_data.pick_rate:.1f}%
Ban Rate: {champion_data.ban_rate:.1f}%
Patch: {champion_data.patch}"""
            
            tk.Label(basic_frame, text=stats_text, font=("Segoe UI", 11), justify=tk.LEFT).pack(anchor=tk.W)
            
            # Runes frame with icons
            runes_frame = ttk.LabelFrame(stats_container, text="Runes", padding=10)
            runes_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
            
            # Primary rune with icon
            primary_container = ttk.Frame(runes_frame)
            primary_container.pack(anchor=tk.W, pady=2)
            tk.Label(primary_container, text="Primary:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
            primary_icon = self.assets.get_rune_icon(champion_data.primary_rune, size=28)
            if primary_icon:
                icon_label = tk.Label(primary_container, image=primary_icon)
                icon_label.image = primary_icon
                icon_label.pack(side=tk.LEFT, padx=(5, 3))
            tk.Label(primary_container, text=champion_data.primary_rune, font=("Segoe UI", 10)).pack(side=tk.LEFT)
            
            # Secondary rune with icon
            secondary_container = ttk.Frame(runes_frame)
            secondary_container.pack(anchor=tk.W, pady=2)
            tk.Label(secondary_container, text="Secondary:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
            secondary_icon = self.assets.get_rune_icon(champion_data.secondary_rune, size=28)
            if secondary_icon:
                icon_label = tk.Label(secondary_container, image=secondary_icon)
                icon_label.image = secondary_icon
                icon_label.pack(side=tk.LEFT, padx=(5, 3))
            tk.Label(secondary_container, text=champion_data.secondary_rune, font=("Segoe UI", 10)).pack(side=tk.LEFT)

            # Items section
            items_container = ttk.Frame(self.champion_scrollable_frame)
            items_container.pack(fill=tk.X, padx=10, pady=5)
            
            # Most popular items with icons
            popular_frame = ttk.LabelFrame(items_container, text="📦 Most Popular Build", padding=10)
            popular_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            for i, item in enumerate(champion_data.most_popular_items, 1):
                item_container = ttk.Frame(popular_frame)
                item_container.pack(anchor=tk.W, pady=3)
                
                # Item icon
                item_icon = self.assets.get_item_icon(item, size=32)
                if item_icon:
                    icon_label = tk.Label(item_container, image=item_icon)
                    icon_label.image = item_icon
                    icon_label.pack(side=tk.LEFT, padx=(0, 5))
                
                # Item name
                tk.Label(item_container, text=item, font=("Segoe UI", 10)).pack(side=tk.LEFT)
            
            # Highest winrate items with icons
            winrate_frame = ttk.LabelFrame(items_container, text="🏆 Highest Win Rate Build", padding=10)
            winrate_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
            
            for i, item in enumerate(champion_data.highest_winrate_items, 1):
                item_container = ttk.Frame(winrate_frame)
                item_container.pack(anchor=tk.W, pady=3)
                
                # Item icon
                item_icon = self.assets.get_item_icon(item, size=32)
                if item_icon:
                    icon_label = tk.Label(item_container, image=item_icon)
                    icon_label.image = item_icon
                    icon_label.pack(side=tk.LEFT, padx=(0, 5))
                
                # Item name
                tk.Label(item_container, text=item, font=("Segoe UI", 10)).pack(side=tk.LEFT)

            # Matchups section
            matchups_container = ttk.Frame(self.champion_scrollable_frame)
            matchups_container.pack(fill=tk.X, padx=10, pady=5)
            
            # Best matchups
            best_frame = ttk.LabelFrame(matchups_container, text="✅ Best Matchups (Easy)", padding=10)
            best_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            for matchup in champion_data.best_matchups:
                matchup_container = ttk.Frame(best_frame)
                matchup_container.pack(anchor=tk.W, pady=3)
                
                # Champion icon
                champ_icon = self.assets.get_champion_icon(matchup.opponent_name, size=28)
                if champ_icon:
                    icon_label = tk.Label(matchup_container, image=champ_icon)
                    icon_label.image = champ_icon
                    icon_label.pack(side=tk.LEFT, padx=(0, 5))
                
                # Matchup text
                matchup_text = f"{matchup.opponent_name}: {matchup.win_rate:.1f}% ({matchup.games}g)"
                tk.Label(matchup_container, text=matchup_text, font=("Segoe UI", 10), 
                        foreground="green").pack(side=tk.LEFT)
            
            # Worst matchups
            worst_frame = ttk.LabelFrame(matchups_container, text="❌ Worst Matchups (Hard)", padding=10)
            worst_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
            
            for matchup in champion_data.worst_matchups:
                matchup_container = ttk.Frame(worst_frame)
                matchup_container.pack(anchor=tk.W, pady=3)
                
                # Champion icon
                champ_icon = self.assets.get_champion_icon(matchup.opponent_name, size=28)
                if champ_icon:
                    icon_label = tk.Label(matchup_container, image=champ_icon)
                    icon_label.image = champ_icon
                    icon_label.pack(side=tk.LEFT, padx=(0, 5))
                
                # Matchup text
                matchup_text = f"{matchup.opponent_name}: {matchup.win_rate:.1f}% ({matchup.games}g)"
                tk.Label(matchup_container, text=matchup_text, font=("Segoe UI", 10), 
                        foreground="red").pack(side=tk.LEFT)

            # Analysis
            analysis_frame = ttk.LabelFrame(self.champion_scrollable_frame, text="Performance Analysis", padding=10)
            analysis_frame.pack(fill=tk.X, padx=10, pady=5)

            analysis = self._generate_detailed_analysis(champion_data)
            tk.Label(analysis_frame, text=analysis, font=("Segoe UI", 10), 
                    wraplength=900, justify=tk.LEFT).pack(anchor=tk.W)

            # Data source note
            source_label = tk.Label(self.champion_scrollable_frame,
                                   text=f"📊 Lolalytics - Diamond+ Only, Patch {champion_data.patch}\n"
                                        f"Real: Win/Pick/Ban/Tier/Runes | Items: From page (SET stats require JS)",
                                   font=("Segoe UI", 8), fg="gray", justify=tk.CENTER)
            source_label.pack(pady=5)

            self.status_var.set(f"Champion analysis completed for {champion_data.champion_name}")
            
        except Exception as e:
            print(f"❌ Error showing champion results: {str(e)}")
            self._show_error(f"Error displaying champion results: {str(e)}")
    
    def _show_champion_comparison(self, comparison: Dict):
        """Show champion comparison results"""
        try:
            # Clear existing widgets
            for widget in self.champion_scrollable_frame.winfo_children():
                widget.destroy()

            champ1 = comparison['champion1']
            champ2 = comparison['champion2']
            matchup_wr = comparison['matchup_winrate']
            difficulty = comparison['difficulty']

            # Title
            title_label = tk.Label(self.champion_scrollable_frame, 
                                  text=f"{champ1.champion_name} vs {champ2.champion_name}",
                                  font=("Segoe UI", 18, "bold"))
            title_label.pack(pady=10)
            
            # Matchup result
            matchup_frame = ttk.LabelFrame(self.champion_scrollable_frame, text="Lane Matchup", padding=15)
            matchup_frame.pack(fill=tk.X, padx=10, pady=10)
            
            matchup_color = "green" if matchup_wr > 50 else "red" if matchup_wr < 50 else "gray"
            matchup_text = f"{champ1.champion_name}'s Win Rate vs {champ2.champion_name}: {matchup_wr:.1f}%"
            tk.Label(matchup_frame, text=matchup_text, font=("Segoe UI", 14, "bold"), 
                    foreground=matchup_color).pack(pady=5)
            tk.Label(matchup_frame, text=f"Difficulty: {difficulty}", font=("Segoe UI", 12)).pack()

            # Side by side comparison
            comparison_container = ttk.Frame(self.champion_scrollable_frame)
            comparison_container.pack(fill=tk.X, padx=10, pady=5)
            
            # Champion 1 stats
            champ1_frame = ttk.LabelFrame(comparison_container, text=champ1.champion_name, padding=10)
            champ1_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            champ1_text = f"""Tier: {champ1.tier}
Win Rate: {champ1.win_rate:.1f}%
Pick Rate: {champ1.pick_rate:.1f}%
Ban Rate: {champ1.ban_rate:.1f}%

Popular Build:
• {champ1.most_popular_items[0] if len(champ1.most_popular_items) > 0 else 'N/A'}
• {champ1.most_popular_items[1] if len(champ1.most_popular_items) > 1 else 'N/A'}
• {champ1.most_popular_items[2] if len(champ1.most_popular_items) > 2 else 'N/A'}"""
            
            tk.Label(champ1_frame, text=champ1_text, font=("Segoe UI", 10), justify=tk.LEFT).pack(anchor=tk.W)
            
            # Champion 2 stats
            champ2_frame = ttk.LabelFrame(comparison_container, text=champ2.champion_name, padding=10)
            champ2_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
            
            champ2_text = f"""Tier: {champ2.tier}
Win Rate: {champ2.win_rate:.1f}%
Pick Rate: {champ2.pick_rate:.1f}%
Ban Rate: {champ2.ban_rate:.1f}%

Popular Build:
• {champ2.most_popular_items[0] if len(champ2.most_popular_items) > 0 else 'N/A'}
• {champ2.most_popular_items[1] if len(champ2.most_popular_items) > 1 else 'N/A'}
• {champ2.most_popular_items[2] if len(champ2.most_popular_items) > 2 else 'N/A'}"""
            
            tk.Label(champ2_frame, text=champ2_text, font=("Segoe UI", 10), justify=tk.LEFT).pack(anchor=tk.W)
            
            # Matchup recommendation
            recommendation_frame = ttk.LabelFrame(self.champion_scrollable_frame, text="Recommendation", padding=10)
            recommendation_frame.pack(fill=tk.X, padx=10, pady=5)
            
            if matchup_wr > 52:
                rec_text = f"✅ {champ1.champion_name} has a favorable matchup against {champ2.champion_name}. Good pick!"
                color = "green"
            elif matchup_wr < 48:
                rec_text = f"❌ {champ1.champion_name} struggles against {champ2.champion_name}. Consider banning or avoiding."
                color = "red"
            else:
                rec_text = f"⚖️ This is a skill matchup. Player skill matters more than champion choice."
                color = "blue"
            
            tk.Label(recommendation_frame, text=rec_text, font=("Segoe UI", 11), 
                    foreground=color, wraplength=900).pack(anchor=tk.W)

            self.status_var.set(f"Comparison completed: {champ1.champion_name} vs {champ2.champion_name}")
            
        except Exception as e:
            print(f"❌ Error showing comparison: {str(e)}")
            self._show_error(f"Error displaying comparison: {str(e)}")
    
    def _generate_detailed_analysis(self, champion_data: DetailedChampionStats) -> str:
        """Generate detailed analysis for champion"""
        analysis = f"Champion Performance Analysis:\n\n"
        
        # Win rate
        if champion_data.win_rate >= 53:
            analysis += f"• Strong performer with {champion_data.win_rate:.1f}% win rate - currently in a good spot.\n"
        elif champion_data.win_rate >= 50:
            analysis += f"• Balanced with {champion_data.win_rate:.1f}% win rate - viable pick.\n"
        else:
            analysis += f"• Underperforming at {champion_data.win_rate:.1f}% win rate - may need buffs or practice.\n"
        
        # Pick/Ban
        if champion_data.pick_rate >= 10:
            analysis += f"• Very popular with {champion_data.pick_rate:.1f}% pick rate.\n"
        if champion_data.ban_rate >= 20:
            analysis += f"• Frequently banned ({champion_data.ban_rate:.1f}%) - players consider this champion strong.\n"
        
        # Tier
        tier_desc = {
            "S": "Top tier - excellent choice for climbing",
            "A": "Strong pick - reliable and effective",
            "B": "Balanced - requires skill to carry",
            "C": "Situational - needs specific conditions",
            "D": "Weak - not recommended for climbing"
        }
        analysis += f"• Tier {champion_data.tier}: {tier_desc.get(champion_data.tier, 'Unknown tier')}\n"
        
        # Matchups
        if champion_data.best_matchups:
            best_names = ', '.join([m.opponent_name for m in champion_data.best_matchups[:2]])
            analysis += f"• Strong into: {best_names}\n"
        
        if champion_data.worst_matchups:
            worst_names = ', '.join([m.opponent_name for m in champion_data.worst_matchups[:2]])
            analysis += f"• Struggles against: {worst_names}\n"
        
        return analysis

    def _generate_champion_analysis(self, champion_data):
        """Generate analysis text for champion"""
        analysis = f"Based on the current meta data for {champion_data.champion_name}:\n\n"
        
        # Win rate analysis
        if champion_data.win_rate >= 53:
            analysis += f"• Strong win rate of {champion_data.win_rate:.1f}% indicates this champion is performing well in the current meta.\n"
        elif champion_data.win_rate >= 50:
            analysis += f"• Moderate win rate of {champion_data.win_rate:.1f}% suggests balanced performance.\n"
        else:
            analysis += f"• Lower win rate of {champion_data.win_rate:.1f}% may indicate the champion is struggling in the current meta.\n"
        
        # Pick rate analysis
        if champion_data.pick_rate >= 10:
            analysis += f"• High pick rate of {champion_data.pick_rate:.1f}% shows this champion is popular among players.\n"
        elif champion_data.pick_rate >= 5:
            analysis += f"• Moderate pick rate of {champion_data.pick_rate:.1f}% indicates decent popularity.\n"
        else:
            analysis += f"• Lower pick rate of {champion_data.pick_rate:.1f}% suggests niche or situational usage.\n"
        
        # Ban rate analysis
        if champion_data.ban_rate >= 15:
            analysis += f"• High ban rate of {champion_data.ban_rate:.1f}% indicates players consider this champion strong or annoying.\n"
        elif champion_data.ban_rate >= 5:
            analysis += f"• Moderate ban rate of {champion_data.ban_rate:.1f}% shows some concern from opponents.\n"
        else:
            analysis += f"• Low ban rate of {champion_data.ban_rate:.1f}% suggests the champion is not considered a major threat.\n"
        
        # Tier analysis
        tier_analysis = {
            "S": "This champion is considered top-tier and very strong in the current meta.",
            "A": "This champion is strong and viable in most situations.",
            "B": "This champion is decent but may have some weaknesses.",
            "C": "This champion is weaker and may struggle in the current meta.",
            "D": "This champion is considered weak and not recommended for competitive play."
        }
        
        analysis += f"• {tier_analysis.get(champion_data.tier, 'Tier information not available.')}\n"
        
        # Role analysis
        if champion_data.role != "Unknown":
            analysis += f"• Primary role: {champion_data.role}\n"
        
        return analysis


    def export_account_data(self):
        """Export account data to file"""
        if not self.current_account_data:
            messagebox.showerror("Error", "No account data to export")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    # Export as JSON
                    data = {
                        "summoner_name": self.current_account_data.summoner_name,
                        "region": self.current_account_data.region,
                        "level": self.current_account_data.level,
                        "soloq_rank": self.current_account_data.soloq_rank,
                        "flex_rank": self.current_account_data.flex_rank,
                        "champion_performances": [
                            {
                                "champion_name": champ.champion_name,
                                "games_played": champ.games_played,
                                "wins": champ.wins,
                                "losses": champ.losses,
                                "win_rate": champ.win_rate,
                                "kda": champ.kda,
                                "cs_per_min": champ.cs_per_min
                            } for champ in self.current_account_data.champion_performances
                        ],
                        "timestamp": self.current_account_data.last_updated
                    }
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    # Export as text - generate from account data
                    text_content = f"""ACCOUNT ANALYSIS - {self.current_account_data.summoner_name}
Region: {self.current_account_data.region.upper()}
Level: {self.current_account_data.level}
SoloQ: {self.current_account_data.soloq_rank} ({self.current_account_data.soloq_lp} LP)
Flex: {self.current_account_data.flex_rank} ({self.current_account_data.flex_lp} LP)
Last Updated: {self.current_account_data.last_updated}

CHAMPION PERFORMANCES:
"""
                    for i, champ in enumerate(sorted(self.current_account_data.champion_performances, 
                                                     key=lambda x: x.games_played, reverse=True), 1):
                        if champ.champion_name != "Overall Season":
                            text_content += f"\n{i}. {champ.champion_name}\n"
                            text_content += f"   Games: {champ.games_played} | WR: {champ.win_rate:.1f}% | KDA: {champ.kda:.2f}\n"
                            text_content += f"   Queue: {champ.queue_type.upper()}\n"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                
                messagebox.showinfo("Success", f"Account data exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export account data: {str(e)}")

    def export_champion_data(self):
        """Export champion data to file"""
        if not self.current_champion_data:
            messagebox.showerror("Error", "No champion data to export")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    # Export as JSON
                    data = {
                        "champion_name": self.current_champion_data.champion_name,
                        "win_rate": self.current_champion_data.win_rate,
                        "pick_rate": self.current_champion_data.pick_rate,
                        "ban_rate": self.current_champion_data.ban_rate,
                        "tier": self.current_champion_data.tier,
                        "role": self.current_champion_data.role,
                        "patch": self.current_champion_data.patch,
                        "timestamp": datetime.now().isoformat()
                    }
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    # Export as text
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"Champion: {self.current_champion_data.champion_name}\n")
                        f.write(f"Win Rate: {self.current_champion_data.win_rate:.1f}%\n")
                        f.write(f"Pick Rate: {self.current_champion_data.pick_rate:.1f}%\n")
                        f.write(f"Tier: {self.current_champion_data.tier}\n")
                
                messagebox.showinfo("Success", f"Champion data exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export champion data: {str(e)}")

    def clear_results(self):
        """Clear all results"""
        # Clear account view (canvas-based now)
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Clear champion view
        for widget in self.champion_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Clear combined text
        self.combined_text.delete(1.0, tk.END)
        
        # Clear manual matches text
        self.manual_matches_text.delete(1.0, tk.END)
        
        self.current_account_data = None
        self.current_champion_data = None
        self.status_var.set("Results cleared - Ready for new analysis")

    def _show_error(self, error_msg):
        """Show error message"""
        # Clear account view
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Show error in account view
        error_label = tk.Label(self.account_scrollable_frame, 
                              text=f"❌ ERROR: {error_msg}",
                              font=("Segoe UI", 14),
                              foreground="red",
                              wraplength=800)
        error_label.pack(pady=50)
        self.status_var.set("Error occurred")
    
    def add_manual_match(self):
        """Open dialog to add a manual match"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Manual Match")
        dialog.geometry("500x600")
        dialog.resizable(False, False)
        
        # Create form fields
        row = 0
        
        ttk.Label(dialog, text="Match ID:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        match_id_entry = ttk.Entry(dialog, width=40)
        match_id_entry.grid(row=row, column=1, padx=10, pady=5)
        match_id_entry.insert(0, f"MANUAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        row += 1
        
        ttk.Label(dialog, text="Summoner Name:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        summoner_entry = ttk.Entry(dialog, width=40)
        summoner_entry.grid(row=row, column=1, padx=10, pady=5)
        summoner_entry.insert(0, self.summoner_name.get())
        row += 1
        
        ttk.Label(dialog, text="Champion Name:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        champion_entry = ttk.Entry(dialog, width=40)
        champion_entry.grid(row=row, column=1, padx=10, pady=5)
        row += 1
        
        ttk.Label(dialog, text="Result:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        result_var = tk.StringVar(value="WIN")
        result_frame = ttk.Frame(dialog)
        result_frame.grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        ttk.Radiobutton(result_frame, text="WIN", variable=result_var, value="WIN").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(result_frame, text="LOSS", variable=result_var, value="LOSS").pack(side=tk.LEFT, padx=5)
        row += 1
        
        ttk.Label(dialog, text="Kills:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        kills_entry = ttk.Entry(dialog, width=40)
        kills_entry.grid(row=row, column=1, padx=10, pady=5)
        kills_entry.insert(0, "0")
        row += 1
        
        ttk.Label(dialog, text="Deaths:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        deaths_entry = ttk.Entry(dialog, width=40)
        deaths_entry.grid(row=row, column=1, padx=10, pady=5)
        deaths_entry.insert(0, "0")
        row += 1
        
        ttk.Label(dialog, text="Assists:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        assists_entry = ttk.Entry(dialog, width=40)
        assists_entry.grid(row=row, column=1, padx=10, pady=5)
        assists_entry.insert(0, "0")
        row += 1
        
        ttk.Label(dialog, text="CS (Total):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        cs_entry = ttk.Entry(dialog, width=40)
        cs_entry.grid(row=row, column=1, padx=10, pady=5)
        cs_entry.insert(0, "0")
        row += 1
        
        ttk.Label(dialog, text="Game Duration (minutes):").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        duration_entry = ttk.Entry(dialog, width=40)
        duration_entry.grid(row=row, column=1, padx=10, pady=5)
        duration_entry.insert(0, "25")
        row += 1
        
        ttk.Label(dialog, text="Queue Type:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        queue_combo = ttk.Combobox(dialog, values=["custom", "tournament", "soloq", "flex", "normal", "aram"], width=37)
        queue_combo.grid(row=row, column=1, padx=10, pady=5)
        queue_combo.set("custom")
        row += 1
        
        ttk.Label(dialog, text="Notes:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        notes_text = tk.Text(dialog, width=30, height=5)
        notes_text.grid(row=row, column=1, padx=10, pady=5)
        row += 1
        
        def save_match():
            try:
                match = ManualMatch(
                    match_id=match_id_entry.get().strip(),
                    summoner_name=summoner_entry.get().strip(),
                    champion_name=champion_entry.get().strip(),
                    result=result_var.get(),
                    kills=float(kills_entry.get()),
                    deaths=float(deaths_entry.get()),
                    assists=float(assists_entry.get()),
                    cs=float(cs_entry.get()),
                    game_duration=int(duration_entry.get()),
                    queue_type=queue_combo.get(),
                    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    notes=notes_text.get(1.0, tk.END).strip()
                )
                
                if self.manual_match_storage.add_match(match):
                    messagebox.showinfo("Success", f"Match added successfully!\nKDA: {match.kda:.2f}")
                    dialog.destroy()
                    self.view_manual_matches()
                else:
                    messagebox.showerror("Error", "Match ID already exists or failed to add")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save Match", command=save_match).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def view_manual_matches(self):
        """View all manual matches"""
        summoner = self.summoner_name.get().strip()
        if not summoner:
            matches = self.manual_match_storage.matches
            title = "All Manual Matches"
        else:
            matches = self.manual_match_storage.get_matches_for_summoner(summoner)
            title = f"Manual Matches for {summoner}"
        
        self.manual_matches_text.delete(1.0, tk.END)
        
        if not matches:
            self.manual_matches_text.insert(1.0, "No manual matches found.\n\nClick 'Add Manual Match' to add your first match!")
            return
        
        output = f"=== {title.upper()} ===\n"
        output += f"Total Matches: {len(matches)}\n\n"
        
        # Sort by date (most recent first)
        sorted_matches = sorted(matches, key=lambda x: x.date, reverse=True)
        
        for i, match in enumerate(sorted_matches, 1):
            output += f"{i}. {match.champion_name} - {match.result}\n"
            output += f"   Match ID: {match.match_id}\n"
            output += f"   Date: {match.date}\n"
            output += f"   K/D/A: {match.kills:.0f}/{match.deaths:.0f}/{match.assists:.0f} (KDA: {match.kda:.2f})\n"
            output += f"   CS: {match.cs:.0f} ({match.cs_per_min:.1f}/min)\n"
            output += f"   Queue: {match.queue_type.upper()}\n"
            if match.notes:
                output += f"   Notes: {match.notes}\n"
            output += "\n"
        
        self.manual_matches_text.insert(1.0, output)
        self.status_var.set(f"Loaded {len(matches)} manual matches")
    
    def show_combined_stats(self):
        """Show combined stats from ranked + manual matches"""
        summoner = self.summoner_name.get().strip()
        if not summoner:
            messagebox.showerror("Error", "Please enter a summoner name first")
            return
        
        self.combined_text.delete(1.0, tk.END)
        
        output = f"=== COMBINED STATISTICS ===\n"
        output += f"Summoner: {summoner}\n"
        output += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Get manual match stats
        manual_stats = self.manual_match_storage.get_all_champion_stats(summoner)
        
        # Get ranked stats from current account data
        ranked_stats = {}
        if self.current_account_data:
            for champ in self.current_account_data.champion_performances:
                if champ.champion_name != "Overall Season":
                    ranked_stats[champ.champion_name] = champ
        
        # Combine stats
        all_champions = set()
        if manual_stats:
            all_champions.update(m['champion_name'] for m in manual_stats)
        if ranked_stats:
            all_champions.update(ranked_stats.keys())
        
        if not all_champions:
            output += "No data available. Analyze an account or add manual matches first.\n"
            self.combined_text.insert(1.0, output)
            return
        
        output += "=== CHAMPION STATISTICS (RANKED + MANUAL COMBINED) ===\n\n"
        
        # Create combined stats for each champion
        combined_list = []
        
        for champion in all_champions:
            # Get manual stats
            manual = next((m for m in manual_stats if m['champion_name'] == champion), None) if manual_stats else None
            # Get ranked stats
            ranked = ranked_stats.get(champion)
            
            # Combine
            if manual and ranked:
                total_games = manual['games_played'] + ranked.games_played
                total_wins = manual['wins'] + ranked.wins
                combined_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
                
                # Weighted average for KDA and CS
                manual_weight = manual['games_played'] / total_games
                ranked_weight = ranked.games_played / total_games
                
                combined_kda = (manual['kda'] * manual_weight) + (ranked.kda * ranked_weight)
                combined_cs = (manual['cs_per_min'] * manual_weight) + (ranked.cs_per_min * ranked_weight)
                
                combined_list.append({
                    'champion': champion,
                    'games': total_games,
                    'wins': total_wins,
                    'win_rate': combined_win_rate,
                    'kda': combined_kda,
                    'cs_per_min': combined_cs,
                    'manual_games': manual['games_played'],
                    'ranked_games': ranked.games_played
                })
            elif manual:
                combined_list.append({
                    'champion': champion,
                    'games': manual['games_played'],
                    'wins': manual['wins'],
                    'win_rate': manual['win_rate'],
                    'kda': manual['kda'],
                    'cs_per_min': manual['cs_per_min'],
                    'manual_games': manual['games_played'],
                    'ranked_games': 0
                })
            elif ranked:
                combined_list.append({
                    'champion': champion,
                    'games': ranked.games_played,
                    'wins': ranked.wins,
                    'win_rate': ranked.win_rate,
                    'kda': ranked.kda,
                    'cs_per_min': ranked.cs_per_min,
                    'manual_games': 0,
                    'ranked_games': ranked.games_played
                })
        
        # Sort by total games
        combined_list.sort(key=lambda x: x['games'], reverse=True)
        
        for i, champ_stats in enumerate(combined_list, 1):
            output += f"{i}. {champ_stats['champion']}\n"
            output += f"   Total Games: {champ_stats['games']} (Ranked: {champ_stats['ranked_games']}, Manual: {champ_stats['manual_games']})\n"
            output += f"   Win Rate: {champ_stats['win_rate']:.1f}% ({champ_stats['wins']}W {champ_stats['games']-champ_stats['wins']}L)\n"
            output += f"   KDA: {champ_stats['kda']:.2f}\n"
            output += f"   CS/min: {champ_stats['cs_per_min']:.1f}\n\n"
        
        self.combined_text.insert(1.0, output)
        self.status_var.set(f"Combined stats generated for {len(combined_list)} champions")
    
    def clear_manual_matches(self):
        """Clear all manual matches"""
        result = messagebox.askyesno("Confirm", "Are you sure you want to delete ALL manual matches?\n\nThis cannot be undone!")
        if result:
            self.manual_match_storage.clear_all_matches()
            self.manual_matches_text.delete(1.0, tk.END)
            self.manual_matches_text.insert(1.0, "All manual matches have been cleared.")
            messagebox.showinfo("Success", "All manual matches have been deleted")

def main():
    """Launch application"""
    root = tk.Tk()
    app = AccountGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


