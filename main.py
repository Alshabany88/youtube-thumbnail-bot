# main.py - بوت تحميل صور يوتيوب
import telebot
import requests
import re
import os
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TOKEN = '8503136466:AAEGwmnaMnc3ASV8mG-_2twx5rpUSGRG_QQ'
YOUTUBE_API_KEY = 'AIzaSyDbSRy8bF22VMmvytE1Z2qFJDu2e-RRBrU'

bot = telebot.TeleBot(TOKEN)
TEMP_FOLDER = '/tmp'

# تهيئة YouTube API client
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def extract_video_id(url):
    """استخراج معرف الفيديو"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([\w-]+)',
        r'(?:youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/shorts\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/live\/)([\w-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_all_video_ids(text):
    """استخراج جميع معرفات الفيديو من النص"""
    lines = text.strip().split('\n')
    video_ids = []
    urls = []
    
    for line in lines:
        words = line.split()
        for word in words:
            video_id = extract_video_id(word)
            if video_id and video_id not in video_ids:
                video_ids.append(video_id)
                urls.append(word)
    
    return video_ids, urls

def get_video_info_with_api(video_id):
    """الحصول على معلومات الفيديو باستخدام YouTube API"""
    try:
        request = youtube.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if response['items']:
            video_data = response['items'][0]['snippet']
            title = video_data['title']
            
            thumbnails = video_data['thumbnails']
            
            quality_order = ['maxres', 'standard', 'high', 'medium', 'default']
            quality_names = {
                'maxres': '🔥 عالية جداً (HD 1080p)',
                'standard': '📺 عالية (SD 640p)',
                'high': '📱 متوسطة (480p)',
                'medium': '💻 عادية (360p)',
                'default': '📸 صغيرة (120p)'
            }
            
            for q in quality_order:
                if q in thumbnails:
                    img_url = thumbnails[q]['url']
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        filename = os.path.join(TEMP_FOLDER, f"{video_id}.jpg")
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                        return filename, quality_names[q], title
            
            return None, None, title
        else:
            return None, None, None
            
    except HttpError as e:
        print(f"❌ خطأ في YouTube API: {e}")
        return None, None, None

def download_thumbnail_fallback(video_id):
    """حل احتياطي إذا فشل API"""
    try:
        fallback_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        response = requests.get(fallback_url, timeout=10)
        if response.status_code == 200:
            filename = os.path.join(TEMP_FOLDER, f"{video_id}_fallback.jpg")
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename, "🔄 متوسط (احتياطي)", None
    except:
        pass
    return None, None, None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
🎬 **بوت تحميل صور يوتيوب المتطور!**

📥 **أرسل رابط فيديو أو عدة روابط وسأحمل لك الصور.**

✨ **المميزات:**
• 🔥 **أعلى دقة متاحة** (حتى 1080p)
• 📝 **عرض عنوان الفيديو**
• 🔗 **دعم عدة روابط** في رسالة واحدة
• 🚀 **معالجة متسلسلة** واحد تلو الآخر
• ✅ **باستخدام YouTube API الرسمي**

📌 **أمثلة:**
• رابط واحد: `https://youtu.be/dQw4w9WgXcQ`
• عدة روابط: (كل رابط في سطر منفصل)

https://youtu.be/VIDEO1
https://youtu.be/VIDEO2
https://youtu.be/VIDEO3

👨‍💻 **مطور:** @alshabany8
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    bot.send_chat_action(message.chat.id, 'typing')
    
    video_ids, urls = extract_all_video_ids(text)
    
    if not video_ids:
        bot.reply_to(message, "❌ **لم يتم العثور على روابط صحيحة!**\nيرجى إرسال رابط يوتيوب صحيح.", parse_mode='Markdown')
        return
    
    if len(video_ids) == 1:
        # حالة رابط واحد
        video_id = video_ids[0]
        original_url = urls[0]
        
        wait_msg = bot.reply_to(message, f"⏳ **جاري تحميل الصورة...**\n📹 `{video_id}`", parse_mode='Markdown')
        
        thumb_path, quality, title = get_video_info_with_api(video_id)
        
        if not thumb_path:
            thumb_path, quality, _ = download_thumbnail_fallback(video_id)
        
        if thumb_path:
            with open(thumb_path, 'rb') as photo:
                caption = f"✅ **تم التحميل بنجاح!**\n"
                if title:
                    # تنظيف العنوان من علامات Markdown الخاصة
                    clean_title = title.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
                    caption += f"\n📹 **العنوان:** {clean_title[:100]}"
                else:
                    caption += f"\n📹 **المعرف:** `{video_id}`"
                caption += f"\n🖼️ **الدقة:** {quality}"
                caption += f"\n🔗 **الرابط:** [اضغط هنا]({original_url})"
                
                bot.send_photo(
                    message.chat.id,
                    photo,
                    caption=caption,
                    parse_mode='Markdown'
                )
            
            bot.delete_message(message.chat.id, wait_msg.message_id)
            
            try:
                os.remove(thumb_path)
            except:
                pass
        else:
            bot.edit_message_text(
                "❌ **فشل تحميل الصورة!**",
                message.chat.id,
                wait_msg.message_id,
                parse_mode='Markdown'
            )
    
    else:
        # حالة عدة روابط
        status_msg = bot.reply_to(
            message, 
            f"🔄 **تم العثور على {len(video_ids)} رابط**\n⏳ جاري التحميل واحداً تلو الآخر...",
            parse_mode='Markdown'
        )
        
        successful = 0
        failed = 0
        
        for i, (video_id, original_url) in enumerate(zip(video_ids, urls), 1):
            bot.edit_message_text(
                f"🔄 **جاري التحميل...**\n"
                f"📊 **التقدم:** {i}/{len(video_ids)}\n"
                f"📹 **الحالي:** `{video_id}`",
                message.chat.id,
                status_msg.message_id,
                parse_mode='Markdown'
            )
            
            thumb_path, quality, title = get_video_info_with_api(video_id)
            
            if not thumb_path:
                thumb_path, quality, _ = download_thumbnail_fallback(video_id)
            
            if thumb_path:
                with open(thumb_path, 'rb') as photo:
                    caption = f"✅ **تم التحميل ({i}/{len(video_ids)})**\n"
                    if title:
                        clean_title = title.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
                        caption += f"\n📹 **العنوان:** {clean_title[:100]}"
                    else:
                        caption += f"\n📹 **المعرف:** `{video_id}`"
                    caption += f"\n🖼️ **الدقة:** {quality}"
                    caption += f"\n🔗 **الرابط:** [اضغط هنا]({original_url})"
                    
                    bot.send_photo(
                        message.chat.id,
                        photo,
                        caption=caption,
                        parse_mode='Markdown'
                    )
                
                successful += 1
                try:
                    os.remove(thumb_path)
                except:
                    pass
            else:
                failed += 1
                bot.reply_to(
                    message,
                    f"❌ **فشل تحميل:** `{video_id}`",
                    parse_mode='Markdown'
                )
            
            time.sleep(1)  # تأخير بسيط
        
        summary = f"📊 **ملخص التحميل:**\n"
        summary += f"✅ **نجح:** {successful}\n"
        summary += f"❌ **فشل:** {failed}\n"
        summary += f"📹 **الإجمالي:** {len(video_ids)}"
        
        bot.reply_to(message, summary, parse_mode='Markdown')
        bot.delete_message(message.chat.id, status_msg.message_id)

if __name__ == '__main__':
    print("=" * 60)
    print("🎬 بوت تحميل صور يوتيوب")
    print(f"🤖 اسم البوت: @YouTube_Playlist2_bot")
    print("📡 يعمل على Render مع YouTube API")
    print("=" * 60)
    bot.infinity_polling()