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

# Vaqtinchalik ma'lumotlar ombori
search_results = {}
user_links = {}

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
        # TUGMA NOMI O'ZGARTIRILDI:
        keyboard = [[InlineKeyboardButton("🎥 Video", callback_data="v"), 
                     InlineKeyboardButton("🎵 Music Shazam", callback_data="s")]]
        await update.message.reply_text("Link aniqlandi. Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        status_msg = await update.message.reply_text(f"🔍 '{text}' bo'yicha 10 ta variant qidirilmoqda...")
        try:
            ydl_opts = {'quiet': True, 'extract_flat': True, 'force_generic_ext': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 10 TA NATIJANI QIDIRISH
                info = ydl.extract_info(f"ytsearch10:{text}", download=False)
                entries = info['entries']

            if not entries:
                await status_msg.edit_text("❌ Hech narsa topilmadi.")
                return

            keyboard = []
            results_text = "✨ **Topilgan 10 ta variant:**\n\n"
            search_results[chat_id] = {}

            # Natijalarni 2 ustunli tugma qilib chiqarish (chiroyli bo'lishi uchun)
            current_row = []
            for i, entry in enumerate(entries):
                title = entry.get('title', "Noma'lum")[:45]
                duration = entry.get('duration')
                time_str = f"({int(duration//60)}:{int(duration%60):02d})" if duration else ""
                
                results_text += f"{i+1}. {title} {time_str}\n"
                
                btn = InlineKeyboardButton(f"{i+1}-variant", callback_data=f"dl_{i}")
                current_row.append(btn)
                if len(current_row) == 2: # Har 2 ta tugmadan keyin yangi qator
                    keyboard.append(current_row)
                    current_row = []
                
                search_results[chat_id][str(i)] = {'url': entry.get('url'), 'title': title}

            if current_row: keyboard.append(current_row)

            await status_msg.delete()
            await update.message.reply_text(results_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        except Exception as e:
            await status_msg.edit_text(f"❌ Xatolik: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    # await query.answer() # Bu yerda javobni pastroqda beramiz

    if query.data == "check_sub":
        await query.answer()
        if await is_subscribed(update, context):
            await query.message.delete()
            await query.message.reply_text("Rahmat! Endi foydalanishingiz mumkin. 🎵")
        else: await context.bot.send_message(chat_id, "Hali obuna bo'lmagansiz!")
        return

    # QIDIRUV NATIJASINI YUKLASH
    if query.data.startswith("dl_"):
        idx = query.data.replace("dl_", "")
        if chat_id in search_results and idx in search_results[chat_id]:
            selected = search_results[chat_id][idx]
            
            # TUGMALAR O'CHMASLIGI UCHUN query.answer ishlatamiz xolos
            await query.answer(f"Yuklanmoqda: {selected['title']}", show_alert=False)
            
            path = f"downloads/mus_{chat_id}_{idx}.mp3"
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': path[:-4],
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    'quiet': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([selected['url']])
                
                await query.message.reply_audio(audio=open(path, 'rb'), caption=f"✅ {selected['title']}\nBy {CHANNEL_USERNAME}")
                os.remove(path)
            except Exception as e:
                await query.message.reply_text(f"Xato: {e}")
        return

    # LINKLAR UCHUN (Video/Shazam)
    await query.answer()
    url = user_links.get(chat_id)
    if not url: return
    
    # Bu yerda edit_message o'rniga reply ishlatamiz, tugmalar yo'qolmasligi uchun
    msg = await query.message.reply_text("⏳ Jarayon boshlandi...")
    try:
        if query.data == "v":
            path = f"downloads/v_{chat_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'quiet': True}) as ydl:
                ydl.download([url])
            await query.message.reply_video(video=open(path, 'rb'), caption=CHANNEL_USERNAME)
            os.remove(path)
        elif query.data == "s":
            temp = f"downloads/t_{chat_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'bestaudio', 'outtmpl': temp, 'quiet': True}) as ydl:
                ydl.download([url])
            shazam = Shazam()
            out = await shazam.recognize_song(temp)
            if out.get('track'):
                name = f"{out['track']['subtitle']} - {out['track']['title']}"
                await query.message.reply_text(f"✅ Topildi: {name}\nYuklanmoqda...")
                path = f"downloads/a_{chat_id}.mp3"
                opts = {'format': 'bestaudio', 'outtmpl': path[:-4], 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]}
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([f"ytsearch1:{name} audio"])
                await query.message.reply_audio(audio=open(path, 'rb'), title=out['track']['title'], performer=out['track']['subtitle'])
                os.remove(path)
            os.remove(temp)
        await msg.delete()
    except Exception as e: await query.message.reply_text(f"Xato: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))

print("Bot Pro (10 variant + Doimiy tugmalar) ishga tushdi...")
app.run_polling()
