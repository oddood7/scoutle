
"""
ScoutLE Discord Bot Launcher
Simple script to start the Discord bot with proper error handling
"""

import os
import sys
from pathlib import Path

def check_requirements():
    """Check if all requirements are installed"""
    try:
        import discord
        import pandas
        import matplotlib
        from dotenv import load_dotenv
        print("✅ All requirements are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing requirement: {e}")
        print("Install with: pip install discord.py pandas matplotlib python-dotenv")
        return False

def check_env_file():
    """Check if .env file exists and is configured"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Copy env_example.txt to .env and configure it:")
        print("  cp env_example.txt .env")
        print("  # Edit .env with your Discord bot token")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token or token == 'your_bot_token_here':
        print("❌ DISCORD_BOT_TOKEN not configured in .env file!")
        print("Get your bot token from: https://discord.com/developers/applications")
        return False
    
    print("✅ .env file configured")
    return True

def main():
    """Main launcher function"""
    print("🤖 ScoutLE Discord Bot Launcher")
    print("=" * 40)
    
    if not check_requirements():
        sys.exit(1)
    
    if not check_env_file():
        sys.exit(1)
    
    try:
        print("🚀 Starting ScoutLE Discord Bot...")
        from scoutle_discord_bot import ScoutLEBot
        
        bot = ScoutLEBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
