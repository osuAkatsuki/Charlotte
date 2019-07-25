import discord
from discord.ext import commands
import mysql.connector
from mysql.connector import errorcode
import time
import asyncio

import json
import requests

# TODO: stop using these!
from colorama import init
from colorama import Fore, Back, Style

# Initialize colorama.
init(autoreset=True)

# Initalize values as None for now.
SQL_HOST, SQL_USER, SQL_PASS, SQL_DB = [None] * 4

# Config.
config = open('config.ini', 'r')
config_contents = config.read().split("\n")
for line in config_contents:
    line = line.split("=")
    if line[0].strip() == "SQL_HOST": # IP Address for SQL.
        SQL_HOST = line[1].strip()
    elif line[0].strip() == "SQL_USER": # Username for SQL.
        SQL_USER = line[1].strip()
    elif line[0].strip() == "SQL_PASS": # Password for SQL.
        SQL_PASS = line[1].strip()
    elif line[0].strip() == "SQL_DB": # DB name for SQL.
        SQL_DB = line[1].strip()
    else: # Config value is unknown. continue iterating anyways.
        continue

# MySQL.
try:
    cnx = mysql.connector.connect(
        user       = SQL_USER,
        password   = SQL_PASS,
        host       = SQL_HOST,
        database   = SQL_DB,
        autocommit = True)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your username or password.")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist.")
    else:
        print(err)
else:
    SQL = cnx.cursor()

# Subsystem versions.
AIKA_VERSION = 4.19 # Aika (This bot).
ABNS_VERSION = 2.11 # Akatsuki's Beatmap Nomination System (#rank-request(s)).

# Akatsuki's server/channel IDs.
# [S] = Server.
# [T] = Text channel.
# [V] = Voice channel.
AKATSUKI_SERVER_ID           = 365406575893938177 # [S] | ID for osu!Akatsuki.
AKATSUKI_GENERAL_ID          = 592490140497084436 # [T] | ID for #general.
AKATSUKI_HELP_ID             = 365413867167285249 # [T] | ID for #help.
AKATSUKI_VERIFY_ID           = 596662084339761172 # [T] | ID for #verify.
AKATSUKI_PLAYER_REPORTING_ID = 367068661837725706 # [T] | ID for #player_reporting.
AKATSUKI_REPORTS_ID          = 367080772076568596 # [T] | ID for #reports.
AKATSUKI_NSFW_STRAIGHT_ID    = 428460752698081291 # [T] | ID for #nsfw.
AKATSUKI_NSFW_TRAPS_ID       = 505960162411020288 # [T] | ID for #nsfw-traps.
AKATSUKI_RANK_REQUEST_ID     = 597200076561055795 # [T] | ID for #rank-request (User).
AKATSUKI_RANK_REQUESTS_ID    = 557095943602831371 # [T] | ID for #rank-requests (Staff).
AKATSUKI_BOTSPAM_ID          = 369829943372152833 # [T] | ID for #botspam.

AKATSUKI_FRIENDS_ONLY        = 597948877621952533 # [T] | ID for #friends-only.
AKATSUKI_DRAG_ME_IN_VOICE    = 597949535938936833 # [V] | ID for Drag me in (VC).
AKATSUKI_FRIENDS_ONLY_VOICE  = 597948898421768192 # [V] | ID for ✨cmyui (VC).

# Aika's command prefix.
COMMAND_PREFIX = '!'

# Akatsuki's logo.
# To be used mostly for embed thumbnails.
AKATSUKI_LOGO = "https://akatsuki.pw/static/logos/logo.png"
CRAB_EMOJI    = "https://cdn.discordapp.com/attachments/365406576548511745/591470256497754112/1f980.png"

# A list of filters.
# These are to be used to wipe messages that are deemed inappropriate,
# or break rules. For the most part, these are of other private servers,
# as required by rule #2 of the Akatsuki Discord & Chat Rules
# (https://akatsuki.pw/doc/rules).
filters       = [
                # Paypal
                "https://pp.me", "http://pp.me", "https://paypal.me", "http://paypal.me",

                # osu! private servers
                "yozora", "ainu", "okamura", "kotorikku", "kurikku", "kawata",
                "ryusei", "ryu-sei", "enjuu", "verge", "katori", "osu-thailand",
                "gatari", "hidesu", "hiragi", "asuki", "mikoto", "homaru", "awasu",
                "vipsu", "xii", "xii.nz", "yarota", "silverosu", "sugoisu", "kono",
                "zeltu", "karizuku", "koreasu", "asta", "tiller", # I really didn't want to block "tiller", but it seems like it keeps getting mentioned..

                # osu! cheating programs
                "aqn", "hq", "hqosu", "aquila",

                # Discord links
                "https://discord.gg/", "http://discord.gg/", "https://discordapp.com/channels", "http://discordapp.com/channels",

                # Bad boy substances
                "lsd", "dmt", "shrooms"
                ]

# A list of message (sub)strings that we will use to deem
# a quantifiable value for the "quality" of a message.
profanity     = ["nigg", "n1gg", "retard", "idiot",
                 "fuck off", "shut the fuck up", "??"]

high_quality  = ["!faq", "!help", "welcome", "have a good", "enjoy", "no problem",
                 "of course", "can help", "i can", "how can i help you"]

# Assign discord owner value.
SQL.execute("SELECT value_string FROM aika_settings WHERE name = 'discord_owner'")
discord_owner = int(SQL.fetchone()[0])


def debug_print(string):
    """
    Print a debug message to the console.

    Example in use:      https://nanahira.life/dOgXljmmKW336gro3Ts5gJmU7P4hNDZz.png

    :param string:       The message to be printed to the console.
    """

    # Debug value
    SQL.execute("SELECT value_int FROM aika_settings WHERE name = 'debug'")
    debug = SQL.fetchone()[0]

    if debug:
        print(f"{Fore.MAGENTA}\n{string}\n")


def get_prefix(client, message):

    prefixes = [COMMAND_PREFIX] # More prefixes can be added to this

    # Users can also mention the bot.
    return commands.when_mentioned_or(*prefixes)(client, message)

client = discord.Client()
bot = commands.Bot(
    command_prefix   = get_prefix,
    description      = "Aika - osu!Akatsuki's official Discord bot.",
    owner_id         = discord_owner,
    case_insensitive = True # No case sensitivity on commands
)


cogs = ["cogs.staff", "cogs.user"]


@bot.event
async def on_voice_state_update(member, before, after): # TODO: check if they left dragmein, and delete embed.. if that's even possible..
    # Await for the bot to be ready before processing voice state updates whatsoever.
    await bot.wait_until_ready()

    # Only use this event for the "drag me in" voice channel.
    if after.channel is None or after.channel.id != AKATSUKI_DRAG_ME_IN_VOICE:
        return

    debug_print(f"on_voice_state_update event fired.\n\nData:\n\n{member}\n\n{before}\n\n{after}")

    # Create our vote embed.
    embed = discord.Embed(
        title       = f"{member} wants to be dragged in.",
        description = "Please add a reaction to determine their fate owo..",
        color       = 0x00ff00)

    embed.set_footer(icon_url=CRAB_EMOJI, text="Only one vote is required.")
    embed.set_thumbnail(url=AKATSUKI_LOGO)

    # Assign friends-only chat and voice channel as constants.
    FRIENDS_ONLY_TEXT  = bot.get_channel(AKATSUKI_FRIENDS_ONLY)
    FRIENDS_ONLY_VOICE = bot.get_channel(AKATSUKI_FRIENDS_ONLY_VOICE)

    # Send our embed, and add our base 👍.
    msg = await FRIENDS_ONLY_TEXT.send(embed=embed)
    await msg.add_reaction("👍")

    def check(reaction, user):
        if user == bot.user: return False
        return reaction.emoji == "👍" and user.voice.channel == FRIENDS_ONLY_VOICE

    try: # Wait for a 👍 from a "friend". Timeout: 5 minutes (300 seconds).
        reaction, user = await bot.wait_for("reaction_add", timeout=300.0, check=check)
    except asyncio.TimeoutError: # Timed out. Remove the embed.
        await FRIENDS_ONLY_TEXT.send(f"Timed out {member}'s join query.")
        await msg.delete()
        return

    try: # Actually move the member into friends voice channel.
        await member.move_to(channel=FRIENDS_ONLY_VOICE, reason="Voted in.")
    except discord.errors.HTTPException: # The user has already left the "drag me in" voice channel.
        await msg.delete()
        return

    # Send our vote success, and delete the original embed.
    await FRIENDS_ONLY_TEXT.send(f"{user} voted {member} in.")
    await msg.delete()
    return

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} - {bot.user.id}")
    await bot.change_presence(activity=discord.Game(name="osu!Akatsuki", url="https://akatsuki.pw/", type=1))
    for cog in cogs:
        bot.load_extension(cog)

    # Announce online status to #general if we're on a server build of Aika.
    SQL.execute("SELECT value_int FROM aika_settings WHERE name = 'server_build'")
    server_build = bool(SQL.fetchone()[0])

    if server_build:
        # Get the server's latest version of Aika run.
        SQL.execute("SELECT value_int FROM aika_settings WHERE name = 'version_latest'")
        version_latest = SQL.fetchone()[0]

        SQL.execute("UPDATE aika_settings SET value_int = %s WHERE name = 'version_latest'", [AIKA_VERSION])

        # If the server version mismatches the version of the code, display the update.
        if version_latest != AIKA_VERSION:
            announce_title = f"Aika has been updated to v{AIKA_VERSION}. (Previous: v{version_latest})"
        else:
            announce_title = f"Aika v{AIKA_VERSION} Online"

        # Configure, and send the embed to #general.
        announce_online = discord.Embed(
            title       = announce_title,
            description = "Ready for commands <3\n\nAika is osu!Akatsuki's [open source](https://github.com/osuAkatsuki/Aika) "
                          "discord bot.\n\n[Akatsuki](https://akatsuki.pw)\n[Support Akatsuki](https://akatsuki.pw/support)",
            color       = 0x00ff00)

        announce_online.set_footer(icon_url=CRAB_EMOJI, text="Thank you for playing!")
        announce_online.set_thumbnail(url=AKATSUKI_LOGO)
        await bot.get_channel(AKATSUKI_GENERAL_ID).send(embed=announce_online)
    return


@bot.event
async def on_message(message):
    # Await for the bot to be ready before processing messages whatsoever.
    await bot.wait_until_ready()

    # The message has no content.
    # Don't bother doing anything with it.
    if not message.content:
        return

    if message.author.id != discord_owner: # Regular user
        if message.content.lower().split(' ')[0][1:7] == "verify" and message.channel.id == AKATSUKI_VERIFY_ID: # Verify command.
            await message.author.add_roles(discord.utils.get(message.guild.roles, name="Members"))
            await message.delete()
            return
        
        # Prevent client crashing.. or atleast try a little bit.
        if not all(ord(char) < 128 for char in message.content) and len(message.content) > 1500:
            await message.delete()
            return

    else: # Owner

        if message.content.split(' ')[0][1:] == "reload":
            cog_name = message.content.split(' ')[1].lower()
            if cog_name in ("staff", "user"):
                bot.reload_extension(f"cogs.{cog_name}")
                await message.channel.send(f"Reloaded extension {cog_name}.")
            else:
                await message.channel.send(f"Invalid extension {cog_name}.")
            return


    if message.channel.id in (AKATSUKI_NSFW_STRAIGHT_ID, AKATSUKI_NSFW_TRAPS_ID):
        def check_content(m): # Don't delete links or images.
            if "http" in message.content or message.attachments:
                return False
            return True

        if check_content(message):
            await message.delete()
        return


    # Message sent in #rank-request, move to #rank-requests.
    if message.channel.id == AKATSUKI_RANK_REQUEST_ID:
        await message.delete()

        if not any(required in message.content for required in ("akatsuki.pw", "osu.ppy.sh")) or len(message.content) > 29: # Should not EVER be over 29 characters.
            await message.author.send("Your beatmap request was incorrectly formatted, and thus has not been submitted. Please use the old osu links for the time being. (e.g. https://osu.ppy.sh/b/123)")
            return

        # TODO: New osu link support.
        if "://" in message.content: # Support both links like "https://osu.ppy.sh/b/123" AND "osu.ppy.sh/b/123". Also allow both /s/ and /b/ links.
            partitions = message.content.split("/")[3:]
        else:
            partitions = message.content.split("/")[1:]

        beatmapset = partitions[0] == "s" # Link is a beatmapset_id link, not a beatmap_id link.
        map_id = partitions[1] # Can be SetID or MapID.

        if not beatmapset: # If the user used a /b/ link, let's turn it into a set id.
            SQL.execute("SELECT beatmapset_id FROM beatmaps WHERE beatmap_id = %s LIMIT 1", [map_id])
            map_id = SQL.fetchone()[0]

        # Do this so we can check if any maps in the set are ranked or loved.
        # If they are, the QAT have most likely already determined statuses of the map.
        SQL.execute("SELECT mode, ranked FROM beatmaps WHERE beatmapset_id = %s ORDER BY ranked DESC LIMIT 1", [map_id])
        sel = SQL.fetchone()

        if not sel: # We could not find any matching rows with the map_id.
            await message.author.send("That map seems to be invalid. Quoi?")
            return

        mode, status = sel

        if status in (2, 5): # Map is already ranked/loved
            await message.author.send(f"Some (or all) of the difficulties in the beatmap you requested already seem to be {'ranked' if status == 2 else 'loved'} "
                                       "on the Akatsuki server!\n\nIf this is false, please contact a QAT directly to proceed.")
            return

        # Sort out mode to be used to check difficulty.
        # Also have a formatted one to be used for final post.
        if mode == 0: mode, mode_formatted = "std", "osu!"
        elif mode == 1: mode, mode_formatted = "taiko", "osu!taiko"
        elif mode == 2: mode, mode_formatted = "ctb", "osu!catch"
        else: mode, mode_formatted = "mania", "osu!mania"

        # Select map information.
        SQL.execute(f"SELECT song_name, ar, od, max_combo, bpm, difficulty_{mode} FROM beatmaps WHERE beatmapset_id = %s ORDER BY difficulty_{mode} DESC LIMIT 1", [map_id])
        bdata = SQL.fetchone()

        # Return values from web request/DB query.
        # TODO: either use the API for everything, or dont use it at all.
        artist = json.loads(requests.get(f"https://cheesegull.mxr.lol/api/s/{map_id}").text)["Creator"]
        song_name, ar, od, max_combo, bpm, star_rating = bdata

        # Create embeds.
        embed = discord.Embed(
            title       = "A new beatmap request has been recieved.",
            description = "** **",
            color       = 5516472 # Akatsuki purple.
        )

        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{map_id}/covers/cover.jpg?1522396856")
        embed.set_author(name=song_name, url=f"https://akatsuki.pw/d/{map_id}", icon_url=AKATSUKI_LOGO)
        embed.set_footer(text=f"Akatsuki's beatmap nomination system v{ABNS_VERSION}", icon_url="https://nanahira.life/MpgDe2ssQ5zDsWliUqzmQedZcuR4tr4c.jpg")
        embed.add_field(name="Nominator", value=message.author.name)
        embed.add_field(name="Mapper", value=artist)
        embed.add_field(name="Gamemode", value=mode_formatted)
        embed.add_field(name="Highest SR", value="%.2f*" % round(star_rating, 2))
        embed.add_field(name="Highest AR", value=ar)
        embed.add_field(name="Highest OD", value=od)
        embed.add_field(name="Highest Max Combo", value=f"{max_combo}x")
        embed.add_field(name="BPM", value=bpm)

        # Prepare, and send the report to the reporter.
        embed_dm = discord.Embed(
            title       = "Your beatmap nomination request has been sent to Akatsuki's Quality Assurance Team for review.",
            description = "We will review it shortly.",
            color       = 0x00ff00 # Lime green.
        )

        embed_dm.set_thumbnail(url=AKATSUKI_LOGO)
        embed_dm.set_image(url=f"https://assets.ppy.sh/beatmaps/{map_id}/covers/cover.jpg?1522396856")
        embed_dm.set_footer(text=f"Akatsuki's beatmap nomination system v{ABNS_VERSION}", icon_url="https://nanahira.life/MpgDe2ssQ5zDsWliUqzmQedZcuR4tr4c.jpg")

        # Send the embed to the #rank_requests channel.
        request_post = await bot.get_channel(AKATSUKI_RANK_REQUESTS_ID).send(embed=embed)

        # Send the embed to the nominator by DM. 
        try: # TODO: check if we can message the user rather than abusing try-except.
            await message.author.send(embed=embed_dm)
        except:
            print(f"Could not DM ({message.author.name}).")

        for i in ["👎", "👍"]: # Add thumbs.
            await request_post.add_reaction(i)
        return


    # Message sent in #player-reporting, move to #reports.
    if message.channel.id == AKATSUKI_PLAYER_REPORTING_ID:
        await message.delete() # Delete the message from #player-reporting.

        # Prepare, and send the report in #reports.
        embed = discord.Embed(title="New report recieved.", description="** **", color=0x00ff00)
        embed.set_thumbnail(url=AKATSUKI_LOGO)
        embed.add_field(name="Report content", value=message.content, inline=True)
        embed.add_field(name="Author", value=message.author.mention, inline=True)

        # Prepare, and send the report to the reporter.
        embed_pm = discord.Embed(title="Thank you for the player report.", description="We will review the report shortly.", color=0x00ff00)

        embed_pm.add_field(name="Report content", value=message.content, inline=True)
        embed_pm.set_thumbnail(url=AKATSUKI_LOGO)

        if not message.content.startswith(COMMAND_PREFIX): # Do not pm or link to #reports if it is a command.
            await message.author.send(embed=embed_pm)
            await bot.get_channel(AKATSUKI_REPORTS_ID).send(embed=embed)
        return

    elif message.author != bot.user and message.guild:

        # Message sent in #help, log to db.
        if message.channel.id == AKATSUKI_HELP_ID:
            # Split the content into sentences by periods.
            # TODO: Other punctuation marks!
            sentence_split = message.content.split(".")

            # Default values for properly formatted messages / negative messages.
            properly_formatted, negative = [False] * 2

            debug_print(f"Sentence split: {sentence_split}")

            # After every period, check they have a space and the next sentence starts with a capital letter (ignore things like "...").
            for idx, sentence in enumerate(sentence_split):
                if len(sentence) > 1 and idx != 0:
                    if sentence[0] == " " and sentence[1].isupper():
                        continue
                    negative = True

            properly_formatted = message.content[0].isupper() and message.content[len(message.content) - 1] in (".", "?", "!") and not negative

            # Default for quality. 1 : normal message.
            quality = 1

            # The user used profanity in their message.
            # Flag it as 'low quality' content.
            if any(x in message.content.lower() for x in profanity):
                quality = 0
            # The user either used content deemed 'high quality' in their message, and/or properly formatted their message.
            # Flag it as 'high quality' content.
            elif any(x in message.content.lower() for x in high_quality) or properly_formatted:
                quality = 2

            debug_print(f"Quality of message\n\n{message.author}: {message.content} - {quality}")

            # TODO: Store the whole bitch in a single number. 
            # Maybe even do some bitwise black magic shit.
            SQL.execute("INSERT INTO help_logs (id, user, content, datetime, quality) VALUES (NULL, %s, %s, %s, %s)",
                [message.author.id, message.content.encode('ascii', errors='ignore'), time.time(), quality])

        # Ignore moderators for the following flagging.
        if not message.author.guild_permissions.manage_messages:
            # Split the message up word by word to avoid problems.
            for split in message.content.lower().split(" "):
                # Scan for filters, word by word.
                if any(split.startswith(individual_filter) for individual_filter in filters):
                    # Delete the message from the server.
                    await message.delete()

                    await message.author.send(
                        "Hello,\n\nYour message in osu!Akatsuki has been removed as it has been deemed "
                        "unsuitable.\n\nIf you have any questions, please ask <@285190493703503872>. "
                        "\n**Do not try to evade this filter as it is considered fair ground for a ban**."
                        f"\n\n```{message.content.replace('`', '')}: {message.content.replace('`', '')}```")

                    debug_print(f"Filtered message | '{message.author}: {message.content}'")

                    SQL.execute("INSERT INTO profanity_logs (id, user, content, datetime) VALUES (NULL, %s, %s, %s)",
                        [message.author.id, message.content.encode('ascii', errors='ignore'), time.time()])

                    # End here so we don't process the message as a command or anything like that..
                    return

        if message.channel.id != AKATSUKI_BOTSPAM_ID: # Don't print anything from botspam. This helps reduce a LOT of clutter.

            # Formatted message to be printed to console on message event.
            message_string = f"{message.created_at} [{message.guild if message.guild is not None else ''} {message.channel}] {message.author}: {message.content}"

            if message.guild is None: # Private message.
                print(Fore.YELLOW + message_string)
            elif "cmyui" in message.content.lower(): # cmyui was mentioned in the message.
                print(Fore.CYAN + message_string)
            elif message.guild.id == AKATSUKI_SERVER_ID: # The server is Akatsuki.
                print(Fore.BLUE + message_string)
            else: # Regular message.
                print(message_string)

        # Finally, process commands.
        await bot.process_commands(message)
    return

SQL.execute("SELECT value_string FROM aika_settings WHERE name = 'rewrite_token'")
bot.run(SQL.fetchone()[0], bot=True, reconnect=True)

# Clean up
print("\nForce-quit detected. Cleaning up Aika before shutdown..\nCleaning up MySQL variables..")
SQL.close()
cnx.close()
print("Cleaning complete.")