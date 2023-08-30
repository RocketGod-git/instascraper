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
from random import randint
from time import sleep

# Sleep for a random number of seconds between 5 and 15
sleep(randint(5, 15))

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
import aiohttp
import asyncio
import re
import random

def sanitize_username(username):
    """Sanitizes Instagram usernames by removing characters that aren't alphanumeric, underscores, or periods."""
    return re.sub(r'[^a-zA-Z0-9_.]', '', username)

async def fetch_profile(username):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, instaloader.Profile.from_username, L.context, username)

# Initialize instaloader
L = instaloader.Instaloader()

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

class MyRateController(instaloader.RateController):
    def sleep(self, secs):
        # Add a random sleep time to further avoid detection
        sleep_time = secs + random.randint(1, 5)
        logging.info(f"Sleeping for {sleep_time} seconds due to rate limits.")
        super().sleep(sleep_time)

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

async def check_profile(username):
    """Check if an Instagram account is private or doesn't exist."""
    username = sanitize_username(username) 
    try:
        profile = await fetch_profile(username)
        return True, "private" if profile.is_private else "public"
    except instaloader.ProfileNotExistsException:
        return False, "nonexistent"
    except instaloader.InstaloaderException as e:
        logging.error(f"Instaloader error for {username}: {e}")
        return False, "error"
    except Exception as e:
        logging.error(f"Unknown error checking profile privacy for {username}: {e}")
        return False, "error"

async def scrape_posts_for_user(username, send_all=False):
    try:
        profile = await fetch_profile(username)
        posts_urls = []
        for idx, post in enumerate(profile.get_posts()):
            if idx >= 50:
                break
            
            # If send_all is True, send all posts. Otherwise, only send new posts.
            if send_all or username not in last_post_times or post.date_utc > last_post_times[username]:
                last_post_times[username] = post.date_utc
                posts_urls.append(f"Post from `{username}` at {datetime.utcnow()}: {post.url}")

        if posts_urls:
            save_last_post_times()
            thread = await get_thread_for_user(username)
            for post_url in posts_urls:  # Send each post URL separately
                await thread.send(post_url)
                await asyncio.sleep(2)  # Add a 2-second delay between each send to avoid rate limits
    except instaloader.InstaloaderException as e:
        logging.error(f"Instaloader error for {username}: {e}")
    except Exception as e:
        logging.error(f"Unknown error scraping for {username}: {e}")
   
async def get_thread_for_user(username):
    channel = discord.utils.get(bot.get_all_channels(), name=config["DISCORD_CHANNEL_NAME"])
    thread = discord.utils.get(channel.threads, name=username)
    if not thread:
        thread = await channel.create_thread(name=username)
        logging.info(f"Created a thread for {username}.")
    return thread

async def scrape_username(username):
    logging.info(f"Starting scraping for {username}.")
    
    thread = await get_thread_for_user(username)  # Get the thread here
    
    if not thread:
        logging.warning(f"Couldn't find or create thread for {username}.")
        return

    await scrape_posts_for_user(username)

    try:
        async with aiohttp.ClientSession() as session:  # Using aiohttp
            story_url = f"https://instagram.com/stories/{username}/"  # Define the story_url
            async with session.get(story_url) as response:
                if response.status == 200:
                    last_story_times[username] = datetime.utcnow()  # Update the timestamp
                    await thread.send(f"Possible Story URL for `{username}`: {story_url}")
                else:
                    logging.info(f"No stories found for `{username}`. Status code: {response.status_code}")

                # Check if the story URL was posted in the last 24 hours
                last_story_time = last_story_times.get(username, None)
                if not last_story_time or (datetime.utcnow() - last_story_time).total_seconds() > 24 * 60 * 60:
                    if response.status_code == 200:
                        last_story_times[username] = datetime.utcnow()  # Update the timestamp
                        await thread.send(f"Story URL for `{username}`: {story_url}")
                    else:
                        await thread.send(f"No stories found for `{username}`.")

                profile = await fetch_profile(username)(L.context, username)

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
        success, status = await check_profile(username) 
        if success and status == "public":
            config["INSTAGRAM_USERNAMES"].append(username)
            save_config()
            await ctx.send(f"Added `{username}` to the list!")
            await scrape_posts_for_user(username, send_all=True) 
        elif status == "private":
            await ctx.send(f"Profile `{username}` is private. Cannot add!")
        elif status == "nonexistent":
            await ctx.send(f"Profile `{username}` does not exist. Cannot add!")
        else:
            await ctx.send(f"An error occurred while checking the profile `{username}`. Please try again later.")
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

        # Remove the last scrape time for the username
        if username in last_post_times:
            del last_post_times[username]
            save_last_post_times()
            logging.info(f"Removed last scrape time for {username}.")
            
        await ctx.send(f"Removed `{username}` from the list and deleted their thread!")
    else:
        await ctx.send(f"`{username}` is not in the list!")

@bot.command()
async def list(ctx):
    if not ctx.guild:  # Ignore DMs
        return

    usernames = ", ".join(config["INSTAGRAM_USERNAMES"])
    await ctx.send(f"Currently tracking: {usernames}")

@tasks.loop(minutes=30)
async def scrape_instagram():
    logging.info("Starting the scraping loop.")
    for username in config["INSTAGRAM_USERNAMES"]:
        retries = 3
        while retries > 0:
            try:
                logging.info(f"Scraping {username}.")
                await scrape_posts_for_user(username)
                await asyncio.sleep(random.randint(10, 30))
                break
            except instaloader.InstaloaderException as e:
                logging.warning(f"Instaloader error for {username}. Retries left: {retries}. Error: {str(e)}")
            except Exception as e:
                logging.warning(f"Unexpected error scraping {username}. Retries left: {retries}. Error: {str(e)}")
            retries -= 1
            await asyncio.sleep(random.randint(10, 30))
    logging.info("Finished the scraping loop.")

@bot.event
async def on_ready():
    logging.info(f'Bot is logged in as {bot.user.name}({bot.user.id})')
    if not scrape_instagram.is_running():
        scrape_instagram.start()
        logging.info("Scrape task has been started.")

if __name__ == "__main__":
    try:
        bot.run(config["TOKEN"])
    except KeyboardInterrupt:
        logging.info("Received interrupt. Shutting down gracefully...")
        save_last_post_times()
        save_config()  # Save last post times and other config changes on shutdown
        bot.logout()