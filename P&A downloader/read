# Spotify Playlist to Google Drive Discord Bot

A Discord bot that downloads songs from a Spotify playlist or album by searching and converting them via YouTube, then uploads the MP3 files to your Google Drive.

---

## How It Works

1. You send the bot a Spotify playlist or album URL in Discord using the command:  
   `!d <spotify_url>`

2. The bot grabs all the songs from the Spotify playlist or album.

3. For each song, it searches YouTube for the best matching video and downloads the audio as an MP3.

4. Once all songs are downloaded, the bot uploads them to a new folder in your Google Drive.

5. The bot sends you a link to the folder containing your playlist's MP3s.

---

## Requirements

- Python 3.8 or higher  
- Discord bot token (from [Discord Developer Portal](https://discord.com/developers/applications))  
- Spotify API credentials (Client ID and Client Secret)  
- YouTube Data API key  
- Google API credentials file (`client_secret.json`) for Drive API access  
- Python packages:
  - `discord.py`
  - `spotipy`
  - `google-auth-oauthlib`
  - `google-api-python-client`
  - `yt-dlp`
  - `python-dotenv`

---

## Setup Instructions

1. Clone this repository or copy the bot script.

2. Create a `.env` file in the same folder as the script with these variables:

   ```env
   SPOTIFY_CLIENT_ID=your_spotify_client_id_here
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
   YOUTUBE_API_KEY=your_youtube_api_key_here
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   GOOGLE_CLIENT_SECRETS_FILE=client_secret.json
   GOOGLE_TOKEN_PICKLE=token.pickle

NOTE

Ensure your bot has permission to read and send messages in your Discord server.

Downloads can take time depending on playlist size and YouTube availability.

Uploaded files are private to your Google Drive account.

Keep your .env file and Google credentials secure.
