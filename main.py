import discord
import os # default module
from dotenv import load_dotenv
import random
import base64
from captcha.image import ImageCaptcha
import asyncio
load_dotenv() # load all the variables from the env file
bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.command(name="verify", description="Verify yourself", guild_ids=[1073787100664696852])
async def verify(ctx):
    await ctx.defer()
    abc = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    #generate a random 5 word code
    code = ""
    for i in range(5):
        code += random.choice(abc)
    filename = ""
    for i in range(5):
        filename += random.choice(abc)
    await ctx.respond(code) # send the code to the user
    image = ImageCaptcha(width = 280, height = 90)
    captcha_text = image.generate(f'{code}')
    image.write(code, f'{filename}.png')
    # print(img)
    class MyModal(discord.ui.Modal):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.add_item(discord.ui.InputText(label="Short Input"))
        async def callback(self, interaction: discord.Interaction):
            if self.children[0].value == code:
                await interaction.response.send_message("You have been verified!", ephemeral=True)
                # button.disabled = Tru
    class MyView(discord.ui.View):
        @discord.ui.button(label="Verify code...", style=discord.ButtonStyle.green)
        async def button_callback(self, button, interaction):
            await interaction.response.send_modal(MyModal(title="ENTER CODE"))

    await ctx.respond('To verify enter the code...',file=discord.File(f'{filename}.png'), view=MyView(timeout=15))
    os.remove(f'{filename}.png')






bot.run(os.getenv('TOKEN')) # run the bot with the token