import asyncio
import random
import logging
import copy
import os
import importlib
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiohttp import web  # Web server uchun qo'shildi

# --- SOZLAMALAR ---
TOKEN = "8572643134:AAGssm23gt_MuS5Y8kZ6XbTUeiVb1dFs91A"
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_test_data = {}

# --- WEB SERVER QISMI (Cron-job uchun) ---
async def handle(request):
    """Cron-job so'rov yuborganda 'OK' javobini qaytaradi"""
    return web.Response(text="Bot is running...")

async def start_web_server():
    """Render bergan PORTda kichik web serverni ishga tushiradi"""
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render avtomatik beradigan PORT ni oladi, bo'lmasa 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web server {port}-portda ishga tushdi.")

# --- 1. DINAMIK YUKLOVCHI ---
def get_dynamic_source(text):
    try:
        c_num = re.search(r'\d+', text).group() if re.search(r'\d+', text) else ""
        suffix = "ut" if any(x in text for x in ["O'zb", "🇺🇿"]) else "jt"
        
        if "💡" in text or "Ixtirolar" in text: target_file = "data_ixtirolar"
        elif "📚" in text or "Asarlar" in text: target_file = "data_asarlar"
        elif "🚩" in text or "Mustamlakachilik" in text: target_file = "data_mustamlakachilik"
        elif "Asrlar" in text: target_file = f"data_{c_num}{suffix}_asrlar"
        elif "Yillar" in text: target_file = f"data_{c_num}{suffix}_yillar"
        elif "📖" in text or "Atamalar" in text:
            target_file = "data_6_atamalar" if c_num == "6" else f"data_{c_num}{suffix}_atamalar"
        elif "👤" in text or "Shaxslar" in text:
            target_file = f"data_{c_num}{suffix}_shaxslar"
        else:
            target_file = "data_6" if c_num == "6" else f"data_{c_num}{suffix}"

        if os.path.exists(f"{target_file}.py"):
            module = importlib.import_module(target_file)
            importlib.reload(module)
            for attr in dir(module):
                if not attr.startswith("__"):
                    val = getattr(module, attr)
                    if isinstance(val, list): return val
    except: return None
    return None

# --- 2. MENYULAR ---
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.row(types.KeyboardButton(text="⏳ Xronologiya"), types.KeyboardButton(text="📖 Atamalar"))
    kb.row(types.KeyboardButton(text="👤 Shaxslar"), types.KeyboardButton(text="💡 Ixtirolar"))
    kb.row(types.KeyboardButton(text="📚 Asarlar"), types.KeyboardButton(text="🚩 Mustamlakachilik"))
    return kb.as_markup(resize_keyboard=True)

def subject_menu(class_num, prefix):
    kb = ReplyKeyboardBuilder()
    if class_num in ["9", "10", "11"] and "⏳" in prefix:
        kb.row(types.KeyboardButton(text=f"🇺🇿 {class_num}-O'zb (Yillar)"), types.KeyboardButton(text=f"🇺🇿 {class_num}-O'zb (Asrlar)"))
        kb.row(types.KeyboardButton(text=f"🌍 {class_num}-Jahon (Yillar)"), types.KeyboardButton(text=f"🌍 {class_num}-Jahon (Asrlar)"))
    else:
        kb.row(types.KeyboardButton(text=f"🇺🇿 {class_num}-O'zbekiston ({prefix})"),
               types.KeyboardButton(text=f"🌍 {class_num}-Jahon ({prefix})"))
    kb.row(types.KeyboardButton(text="⬅️ Ortga"))
    return kb.as_markup(resize_keyboard=True)

# --- 3. HANDLERLAR ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Bo'limni tanlang:", reply_markup=main_menu())

@dp.message(F.text == "⬅️ Ortga")
async def go_back(message: types.Message):
    await cmd_start(message)

@dp.message(F.text.in_({"💡 Ixtirolar", "📚 Asarlar", "🚩 Mustamlakachilik"}))
async def direct_test(message: types.Message):
    source = get_dynamic_source(message.text)
    if source: await start_test(message, source)

@dp.message(F.text.in_({"⏳ Xronologiya", "📖 Atamalar", "👤 Shaxslar"}))
async def select_cat(message: types.Message):
    prefix = message.text.split(" ")[0]
    kb = ReplyKeyboardBuilder()
    for i in range(6, 12): kb.add(types.KeyboardButton(text=f"{i}-sinf ({prefix})"))
    kb.adjust(2).row(types.KeyboardButton(text="⬅️ Ortga"))
    await message.answer("Sinfni tanlang:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text.regexp(r"^\d+-sinf \("))
async def select_class(message: types.Message):
    c_num = re.search(r'\d+', message.text).group()
    prefix = message.text.split("(")[1].split(")")[0]
    if c_num == "6":
        source = get_dynamic_source(message.text)
        if source: await start_test(message, source)
        else: await message.answer("⚠️ 6-sinf fayli topilmadi!")
    else:
        await message.answer("Yo'nalishni tanlang:", reply_markup=subject_menu(c_num, prefix))

@dp.message(F.text.contains("🇺🇿") | F.text.contains("🌍") | F.text.contains("Yillar") | F.text.contains("Asrlar"))
async def start_final_test(message: types.Message):
    source = get_dynamic_source(message.text)
    if source: await start_test(message, source)
    else: await message.answer("⚠️ Ma'lumot topilmadi!")

async def start_test(message, source):
    user_id = message.from_user.id
    questions = [copy.deepcopy(q) for q in source]
    random.shuffle(questions)
    user_test_data[user_id] = {"qs": questions, "curr": 0, "score": 0}
    await send_q(message.chat.id, user_id)

async def send_q(chat_id, user_id):
    data = user_test_data.get(user_id)
    if not data or data["curr"] >= len(data["qs"]):
        if data:
            await bot.send_message(chat_id, f"🏁 Yakunlandi: {data['score']}/{len(data['qs'])}", reply_markup=main_menu())
            user_test_data.pop(user_id, None)
        return
    q = data["qs"][data["curr"]]
    kb = InlineKeyboardBuilder()
    opts = list(q["v"]); random.shuffle(opts); q["temp_v"] = opts 
    for i, o in enumerate(opts):
        kb.row(types.InlineKeyboardButton(text=str(o), callback_data=f"ans_{i}"))
    await bot.send_message(chat_id, f"{data['curr']+1}. {q['s']}", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("ans_"))
async def check_ans(call: types.CallbackQuery):
    user_id = call.from_user.id
    data = user_test_data.get(user_id)
    if not data: return
    sel_idx = int(call.data.split("_")[1])
    q = data["qs"][data["curr"]]
    if str(q["temp_v"][sel_idx]).strip() == str(q["t"]).strip():
        data["score"] += 1
        await call.answer("✅ To'g'ri")
    else:
        await call.answer(f"❌ Xato! To'g'ri: {q['t']}", show_alert=True)
    data["curr"] += 1
    await send_q(call.message.chat.id, user_id)

# --- ASOSIY ISHGA TUSHIRISH ---
async def main():
    # Web server va Botni bir vaqtda ishga tushirish
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())