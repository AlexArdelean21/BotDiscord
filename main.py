import discord
from discord.ext import commands
import asyncio
import yt_dlp

# Define bot and intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Queue to store up to 20 songs
song_queue = []
MAX_QUEUE_SIZE = 20
loop_song = False
current_song = None


# Play command to handle single YouTube videos or playlists
@bot.command(name='play')
async def play(ctx, *, url):
    global current_song
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("You need to be in a voice channel to play music.")
        return

    if len(song_queue) >= MAX_QUEUE_SIZE:
        await ctx.send(f"The queue is full. Maximum {MAX_QUEUE_SIZE} songs are allowed.")
        return

    # Detect if the URL is a playlist
    ydl_opts = {'quiet': True, 'extract_flat': True, 'playlistend': MAX_QUEUE_SIZE - len(song_queue)}  # Limit to max queue size
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:  # It's a playlist
                for video in info['entries']:
                    song_queue.append(video['url'])
                    await ctx.send(f"Added {video['title']} to the queue.")
            else:  # It's a single video
                song_queue.append(url)
                await ctx.send(f"Added {info['title']} to the queue.")
        except Exception as e:
            await ctx.send(f"Error adding song or playlist: {str(e)}")
            return

    # If nothing is currently playing, start playing the first song
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice_client or not voice_client.is_playing():
        current_song = song_queue.pop(0)
        await play_next_song(ctx)


# Helper function to play the next song from the queue
async def play_next_song(ctx):
    global current_song, loop_song

    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client is None:
        voice_channel = ctx.author.voice.channel
        voice_client = await voice_channel.connect()

    if loop_song and current_song:
        url = current_song
    elif len(song_queue) > 0:
        url = song_queue.pop(0)
        current_song = url
    else:
        await ctx.send("No more songs in the queue.")
        return

    ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        url2 = info['url']
        title = info.get('title', 'Unknown Title')

    source = await discord.FFmpegOpusAudio.from_probe(url2, method='fallback')

    def after_playing(error):
        if not loop_song:
            coro = play_next_song(ctx)
        else:
            coro = asyncio.sleep(0)  # No-op for the loop
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except:
            pass

    voice_client.play(source, after=after_playing)
    await ctx.send(f"Now playing: **{title}**")


# Skip or next command to skip the current song
@bot.command(name='skip')
async def skip(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()  # This will trigger the `after_playing` callback to play the next song
        await ctx.send("Skipping to the next song.")
    else:
        await ctx.send("There is no song currently playing.")


# Leave command to disconnect the bot from the voice channel
@bot.command(name='leave')
async def leave(ctx):
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client:
        await voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("The bot is not connected to any voice channel.")


# Repeat command to repeat the current song
@bot.command(name='repeat')
async def repeat(ctx):
    global current_song
    if current_song:
        song_queue.insert(0, current_song)
        await ctx.send("The current song will be repeated.")
    else:
        await ctx.send("No song is currently playing to repeat.")


# Loop command to loop the current song indefinitely
@bot.command(name='loop')
async def loop(ctx):
    global loop_song, song_queue
    if len(song_queue) == 0 and current_song:
        loop_song = not loop_song
        if loop_song:
            await ctx.send("Looping the current song indefinitely.")
        else:
            await ctx.send("Looping stopped.")
    else:
        await ctx.send("Loop only works if there are no other songs in the queue.")


# Help command to list available commands
@bot.command(name='helpme')
async def help_command(ctx):
    help_text = """
    **Available Commands:**
    `!play <YouTube URL or Playlist URL>` - Adds a song or playlist to the queue and plays it.
    `!skip` or `!next` - Skips the current song and plays the next one.
    `!leave` - Makes the bot leave the voice channel.
    `!repeat` - Repeats the current song next in the queue.
    `!loop` - Loops the current song indefinitely if the queue is empty.
    """
    await ctx.send(help_text)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


# Run the bot with your token
bot.run('???')
