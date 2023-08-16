# InstaScraper Discord Bot

InstaScraper is a Discord bot that tracks Instagram user posts and stories and notifies a designated Discord channel. Keep track of your favorite influencers, friends, or anyone you wish to follow on Instagram, right from your Discord server. Great for OSINT. 
Each user gets their own thread in your specified channel. Updates every 5 minutes.

### IMPORTANT! Use a VPN to avoid IP Bans!

## Table of Contents
1. [Features](#features)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Contributing](#contributing)
6. [License](#license)

## Features
- **Track Instagram Users**: Add and remove users to track their posts and stories.
- **Real-Time Notifications**: Receive notifications for new posts and stories in a designated Discord channel.
- **Instagram Profile Privacy Check**: Ensures that the profile is public to track.
- **Persistent Data**: Remembers the last post time even after bot restarts to avoid duplicate notifications.
- **Customizable**: Easily configurable to suit your specific needs and preferences.

## Installation
Follow the steps below to set up the bot on your system:

### Prerequisites
- Python 3.6 or higher
- `discord.py`
- `instaloader`

### Step-by-Step Guide
1. **Clone the repository**:
   ```bash
   git clone https://github.com/RocketGod-git/instascraper.git
   cd instascraper
   ```

2. **Install dependencies**:
   ```bash
   Automatically installs required packages!
   ```

3. **Configure the bot** by editing the `config.json` file. [See the configuration section](#configuration) for details.

4. **Run the bot**:
   ```bash
   python bot.py
   ```

## Configuration
You will need to modify the `config.json` file to include your specific details:

```json
{
  "TOKEN": "YOUR_DISCORD_BOT_TOKEN",
  "DISCORD_CHANNEL_NAME": "channel-name",
  "INSTAGRAM_USERNAMES": ["username1", "username2"]
}
```
- **TOKEN**: Your Discord bot token.
- **DISCORD_CHANNEL_NAME**: The name of the channel where the bot will send notifications.
- **INSTAGRAM_USERNAMES**: An array of Instagram usernames you want to track initially. Leave the usernames blank [] or prefill some if you want.

## Usage
Once the bot is running, you can use the following commands:

- `!add <username>`: Add an Instagram username to track.
- `!remove <username>`: Remove an Instagram username from tracking.
- `!list`: List all tracked Instagram usernames.

## Contributing
I always welcome contributions! If you'd like to contribute, please follow the standard GitHub fork & pull request process. If you have any specific questions or need guidance, feel free to create an issue.

## License
This project is licensed under the GNU License - see the [LICENSE.md](LICENSE.md) file for details.
