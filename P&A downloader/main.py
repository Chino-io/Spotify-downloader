import os
from dotenv import load_dotenv
import re
import shutil
import tempfile
import discord
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http
import google.auth.transport.requests
import pickle

from googleapiclient.discovery import build
import yt_dlp
import asyncio

# === Load environment variables ===
load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE")
GOOGLE_TOKEN_PICKLE = os.getenv("GOOGLE_TOKEN_PICKLE")

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === Spotify Setup ===
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# === YouTube Search function ===
def search_youtube_video(query):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(
        q=query,
        part='id,snippet',
        maxResults=1,
        type='video'
    )
    response = request.execute()
    items = response.get('items')
    if not items:
        print(f"No YouTube results for: {query}")
        return None
    video_id = items[0]['id']['videoId']
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Search result for '{query}': {video_url}")
    return video_url

# === Google Drive Authentication and Upload ===
def google_drive_authenticate():
    creds = None
    if os.path.exists(GOOGLE_TOKEN_PICKLE):
        with open(GOOGLE_TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                GOOGLE_CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_console()
        with open(GOOGLE_TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def upload_file_to_drive(file_path, drive_service, folder_id=None):
    file_metadata = {'name': os.path.basename(file_path)}
    if folder_id:
        file_metadata['parents'] = [folder_id]
    media = googleapiclient.http.MediaFileUpload(file_path, mimetype='audio/mpeg')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    print(f"Uploaded {file_path} with ID {file['id']}")
    return file.get('webViewLink')

def create_drive_folder(name, drive_service):
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    print(f"Created folder '{name}' with ID {folder['id']}")
    return folder['id']

# === Spotify playlist & album scraping ===
def extract_id_and_type(url):
    m_playlist = re.search(r'playlist/([a-zA-Z0-9]+)', url)
    if m_playlist:
        return 'playlist', m_playlist.group(1)
    m_album = re.search(r'album/([a-zA-Z0-9]+)', url)
    if m_album:
        return 'album', m_album.group(1)
    return None, None

def scrape_spotify_playlist(playlist_id):
    results = sp.playlist_items(playlist_id)
    tracks = results['items']
    songs = []
    for item in tracks:
        track = item['track']
        name = track['name']
        artists = ", ".join([artist['name'] for artist in track['artists']])
        songs.append(f"{artists} - {name}")
    return songs

def scrape_spotify_album(album_id):
    results = sp.album_tracks(album_id)
    tracks = results['items']
    songs = []
    for track in tracks:
        name = track['name']
        artists = ", ".join([artist['name'] for artist in track['artists']])
        songs.append(f"{artists} - {name}")
    return songs

# === yt-dlp progress tracking ===
current_progress = {
    'index': 0,
    'total': 0,
    'title': '',
    'percent': 0,
}

def yt_dlp_progress_hook(d):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', 1)
        current_progress['percent'] = downloaded / total * 100 if total else 0
    elif d['status'] == 'finished':
        current_progress['percent'] = 100

async def download_song(yt_url, out_dir, song_index, total_songs):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(out_dir, '%(title).80s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'progress_hooks': [yt_dlp_progress_hook],
        'quiet': True,
        'no_warnings': True,
    }

    global current_progress
    current_progress['index'] = song_index
    current_progress['total'] = total_songs
    current_progress['percent'] = 0
    current_progress['title'] = ''

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(yt_url, download=False)
        current_progress['title'] = info_dict.get('title', 'Unknown title')
        ydl.download([yt_url])

    current_progress['percent'] = 100

async def update_status_message(status_message):
    while True:
        if current_progress['title']:
            percent_str = f"{current_progress['percent']:.1f}%"
            text = (f"🎧 Downloading song {current_progress['index']}/{current_progress['total']}: "
                    f"**{current_progress['title']}** - {percent_str}")
            try:
                await status_message.edit(content=text)
            except Exception:
                pass
            if current_progress['percent'] >= 100:
                break
        await asyncio.sleep(1)

# === Discord Bot Events ===
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("!d "):
        try:
            await message.delete()
        except Exception:
            pass

        url = message.content[3:].strip()
        if not url.startswith("http"):
            await message.channel.send(f"{message.author.mention} ❌ Invalid URL.")
            return

        type_, id_ = extract_id_and_type(url)
        if not type_ or not id_:
            await message.channel.send(f"{message.author.mention} ❌ Could not find playlist or album ID in URL.")
            return

        status_message = await message.channel.send(f"📥 Received playlist/album request from {message.author.mention}...")

        if type_ == 'playlist':
            songs = scrape_spotify_playlist(id_)
        else:
            songs = scrape_spotify_album(id_)

        if not songs:
            await status_message.edit(content=f"{message.author.mention} ❌ No songs found in the {type_}.")
            return

        temp_dir = tempfile.mkdtemp()
        total_songs = len(songs)

        if type_ == 'playlist':
            playlist_info = sp.playlist(id_)
            folder_name = playlist_info['name']
        else:
            album_info = sp.album(id_)
            folder_name = album_info['name']

        folder_id = None
        try:
            creds = google_drive_authenticate()
            drive_service = googleapiclient.discovery.build('drive', 'v3', credentials=creds)
            folder_id = create_drive_folder(folder_name, drive_service)
        except Exception as e:
            await status_message.edit(content=f"{message.author.mention} ❌ Failed to authenticate/upload: {e}")
            shutil.rmtree(temp_dir)
            return

        for i, song in enumerate(songs, start=1):
            yt_url = search_youtube_video(song)
            if yt_url:
                download_task = asyncio.create_task(download_song(yt_url, temp_dir, i, total_songs))
                update_task = asyncio.create_task(update_status_message(status_message))

                await download_task
                await update_task
            else:
                print(f"Skipping (no YouTube result): {song}")

        await status_message.edit(content=f"⬆️ All songs downloaded. Uploading to Google Drive folder '{folder_name}'...")

        uploaded_links = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".mp3"):
                    file_path = os.path.join(root, file)
                    link = upload_file_to_drive(file_path, drive_service, folder_id=folder_id)
                    if link:
                        uploaded_links.append(link)

        shutil.rmtree(temp_dir)

        if uploaded_links:
            embed = discord.Embed(
                title="Your playlist is here",
                description=f"[Playlist](https://drive.google.com/drive/folders/{folder_id})",
                color=discord.Color.green()
            )
            await status_message.edit(content=f"{message.author.mention}", embed=embed)
        else:
            await status_message.edit(content=f"{message.author.mention} ❌ Upload failed for all songs.")

    await bot.process_commands(message)


# === Run the bot ===
bot.run(DISCORD_BOT_TOKEN)
