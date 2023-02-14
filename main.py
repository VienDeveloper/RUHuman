import discord
import os # default module
from dotenv import load_dotenv
import random
from captcha.image import ImageCaptcha
import aiosqlite
from discord.ext import bridge, commands
# import datetime
from datetime import datetime, timedelta

load_dotenv() # load all the variables from the env file
bot = discord.Bot(help_command=None)


@bot.event
async def on_ready():
    bot.db = await aiosqlite.connect("database.db")
    async with bot.db.cursor() as cursor:
        await cursor.execute("CREATE TABLE IF NOT EXISTS servers (server_id INTEGER, role_id INTEGER, channel_id INTEGER)")
        await cursor.execute("CREATE TABLE IF NOT EXISTS log_channels (server_id INTEGER, channel_id INTEGER)")
        await cursor.execute("CREATE TABLE IF NOT EXISTS anti_alt (server_id INTEGER, enabled INTEGER)")
        await bot.db.commit()
    print(f"{bot.user} is ready and online!")

@bot.command(name="setup", description="Setup the verification system")
@bridge.has_permissions(administrator=True)
async def setup(ctx, role: discord.Role, channel: discord.TextChannel):
    await ctx.defer()
    guild_id = ctx.guild.id
    role_id = role.id
    channel_id = channel.id
    data = await bot.db.execute("SELECT * FROM servers WHERE server_id = ?", (guild_id,))
    # if data is not None:
    #     async with bot.db.cursor() as cursor:
    #         await cursor.execute("UPDATE servers SET role_id = ?, channel_id = ? WHERE server_id = ?", (role_id, channel_id, guild_id))
    #         await bot.db.commit()
    #     await ctx.respond("You have successfully updated the verification system!")
    # if data is None:
    async with bot.db.cursor() as cursor:
        await cursor.execute("INSERT INTO servers VALUES (?, ?, ?)", (guild_id, role_id, channel_id))
        await bot.db.commit()
    await ctx.respond("You have successfully set up the verification system!")


@bot.command(name='updateverification', description="Update the verification")
@bridge.has_permissions(administrator=True)
async def updateverification(ctx, role: discord.Role, channel: discord.TextChannel):
    await ctx.defer()
    guild_id = ctx.guild.id
    role_id = role.id
    channel_id = channel.id
    async with bot.db.cursor() as cursor:
        await cursor.execute("UPDATE servers SET role_id = ?, channel_id = ? WHERE server_id = ?", (role_id, channel_id, guild_id))
        await bot.db.commit()
    await ctx.respond("You have successfully updated the verification system!")

@bot.command(name="help", description="Help command")
async def help(ctx):
    await ctx.defer()
    embed = discord.Embed(title="Help", description="This is a help command", color=discord.Color.green())
    embed.add_field(name="setup", value="To set up the verification system, you need to do /setup @role #channel")
    embed.add_field(name="verify", value="To verify yourself, you need to do /verify")
    await ctx.respond(embed=embed)
@bot.command(name="verify", description="Verify yourself")
async def verify(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT * FROM servers WHERE server_id = ?", (guild_id,))
        data = await cursor.fetchone()
        if data is None:
            await ctx.respond("You have not set up the verification system yet! Please contact the server owner. (do /help for more info)")
            return
        role_id = data[1]
        channel_id = data[2]
    if ctx.channel.id != channel_id:
        await ctx.respond("You cannot use this command here!")
        return
    is_antialt_enabled = await check_anti_alt(ctx.guild.id)
    if is_antialt_enabled:
        if ctx.author.bot:
            await ctx.respond("You cannot verify yourself because you are a bot!")
            return
        # adds an override if user is admin
        if ctx.author.guild_permissions.administrator:
            pass
        else:
            #checks if the user is too new
            days = 14
            d1 = datetime.today() - timedelta(days=days)
            d2 = ctx.author.created_at
            d2 = d2.replace(tzinfo=None)
            if d1 < d2:
                await ctx.respond("You cannot verify yourself because your account is too new!")
                return
            else:
                pass
    #checks if the user already has the role
    role = ctx.guild.get_role(role_id)
    if role in ctx.author.roles:
        await ctx.respond("You are already verified!")
        return

    abc = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    #generate a random 5 word code
    code = ""
    for i in range(5):
        code += random.choice(abc)
    filename = ""
    for i in range(5):
        filename += random.choice(abc)
    image = ImageCaptcha(width = 280, height = 90, font_sizes=[70], fonts=['./captcha.ttf'])
    captcha_text = image.generate(f'{code}')
    image.write(code, f'{filename}.png')
    # print(img)
    class MyModal(discord.ui.Modal):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.add_item(discord.ui.InputText(label="Type the code"))
        async def callback(self, interaction: discord.Interaction):
            if self.children[0].value == code:
                try:
                    role = ctx.guild.get_role(role_id)
                    await ctx.author.add_roles(role)
                    await interaction.response.send_message("You have been verified!", ephemeral=True)
                    async with bot.db.cursor() as cursor:
                        await cursor.execute("SELECT * FROM log_channels WHERE server_id = ?", (guild_id,))
                        data = await cursor.fetchone()
                        if data is not None:
                            channel_id = data[1]
                            channel = bot.get_channel(channel_id)
                            await channel.send(f"{ctx.author} has verified themselves!")
                        else:
                            pass
                except discord.Forbidden:
                    await interaction.response.send_message("I do not have permissions to give you the role!", ephemeral=True)
            else:
                await interaction.response.send_message("You have entered the wrong code!", ephemeral=True)
                # button.disabled = Tru
    class MyView(discord.ui.View):
        @discord.ui.button(label="Verify code...", style=discord.ButtonStyle.green)
        async def button_callback(self, button, interaction):
            await interaction.response.send_modal(MyModal(title="ENTER CODE"))

    await ctx.respond('To verify enter the code...',file=discord.File(f'{filename}.png'), view=MyView(timeout=15), ephemeral=True)
    os.remove(f'{filename}.png')

@bot.command(name='set_log_channel', description="Set the log channel")
@bridge.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    await ctx.defer()
    guild_id = ctx.guild.id
    channel_id = channel.id
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT * FROM log_channels WHERE server_id = ?", (guild_id,))
        data = await cursor.fetchone()
        if data is None:
            await cursor.execute("INSERT INTO log_channels VALUES (?, ?)", (guild_id, channel_id))
            await bot.db.commit()
            await ctx.respond("You have successfully set the log channel!")
        else:
            await cursor.execute("UPDATE log_channels SET channel_id = ? WHERE server_id = ?", (channel_id, guild_id))
            await bot.db.commit()
            await ctx.respond("You have successfully updated the log channel!")

@bot.command(name='remove_log_channel', description="Remove the log channel")
@bridge.has_permissions(administrator=True)
async def remove_log_channel(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT * FROM log_channels WHERE server_id = ?", (guild_id,))
        data = await cursor.fetchone()
        if data is None:
            await ctx.respond("You have not set the log channel yet!")
        else:
            await cursor.execute("DELETE FROM log_channels WHERE server_id = ?", (guild_id,))
            await bot.db.commit()
            await ctx.respond("You have successfully removed the log channel!")

@bot.command(name='anti-alt', description="Checks if the users account is a alt (or new)")
@bridge.has_permissions(administrator=True)
async def anti_alt(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT * FROM anti_alt WHERE server_id = ?", (guild_id,))
        data = await cursor.fetchone()
        if data is None:
            await cursor.execute("INSERT INTO anti_alt VALUES (?, ?)", (guild_id, 1))
            await bot.db.commit()
            await ctx.respond("You have successfully enabled anti-alt!")
        else:
            await cursor.execute("UPDATE anti_alt SET enabled = ? WHERE server_id = ?", (0, guild_id))
            await bot.db.commit()
            await ctx.respond("You have successfully disabled anti-alt!")

async def check_anti_alt(guild_id):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT * FROM anti_alt WHERE server_id = ?", (guild_id,))
        data = await cursor.fetchone()
        if data is None:
            return False
        if data[1] == 0:
            return False
        if data[1] == 1:
            return True
        else:
            return False
@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    if await check_anti_alt(guild_id) == True:
        d1 = datetime.datetime.now()
        d2 = member.created_at
        d2 = d2.replace(tzinfo=None)
        d1 = d1.replace(tzinfo=None)
        if d1 < d2:
            try:
                await member.send("You cannot join this server because your account is too new!")
                await member.kick()
            except discord.Forbidden:
                #check log channel
                async with bot.db.cursor() as cursor:
                    await cursor.execute("SELECT * FROM log_channels WHERE server_id = ?", (guild_id,))
                    data = await cursor.fetchone()
                    if data is not None:
                        channel_id = data[1]
                        channel = bot.get_channel(channel_id)
                        await channel.send(f"{member} cannot kicked because their account is too new! (i dont have permissions to kick them)")
        else:
            pass
    else:
        pass

@bot.command(name='disable-anti-alt', description="Disable anti-alt")
@bridge.has_permissions(administrator=True)
async def disable_anti_alt(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT * FROM anti_alt WHERE server_id = ?", (guild_id,))
        data = await cursor.fetchone()
        if data is None:
            await cursor.execute("INSERT INTO anti_alt VALUES (?, ?)", (guild_id, 0))
            await bot.db.commit()
            await ctx.respond("You have successfully disabled anti-alt!")
        else:
            await cursor.execute("UPDATE anti_alt SET enabled = ? WHERE server_id = ?", (0, guild_id))
            await bot.db.commit()
            await ctx.respond("You have successfully disabled anti-alt!")

bot.run(os.getenv('TOKEN')) # run the bot with the token