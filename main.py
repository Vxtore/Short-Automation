import os
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
import requests
import json
import moviepy.editor as mp
import base64
from PIL import Image, ImageDraw, ImageFont
import cv2
import urllib.request 
import threading
import queue
from bs4 import BeautifulSoup
import asyncio
import uuid
os.environ['FFMPEG_BINARY'] = 'C:\\PATH_Programs\\ffmpeg.exe'
from io import BytesIO

intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
font_path = "C:\\Users\\bucke\\Downloads\\ShortsAuto\\burbank.otf"

def create_tts_order(session_id, text_speaker, req_text):
    headers = {
        'User-Agent': 'com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)',
        'Cookie': f'sessionid={session_id}'
    }
    url = f"https://api16-normal-useast5.us.tiktokv.com/media/api/text/speech/invoke/?text_speaker={text_speaker}&req_text={req_text}&speaker_map_type=0&aid=1233"
    r = requests.post(url, headers=headers)
    if r.json()["message"] == "Couldn't load speech. Try again.":
        return {"status": "Session ID is invalid", "status_code": 5}
    vstr = r.json()["data"]["v_str"]
    dur = r.json()["data"]["duration"]
    spkr = r.json()["data"]["speaker"]
    b64d = base64.b64decode(vstr)
    filename = 'output.mp3'
    with open(filename, "wb") as out:
        out.write(b64d)
    output_data = {
        "status": r.json()["message"].capitalize(),
        "status_code": r.json()["status_code"],
        "duration": dur,
        "speaker": spkr,
        "log": r.json()["extra"]["log_id"]
    }
    return output_data

def get_syllable_count(word):
    word = word.lower()  
    vowels = "aeiouy"
    count = 0
    if word[0] in vowels:
        count += 1
    for i in range(1, len(word)):
        if word[i] in vowels and word[i-1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if word.endswith("le"):
        count += 1
    if count == 0:
        count += 1
    return count

voices = {
    "Jessie": 'en_us_001',
}

emotes = {
    "Point": "Point.mp4",
    "Shuffle": "Shuffle.mp4",
    "Arm Wave": "Arm Wave.mp4",
    "Heart Skip": "Heart Skip.mp4",
    "Baby Dance": "Baby Dance.mp4",
}

color_mappings = {
    "Lime": (0, 255, 0),
    "Cyan": (0, 255, 255),
    "Blue": (0, 0, 255),
    "Pink": (255, 20, 147),
    "White": (255, 255, 255),
    "Purple": (138, 43, 226),
    "Orange": (255, 69, 0),
    "Yellow": (255, 255, 0),
    "Magenta": (255, 0, 255)
}


def create_text_image(text, font_path, fill_color, output_filename, text_color=None, font_size=90):
    im = Image.new('RGBA', (1920, 1080), (255, 255, 255, 0))
    font = ImageFont.truetype(font=font_path, size=font_size)
    drawer = ImageDraw.Draw(im)
    stroke_color = (0, 0, 0)

    shadow_offset = (3, 3)
    drawer.text((50 + shadow_offset[0], 10 + shadow_offset[1]), text, font=font, fill=(50, 50, 50), stroke_width=7, stroke_fill=stroke_color)
    drawer.text((50, 10), text, font=font, fill=text_color if text_color else fill_color, stroke_width=7, stroke_fill=stroke_color)
    im.save(output_filename)
    img = cv2.imread(output_filename, cv2.IMREAD_UNCHANGED)
    coords = cv2.findNonZero(img[..., 3]) 
    x, y, w, h = cv2.boundingRect(coords)
    rect = img[y:y+h, x:x+w]
    cv2.imwrite(output_filename, rect)
    
def resize_and_center_crop(img, desired_size=600):
    min_side = min(img.width, img.height)
    left_margin = (img.width - min_side) / 2
    top_margin = (img.height - min_side) / 2
    right_margin = left_margin + min_side
    bottom_margin = top_margin + min_side

    img = img.crop((left_margin, top_margin, right_margin, bottom_margin))
    
    img = img.resize((desired_size, desired_size), Image.LANCZOS)
    
    return img

def create_image_clips_from_url(image_url, rgb_filename, gray_filename):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(image_url, headers=headers)
    image_stream = BytesIO(response.content)
    pil_image = Image.open(image_stream).convert("RGBA")
    
    pil_image_cropped = resize_and_center_crop(pil_image)

    pil_image_cropped.save(rgb_filename, format="PNG")  

    alpha_channel = pil_image_cropped.split()[3]

    pil_image_gray = Image.merge("RGBA", (pil_image_cropped.convert("L"), pil_image_cropped.convert("L"), pil_image_cropped.convert("L"), alpha_channel))
    
    pil_image_gray.save(gray_filename, format="PNG")


video_generation_queue = queue.Queue()



def generate_video(args):
    ctx, text1, text2, voice, music, emote, list, reasons, image, textcolor, text1_size, text2_size, sfx = args 
    

    user_mention = ctx.user.mention
    embed = nextcord.Embed(
        title="Generating Your YT Short..",
        description=f"<:eta:1148494281628188692> ETA:  ``0-1 Minute(s)``\n"
                    f"<:length:1148494362880249917> Video Length: ``28 Seconds``\n"
                    f"<:voice:1148494371621191730> Voice Used: ``{voice}``\n"
                    f"<:font:1148494369985413130> Font Used: <:burbank1:1148494279921123368><:burbank2:1148494278776078346><:burbank3:1148494276372729937>\n"
                    f"<:emote:1148494377304477756> Emote Used: ``{emote}``\n"
                    f"<:sfx:1148495320544727080> Sound Used: ``{sfx}``\n"
                    f"<:textcolor:1148494366613176330> Text Color Used: ``{textcolor}``",
        color=0xf40407
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/831694132878508092.gif")
    embed.set_footer(text="discord.gg/shorts", icon_url="https://cdn.discordapp.com/attachments/1141823268978962464/1147324502158618714/Shorts_Automator_2.png")
    embed.timestamp = ctx.created_at

    combined_message = f"{user_mention}\n\n"
    for field in embed.fields:
        combined_message += f"{field.name}: {field.value}\n"

    asyncio.run_coroutine_threadsafe(ctx.send(content=combined_message, embed=embed), bot.loop)

def video_generation_worker():
    while True:
        args = video_generation_queue.get() 
        generate_video(args)
        video_generation_queue.task_done()

@bot.slash_command(name="generate")
async def generate(ctx, 
                   text1: str = nextcord.SlashOption(description="example: Roblox Games, Roblox YouTubers", required=True),
                   text2: str = nextcord.SlashOption(description="example: That Died, That Are Sus", required=True),
                   voice: str = nextcord.SlashOption(description="voice to be used for text to speech", choices=list(voices.keys()), required=True),
                   music: str = nextcord.SlashOption(description="audio edit to play in the short", choices=["House Of Memories (Basic)", "House Of Memories (Dramatic)",  "House Of Memories (Sped Up)", "After Dark x Sweater Weather (Basic)","After Dark x Sweater Weather (Dramatic)", "Money So Big (Basic)", "Money So Big (Dramatic)", "Miss You (Sped Up)", "Another Love (Sad)", "No Music"], required=True),
                   emote: str = nextcord.SlashOption(description="roblox emote that will be in the background", choices=list(emotes.keys()), required=True),
                   list: str = nextcord.SlashOption(description="example: Adopt Me,Work At A Pizza Place,Jailbreak", required=True),
                   reasons: str = nextcord.SlashOption(description="example: Boring,Old,Toxic", required=True),
                   image: str = nextcord.SlashOption(description="separate your 3 images with a comma (example: discord.com/image.png,discord.com/image.png)", required=True),
                   textcolor: str = nextcord.SlashOption(description="color for the text", choices=list(color_mappings.keys()), required=False),
                   reason_color: str = nextcord.SlashOption(description="color for the reasons text", choices=list(color_mappings.keys()), required=False),
                   text1_size: int = nextcord.SlashOption(description="font size for text1", choices=[60, 70, 80, 100], required=False),
                   text2_size: int = nextcord.SlashOption(description="font size for text2", choices=[60, 70, 80, 100], required=False),
                   reason_size: int = nextcord.SlashOption(description="font size for reasons", choices=[60, 70, 80, 100], required=False),
                   sfx: str = nextcord.SlashOption(description="sound effect to play in the background", choices=["Vine Boom", "Money"], required=False)):

    if ctx.channel.category_id != 1139392281829453856:
        await ctx.send("This command can only be used in the designated channel!")
        return
    
    task_args = (ctx, text1, text2, voice, music, emote, list, reasons, image, textcolor, text1_size, text2_size, sfx)
    video_generation_queue.put(task_args)

    reason_font_size = reason_size if reason_size else 90 

    if reason_color:
        chosen_reason_color = color_mappings[reason_color]
    else:
        chosen_reason_color = (255, 0, 0)  

    if textcolor:
        chosen_color = color_mappings[textcolor]
    else:
        chosen_color = (255, 255, 255) 

    text1_font_size = text1_size if text1_size else 90  
    text2_font_size = text2_size if text2_size else 90  

    text1 = text1.replace('|', '\n')
    text2 = text2.replace('|', '\n')
    text1 = text1.replace('|', '\n')
    text2 = text2.replace('|', '\n')
    list_texts = list.split(',')
    if len(list_texts) != 3:
        await ctx.send("Your list must be seperated with commas!")
        return

    reasons_texts = reasons.split(',')
    if len(reasons_texts) != 3:
        await ctx.send("The reasons must be seperated with commas!")
        return

    full_text = text1 + ' ' + text2

    session_id = "109dac84f6874fd4dd8edc4e5655281e"
    user_mention = ctx.user.mention
    embed = nextcord.Embed(
        title="Generating Your YT Short..",
        description=f"<:eta:1148494281628188692> ETA:  ``0-1 Minute(s)``\n"
                    f"<:length:1148494362880249917> Video Length: ``28 Seconds``\n"
                    f"<:voice:1148494371621191730> Voice Used: ``{voice}``\n"
                    f"<:font:1148494369985413130> Font Used: <:burbank1:1148494279921123368><:burbank2:1148494278776078346><:burbank3:1148494276372729937>\n"
                    f"<:emote:1148494377304477756> Emote Used: ``{emote}``\n"
                    f"<:sfx:1148495320544727080> Sound Used: ``{sfx}``\n"
                    f"<:textcolor:1148494366613176330> Text Color Used: ``{textcolor}``",
        color=0xf40407
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/831694132878508092.gif")
    embed.set_footer(text="discord.gg/shorts", icon_url="https://cdn.discordapp.com/attachments/1138893322996424734/1149532130934804540/34ed3fc6c7a69d42fe392d05c7cca025-modified.png")
    embed.timestamp = ctx.created_at

    combined_message = f"{user_mention}\n\n"
    for field in embed.fields:
        combined_message += f"{field.name}: {field.value}\n"

    message = await ctx.send(content=combined_message, embed=embed)
    
    tts_text = full_text.replace('.', ',').replace('!', '.').replace('"', '')
    text_speaker = voices[voice]
    words = tts_text.split()
    audio_clips = []
    text_clips = []
    start_time = 0
    text1_words = text1.split()
    text2_words = text2.split()

    response_data = create_tts_order(session_id, text_speaker, text1)
    if response_data['status_code'] != 0:
        await ctx.send(f"TTS generation error: {response_data['status']}")
        return

    audio_clip = mp.AudioFileClip('output.mp3')
    audio_clips.append(audio_clip)

    create_text_image(text1, font_path, (255, 255, 255), "text1.png", text_color=chosen_color, font_size=text1_font_size)
    text_clip = mp.ImageClip("text1.png").set_duration(audio_clip.duration).set_position('center').set_start(start_time)
    text_clips.append(text_clip)
    start_time += audio_clip.duration

    response_data = create_tts_order(session_id, text_speaker, text2)
    if response_data['status_code'] != 0:
        await ctx.send(f"TTS generation error: {response_data['status']}")
        return

    audio_clip = mp.AudioFileClip('output.mp3')
    audio_clips.append(audio_clip)

    create_text_image(text2, font_path, (255, 255, 255), "text2.png", text_color=chosen_color, font_size=text2_font_size)
    text_clip = mp.ImageClip("text2.png").set_duration(audio_clip.duration).set_position('center').set_start(start_time)
    text_clips.append(text_clip)
    start_time += audio_clip.duration

    image_urls = image.split(',')
    if len(image_urls) != 3:
        await ctx.send("Please provide 3 image URLs separated by commas!")
        return

    image_clips_rgb = []
    image_clips_gray = []

    for idx, img_url in enumerate(image_urls):
        create_image_clips_from_url(img_url, f"image_rgb_{idx}.png", f"image_gray_{idx}.png")
        image_rgb_clip = mp.ImageClip(f"image_rgb_{idx}.png").set_duration(3).set_start(10 + idx*6).set_position("center")
        image_gray_clip = mp.ImageClip(f"image_gray_{idx}.png").set_duration(3).set_start(13 + idx*6).set_position("center")
        image_clips_rgb.append(image_rgb_clip)
        image_clips_gray.append(image_gray_clip)

    reasons_clips = []
    for idx, reason in enumerate(reasons_texts):
        create_text_image(reason, font_path, chosen_reason_color, f"reason_{idx}.png", font_size=reason_font_size)
        reason_clip = mp.ImageClip(f"reason_{idx}.png").set_duration(3).set_start(13 + idx*6).set_position("center")
        reasons_clips.append(reason_clip)

    list_clips = []
    for idx, text in enumerate(list_texts):
        create_text_image(text, font_path, (255, 255, 255), f"list_{idx}.png")
        if idx == 0:
            list_clip = mp.ImageClip(f"list_{idx}.png").set_duration(3).set_start(10).set_position("center")
        else:
            list_clip = mp.ImageClip(f"list_{idx}.png").set_duration(3).set_start(16 + (idx - 1)*6).set_position("center")
        list_clips.append(list_clip)
        
    video_filename = emotes[emote]
    video = mp.VideoFileClip(video_filename)

    gameplay_audio = video.audio
    background_music = mp.AudioFileClip(f"C:\\Users\\bucke\\Downloads\\SA\\{music}.mp3").subclip(0, video.duration)

    audio_clips_to_combine = [mp.concatenate_audioclips(audio_clips).volumex(0.6), gameplay_audio.volumex(0.4)]

    sfx_audio = None

    if sfx == "Vine Boom":
        sfx_audio = mp.AudioFileClip("Vine Boom.mp3").subclip(0, video.duration)
    elif sfx == "Money":
        sfx_audio = mp.AudioFileClip("Money.mp3").subclip(0, video.duration)
        if sfx_audio:
            background_music = mp.CompositeAudioClip([background_music, sfx_audio]).volumex(0.4)

    audio_clips_to_combine.append(background_music)
    final_audio = mp.CompositeAudioClip(audio_clips_to_combine)
    final_video = mp.CompositeVideoClip([video.set_audio(final_audio), *text_clips, *image_clips_rgb, *image_clips_gray, *reasons_clips, *list_clips]).set_duration(video.duration)
    final_video.write_videofile('output.mp4', audio_codec='aac')

    with open('output.mp4', 'rb') as file:
        await ctx.send(file=nextcord.File(file, 'output.mp4'))

def save_image_from_url(url, path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(path, 'wb') as file:
        for chunk in response.iter_content(8192):
            file.write(chunk)

@bot.slash_command(name="game-icon")
async def game_icon_command(interaction: Interaction,
                            game_link: str = SlashOption(
                                name="link",
                                required=True)):
    try:
        game_id = game_link.split("/")[4]
    except:
        return await interaction.send(":x:")

    file_id = str(uuid.uuid4())
    res = requests.get(f'https://rp.elijah.rip/game-icon?id={game_id}')
    data = res.json()
    path = f"downloads/{file_id}.png"
    save_image_from_url(data['iconUrl'], path)
    with Image.open(path) as img:
        grayscale = img.convert('L')
        grayscale.save(f"downloads/{file_id}_gray.png")

    game_icon = nextcord.File(path, filename=f"{game_id}-Icon.png")
    game_icon_grayscale = nextcord.File(f"downloads/{file_id}_gray.png",
                                        filename=f"{game_id}-Grayscale.png")
    return await interaction.send(files=[game_icon, game_icon_grayscale])

@bot.slash_command(name="pfp",)
async def pfp_command(
    interaction: Interaction, 
    channel_url: str = SlashOption(
        name="channel",
        required=True
    )
):
    await interaction.response.defer()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(channel_url, headers=headers)
    if response.status_code != 200:
        return await interaction.send(":x:")

    soup = BeautifulSoup(response.content, 'html.parser')
    filename = str(uuid.uuid4())
    meta_tag = soup.find('meta', attrs={'property': 'og:image'})

    if meta_tag and 'content' in meta_tag.attrs:
        url = meta_tag['content']
        save_image_from_url(url, f"downloads/{filename}.png")
        path = f"downloads/{filename}.png"

        with Image.open(path) as img:
            grayscale = img.convert('L')
            grayscale.save(f"downloads/{filename}_gray.png")
    
        pfp = nextcord.File(path, filename=f"Channel-Icon.png")
        pfp_grayscale = nextcord.File(f"downloads/{filename}_gray.png",
                                            filename=f"Channel-Grayscale.png")
        await interaction.send(files=[pfp, pfp_grayscale])

@bot.slash_command(name="sendjson", description="send json data from discohook to any channel")
async def sendjson(ctx, channel: nextcord.TextChannel, json_data: str):
    if ctx.user.id != 816042009834815578:
        embed = nextcord.Embed(
            description="You do not have permission to use this command",
            color=0xf40407
        )
        await ctx.send(embed=embed)
        return
    try:
        data = json.loads(json_data)
        
        embeds = []
        for embed_data in data.get("embeds", []):
            if "timestamp" in embed_data and embed_data["timestamp"].endswith("Z"):
                embed_data["timestamp"] = embed_data["timestamp"].rstrip("Z")
            embed = nextcord.Embed.from_dict(embed_data)
            embeds.append(embed)        
        for embed in embeds:
            await channel.send(embed=embed)
        await ctx.send("✅")
    except json.JSONDecodeError:
        await ctx.send("Invalid JSON data provided")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.event
async def on_ready():
    print("Bot is online!")
    
    worker_thread = threading.Thread(target=video_generation_worker)
    worker_thread.start()

bot.run('MTE1NDIxMDAxODQ2ODU3MzMwNg.Gi3N4s.-EwZf9fME0NuVrf9p-QoJntkYj11ajAqeeYD7M')