"""
Account-focused GUI for ScoutLE
Focuses on Riot account stats from op.gg and champion stats from lolalytics
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime
import threading
import json
from tkinter.font import BOLD

# Import modules
from simple_account_scraper import SimpleAccountScraper, LolalyticsScraper, PlayerAccount, ChampionMetaData
from tournament_scraper import TournamentScraper, TournamentStats

class AccountGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ScoutLE - Account Stats & Champion Analysis")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        # Variables
        self.summoner_name = tk.StringVar()
        self.region = tk.StringVar(value="euw")
        self.champion_name = tk.StringVar()
        self.use_mock_data = tk.BooleanVar(value=True)

        # Scraper instances
        self.account_scraper = SimpleAccountScraper()
        self.lolalytics_scraper = LolalyticsScraper()
        self.tournament_scraper = TournamentScraper()
        self.current_account_data = None
        self.current_champion_data = None
        self.current_tournament_data = None

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
        title_label = ttk.Label(main_frame, text="ScoutLE - Account Stats & Champion Analysis", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Account analysis section
        self.setup_account_section(main_frame, 1)

        # Separator
        separator1 = ttk.Separator(main_frame, orient='horizontal')
        separator1.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)

        # Champion analysis section
        self.setup_champion_section(main_frame, 3)

        # Separator
        separator2 = ttk.Separator(main_frame, orient='horizontal')
        separator2.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)

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

        # Options
        options_frame = ttk.Frame(account_frame)
        options_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Checkbutton(options_frame, text="Use Mock Data (for demo)", variable=self.use_mock_data).pack(side=tk.LEFT, padx=(0, 20))

        # Buttons
        button_frame = ttk.Frame(account_frame)
        button_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        analyze_btn = ttk.Button(button_frame, text="Analyze Account", 
                                command=self.analyze_account, style="Accent.TButton")
        analyze_btn.pack(side=tk.LEFT, padx=(0, 10))

        export_btn = ttk.Button(button_frame, text="Export Account Data", 
                               command=self.export_account_data)
        export_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = ttk.Button(button_frame, text="Clear Results", 
                              command=self.clear_results)
        clear_btn.pack(side=tk.LEFT)

    def setup_champion_section(self, parent, row):
        """Champion analysis section"""
        champion_frame = ttk.LabelFrame(parent, text="Champion Analysis", padding=10)
        champion_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        champion_frame.columnconfigure(1, weight=1)

        # Champion name
        ttk.Label(champion_frame, text="Champion Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        champion_entry = ttk.Entry(champion_frame, textvariable=self.champion_name, width=30)
        champion_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        champion_entry.bind('<Return>', lambda e: self.analyze_champion())

        # Buttons
        button_frame = ttk.Frame(champion_frame)
        button_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        analyze_champ_btn = ttk.Button(button_frame, text="Analyze Champion", 
                                      command=self.analyze_champion)
        analyze_champ_btn.pack(side=tk.LEFT, padx=(0, 10))

        batch_btn = ttk.Button(button_frame, text="Batch Champion Analysis", 
                              command=self.batch_champion_analysis)
        batch_btn.pack(side=tk.LEFT, padx=(0, 10))

        export_champ_btn = ttk.Button(button_frame, text="Export Champion Data", 
                                     command=self.export_champion_data)
        export_champ_btn.pack(side=tk.LEFT)

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

        # Tournament stats tab
        self.tournament_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.tournament_frame, text="Tournament Stats")

        # Combined analysis tab
        self.combined_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.combined_frame, text="Combined Analysis")

        # Setup tab contents
        self.setup_account_tab()
        self.setup_champion_tab()
        self.setup_tournament_tab()
        self.setup_combined_tab()

        # Configure results area
        parent.rowconfigure(row, weight=1)

    def setup_account_tab(self):
        """Setup account stats tab"""
        # Text area for account stats
        self.account_text = scrolledtext.ScrolledText(self.account_frame, width=100, height=25,
                                                     font=("Consolas", 10))
        self.account_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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

    def setup_tournament_tab(self):
        """Setup tournament stats tab"""
        # Canvas with scrollbar for tournament view
        self.tournament_canvas = tk.Canvas(self.tournament_frame)
        self.tournament_scrollbar = ttk.Scrollbar(self.tournament_frame, orient="vertical", 
                                                 command=self.tournament_canvas.yview)
        self.tournament_scrollable_frame = ttk.Frame(self.tournament_canvas)

        self.tournament_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.tournament_canvas.configure(scrollregion=self.tournament_canvas.bbox("all"))
        )

        self.tournament_canvas.create_window((0, 0), window=self.tournament_scrollable_frame, anchor="nw")
        self.tournament_canvas.configure(yscrollcommand=self.tournament_scrollbar.set)

        self.tournament_canvas.pack(side="left", fill="both", expand=True)
        self.tournament_scrollbar.pack(side="right", fill="y")

    def setup_combined_tab(self):
        """Setup combined analysis tab"""
        # Text area for combined analysis
        self.combined_text = scrolledtext.ScrolledText(self.combined_frame, width=100, height=25,
                                                      font=("Consolas", 10))
        self.combined_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def setup_status_bar(self, parent, row):
        """Status bar"""
        self.status_var = tk.StringVar(value="Ready - Enter summoner name and champion to analyze")
        status_label = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

    def analyze_account(self):
        """Analyze account"""
        summoner_name = self.summoner_name.get().strip()
        if not summoner_name:
            messagebox.showerror("Error", "Please enter a summoner name")
            return

        # Launch analysis in a separate thread
        self.status_var.set(f"Analyzing account: {summoner_name}...")
        thread = threading.Thread(target=self._analyze_account_thread, args=(summoner_name,))
        thread.daemon = True
        thread.start()

    def _analyze_account_thread(self, summoner_name):
        """Thread for account analysis"""
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
                    
                    # Also scrape tournament data
                    self.root.after(0, lambda: self.status_var.set("Analyzing tournament games..."))
                    tournament_data = self.tournament_scraper.scrape_tournament_games(summoner_name, self.region.get())
                    if tournament_data:
                        self.current_tournament_data = tournament_data
                        self.root.after(0, lambda: self._show_tournament_results(tournament_data))
                else:
                    self.root.after(0, lambda: self._show_error("Failed to retrieve account data. Try using mock data for demonstration."))
            
        except Exception as e:
            print(f"❌ Error during account analysis: {str(e)}")
            self.root.after(0, lambda: self._show_error(f"Error during account analysis: {str(e)}"))

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
        """Show account analysis results"""
        try:
            # Clear the account text area completely
            self.account_text.delete(1.0, tk.END)
            
            # Also clear any previous tournament data display
            for widget in self.tournament_scrollable_frame.winfo_children():
                widget.destroy()
            
            account_info = f"""
=== ACCOUNT ANALYSIS RESULTS ===
Summoner: {account_data.summoner_name}
Region: {account_data.region.upper()}
Analysis Time: {account_data.last_updated}

=== BASIC INFO ===
Level: {account_data.level}
SoloQ Rank: {account_data.soloq_rank} ({account_data.soloq_lp} LP)
Flex Rank: {account_data.flex_rank} ({account_data.flex_lp} LP)

=== CHAMPION PERFORMANCES ===
Total Champions Played: {len(account_data.champion_performances)}

"""
            
            # Sort champions by games played
            sorted_champions = sorted(account_data.champion_performances, 
                                    key=lambda x: x.games_played, reverse=True)
            
            for i, champ in enumerate(sorted_champions, 1):
                account_info += f"""
{i}. {champ.champion_name}
   Games: {champ.games_played} | Win Rate: {champ.win_rate:.1f}% | KDA: {champ.kda:.2f}
   Kills: {champ.kills:.1f} | Deaths: {champ.deaths:.1f} | Assists: {champ.assists:.1f}
   CS/min: {champ.cs_per_min:.1f} | Queue: {champ.queue_type.upper()}
"""
            
            # Calculate overall stats
            total_games = sum(champ.games_played for champ in account_data.champion_performances)
            total_wins = sum(champ.wins for champ in account_data.champion_performances)
            overall_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
            
            account_info += f"""
=== OVERALL STATISTICS ===
Total Games: {total_games}
Total Wins: {total_wins}
Overall Win Rate: {overall_win_rate:.1f}%
Most Played Champion: {sorted_champions[0].champion_name if sorted_champions else "None"}
Best Win Rate Champion: {max(account_data.champion_performances, key=lambda x: x.win_rate).champion_name if account_data.champion_performances else "None"}
"""
            
            self.account_text.insert(1.0, account_info)
            self.status_var.set(f"Account analysis completed for {account_data.summoner_name}")
            
        except Exception as e:
            print(f"❌ Error showing account results: {str(e)}")
            self._show_error(f"Error displaying account results: {str(e)}")

    def _show_tournament_results(self, tournament_data):
        """Show tournament analysis results"""
        try:
            # Clear existing widgets
            for widget in self.tournament_scrollable_frame.winfo_children():
                widget.destroy()

            # Title
            title_label = tk.Label(self.tournament_scrollable_frame, 
                                  text="Tournament Game Analysis",
                                  font=("Arial", 16, "bold"))
            title_label.pack(pady=10)

            # Tournament stats summary
            stats_frame = ttk.LabelFrame(self.tournament_scrollable_frame, text="Tournament Statistics", padding=10)
            stats_frame.pack(fill=tk.X, padx=10, pady=5)

            stats_text = f"""
Total Tournament Games: {tournament_data.total_tournament_games}
Tournament Wins: {tournament_data.tournament_wins}
Tournament Losses: {tournament_data.tournament_losses}
Tournament Win Rate: {tournament_data.tournament_win_rate:.1f}%
Most Played Champion: {tournament_data.most_played_champion}
Best Performing Champion: {tournament_data.best_performing_champion}
Average KDA: {tournament_data.average_kda:.2f}
Average CS: {tournament_data.average_cs:.1f}
Average Damage: {tournament_data.average_damage:.0f}
"""
            
            stats_label = tk.Label(stats_frame, text=stats_text, font=("Arial", 10), justify=tk.LEFT)
            stats_label.pack(anchor=tk.W)

            # Tournament codes
            if tournament_data.tournament_codes:
                codes_frame = ttk.LabelFrame(self.tournament_scrollable_frame, text="Tournament Codes Found", padding=10)
                codes_frame.pack(fill=tk.X, padx=10, pady=5)

                codes_text = f"Found {len(tournament_data.tournament_codes)} tournament codes:\n"
                codes_text += ", ".join(tournament_data.tournament_codes[:10])  # Show first 10
                if len(tournament_data.tournament_codes) > 10:
                    codes_text += f" ... and {len(tournament_data.tournament_codes) - 10} more"

                codes_label = tk.Label(codes_frame, text=codes_text, font=("Arial", 10), wraplength=800)
                codes_label.pack(anchor=tk.W)

            # Recent tournament games
            if tournament_data.recent_tournaments:
                games_frame = ttk.LabelFrame(self.tournament_scrollable_frame, text="Recent Tournament Games", padding=10)
                games_frame.pack(fill=tk.X, padx=10, pady=5)

                for game in tournament_data.recent_tournaments[:5]:  # Show first 5
                    game_text = f"{game.date}: {game.champion} ({game.result}) - {game.game_type}"
                    if game.tournament_code:
                        game_text += f" [{game.tournament_code}]"
                    
                    game_label = tk.Label(games_frame, text=game_text, font=("Arial", 9))
                    game_label.pack(anchor=tk.W, pady=1)

            # Analysis
            analysis_frame = ttk.LabelFrame(self.tournament_scrollable_frame, text="Tournament Analysis", padding=10)
            analysis_frame.pack(fill=tk.X, padx=10, pady=5)

            analysis = self._generate_tournament_analysis(tournament_data)
            analysis_label = tk.Label(analysis_frame, text=analysis, font=("Arial", 10), 
                                     wraplength=800, justify=tk.LEFT)
            analysis_label.pack(anchor=tk.W)

        except Exception as e:
            print(f"❌ Error showing tournament results: {str(e)}")
            self._show_error(f"Error displaying tournament results: {str(e)}")

    def _generate_tournament_analysis(self, tournament_data):
        """Generate analysis text for tournament data"""
        if tournament_data.total_tournament_games == 0:
            return "No tournament games found. This player may not have participated in official tournaments or custom tournament games."
        
        analysis = f"Tournament Performance Analysis:\n\n"
        
        # Win rate analysis
        if tournament_data.tournament_win_rate >= 70:
            analysis += f"• Excellent tournament performance with {tournament_data.tournament_win_rate:.1f}% win rate.\n"
        elif tournament_data.tournament_win_rate >= 60:
            analysis += f"• Strong tournament performance with {tournament_data.tournament_win_rate:.1f}% win rate.\n"
        elif tournament_data.tournament_win_rate >= 50:
            analysis += f"• Decent tournament performance with {tournament_data.tournament_win_rate:.1f}% win rate.\n"
        else:
            analysis += f"• Tournament performance could be improved with {tournament_data.tournament_win_rate:.1f}% win rate.\n"
        
        # Game count analysis
        if tournament_data.total_tournament_games >= 20:
            analysis += f"• High tournament activity with {tournament_data.total_tournament_games} games played.\n"
        elif tournament_data.total_tournament_games >= 10:
            analysis += f"• Moderate tournament activity with {tournament_data.total_tournament_games} games played.\n"
        else:
            analysis += f"• Limited tournament experience with {tournament_data.total_tournament_games} games played.\n"
        
        # Champion analysis
        if tournament_data.most_played_champion != "None":
            analysis += f"• Most played tournament champion: {tournament_data.most_played_champion}\n"
        
        if tournament_data.best_performing_champion != "None":
            analysis += f"• Best performing tournament champion: {tournament_data.best_performing_champion}\n"
        
        # KDA analysis
        if tournament_data.average_kda >= 3.0:
            analysis += f"• Strong individual performance with {tournament_data.average_kda:.2f} average KDA.\n"
        elif tournament_data.average_kda >= 2.0:
            analysis += f"• Good individual performance with {tournament_data.average_kda:.2f} average KDA.\n"
        else:
            analysis += f"• Individual performance could be improved with {tournament_data.average_kda:.2f} average KDA.\n"
        
        # Tournament codes analysis
        if tournament_data.tournament_codes:
            analysis += f"• Participated in {len(tournament_data.tournament_codes)} different tournaments.\n"
        
        return analysis

    def analyze_champion(self):
        """Analyze champion"""
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
        """Thread for champion analysis"""
        try:
            # Try real scraping first
            champion_data = self.lolalytics_scraper.scrape_champion_meta(champion_name)
            
            if champion_data and (champion_data.win_rate > 0 or champion_data.pick_rate > 0):
                self.current_champion_data = champion_data
                self.root.after(0, lambda: self._show_champion_results(champion_data))
            else:
                # Use mock data if real data is not available
                mock_data = self._create_mock_champion_data(champion_name)
                self.current_champion_data = mock_data
                self.root.after(0, lambda: self._show_champion_results(mock_data))
            
        except Exception as e:
            print(f"❌ Error during champion analysis: {str(e)}")
            self.root.after(0, lambda: self._show_error(f"Error during champion analysis: {str(e)}"))

    def _create_mock_champion_data(self, champion_name):
        """Create mock champion data for demonstration"""
        from simple_account_scraper import ChampionMetaData
        
        # Mock data based on champion name
        mock_data = {
            "Ahri": {"win_rate": 52.3, "pick_rate": 8.7, "ban_rate": 12.4, "tier": "A", "role": "Mid"},
            "Yasuo": {"win_rate": 48.9, "pick_rate": 15.2, "ban_rate": 25.8, "tier": "B", "role": "Mid"},
            "Lux": {"win_rate": 51.7, "pick_rate": 6.3, "ban_rate": 3.1, "tier": "A", "role": "Support"},
            "Zed": {"win_rate": 49.8, "pick_rate": 9.1, "ban_rate": 18.7, "tier": "B", "role": "Mid"},
            "Jinx": {"win_rate": 53.2, "pick_rate": 7.8, "ban_rate": 5.2, "tier": "S", "role": "ADC"},
        }
        
        data = mock_data.get(champion_name, {
            "win_rate": 50.0, "pick_rate": 5.0, "ban_rate": 5.0, "tier": "B", "role": "Unknown"
        })
        
        return ChampionMetaData(
            champion_name=champion_name,
            win_rate=data["win_rate"],
            pick_rate=data["pick_rate"],
            ban_rate=data["ban_rate"],
            tier=data["tier"],
            role=data["role"],
            patch="Current"
        )

    def _show_champion_results(self, champion_data):
        """Show champion analysis results"""
        try:
            # Clear existing widgets
            for widget in self.champion_scrollable_frame.winfo_children():
                widget.destroy()

            # Title
            title_label = tk.Label(self.champion_scrollable_frame, 
                                  text=f"Champion Analysis: {champion_data.champion_name}",
                                  font=("Arial", 16, "bold"))
            title_label.pack(pady=10)

            # Create info frame
            info_frame = ttk.LabelFrame(self.champion_scrollable_frame, text="Meta Statistics", padding=10)
            info_frame.pack(fill=tk.X, padx=10, pady=5)

            # Display stats
            stats_text = f"""
Win Rate: {champion_data.win_rate:.1f}%
Pick Rate: {champion_data.pick_rate:.1f}%
Ban Rate: {champion_data.ban_rate:.1f}%
Tier: {champion_data.tier}
Role: {champion_data.role}
Patch: {champion_data.patch}
"""
            
            stats_label = tk.Label(info_frame, text=stats_text, font=("Arial", 12), justify=tk.LEFT)
            stats_label.pack(anchor=tk.W)

            # Analysis frame
            analysis_frame = ttk.LabelFrame(self.champion_scrollable_frame, text="Analysis", padding=10)
            analysis_frame.pack(fill=tk.X, padx=10, pady=5)

            # Generate analysis based on stats
            analysis = self._generate_champion_analysis(champion_data)
            analysis_label = tk.Label(analysis_frame, text=analysis, font=("Arial", 10), 
                                     wraplength=800, justify=tk.LEFT)
            analysis_label.pack(anchor=tk.W)

            self.status_var.set(f"Champion analysis completed for {champion_data.champion_name}")
            
        except Exception as e:
            print(f"❌ Error showing champion results: {str(e)}")
            self._show_error(f"Error displaying champion results: {str(e)}")

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

    def batch_champion_analysis(self):
        """Perform batch champion analysis"""
        # Get champion names from user
        champions_text = tk.simpledialog.askstring("Batch Analysis", 
                                                  "Enter champion names (comma-separated):")
        if not champions_text:
            return

        champion_names = [name.strip() for name in champions_text.split(',')]
        
        # Launch batch analysis in thread
        self.status_var.set(f"Starting batch analysis of {len(champion_names)} champions...")
        thread = threading.Thread(target=self._batch_analysis_thread, args=(champion_names,))
        thread.daemon = True
        thread.start()

    def _batch_analysis_thread(self, champion_names):
        """Thread for batch analysis"""
        try:
            results = self.lolalytics_scraper.scrape_multiple_champions(champion_names)
            
            # Update UI with batch results
            self.root.after(0, lambda: self._show_batch_results(results))
            
        except Exception as e:
            print(f"❌ Error during batch analysis: {str(e)}")
            self.root.after(0, lambda: self._show_error(f"Error during batch analysis: {str(e)}"))

    def _show_batch_results(self, results):
        """Show batch analysis results"""
        # Clear existing widgets
        for widget in self.champion_scrollable_frame.winfo_children():
            widget.destroy()

        # Title
        title_label = tk.Label(self.champion_scrollable_frame, 
                              text=f"Batch Champion Analysis ({len(results)} champions)",
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Display results
        for champion_name, meta_data in results.items():
            champ_frame = ttk.LabelFrame(self.champion_scrollable_frame, text=champion_name, padding=10)
            champ_frame.pack(fill=tk.X, padx=10, pady=5)

            stats_text = f"Win Rate: {meta_data.win_rate:.1f}% | Pick Rate: {meta_data.pick_rate:.1f}% | Tier: {meta_data.tier}"
            stats_label = tk.Label(champ_frame, text=stats_text, font=("Arial", 10))
            stats_label.pack(anchor=tk.W)

        self.status_var.set(f"Batch analysis completed - {len(results)} champions analyzed")

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
                    # Export as text
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(self.account_text.get(1.0, tk.END))
                
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
        self.account_text.delete(1.0, tk.END)
        
        # Clear champion view
        for widget in self.champion_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Clear tournament view
        for widget in self.tournament_scrollable_frame.winfo_children():
            widget.destroy()
        
        self.combined_text.delete(1.0, tk.END)
        
        self.current_account_data = None
        self.current_champion_data = None
        self.current_tournament_data = None
        self.status_var.set("Results cleared - Ready for new analysis")

    def _show_error(self, error_msg):
        """Show error message"""
        self.account_text.delete(1.0, tk.END)
        self.account_text.insert(1.0, f"❌ ERROR: {error_msg}")
        self.status_var.set("Error occurred")

def main():
    """Launch application"""
    root = tk.Tk()
    app = AccountGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


