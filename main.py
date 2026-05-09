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

# Role ID (ระบุ Role ที่จะมอบให้เมื่อกดยืนยันตัวตนสำเร็จ)
VERIFIED_ROLE_ID = 123456789012345678 # <<< เปลี่ยนเป็น ID Role ของคุณ

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

# --- Verification System Components ---

class VerifyRequestView(discord.ui.View):
    """ปุ่มสำหรับให้ User กดเพื่อขอการยืนยันตัวตน"""
    def __init__(self):
        super().__init__(timeout=None) # timeout=None เพื่อให้ปุ่มอยู่ถาวร

    @discord.ui.button(label="ยืนยันตัวตนที่นี่ / Verify Here", style=discord.ButtonStyle.success, custom_id="verify_request_btn")
    async def request_callback(self, interaction: discord.Interaction):
        # ตรวจสอบว่ามี Role อยู่แล้วหรือไม่
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if role in interaction.user.roles:
            return await interaction.response.send_message("คุณได้รับการยืนยันตัวตนอยู่แล้วครับ!", ephemeral=True)

        # ส่งข้อความไปยังห้อง Command เพื่อให้ทีมงานตรวจ
        cmd_channel = bot.get_channel(command_channel_id)
        if cmd_channel:
            embed = discord.Embed(
                title="🔔 คำขอการยืนยันตัวตนใหม่",
                description=f"ผู้ใช้: {interaction.user.mention}\nID: `{interaction.user.id}`\nกรุณาตรวจสอบและกดยืนยันด้านล่าง",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = AdminApproveView(target_user=interaction.user)
            await cmd_channel.send(embed=embed, view=view)
            await interaction.response.send_message("ส่งคำขอไปยังทีมงานแล้ว กรุณารอสักครู่ครับ", ephemeral=True)
        else:
            await interaction.response.send_message("❌ เกิดข้อผิดพลาด: ไม่พบห้องสำหรับทีมงาน", ephemeral=True)

class AdminApproveView(discord.ui.View):
    """ปุ่มสำหรับให้ Admin กดยืนยันให้ User"""
    def __init__(self, target_user):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Approve (ยืนยัน)", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if not role:
            return await interaction.response.send_message("❌ ไม่พบ Role สำหรับยืนยันตัวตน กรุณาเช็ค ID ในโค้ด", ephemeral=True)

        try:
            await self.target_user.add_roles(role)
            # ปิดการทำงานของปุ่ม
            for item in self.children:
                item.disabled = True
            
            embed = interaction.message.embeds[0]
            embed.title = "✅ ยืนยันตัวตนสำเร็จ"
            embed.color = discord.Color.green()
            embed.add_field(name="ดำเนินการโดย", value=interaction.user.mention)
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            # แจ้งเตือนผู้ใช้ (ถ้า DM เปิดอยู่)
            try:
                await self.target_user.send(f"🎉 คุณได้รับการยืนยันตัวตนในเซิร์ฟเวอร์ **{interaction.guild.name}** เรียบร้อยแล้ว!")
            except:
                pass
        except Exception as e:
            await interaction.response.send_message(f"เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'[System] Bot {bot.user} is now Online')
    # ทำให้ปุ่ม Verify ทำงานตลอดเวลาแม้บอทรีสตาร์ท
    bot.add_view(VerifyRequestView())
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Sync error: {e}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            f"❌ คุณสามารถใช้คำสั่งได้เฉพาะในห้อง <#{command_channel_id}> เท่านั้นครับ", 
            ephemeral=True
        )

# --- Check Function ---
def is_command_channel():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.channel_id == command_channel_id
    return app_commands.check(predicate)

# --- Slash Commands ---

@bot.tree.command(name='setup_verify', description="ส่งปุ่มยืนยันตัวตนไปยังห้อง Verify (Admin Only)")
@is_command_channel()
async def setup_verify(interaction: discord.Interaction):
    verify_channel = bot.get_channel(verify)
    if verify_channel:
        embed = discord.Embed(
            title="🔒 การยืนยันตัวตน (Verification)",
            description="ยินดีต้อนรับสู่ Sponglium! กรุณากดปุ่มด้านล่างเพื่อส่งคำขอยืนยันตัวตนเข้าสู่เซิร์ฟเวอร์",
            color=0x2ecc71
        )
        embed.set_footer(text="เมื่อกดแล้ว ทีมงานจะตรวจสอบและอนุมัติให้เร็วที่สุด")
        
        view = VerifyRequestView()
        await verify_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ ส่งระบบยืนยันตัวตนไปที่ {verify_channel.mention} เรียบร้อย!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ ไม่พบห้อง Verify", ephemeral=True)

@bot.tree.command(name='poll', description="สร้างระบบโหวตและส่งไปยังห้องประกาศ")
@is_command_channel()
@app_commands.describe(
    question='หัวข้อการโหวต',
    options='ตัวเลือก (แยกด้วยเครื่องหมายจุลภาค , เช่น ใช่,ไม่ หรือ A,B,C)'
)
async def poll(interaction: discord.Interaction, question: str, options: str):
    # (โค้ดเดิมคงไว้...)
    option_list = [opt.strip() for opt in options.split(',')]
    if len(option_list) < 2:
        return await interaction.response.send_message("กรุณาใส่ตัวเลือกอย่างน้อย 2 อย่าง (เช่น ใช่,ไม่)", ephemeral=True)
    
    channel = bot.get_channel(announcement_channel_id)
    if not channel:
        return await interaction.response.send_message("❌ ไม่พบแชนแนลสำหรับประกาศ กรุณาตรวจสอบ ID", ephemeral=True)

    embed = discord.Embed(
        title="📊 LIVE POLL",
        description=f"# {question}\n\n*คลิกปุ่มด้านล่างเพื่อลงคะแนน*\n*ผู้สร้างสามารถกด Close Poll เพื่อปิดโหวตได้*",
        color=0x5865F2,
        timestamp=discord.utils.utcnow()
    )
    # ... (ส่วนที่เหลือของ poll เหมือนเดิม)
    await interaction.response.send_message("สร้างโหวตสำเร็จ", ephemeral=True)

# (คำสั่งอื่นๆ hello, announce, server_members, timer คงเดิม...)

server_on()
bot.run(os.getenv('TOKEN'))
