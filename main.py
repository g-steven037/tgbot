import os
import re
import io
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# 配置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 从 Docker 环境变量读取
TOKEN = os.getenv('TELEGRAM_TOKEN')
TMDB_KEY = os.getenv('TMDB_API_KEY')
FONT_PATH = os.getenv('FONT_PATH', 'simhei.ttf')

def get_tmdb_image(tmdb_id):
    """从 TMDB 获取剧照或海报"""
    # 先尝试获取 TV 信息，如果失败尝试 Movie
    types = ['tv', 'movie']
    for t in types:
        url = f"https://api.themoviedb.org/3/{t}/{tmdb_id}?api_key={TMDB_KEY}&language=zh-CN"
        try:
            res = requests.get(url, timeout=10).json()
            path = res.get('backdrop_path') or res.get('poster_path')
            if path:
                return f"https://image.tmdb.org/t/p/w1280{path}"
        except:
            continue
    return None

def generate_poster(text, img_url):
    """合成美化剧照"""
    # 1. 基础背景处理
    if img_url:
        bg_data = requests.get(img_url).content
        img = Image.open(io.BytesIO(bg_data)).convert("RGB")
    else:
        img = Image.new('RGB', (1280, 720), color=(30, 30, 30))

    # 2. 调暗背景，增加文字可读性
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.4)
    draw = ImageDraw.Draw(img)
    
    # 3. 加载字体
    try:
        title_font = ImageFont.truetype(FONT_PATH, 48)
        body_font = ImageFont.truetype(FONT_PATH, 28)
    except:
        title_font = body_font = ImageFont.load_default()

    # 4. 文字排版 (居中)
    lines = text.strip().split('\n')
    width, height = img.size
    y_offset = height // 4
    
    for i, line in enumerate(lines):
        current_font = title_font if i == 2 else body_font # 假设第3行是片名
        color = (255, 215, 0) if "tmdbid" in line else (255, 255, 255)
        
        # 计算文字位置
        bbox = draw.textbbox((0, 0), line, font=current_font)
        text_w = bbox[2] - bbox[0]
        draw.text(((width - text_w) // 2, y_offset), line, font=current_font, fill=color)
        y_offset += 65

    # 5. 输出流
    bio = io.BytesIO()
    img.save(bio, 'JPEG', quality=95)
    bio.seek(0)
    return bio

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text
    if not content: return
    
    # 提取 tmdbid
    match = re.search(r'tmdbid-(\d+)', content)
    if match:
        tmdb_id = match.group(1)
        logging.info(f"正在处理 TMDB ID: {tmdb_id}")
        
        img_url = get_tmdb_image(tmdb_id)
        poster = generate_poster(content, img_url)
        
        await update.message.reply_photo(photo=poster, caption="🎬 剧集卡片已生成")

if __name__ == '__main__':
    if not TOKEN or not TMDB_KEY:
        print("错误: 请在 docker-compose.yml 中配置 TOKEN 和 API_KEY")
        exit(1)
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_message))
    print("Bot 启动成功...")
    app.run_polling()
