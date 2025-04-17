
import telebot
import requests
import time
import os
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

# إعداد توكن البوت وتوكن Replicate
BOT_TOKEN = "8138585271:AAEGr5xnOmncU23__Zwza5Xem8e_9nZ-jwc"
REPLICATE_API_TOKEN = "r8_FauzCwlUMn8eDDjUBv7PDxU2EIlol9401y5C3"
REPLICATE_URL = "https://api.replicate.com/v1/models/anthropic/claude-3.7-sonnet/predictions"

bot = telebot.TeleBot(BOT_TOKEN)

# تخزين بيانات المستخدم والتحكم في معدل الاستخدام
user_data = {}
rate_limit_data = defaultdict(lambda: {"count": 0, "reset_time": None})
line_limit_usage = defaultdict(int)  # تتبع استخدام حد الأسطر

RATE_LIMIT = 10  # عدد المرات المسموح بها
RATE_LIMIT_PERIOD = 18 * 60  # 15 دقيقة بالثواني
MAX_LINES_LIMIT = 1100  # الحد الأقصى للأسطر
REDUCED_LINES_LIMIT = 480  # الحد المخفض للأسطر
MAX_HIGH_LIMIT_USAGE = 3  # عدد المرات المسموح بها للحد الأعلى

def check_rate_limit(chat_id):
    now = datetime.now()
    user_limit = rate_limit_data[chat_id]
    
    if user_limit["reset_time"] is None or now >= user_limit["reset_time"]:
        user_limit["count"] = 0
        user_limit["reset_time"] = now + timedelta(seconds=RATE_LIMIT_PERIOD)
    
    if user_limit["count"] >= RATE_LIMIT:
        remaining_time = (user_limit["reset_time"] - now).seconds
        return False, remaining_time
    
    user_limit["count"] += 1
    return True, 0

def send_animated_wait_message(chat_id):
    stages = ["⌛️ جاري المعالجة", "⏳ جاري المعالجة.", "⌛️ جاري المعالجة..", "⏳ جاري المعالجة..."]
    message = bot.send_message(chat_id, stages[0])
    for i in range(3):
        time.sleep(0.7)
        bot.edit_message_text(stages[i+1], chat_id, message.message_id)
    return message

def send_long_message(chat_id, text, chunk_size=4096):
    for i in range(0, len(text), chunk_size):
        bot.send_message(chat_id, text[i:i+chunk_size])

def get_file_extension(question, script_content):
    combined_text = (question + " " + script_content).lower()
    if any(lang in combined_text for lang in ["python", "بايثون", "سكربت", "اداة"]):
        return ".py"
    elif "html" in combined_text:
        return ".html"
    return ".py"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
🌟 *مرحباً بك في بوت تحليل وتحسين السكربتات* 🌟

🔹 يمكنك استخدام البوت للحصول على:
   • تحليل تفصيلي للكود
   • اقتراحات للتحسين
   • شرح مفصل للسكربت

📝 *كيفية الاستخدام:*
1. أرسل سؤالك أو طلبك
2. أرسل ملف السكربت
3. انتظر التحليل والنتائج

⚠️ *ملاحظة:* يمكنك استخدام البوت 10 مرات كل 15 دقيقة

🚀 ابدأ الآن بإرسال سؤالك!
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text != "/start" and m.chat.id not in user_data)
def process_question(message):
    chat_id = message.chat.id
    can_proceed, wait_time = check_rate_limit(chat_id)
    
    if not can_proceed:
        minutes = wait_time // 60
        seconds = wait_time % 60
        bot.reply_to(message, f"⚠️ لقد تجاوزت الحد المسموح به. الرجاء الانتظار {minutes} دقيقة و {seconds} ثانية.")
        return
    
    user_data[chat_id] = {"question": message.text}
    bot.reply_to(message, "📤 الرجاء إرسال ملف السكربت الآن...")

@bot.message_handler(content_types=['document'])
def process_document(message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or "question" not in user_data[chat_id]:
        bot.reply_to(message, "❌ يرجى بدء المحادثة بإرسال السؤال أولاً باستخدام /start")
        return

    # التحقق من عدد الأسطر في الملف
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    script_content = downloaded_file.decode('utf-8')
    line_count = len(script_content.splitlines())
    
    current_limit = MAX_LINES_LIMIT if line_limit_usage[chat_id] < MAX_HIGH_LIMIT_USAGE else REDUCED_LINES_LIMIT
    
    if line_count > current_limit:
        remaining_high_limit = MAX_HIGH_LIMIT_USAGE - line_limit_usage[chat_id]
        if current_limit == MAX_LINES_LIMIT:
            line_limit_usage[chat_id] += 1
            bot.reply_to(message, f"⚠️ تم استخدام {line_limit_usage[chat_id]} من {MAX_HIGH_LIMIT_USAGE} مرات للحد الأقصى ({MAX_LINES_LIMIT} سطر)")
        else:
            bot.reply_to(message, f"⚠️ لقد تجاوزت الحد المسموح به ({current_limit} سطر). الرجاء تقليل عدد الأسطر.")
            return
    
    wait_message = send_animated_wait_message(chat_id)
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        script_content = downloaded_file.decode('utf-8')
        
        question = user_data[chat_id]["question"]
        prompt_text = f"{question}\n\nالسكربت:\n{script_content}"
        
        data = {
            "input": {
                "prompt": prompt_text,
                "max_tokens": 64000,
                "system_prompt": "",
                "max_image_resolution": 0.5,
            }
        }
        
        headers = {
            "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }
        
        response = requests.post(REPLICATE_URL, headers=headers, json=data)
        response_json = response.json()
        
        get_url = response_json.get("urls", {}).get("get", "")
        output = ""
        
        if get_url:
            while True:
                status_response = requests.get(get_url, headers=headers).json()
                status = status_response.get("status")
                if status == "succeeded":
                    output = status_response.get("output", "")
                    break
                elif status == "failed":
                    bot.edit_message_text("❌ فشل في معالجة الطلب", chat_id, wait_message.message_id)
                    return
                time.sleep(1)
        
        # معالجة المخرجات وإرسال النتائج
        if isinstance(output, list):
            answer_text = "".join(output)
        else:
            answer_text = output
            
        code_pattern = r"```(?:python)?\s*\n(.*?)```"
        match = re.search(code_pattern, answer_text, re.DOTALL)
        
        if match:
            code_part = match.group(1).strip()
            explanation_text = re.sub(code_pattern, "", answer_text, flags=re.DOTALL).strip()
        else:
            code_part = answer_text.strip()
            explanation_text = "🔍 تحليل السكربت المقدم"
            
        file_extension = get_file_extension(question, script_content)
        random_filename = f"{uuid.uuid4()}{file_extension}"
        
        with open(random_filename, "w", encoding="utf-8") as file:
            file.write(code_part)
            
        bot.delete_message(chat_id, wait_message.message_id)
        
        # إرسال النتائج بتنسيق جميل
        result_message = f"""
✨ *تم تحليل السكربت بنجاح* ✨

📝 *التحليل والشرح:*
{explanation_text}

🔧 *السكربت المحسن مرفق أدناه* 🔧
"""
        
        bot.send_message(chat_id, result_message, parse_mode="Markdown")
        
        with open(random_filename, "rb") as file:
            bot.send_document(chat_id, file, caption="🚀 السكربت المحسن")
            
        # تنظيف
        os.remove(random_filename)
        del user_data[chat_id]
        
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ: {str(e)}", chat_id, wait_message.message_id)

bot.polling()
