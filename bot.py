# __________                  __             __     ________             .___ 
# \______   \  ____    ____  |  | __  ____ _/  |_  /  _____/   ____    __| _/ 
#  |       _/ /  _ \ _/ ___\ |  |/ /_/ __ \\   __\/   \  ___  /  _ \  / __ |  
#  |    |   \(  <_> )\  \___ |    < \  ___/ |  |  \    \_\  \(  <_> )/ /_/ |  
#  |____|_  / \____/  \___  >|__|_ \ \___  >|__|   \______  / \____/ \____ |  
#         \/              \/      \/     \/               \/              \/  
#
# Discord bot for scraping Instagram accounts
# Edit config.json and run bot.py after the bot has been invited to your Discord server

### COMMANDS ###
# !add <username>
# !remove <username>
# !list

import subprocess
import logging
import importlib.util

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to check if a package is installed
def is_module_installed(module_name):
    spec = importlib.util.find_spec(module_name)
    return spec is not None

# Try to install required packages if not already installed
required_packages = ['discord', 'instaloader', 'requests']
for package in required_packages:
    if not is_module_installed(package):
        try:
            subprocess.check_call(["pip", "install", package])
        except subprocess.CalledProcessError:
            logging.error(f"Couldn't automatically install {package}. Please run: pip install {package}")
            exit(1)

import discord
from discord.ext import commands, tasks
import json
import instaloader
from datetime import datetime
import requests

# Initialize instaloader
L = instaloader.Instaloader()

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize instaloader with a custom rate controller
class MyRateController(instaloader.RateController):
    def sleep(self, secs):
        logging.info(f"Sleeping for {secs} seconds due to rate limits.")
        super().sleep(secs)

L = instaloader.Instaloader(rate_controller=MyRateController)

intents = discord.Intents.all()  # Enable all intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store the last post datetime for each user
last_post_times = {}

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f)

def save_last_post_times():
    with open('last_post_times.json', 'w') as f:
        json.dump({k: v.isoformat() for k, v in last_post_times.items()}, f)

def load_last_post_times():
    try:
        with open('last_post_times.json', 'r') as f:
            return json.load(f, object_hook=lambda d: {k: datetime.fromisoformat(v) for k, v in d.items()})
    except FileNotFoundError:
        return {}

last_post_times = load_last_post_times()
last_story_times = {}

def is_private(username):
    """Check if an Instagram account is private."""
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        return profile.is_private
    except instaloader.InstaloaderException as e:
        logging.error(f"Instaloader error for {username}: {e}")
        return True
    except Exception as e:
        logging.error(f"Unknown error checking profile privacy for {username}: {e}")
        return True

async def scrape_username(username):
    logging.info(f"Starting scraping for {username}.")
    channel = discord.utils.get(bot.get_all_channels(), name=config["DISCORD_CHANNEL_NAME"])
    if not channel:
        logging.warning(f"Couldn't find channel named {config['DISCORD_CHANNEL_NAME']}.")
        return

    try:
        # Check if a thread for the username exists
        thread = discord.utils.get(channel.threads, name=username)
        if not thread:
            # If not, create a thread for the username
            thread = await channel.create_thread(name=username)
            logging.info(f"Created a thread for {username}.")
            await channel.send(f"Created a new thread for `{username}` to keep track of their posts!")

        # Construct and check the story URL for the user
        story_url = f"https://instagram.com/stories/{username}/"
        response = requests.get(story_url)

        # Check if the story URL was posted in the last 24 hours
        last_story_time = last_story_times.get(username, None)
        if not last_story_time or (datetime.utcnow() - last_story_time).total_seconds() > 24 * 60 * 60:
            if response.status_code == 200:
                last_story_times[username] = datetime.utcnow()  # Update the timestamp
                await thread.send(f"Story URL for `{username}`: {story_url}")
            else:
                await thread.send(f"No stories found for `{username}`.")

        profile = instaloader.Profile.from_username(L.context, username)

        # Check the last post time for the username, if it exists
        latest_post_time = last_post_times.get(username, None)

        # Collect new posts
        for idx, post in enumerate(profile.get_posts()):
            if idx >= 50:
                break
            if not latest_post_time or post.date_utc > latest_post_time:
                last_post_times[username] = post.date_utc
                save_last_post_times()
                await thread.send(f"New post from `{username}` at {datetime.utcnow()}: {post.url}")
        
        logging.info(f"Finished scraping for {username}.")

    except instaloader.LoginRequiredException:
        logging.error(f"Instagram is requiring login to access the profile of {username}.")
    except instaloader.InstaloaderException as e:
        logging.error(f"Instaloader error for {username}: {e}")
    except Exception as e:
        logging.error(f"Unknown error scraping for {username}: {e}")

@bot.command()
async def add(ctx, username: str):
    logging.info(f"Received request to add {username}.")
    if not ctx.guild:  # Ignore DMs
        return

    if username not in config["INSTAGRAM_USERNAMES"]:
        if not is_private(username):
            config["INSTAGRAM_USERNAMES"].append(username)
            save_config()
            await ctx.send(f"Added `{username}` to the list!")
            await scrape_username(username)  # Scrape the account immediately
        else:
            await ctx.send(f"Profile `{username}` is private or an error occurred!")
    else:
        await ctx.send(f"`{username}` is already in the list!")

@bot.command()
async def remove(ctx, username: str):
    logging.info(f"Received request to remove {username}.")
    if not ctx.guild:  # Ignore DMs
        return

    if username in config["INSTAGRAM_USERNAMES"]:
        config["INSTAGRAM_USERNAMES"].remove(username)
        save_config()

        # Remove the thread associated with the username
        channel = discord.utils.get(bot.get_all_channels(), name=config["DISCORD_CHANNEL_NAME"])
        thread = discord.utils.get(channel.threads, name=username)
        if thread:
            await thread.delete()
            logging.info(f"Deleted thread for {username}.")
            
        await ctx.send(f"Removed `{username}` from the list and deleted their thread!")
    else:
        await ctx.send(f"`{username}` is not in the list!")

@bot.command()
async def list(ctx):
    if not ctx.guild:  # Ignore DMs
        return

    usernames = ", ".join(config["INSTAGRAM_USERNAMES"])
    await ctx.send(f"Currently tracking: {usernames}")

@tasks.loop(minutes=5)
async def scrape_instagram():
    logging.info("Starting the scraping loop.")
    for username in config["INSTAGRAM_USERNAMES"]:
        logging.info(f"Scraping {username}.")
        await scrape_username(username)  # Scrape asynchronously

        try:
            channel = discord.utils.get(bot.get_all_channels(), name=config["DISCORD_CHANNEL_NAME"])
            # Check if a thread for the username exists
            thread = discord.utils.get(channel.threads, name=username)
            if not thread:
                # If not, create a thread for the username
                thread = await channel.create_thread(name=username)
                logging.info(f"Created a thread for {username}.")

            profile = instaloader.Profile.from_username(L.context, username)
            
            # Get the latest 50 posts
            posts = []
            for idx, post in enumerate(profile.get_posts()):
                if idx >= 50:
                    break
                posts.append(post)

            for post in posts:
                if username not in last_post_times or post.date_utc > last_post_times[username]:
                    last_post_times[username] = post.date_utc
                    save_last_post_times()
                    await thread.send(f"New post from `{username}` at {datetime.utcnow()}: {post.url}")
                    break  # Only consider the latest post
                
        except instaloader.InstaloaderException as e:
            logging.error(f"Instaloader error for {username}: {e}")
        except Exception as e:
            logging.error(f"Unknown error scraping for {username}: {e}")

    logging.info("Finished the scraping loop.")

@bot.event
async def on_ready():
    logging.info(f'Bot is logged in as {bot.user.name}({bot.user.id})')
    scrape_instagram.start()  # Then start the regular scraping task

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid command used.")
    else:
        logging.error(f"Unexpected error: {error}")

if __name__ == "__main__":
    try:
        bot.run(config["TOKEN"])
    except KeyboardInterrupt:
        logging.info("Received interrupt. Shutting down gracefully...")
        save_last_post_times()
        save_config()  # Save last post times and other config changes on shutdown
        bot.logout()