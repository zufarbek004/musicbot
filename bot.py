import os
import yt_dlp
from shazamio import Shazam
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# =========================
TOKEN = "8665295102:AAF4TALKq1tf9CGCGXIE7Mx3LZlrFLcitYU"
CHANNEL_USERNAME = "@tanishuvcatone" 
# =========================

if not os.path.exists('downloads'):
    os.makedirs('downloads')

search_results = {}
user_links = {}

# YouTube blokirovkalarini chetlab o'tish uchun universal sozlamalar
YDL_COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'referer': 'https://www.google.com/',
    'nocheckcertificate': True,
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
    await update.message.reply_text("Salom! Qo'shiq nomi yoki link yuboring! 🎵")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await send_sub_request(update, context)
        return
    
    text = update.message.text
    chat_id = update.effective_chat.id

    if "http" in text:
        user_links[chat_id] = text
        keyboard = [[InlineKeyboardButton("🎥 Video", callback_data="v"), 
                     InlineKeyboardButton("🎵 Music Shazam", callback_data="s")]]
        await update.message.reply_text("Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        status_msg = await update.message.reply_text(f"🔍 '{text}' qidirilmoqda...")
        try:
            ydl_opts = {**YDL_COMMON_OPTS, 'extract_flat': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch10:{text}", download=False)
                entries = info.get('entries', [])

            if not entries:
                await status_msg.edit_text("❌ Hech narsa topilmadi.")
                return

            keyboard = []
            results_text = "✨ **Topilgan variantlar:**\n\n"
            search_results[chat_id] = {}

            current_row = []
            for i, entry in enumerate(entries):
                title = entry.get('title', "Noma'lum")[:40]
                results_text += f"{i+1}. {title}\n"
                
                btn = InlineKeyboardButton(f"{i+1}", callback_data=f"dl_{i}")
                current_row.append(btn)
                if len(current_row) == 5:
                    keyboard.append(current_row)
                    current_row = []
                search_results[chat_id][str(i)] = {'url': entry.get('url'), 'title': title}

            if current_row: keyboard.append(current_row)
            await status_msg.delete()
            await update.message.reply_text(results_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        except Exception as e:
            await status_msg.edit_text(f"❌ Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id

    if query.data == "check_sub":
        await query.answer()
        if await is_subscribed(update, context):
            await query.message.delete()
            await query.message.reply_text("Rahmat! Endi foydalanishingiz mumkin. 🎵")
        return

    if query.data.startswith("dl_"):
        idx = query.data.replace("dl_", "")
        selected = search_results.get(chat_id, {}).get(idx)
        if selected:
            await query.answer(f"Yuklanmoqda: {selected['title']}")
            path = f"downloads/mus_{chat_id}_{idx}.mp3"
            try:
                ydl_opts = {
                    **YDL_COMMON_OPTS,
                    'format': 'bestaudio/best',
                    'outtmpl': path[:-4],
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([selected['url']])
                
                await query.message.reply_audio(audio=open(path, 'rb'), caption=f"✅ {selected['title']}\n@tanishuvcatone")
                if os.path.exists(path): os.remove(path)
            except Exception as e:
                await query.message.reply_text("⚠️ YouTube cheklovi sababli yuklab bo'lmadi. Boshqa variantni koring.")
        return

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()
