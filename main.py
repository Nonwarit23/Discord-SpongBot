import os
import discord
from discord.ext import commands
from discord import app_commands

from mysever import server_on
import asyncio

# Channel IDs
schedule = 1502332277072597052
announcement_channel_id = 1502331959517384828
s_output = 1502332037917573261
command_channel_id = 1502332210068324503
verify = 1502581306913980496

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'[System] Bot {bot.user} is now Online')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Sync error: {e}")

# --- Welcome/Leave System ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(s_output)
    if channel:
        embed = discord.Embed(
            title="Welcome to the server!", 
            description=f"Welcome to the Sponglium play & study center, {member.mention}!", 
            color=0xFFD230
        )
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(s_output)
    if channel:
        embed = discord.Embed(
            title="Leave the server!", 
            description=f"{member.mention} has left the server!", 
            color=0xFF2056
        )
        await channel.send(embed=embed)

# --- Vote System Components ---
class PollView(discord.ui.View):
    def __init__(self, options, creator, timeout=None):
        super().__init__(timeout=timeout)
        self.options = options
        self.creator = creator # เก็บข้อมูลคนสร้าง Poll
        self.votes = {option: 0 for option in options}
        self.voters = set()
        
        # สร้างปุ่มตัวเลือก
        for option in self.options:
            button = discord.ui.Button(label=option, style=discord.ButtonStyle.primary, custom_id=option)
            button.callback = self.button_callback
            self.add_item(button)
            
        # เพิ่มปุ่มสำหรับปิดโหวต (เฉพาะคนสร้าง)
        close_button = discord.ui.Button(label="Close Poll", style=discord.ButtonStyle.danger, custom_id="close_poll")
        close_button.callback = self.close_callback
        self.add_item(close_button)

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("คุณได้ลงคะแนนไปแล้ว!", ephemeral=True)
        
        custom_id = interaction.data['custom_id']
        self.votes[custom_id] += 1
        self.voters.add(interaction.user.id)
        
        await self.update_poll_message(interaction)

    async def close_callback(self, interaction: discord.Interaction):
        # ตรวจสอบว่าใช่คนสร้าง Poll หรือไม่
        if interaction.user.id != self.creator.id:
            return await interaction.response.send_message("เฉพาะผู้สร้าง Poll เท่านั้นที่ปิดโหวตได้!", ephemeral=True)
        
        # ปิดการทำงานของปุ่มทั้งหมด
        for item in self.children:
            item.disabled = True
            
        embed = interaction.message.embeds[0]
        embed.title = "📊 POLL CLOSED (สิ้นสุดการโหวต)"
        embed.color = discord.Color.red()
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def update_poll_message(self, interaction):
        total_votes = len(self.voters)
        embed = interaction.message.embeds[0]
        embed.clear_fields()
        
        for opt, count in self.votes.items():
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            bar_count = int(percentage / 10)
            bar = "🟩" * bar_count + "⬜" * (10 - bar_count)
            embed.add_field(
                name=f"🔹 {opt}", 
                value=f"{bar} **{count}** votes ({percentage:.1f}%)", 
                inline=False
            )
        
        embed.set_footer(text=f"Total Voters: {total_votes} | Last update: {interaction.user.display_name}")
        await interaction.response.edit_message(embed=embed, view=self)

# --- Slash Commands ---

@bot.tree.command(name='poll', description="สร้างระบบโหวตและส่งไปยังห้องประกาศ")
@app_commands.describe(
    question='หัวข้อการโหวต',
    options='ตัวเลือก (แยกด้วยเครื่องหมายจุลภาค , เช่น ใช่,ไม่ หรือ A,B,C)'
)
async def poll(interaction: discord.Interaction, question: str, options: str):
    option_list = [opt.strip() for opt in options.split(',')]
    if len(option_list) < 2:
        return await interaction.response.send_message("กรุณาใส่ตัวเลือกอย่างน้อย 2 อย่าง (เช่น ใช่,ไม่)", ephemeral=True)
    if len(option_list) > 5:
        return await interaction.response.send_message("จำกัดสูงสุด 5 ตัวเลือก เพื่อความสวยงาม", ephemeral=True)

    # ค้นหาช่องประกาศ
    channel = bot.get_channel(announcement_channel_id)
    if not channel:
        return await interaction.response.send_message("❌ ไม่พบแชนแนลสำหรับประกาศ กรุณาตรวจสอบ ID", ephemeral=True)

    embed = discord.Embed(
        title="📊 LIVE POLL",
        description=f"# {question}\n\n*คลิกปุ่มด้านล่างเพื่อลงคะแนน*\n*ผู้สร้างสามารถกด Close Poll เพื่อปิดโหวตได้*",
        color=0x5865F2,
        timestamp=discord.utils.utcnow()
    )

    for opt in option_list:
        embed.add_field(name=f"🔹 {opt}", value="⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ **0** votes (0%)", inline=False)
    
    embed.set_footer(text=f"Total Voters: 0 | Created by {interaction.user.display_name}")
    
    view = PollView(option_list, interaction.user)
    
    # ส่งโหวตไปยังช่องประกาศ
    await channel.send(embed=embed, view=view)
    
    # ตอบกลับผู้ใช้ว่าส่งเรียบร้อยแล้ว
    await interaction.response.send_message(f"✅ สร้างโหวตเรียบร้อยแล้วและส่งไปยัง {channel.mention}", ephemeral=True)

@bot.tree.command(name='hello', description="ส่งข้อความทักทายไปที่ห้องประกาศ")
async def hello(interaction: discord.Interaction):
    channel = bot.get_channel(announcement_channel_id)
    if channel:
        embed = discord.Embed(title="HELLO!", description="Hello everyone", color=0xFF2056)
        await channel.send(embed=embed)
        await interaction.response.send_message("ส่งคำทักทายเรียบร้อย!", ephemeral=True)

@bot.tree.command(name='announce', description="ส่งประกาศเปิดห้อง")
@app_commands.describe(
    room_name='ชื่อห้อง',
    type='หัวข้อพูดคุย',
    time_s='เวลาที่เริ่ม',
    time_t='ถึงเวลา',
    link='ลิงค์เอกสาร (พิมพ์ - ถ้าไม่มี)',
    des='รายละเอียดเพิ่มเติม'
)
async def announce_room(interaction: discord.Interaction, room_name: str, type: str, time_s: str, time_t: str, link: str, des: str):
    await interaction.response.defer(ephemeral=True)
    channel = bot.get_channel(announcement_channel_id)

    embed = discord.Embed(
        title="📢   ANNOUNCEMENT   📢", 
        description=f"# 📂 TOPIC: {type}", 
        color=0xFF2056,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="📍 LOCATION", value=f"```\n{room_name}\n```", inline=False)
    embed.add_field(name="⏰ DURATION", value=f"**{time_s}** - **{time_t}**", inline=False)
    embed.add_field(name="​", value="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", inline=False)

    if link != '-':
        actual_link = link if link.startswith('http') else f'https://{link}'
        embed.add_field(name="📃 DOCUMENT", value=f"🔗 [คลิกเพื่อชมเอกสาร]({actual_link})", inline=False)
    else:
        embed.add_field(name="📃 DOCUMENT", value="❌ ไม่มีเอกสารประกอบ", inline=False)

    embed.add_field(name="🎯 INFORMATION", value=f"```fix\n{des}\n```", inline=False)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    if channel:
        await channel.send(embed=embed)
        await interaction.followup.send("✅ ส่งประกาศเรียบร้อยแล้ว!", ephemeral=True)

@bot.tree.command(name='server_members', description="สรุปจำนวนสมาชิกและรายชื่อทั้งหมด")
async def server_members(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild
    members = [m.display_name for m in guild.members if not m.bot]
    bot_count = sum(1 for m in guild.members if m.bot)
    member_list_str = ", ".join(members)
    if len(member_list_str) > 1024:
        member_list_str = member_list_str[:1020] + "..."

    embed = discord.Embed(
        title=f"📊 สรุปข้อมูลสมาชิกใน {guild.name}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="👥 ทั้งหมด", value=f"**{guild.member_count}**", inline=True)
    embed.add_field(name="🤖 บอท", value=f"{bot_count}", inline=True)
    embed.add_field(name="👤 รายชื่อ", value=f"```\n{member_list_str}\n```", inline=False)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name='timer', description="Set a timer with 5-minute interval alerts")
async def timer(interaction: discord.Interaction, minutes: int, details: str = "Time's up!"):
    if minutes <= 0:
        return await interaction.response.send_message("Please enter minutes > 0", ephemeral=True)

    seconds_left = minutes * 60
    embed = discord.Embed(title="⏲️ Timer Started", description=f"**Task:** {details}\n**Time:** {minutes}m", color=0x3498db)
    await interaction.response.send_message(embed=embed)

    while seconds_left > 0:
        if seconds_left > 300:
            await asyncio.sleep(300)
            seconds_left -= 300
            await interaction.channel.send(f"⏳ **Update:** `{seconds_left // 60}m` remaining for: {details}")
        elif 60 < seconds_left <= 300:
            await asyncio.sleep(60)
            seconds_left -= 60
            await interaction.channel.send(f"⚠️ **Countdown:** `{seconds_left // 60}m` left!")
        else:
            await asyncio.sleep(seconds_left)
            seconds_left = 0

    await interaction.channel.send(f"🔔 {interaction.user.mention} **TIME IS UP!** for **{details}**")

server_on()

bot.run(os.getenv('TOKEN'))
