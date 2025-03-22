import discord
import json, os, re
from discord.ext import commands
from datetime import datetime, timedelta

from bot_logic import gen_pass, flip_coin_f, gen_emojis
from config import main_config, command_categories

def load_server_data():
    if os.path.exists("data.txt"):
        with open("data.txt", "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    else:
        return {}

def save_server_data():
    with open("data.txt", "w") as f:
        json.dump(server_data, f)

server_data = load_server_data()

prefix = main_config["Prefix"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix = prefix, intents = intents)

warnings = {}
bad_words = {}
log_channel_id = 1

@bot.event
async def on_ready():
    print(f"Connected as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return await bot.process_commands(message)
    
    guild_id = str(message.guild.id) if message.guild else None
    current_bad_words = server_data.get(guild_id, {}).get("bad_words", list(bad_words))
    content_lower = message.content.lower()

    for word in current_bad_words:
        if word in content_lower:
            try:
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}, your message contains prohibited words.")
            except discord.Forbidden:
                print("Missing permissions to delete messages")
            break

    await bot.process_commands(message)

@bot.command()
async def cmds(ctx, category: str = None):
    if category is None:
        prefix_field = f"```yaml\nPrefix: {prefix}\n```"
        categories_list = "\n".join(f"- {cat}" for cat in command_categories.keys())
        categories_field = f"```yaml\nCategories:\n\n{categories_list}\n```"

        embed = discord.Embed(title = "Command Categories", color = int("84b6f4", 16))
        embed.add_field(name = "", value=prefix_field, inline = False)
        embed.add_field(name = "", value=categories_field, inline = False)
        embed.set_footer(text = f"Use {prefix}cmds <category> to view commands in that category.")

        await ctx.send(embed=embed)
    else:
        found_category = None
        for cat in command_categories.keys():
            if cat.lower() == category.lower():
                found_category = cat
                break

        if found_category is not None:
            prefix_field = f"```yaml\nPrefix: {prefix}\n```"
            commands_list = "\n".join(f"[{cmd}]: {desc}" for cmd, desc in command_categories[found_category].items())
            commands_field = f"```yaml\nCommands:\n\n{commands_list}\n```"

            embed = discord.Embed(title=f"{found_category} Commands", color = int("84b6f4", 16))
            embed.add_field(name = "", value=prefix_field, inline = False)
            embed.add_field(name = "", value=commands_field, inline = False)

            await ctx.send(embed = embed)
        else:
            await ctx.send(f"⚠️ Category '{category}' not found. Use {prefix}cmds to view available categories.")


@bot.command()
async def hello(ctx):
    await ctx.send(f"<:yes:1273791797797326949> Hello {ctx.author.mention}!")

@bot.command()
async def bye(ctx):
    await ctx.send(f"<:yes:1273791797797326949> Bye {ctx.author.mention}!")

@bot.command()
async def random_password(ctx, length: int = 20):
    try:
        password = gen_pass(length)
        await ctx.send(password)
    except Exception as e:
        await ctx.send(str(e))

@bot.command()
async def random_emoji(ctx):
    await ctx.send(gen_emojis())

@bot.command()
async def flip_coin(ctx):
    await ctx.send(flip_coin_f())

@bot.command()
async def user_info(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(title=f"Information for {member.name}", color = int("84b6f4", 16))
    embed.add_field(name = "ID", value=member.id)
    embed.add_field(name = "Joined Server", value = discord.utils.format_dt(member.joined_at, style = "F"))
    embed.add_field(name = "Account Created", value = discord.utils.format_dt(member.created_at, style = "F"))

    if member.avatar:
        embed.set_thumbnail(url = member.avatar.url)

    await ctx.send(embed = embed)

@bot.command()
async def react(ctx, message_id: int, emoji: str):
    try:
        target_message = await ctx.channel.fetch_message(message_id)
        await target_message.add_reaction(emoji)
        await ctx.send(f"✅ Reacted to message with ID {message_id} using {emoji}.")

    except discord.NotFound:
        await ctx.send("⚠️ Message not found.")

    except discord.HTTPException:
        await ctx.send("❌ Error adding reaction.")

@bot.command()
async def poll(ctx, *, question: str):
    embed = discord.Embed(title = "Poll", description=question, color=int("84b6f4", 16))
    sent_msg = await ctx.send(embed=embed)

    await sent_msg.add_reaction("👍")
    await sent_msg.add_reaction("👎")

@bot.command()
@commands.has_permissions(manage_messages = True)
async def warn(ctx, member: discord.Member, *, reason = "Not specified"):
    if member.id not in warnings:
        warnings[member.id] = []
    warnings[member.id].append(reason)

    guild_id = str(ctx.guild.id)
    guild_data = server_data.setdefault(guild_id, {})
    guild_warnings = guild_data.setdefault("warnings", {})
    member_warns = guild_warnings.setdefault(str(member.id), [])
    member_warns.append(reason)
    save_server_data()

    await member.send(f"⚠️ You were warned from {ctx.guild.name}. Reason: {reason}")
    await ctx.send(f"⚠️ {member.mention} has been warned. Reason: {reason}")

    channel_id = guild_data.get("log_channel_id", log_channel_id)
    log_channel = bot.get_channel(channel_id)
    if log_channel:
        await log_channel.send(f"⚠️ {member} was warned by {ctx.author}. Reason: {reason}")

@bot.command()
@commands.has_permissions(manage_messages = True)
async def warnings_list(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    guild_data = server_data.get(guild_id, {})
    member_warnings = guild_data.get("warnings", {}).get(str(member.id), [])

    if not member_warnings:
        await ctx.send(f"{member.mention} has no warnings.")
    else:
        warning_text = "\n".join(f"{i+1}. {w}" for i, w in enumerate(member_warnings))
        await ctx.send(f"⚠️ Warnings for {member.mention}:\n{warning_text}")

@bot.command()
@commands.has_permissions(kick_members = True)
async def kick(ctx, member: discord.Member, *, reason = "Not specified"):
    try:
        await member.send(f"⛔ You were kicked from {ctx.guild.name}. Reason: {reason}")
        await member.kick(reason = reason)
        await ctx.send(f"⛔ {member.mention} has been kicked <:yes:1273791797797326949>. Reason: {reason}")

        guild_id = str(ctx.guild.id)
        channel_id = server_data.get(guild_id, {}).get("log_channel_id", log_channel_id)
        log_channel = bot.get_channel(channel_id)
        
        if log_channel:
            await log_channel.send(f"⛔ {member} was kicked by {ctx.author} <:yes:1273791797797326949>. Reason: {reason}")

    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command()
@commands.has_permissions(ban_members = True)
async def ban(ctx, member: discord.Member, *, reason = "Not specified"):
    try:
        await member.send(f"⚠️ You were banned from {ctx.guild.name}. Reason: {reason}")
        await member.ban(reason = reason)
        await ctx.send(f"⛔ {member.mention} has been banned <:yes:1273791797797326949>. Reason: {reason}")

        guild_id = str(ctx.guild.id)
        channel_id = server_data.get(guild_id, {}).get("log_channel_id", log_channel_id)
        log_channel = bot.get_channel(channel_id)

        if log_channel:
            await log_channel.send(f"⛔ {member} was banned by {ctx.author} <:yes:1273791797797326949>. Reason: {reason}")

    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command()
@commands.has_permissions(ban_members = True)
async def unban(ctx, *, member_name: str):
    async for ban_entry in ctx.guild.bans():
        user = ban_entry.user
        if user.name == member_name:
            try:
                await ctx.guild.unban(user)
                await ctx.send(f"✅ {member_name} has been unbanned <:yes:1273791797797326949>.")

                guild_id = str(ctx.guild.id)
                channel_id = server_data.get(guild_id, {}).get("log_channel_id", log_channel_id)
                log_channel = bot.get_channel(channel_id)

                if log_channel:
                    await log_channel.send(f"✅ {member_name} was unbanned <:yes:1273791797797326949> by {ctx.author}.")
            except Exception as e:
                await ctx.send(f"Error: {str(e)}")
            return

    await ctx.send(f"⚠️ User {member_name} not found in the banned list.")

@bot.command()
@commands.has_permissions(manage_channels = True)
async def slowmode(ctx, seconds: int):
    if seconds < 0:
        await ctx.send("❌ Please provide a non-negative value for slowmode delay.")
        return
    
    try:
        await ctx.channel.edit(slowmode_delay = seconds)
        await ctx.send(f"✅ Slowmode has been set to {seconds} second(s).")

        guild_id = str(ctx.guild.id)
        channel_id = server_data.get(guild_id, {}).get("log_channel_id", log_channel_id)
        log_channel = bot.get_channel(channel_id)
        if log_channel:
            await log_channel.send(f"✅ Slowmode has been set to {seconds} second(s) in {ctx.channel.mention}.")

    except Exception as e:
        print(f"Error setting slowmode: {e}")
        await ctx.send("❌ An error occurred while trying to set slowmode.")

@bot.command()
@commands.has_permissions(administrator = True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    server_data.setdefault(guild_id, {})["log_channel_id"] = channel.id

    save_server_data()

    await ctx.send(f"✅ Log channel set to {channel.mention}.")

@bot.command()
@commands.has_permissions(administrator = True)
async def set_bad_words(ctx, *, words: str):
    guild_id = str(ctx.guild.id)
    word_list = [w.strip() for w in words.split(",")]
    server_data.setdefault(guild_id, {})["bad_words"] = word_list
    
    save_server_data()
    await ctx.send("✅ Bad words list updated: " + ", ".join(word_list))

    guild_id = str(ctx.guild.id)
    channel_id = server_data.get(guild_id, {}).get("log_channel_id", log_channel_id)
    log_channel = bot.get_channel(channel_id)
    if log_channel:
        await log_channel.send("✅ Bad words list updated: " + ", ".join(word_list))

@bot.command()
@commands.has_permissions(administrator = True)
async def clear(ctx, amount: int):
    if amount < 1 or amount > 100:
        await ctx.send("❌ Please provide a number between 1 and 100.")
        return
    deleted_messages = await ctx.channel.purge(limit = amount)
    
    await ctx.send(f"✅ Deleted {len(deleted_messages)} messages.", delete_after = 5)

    guild_id = str(ctx.guild.id)
    channel_id = server_data.get(guild_id, {}).get("log_channel_id", log_channel_id)
    log_channel = bot.get_channel(channel_id)
    if log_channel:
        await log_channel.send(f"⚠️ {amount} messages were deleted in {ctx.channel.mention}.")

@bot.command()
async def test(ctx):
    await ctx.send("Nothing to test right now.")

bot.run(main_config["Token"])
