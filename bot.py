import os
import yt_dlp
import static_ffmpeg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# FFmpeg-ni avtomatik sozlash
static_ffmpeg.add_paths()

# =========================
TOKEN = "8665295102:AAF4TALKq1tf9CGCGXIE7Mx3LZlrFLcitYU"
CHANNEL_USERNAME = "@tanishuvcatone" 
# =========================

if not os.path.exists('downloads'):
    os.makedirs('downloads')

search_results = {}

# YouTube uchun universal sozlamalar (Cookies bilan)
YDL_COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'referer': 'https://www.youtube.com/',
    'nocheckcertificate': True,
    'cookiefile': 'cookies.txt',  # Fayl nomi GitHub-da aynan shunday bo'lsin
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'player_skip': ['webpage', 'configs'],
        }
    }
}

async def is_subscribed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, chat_id)
        return member.status in ["member", "administrator", "creator"]
    except: return True

async def send_sub_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Kanalga o'tish 📢", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
                [InlineKeyboardButton("Obuna bo'ldim ✅", callback_data="check_sub")]]
    text = f"Botdan foydalanish uchun {CHANNEL_USERNAME} kanaliga obuna bo'lishingiz kerak!"
    if update.callback_query: await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await send_sub_request(update, context)
        return
    await update.message.reply_text("Salom! Qo'shiq nomi yoki YouTube link yuboring! 🎵")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await send_sub_request(update, context)
        return
    
    text = update.message.text
    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text(f"🔍 '{text}' qidirilmoqda...")

    try:
        # Qidiruv sozlamalari
        search_opts = {**YDL_COMMON_OPTS, 'extract_flat': True}
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            # Agar link bo'lsa to'g'ridan-to'g'ri olish, matn bo'lsa qidirish
            search_query = text if "http" in text else f"ytsearch10:{text}"
            info = ydl.extract_info(search_query, download=False)
            
            if 'entries' in info:
                entries = info['entries']
            else:
                entries = [info]

        if not entries or len(entries) == 0:
            await status_msg.edit_text("❌ Hech narsa topilmadi.")
            return

        keyboard = []
        results_text = "✨ **Topilgan variantlar:**\n\n"
        search_results[chat_id] = {}

        current_row = []
        for i, entry in enumerate(entries[:10]):
            title = entry.get('title', "Noma'lum")[:40]
            results_text += f"{i+1}. {title}\n"
            
            btn = InlineKeyboardButton(f"{i+1}", callback_data=f"dl_{i}")
            current_row.append(btn)
            if len(current_row) == 5:
                keyboard.append(current_row)
                current_row = []
            search_results[chat_id][str(i)] = {'url': entry.get('url') or entry.get('webpage_url'), 'title': title}

        if current_row: keyboard.append(current_row)
        await status_msg.delete()
        await update.message.reply_text(results_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    except Exception as e:
        print(f"Error: {e}")
        await status_msg.edit_text(f"❌ Xatolik: Cookies muddati o'tgan yoki YouTube blokladi.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "check_sub":
        if await is_subscribed(update, context):
            await query.message.delete()
            await query.message.reply_text("Rahmat! Endi foydalanishingiz mumkin. 🎵")
        return

    if query.data.startswith("dl_"):
        idx = query.data.replace("dl_", "")
        selected = search_results.get(chat_id, {}).get(idx)
        if selected:
            sent_msg = await query.message.reply_text(f"⏳ Yuklanmoqda: {selected['title']}...")
            path = f"downloads/mus_{chat_id}_{idx}.mp3"
            
            try:
                download_opts = {
                    **YDL_COMMON_OPTS,
                    'format': 'bestaudio/best',
                    'outtmpl': path[:-4],
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                }
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    ydl.download([selected['url']])
                
                await query.message.reply_audio(audio=open(path, 'rb'), caption=f"✅ {selected['title']}\n@tanishuvcatone")
                await sent_msg.delete()
                if os.path.exists(path): os.remove(path)
            except Exception as e:
                print(f"Download Error: {e}")
                await sent_msg.edit_text("⚠️ YouTube cheklovi (Sign in). Yangi cookies.txt yuklang.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()
