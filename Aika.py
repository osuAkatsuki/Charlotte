import discord, asyncio, os
from discord.ext import commands

import mysql.connector
from mysql.connector import errorcode

from time import time
import json
from requests import get

# TODO: stop using these!
from colorama import init
from colorama import Fore, Back, Style
init(autoreset=True)

# Hardcoded version numbers.
global __version, __abns_version
__version      = 4.30 # Aika (This bot).
__abns_version = 2.19 # Akatsuki's Beatmap Nomination System (#rank-request(s)).

global config
config = None
""" Read and assign values from config. """
with open(os.path.dirname(os.path.realpath(__file__)) + "/config.json", 'r') as f:
    config = json.loads(f.read())

mysql_host           = config["mysql_host"]
mysql_user           = config["mysql_user"]
mysql_passwd         = config["mysql_passwd"]
mysql_database       = config["mysql_database"]

discord_token        = config["discord_token"]
discord_owner_userid = config["discord_owner_userid"]

debug                = config["debug"]
server_build         = config["server_build"]
version              = config["version"]
abns_version         = config["abns_version"]

try:
    cnx = mysql.connector.connect(
        user       = mysql_user,
        password   = mysql_passwd,
        host       = mysql_host,
        database   = mysql_database,
        autocommit = True)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        raise Exception("Something is wrong with your username or password.")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        raise Exception("Database does not exist.")
    else:
        raise Exception(err)
except: raise Exception("Something really died.")

SQL = cnx.cursor()
del mysql_host, mysql_user, mysql_passwd, mysql_database

# Akatsuki's server/channel IDs.
# [S] = Server.
# [T] = Text channel.
# [V] = Voice channel.
akatsuki_server_id           = config["akatsuki_server_id"]           # [S] | ID for osu!Akatsuki.
akatsuki_general_id          = config["akatsuki_general_id"]          # [T] | ID for #general.
akatsuki_help_id             = config["akatsuki_help_id"]             # [T] | ID for #help.
akatsuki_verify_id           = config["akatsuki_verify_id"]           # [T] | ID for #verify.
akatsuki_player_reporting_id = config["akatsuki_player_reporting_id"] # [T] | ID for #player_reporting.
akatsuki_rank_request_id     = config["akatsuki_rank_request_id"]     # [T] | ID for #rank-request (User).
akatsuki_reports_id          = config["akatsuki_reports_id"]          # [T] | ID for #reports.
akatsuki_rank_requests_id    = config["akatsuki_rank_requests_id"]    # [T] | ID for #rank-requests (Staff).
akatsuki_botspam_id          = config["akatsuki_botspam_id"]          # [T] | ID for #botspam.
akatsuki_nsfw_id             = config["akatsuki_nsfw_id"]             # [T] | ID for #nsfw.
akatsuki_friends_only        = config["akatsuki_friends_only"]        # [T] | ID for #friends-only.
akatsuki_drag_me_in_voice    = config["akatsuki_drag_me_in_voice"]    # [V] | ID for Drag me in (VC).
akatsuki_friends_only_voice  = config["akatsuki_friends_only_voice"]  # [V] | ID for ✨cmyui (VC).


mirror_address = config["mirror_address"] # Akatsuki's beatmap mirror (used in ABNS system).
command_prefix = config["command_prefix"] # Aika's command prefix.
akatsuki_logo  = config["akatsuki_logo"]  # Akatsuki's logo.
crab_emoji     = config["crab_emoji"]     # Yeah?
server_build   = config["server_build"]


""" Chat Filters / Quality Standards. """

# A list of filters.
# These are to be used to wipe messages that are deemed inappropriate,
# or break rules. For the most part, these are of other private servers,
# as required by rule #2 of the Akatsuki Discord & Chat Rules
# (https://akatsuki.pw/doc/rules).
filters = config["filters"]

# Secondary filters.
# These are the same idea as filters,
# although they are *searched for within a string*, rather than compared against.
substring_filters = config["substring_filters"]

# A list of message (sub)strings that we will use to deem
# a quantifiable value for the "quality" of a message.
profanity     = config["profanity"]
high_quality  = config["high_quality"]


# Assign discord owner value.
discord_owner = config["discord_owner_userid"]

#delete config

""" Functions. """

def debug_print(string):
    """
    Print a debug message to the console.

    Example in use:      https://nanahira.life/dOgXljmmKW336gro3Ts5gJmU7P4hNDZz.png

    :param string:       The message to be printed to the console.
    """

    # Debug value
    SQL.execute("SELECT value_int FROM aika_settings WHERE name = %s", ["debug"])
    debug = debug

    if debug:
        print(Fore.MAGENTA, string, '', sep='\n')

def safe_discord(s): return str(s).replace('`', '')

def get_prefix(client, message): return commands.when_mentioned_or(*[config["command_prefix"]])(client, message)


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
    if not after.channel or after.channel.id != akatsuki_drag_me_in_voice: return

    debug_print(f"on_voice_state_update event fired.\n\nData:\n\n{member}\n\n{before}\n\n{after}")

    # Create our vote embed.
    embed = discord.Embed(
        title       = f"{member} wants to be dragged in.",
        description = "Please add a reaction to determine their fate owo..",
        color       = 0x00ff00)

    embed.set_footer(icon_url=crab_emoji, text="Only one vote is required.")
    embed.set_thumbnail(url=akatsuki_logo)

    # Assign friends-only chat and voice channel as constants.
    friends_only_text  = bot.get_channel(akatsuki_friends_only)
    friends_only_voice = bot.get_channel(akatsuki_friends_only_voice)

    # Send our embed, and add our base 👍.
    msg = await friends_only_text.send(embed=embed)
    await msg.add_reaction('👍')

    def check(reaction, user): # TODO: safe
        if user in [member, bot.user]: return False
        return reaction.emoji == '👍' and user.voice.channel == friends_only_voice

    # Wait for a 👍 from a "friend". Timeout: 5 minutes.
    try: reaction, user = await bot.wait_for("reaction_add", timeout=5 * 60, check=check)
    except asyncio.TimeoutError: # Timed out. Remove the embed.
        await friends_only_text.send(f"Timed out {member}'s join query.")
        await msg.delete()
        return

    try: await member.move_to(channel=friends_only_voice, reason="Voted in.")
    except discord.errors.HTTPException: await msg.delete(); return

    # Send our vote success, and delete the original embed.
    await friends_only_text.send(f"{user} voted {member} in.")
    await msg.delete()
    return

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} - {bot.user.id}")
    await bot.change_presence(activity=discord.Game(name="osu!Akatsuki", url="https://akatsuki.pw/", type=1))
    for cog in cogs: bot.load_extension(cog)

    if not server_build or __version == version: return

    # Get config value of latest run.
    with open("config.json", "r+") as _config:
        data = json.load(_config)

        data["version"] = __version
        config["version"] = __version

        _config.seek(0)
        json.dump(data, _config)
        _config.truncate()

        del _config

    # Configure, and send the embed to #general.
    announce_online = discord.Embed(
        title       = "Aika has been updated to v%.2f. (Previous: v%.2f)" % (__version, version),
        description = "Ready for commands <3\n\nAika is osu!Akatsuki's [open source](https://github.com/osuAkatsuki/Aika) "
                      "discord bot.\n\n[Akatsuki](https://akatsuki.pw)\n[Support Akatsuki](https://akatsuki.pw/support)",
        color       = 0x00ff00)

    announce_online.set_footer(icon_url=crab_emoji, text="Thank you for playing!")
    announce_online.set_thumbnail(url=akatsuki_logo)
    await bot.get_channel(akatsuki_general_id).send(embed=announce_online)
    return


@bot.event
async def on_message(message):
    # Await for the bot to be ready before processing messages whatsoever.
    await bot.wait_until_ready()

    # The message has no content.
    # Don't bother doing anything with it.
    if not message.content: return

    # Regular user checks.
    if message.author.id != discord_owner:

        # Verification channel.
        if message.channel.id == akatsuki_verify_id:
            if message.content.lower()[1] == 'v' and not message.content.lower().split(' ')[-1].isdigit():
                await message.author.add_roles(discord.utils.get(message.guild.roles, name="Members"))

            await message.delete() # Delete all messages posted in #verify.
            return

        # If we have unicode in > 1k char message, it's probably with crashing intent?
        if any(ord(char) > 127 for char in message.content) and len(message.content) >= 1000:
            await message.delete()
            return

    else: # Owner checks.
        if len(message.content) > 5 and message.content[1:7] == "reload":
            cog_name = message.content[9:].lower()
            if cog_name in ("staff", "user"):
                bot.reload_extension(f"cogs.{cog_name}")
                await message.channel.send(f"Reloaded extension {cog_name}.")
            else:
                await message.channel.send(f"Invalid extension {cog_name}.")
            return


    # NSFW channel checks (deleting non-images from #nsfw).
    if message.channel.id == akatsuki_nsfw_id:
        def check_content(m): # Don't delete links or images.
            if any(message.content.startswith(s) for s in ("http://", "https://")) or message.attachments: return False
            return True

        if check_content(message): await message.delete()
        return


    # Message sent in #rank-request, move to #rank-requests.
    if message.channel.id == akatsuki_rank_request_id:
        await message.delete()

        if not any(required in message.content for required in ("akatsuki.pw", "osu.ppy.sh")) or len(message.content) > 58: # Should not EVER be over 58 characters. (57 but safe)
            await message.author.send("Your beatmap request was incorrectly formatted, and thus has not been submitted.")
            return

        # Support both links like "https://osu.ppy.sh/b/123" AND "osu.ppy.sh/b/123".
        # Also allow for /s/, /b/, and /beatmapset/setid/discussion/mapid links.
        partitions = message.content.split('/')[3 if "://" in message.content else 1:]

        # Yea thank you for sending something useless in #rank-request very cool.
        if partitions[0] not in ('s', 'b', "beatmapsets"): return

        beatmapset = partitions[0] in ('s', "beatmapsets") # Link is a beatmapset_id link, not a beatmap_id link.
        map_id = partitions[1] # Can be SetID or MapID.

        cnx.ping(reconnect=True, attempts=2, delay=1)

        if not beatmapset: # If the user used a /b/ link, let's turn it into a set id.
            SQL.execute("SELECT beatmapset_id FROM beatmaps WHERE beatmap_id = %s LIMIT 1", [map_id])
            map_id = SQL.fetchone()[0]

        # Do this so we can check if any maps in the set are ranked or loved.
        # If they are, the QAT have most likely already determined statuses of the map.
        SQL.execute("SELECT mode, ranked FROM beatmaps WHERE beatmapset_id = %s ORDER BY ranked DESC LIMIT 1", [map_id])
        sel = SQL.fetchone()

        if not sel: # We could not find any matching rows with the map_id.
            await message.author.send("The beatmap could not be found in our database.")
            return

        mode, status = sel

        if status in (2, 5): # Map is already ranked/loved
            await message.author.send(f"Some (or all) of the difficulties in the beatmap you requested already seem to be {'ranked' if status == 2 else 'loved'}"
                                       " on the Akatsuki server!\n\nIf this is false, please contact a QAT directly to proceed.")
            return

        # Sort out mode to be used to check difficulty.
        # Also have a formatted one to be used for final post.
        if   mode == 0: mode, mode_formatted = "std",   "osu!"
        elif mode == 1: mode, mode_formatted = "taiko", "osu!taiko"
        elif mode == 2: mode, mode_formatted = "ctb",   "osu!catch"
        else:           mode, mode_formatted = "mania", "osu!mania"

        # Select map information.
        SQL.execute(f"SELECT song_name, ar, od, max_combo, bpm, difficulty_{mode} FROM beatmaps WHERE beatmapset_id = %s ORDER BY difficulty_{mode} DESC LIMIT 1", [map_id])
        song_name, ar, od, max_combo, bpm, star_rating = SQL.fetchone()

        # Return values from web request/DB query.
        # TODO: either use the API for everything, or dont use it at all.
        artist = json.loads(get(f"{mirror_address}/s/{map_id}").text)["Creator"]

        # Create embeds.
        embed = discord.Embed(
            title       = "A new beatmap request has been recieved.",
            description = "** **",
            color       = 5516472 # Akatsuki purple.
        )

        embed.set_image (url  = f"https://assets.ppy.sh/beatmaps/{map_id}/covers/cover.jpg?1522396856")
        embed.set_author(url  = f"https://akatsuki.pw/d/{map_id}",                           icon_url = akatsuki_logo, name = song_name)
        embed.set_footer(text = "Akatsuki's beatmap nomination system v%.2f" % abns_version, icon_url = "https://nanahira.life/MpgDe2ssQ5zDsWliUqzmQedZcuR4tr4c.jpg")
        embed.add_field (name = "Nominator",         value = message.author.name)
        embed.add_field (name = "Mapper",            value = artist)
        embed.add_field (name = "Gamemode",          value = mode_formatted)
        embed.add_field (name = "Highest SR",        value = "%.2f*" % round(star_rating, 2))
        embed.add_field (name = "Highest AR",        value = ar)
        embed.add_field (name = "Highest OD",        value = od)
        embed.add_field (name = "Highest Max Combo", value = f"{max_combo}x")
        embed.add_field (name = "BPM",               value = bpm)

        # Prepare, and send the report to the reporter.
        embed_dm = discord.Embed(
            title       = "Your beatmap nomination request has been sent to Akatsuki's Quality Assurance Team for review.",
            description = "We will review it shortly.",
            color       = 0x00ff00 # Lime green.
        )

        embed_dm.set_thumbnail(url  = akatsuki_logo)
        embed_dm.set_image    (url  = f"https://assets.ppy.sh/beatmaps/{map_id}/covers/cover.jpg?1522396856")
        embed_dm.set_footer   (text = f"Akatsuki's beatmap nomination system v{abns_version}", icon_url="https://nanahira.life/MpgDe2ssQ5zDsWliUqzmQedZcuR4tr4c.jpg")

        # Send the embed to the #rank_requests channel.
        request_post = await bot.get_channel(akatsuki_rank_requests_id).send(embed=embed)

        # Send the embed to the nominator by DM. TODO: check if we can message the user rather than abusing try-except? that might just be slower lul
        try: await message.author.send(embed=embed_dm)
        except: print(f"Could not DM ({message.author.name}).")

        for e in ['👎', '👍']: await request_post.add_reaction(e)
        return


    # Message sent in #player-reporting, move to #reports.
    if message.channel.id == akatsuki_player_reporting_id:
        await message.delete() # Delete the message from #player-reporting.

        # Prepare, and send the report in #reports.
        embed = discord.Embed(title = "New report recieved.", description="** **", color=0x00ff00)
        embed.set_thumbnail  (url   = akatsuki_logo)
        embed.add_field      (name  = "Report content", value = message.content,        inline = True)
        embed.add_field      (name  = "Author",         value = message.author.mention, inline = True)

        # Prepare, and send the report to the reporter.
        embed_pm = discord.Embed(title="Thank you for the player report.", description="We will review the report shortly.", color=0x00ff00)

        embed_pm.add_field(name="Report content", value=message.content, inline=True)
        embed_pm.set_thumbnail(url=akatsuki_logo)

        if not message.content.startswith(command_prefix): # Do not pm or link to #reports if it is a command.
            await message.author.send(embed=embed_pm)
            await bot.get_channel(akatsuki_reports_id).send(embed=embed)
        return

    elif message.author != bot.user and message.guild:
        # Message sent in #help, log to db.
        if message.channel.id == akatsuki_help_id:
            # Split the content into sentences by periods.
            # TODO: Other punctuation marks!
            sentence_split = message.content.split('.')

            # Default values for properly formatted messages / negative messages.
            properly_formatted, negative = [False] * 2

            debug_print(f"Sentence split: {sentence_split}")

            # After every period, check they have a space and the next sentence starts with a capital letter (ignore things like "...").
            for idx, sentence in enumerate(sentence_split):
                if len(sentence) > 1 and idx:
                    if sentence[0] == ' ' and sentence[1].isupper(): continue
                    negative = True

            properly_formatted = message.content[0].isupper() and message.content[len(message.content) - 1] in ('.', '?', '!') and not negative

            quality = 1
            if any(x in message.content.lower() for x in profanity): quality = 0
            elif any(x in message.content.lower() for x in high_quality) or properly_formatted: quality = 2

            debug_print(f"Quality of message\n\n{message.author}: {message.content} - {quality}")

            cnx.ping(reconnect=True, attempts=2, delay=1)

            # TODO: Store the whole bitch in a single number.
            # Maybe even do some bitwise black magic shit.
            SQL.execute("INSERT INTO help_logs (id, user, content, datetime, quality) VALUES (NULL, %s, %s, %s, %s)",
                [message.author.id, message.content.encode("ascii", errors="ignore"), time(), quality])

        # Ignore moderators for the following flagging.
        if not message.author.guild_permissions.manage_messages:
            PROFANITY_WARNING = "Hello,\n\nYour message in osu!Akatsuki has been removed as it has been deemed "   \
                                "unsuitable.\n\nIf you have any questions, please ask <@285190493703503872>. "     \
                                "\n**Do not try to evade this filter as it is considered fair ground for a ban**." \
                                f"\n\n```{safe_discord(message.author.name)}: {safe_discord(message.content)}```"

            # Primary filters.
            # These are looking for direct comparison results.
            for split in message.content.lower().split(' '):
                if any(i == split for i in filters) or any(i in message.content.lower() for i in substring_filters):
                    await message.delete()

                    try: await message.author.send(PROFANITY_WARNING)
                    except: print(f"{Fore.LIGHTRED_EX}Could not warn {message.author.name}.")

                    debug_print(f"Filtered message | '{message.author.name}: {message.content}'")

                    cnx.ping(reconnect=True, attempts=2, delay=1)

                    SQL.execute("INSERT INTO profanity_logs (id, user, content, datetime) VALUES (NULL, %s, %s, %s)",
                        [message.author.id, message.content.encode("ascii", errors="ignore"), time()])

                    return

        if message.channel.id != akatsuki_botspam_id:
            message_string = f"{message.created_at} [{message.guild} #{message.channel}] {message.author}: {message.content}"

            col = None
            if not message.guild:                         col = Fore.YELLOW
            elif "cmyui" in message.content.lower():      col = Fore.LIGHTRED_EX
            elif message.guild.id == akatsuki_server_id:  col = Fore.CYAN

            print(col + message_string)
            del col

        # Finally, process commands.
        await bot.process_commands(message)
    return

bot.run(discord_token, bot=True, reconnect=True)

# Clean up
print('', "Force-quit detected. Cleaning up Aika before shutdown..", "Cleaning up MySQL variables..", sep='\n')
SQL.close()
cnx.close()
print("Cleaning complete.")