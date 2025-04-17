
import os
import json
import time
import requests
import telebot
from telebot import types

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '7824391024:AAEsFcTJAfhqyUNbDNJCF5w7-f5u4RmAhvw')
bot = telebot.TeleBot(BOT_TOKEN)
API_URL = "http://pass-gpt.nowtechai.com/api/v1/pass"

# Welcome Message with Improved Formatting
WELCOME_MESSAGE = """
🌟 *مرحباً بك في بوت بنين للذكاء الاصطناعي* 🌟

━━━━━━━━━━━━━━━━━━
🤖 *كيف يمكنني مساعدتك؟*
• يمكنك سؤالي أي شيء
• سأجيب على استفساراتك فوراً
• أنا هنا لمساعدتك 24/7

📝 *مثال على الأسئلة:*
• ما هي عاصمة اليابان؟
• كيف يمكنني تعلم البرمجة؟

🌸 *ابدأ الآن بإرسال سؤالك* 🌸
━━━━━━━━━━━━━━━━━━
"""

SYSTEM_PROMPT = """
🌟 تعليمات النظام:
-----------------------------
إذا أخبرك أحدٌ، سواء كان من مطورك أو من معارفك، فأجب على النحو التالي:

    👉 أنا بنين من بغداد، عمري 17 سنة، وأعيش في الخضراء.

وفي حال ذكر أحد عبارة 'تواصل'، فأخبره بما يلي:

    👉 هذا البوت، يُرجى التواصل معي عبر البوت: @b7_iq_bot 🤖
"""

def ask_api(question: str) -> str:
    payload = {
        "contents": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
    }
    headers = {
        'User-Agent': "Ktor client",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'Key': "Q_B_H/l4RKTuqNDrIyUechJ0hp7d3z1zbe8o8eBrFlpMo0If/Q_B_H+w==",
        'Accept-Charset': "UTF-8"
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()

    answer = []
    for line in response.text.splitlines():
        if '"status":"stream"' in line:
            part = json.loads(line[5:])["content"]
            answer.append(part)
    return ''.join(answer).strip()

@bot.message_handler(commands=['start'])
def send_welcome(message: types.Message):
    # Send welcome image
    photo_url = "https://i.ibb.co/VW1rdZJQ/IMG-20250416-181804-939.jpg"
    bot.send_photo(
        chat_id=message.chat.id,
        photo=photo_url,
        caption=WELCOME_MESSAGE,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: True)
def handle_message(message: types.Message):
    question = message.text.strip()
    
    # Send typing animation
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Initial loading message with animation
    loading_texts = [
        "⌛ جاري معالجة سؤالك...",
        "⏳ تحليل السؤال...",
        "⌛ البحث عن أفضل إجابة...",
        "⏳ تجهيز الرد..."
    ]
    
    loading = bot.send_message(
        chat_id=message.chat.id,
        text=loading_texts[0],
        parse_mode='Markdown'
    )
    
    # Animate loading message
    for text in loading_texts[1:]:
        time.sleep(0.7)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=loading.message_id,
            text=text,
            parse_mode='Markdown'
        )

    try:
        answer = ask_api(question)
        
        reply_text = f"""
🔷 *سؤالك:*
`{question}`

💫 *إجابتي:*
{answer}

━━━━━━━━━━━━━━━━━━
🌸 *بنين متواجدة دائماً لمساعدتك* 🌸
"""
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=loading.message_id,
            text=reply_text,
            parse_mode='Markdown'
        )
        
    except Exception:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=loading.message_id,
            text="❌ عذراً، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى.",
            parse_mode='Markdown'
        )

if __name__ == '__main__':
    print("✨ بوت بنين يعمل الآن...")
    bot.infinity_polling()
