import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from urllib.parse import quote_plus, unquote_plus
import random

TOKEN = "токен"
ADMIN_USER_ID = ид админа
ADMIN_USERNAME = "юз админа"
CHANNEL_USERNAME = "юз канала"

WAITING_FOR_PROBLEM = 1
WAITING_FOR_ADMIN_REPLY = 2
SENDING_POST = 3
WAITING_FOR_QUOTE = 4

user_data = {}
pending_support_requests = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

HEART_REPLIES = [
    "Спасибо за сердечко! И тебе лучи добра! 😊",
    "Ой, как мило! Держи сердечко в ответ! 🥰",
    "Как приятно! Спасибо за позитив! 💖",
    "Спасибо за твою доброту! 🫶",
    "Ух ты, спасибо! 🌟",
    "Как же приятно получать сердечки! Спасибо! 💫",
    "Спасибо! Это очень поднимает настроение! 😄"
]

HEART_EMOJIS = ["❤️", "🧡", "💛", "💚", "💙", "💜", "💖", "🖤", "🤍", "🤎"]

def build_main_keyboard():
    keyboard = [
        [KeyboardButton("👤  Профиль  🖼️"), KeyboardButton("❓  Поддержка  🤝")],
        [KeyboardButton("📤  Отправить Пост  🖌️"), KeyboardButton("💡  Предложить Идею  🌟")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def build_cancel_keyboard():
    keyboard = [
        [KeyboardButton("❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = build_main_keyboard()
    await update.message.reply_text("Приветик! 👋 Я бот канала Кратко и понятно и жду от тебя крутые фоточки и видосики! Просто отправь их мне, и мы обязательно посмотрим! 😉", reply_markup=reply_markup)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or "Не указан"
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip() or "Не указано"

    if user_id not in user_data:
        user_data[user_id] = {
            "username": username,
            "full_name": full_name,
            "join_date": update.effective_message.date.strftime("%d %B %Y"),
            "position": "Подписчик",
        }
        join_date = update.effective_message.date.strftime("%d %B %Y")
        user_data[user_id]["join_date"] = join_date

    profile_info = f"""
ℹ️ Информация о пользователе (💎 Ваш мир)

🌐 ID: <code>{user_id}</code>  
🪪 Имя пользователя: @{user_data[user_id]["username"]}  
📅 Дата присоединения: {user_data[user_id]["join_date"]}  
🧑‍🎤 Должность: {user_data[user_id]["position"]}
    """
    await update.message.reply_text(profile_info, parse_mode="HTML", reply_markup=build_main_keyboard())

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤔 Подробно опишите, что случилось. Администратор получит информацию и постарается как можно скорее решить ваш вопрос! 🚀\n"
        "Администратор ответит вам кнопками после описания проблемы:  \"🔍 Уточнить.\" | \"✅ Всё решено.\"."
    )
    context.user_data['awaiting_problem'] = update.effective_user.id

async def receive_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_problem') != update.effective_user.id:
        return
    user_id = update.effective_user.id
    username = update.effective_user.username or "Не указан"
    problem_description = update.message.text

    keyboard = [
        [
            InlineKeyboardButton("🔍 Уточнить.", callback_data=f"admin_reply_{user_id}"),
            InlineKeyboardButton("✅ Всё решено.", callback_data=f"admin_ignore_{user_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['support_message_id'] = update.message.message_id #Сохраняю
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"Новое сообщение поддержки от @{username} (ID: {user_id}):\n\n{problem_description}",
            reply_markup=reply_markup,
        )
        await update.message.reply_text("⏳ Ваша заявка направлена администратору. Пожалуйста, ожидайте ответа. 🧘‍♀️")
        context.user_data.pop('awaiting_problem', None)
    except Exception as e:
        logger.error(f"❌ Возникла проблема с отправкой вашего сообщения администратору. Пожалуйста, попробуйте отправить его еще раз! 🔄 {e}")
        await update.message.reply_text("⏳ Временные трудности! 😟 Ваше сообщение не может быть отправлено администратору прямо сейчас. Попробуйте, пожалуйста, еще раз через несколько минут.")


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[2]
    context.user_data['awaiting_admin_response'] = user_id

    support_message_id = update.effective_message.message_id
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=ADMIN_USER_ID,
            message_id=support_message_id,
            reply_markup=None
        )
    except Exception as e:
            logger.error(f"Ошибка при удаление кнопки: {e}")

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Отправьте ответ пользователю {user_id} ➡️:",
    )


async def handle_admin_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = context.user_data.get('awaiting_admin_response')
    if not user_id:
        return

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"💬  > Ответ Поддержки <  🛠️:\n\n{update.message.text}"
        )
        await update.message.reply_text(f"Сообщение пользователю {user_id} отправлено. ✅", )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю: {e}")
        await update.message.reply_text(f"Не удалось отправить сообщение пользователю. {e} ❌")
    context.user_data.pop('awaiting_admin_response', None)

async def admin_ignore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[2]

    support_message_id = update.effective_message.message_id

    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text="✔️ Заявка решена. Если потребуется помощь, обращайтесь."
        )
         #Удаляю кнопки
        await context.bot.edit_message_reply_markup(
            chat_id=ADMIN_USER_ID,
            message_id=support_message_id,
            reply_markup=None
        )

    except Exception as e:
        logger.error(f"Не удалось отправить уведомление об игнорировании: {e}")
        await query.message.reply_text(f"Не удалось отправить уведомление об игнорировании пользователю {e} ❌")


async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['state'] = SENDING_POST
    reply_markup = build_cancel_keyboard()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📤 Загрузите ваше фото или видео 🎬, которое хотите видеть в нашем канале! 🚀\n"
        "После отправки фото или видео, вам будет предложено добавить к этому посту цитату или другое сопроводительное сообщение. 📝 Напишите что-нибудь вдохновляющее! 🌟",
        reply_markup=reply_markup
    )
    return SENDING_POST


async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        media = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        media = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text("✨ Загрузите, пожалуйста, фото или видео. Остальные форматы пока не поддерживаются. 📁➡️🏞️", reply_markup=build_cancel_keyboard())
        return ConversationHandler.END

    context.user_data['media'] = media
    context.user_data['media_type'] = media_type
    context.user_data['state'] = WAITING_FOR_QUOTE

    reply_markup = build_cancel_keyboard()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✨ Добавьте изюминку в свой пост! ✍️ Отправьте цитату или, если хотите оставить его без, напишите '-'.",
        reply_markup=reply_markup
    )
    return WAITING_FOR_QUOTE


async def receive_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    quote = update.message.text
    context.user_data["user_id"] = user_id

    if len(quote) > 500:
        quote = quote[:500]
        await update.message.reply_text("⚠️ Внимание! Сообщение сокращено до 500 символов. ✅")

    context.user_data["quote"] = quote
    media = context.user_data.get("media")
    media_type = context.user_data.get("media_type")
    context.user_data['state'] = None

    anonymity_keyboard = [
        [
            InlineKeyboardButton("Да ✅", callback_data="anonymous"),
            InlineKeyboardButton("Нет 🚫", callback_data="not_anonymous"),
        ]
    ]
    anonymity_markup = InlineKeyboardMarkup(anonymity_keyboard)

    context.user_data['media'] = media
    context.user_data['media_type'] = media_type
    context.user_data['quote'] = quote
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Хотите сохранить анонимность? "
             "🔒 Выберите:?",

        reply_markup=anonymity_markup
    )


async def handle_anonymity_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    is_anonymous = query.data == "anonymous"
    media = context.user_data.get("media")
    media_type = context.user_data.get("media_type")
    quote = context.user_data.get("quote")
    username = update.effective_user.username
    user_id = update.effective_user.id

    if is_anonymous:
        caption = f"Новый пост анонимно.\nЦитата: {quote if quote != '-' else 'Нет цитаты'}."
        anonymity_text = f"\n\n(Отправил: @{username} ID: {user_id})"
    else:
        caption = f"Новый пост от @{username}.\nЦитата: {quote if quote != '-' else 'Нет цитаты'}."
        anonymity_text = ""

    admin_keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data="approve"),
            InlineKeyboardButton("🚫 Отклонить", callback_data="reject"),
        ]
    ]
    admin_markup = InlineKeyboardMarkup(admin_keyboard)

    try:
        if media_type == "photo":
            sent_message = await context.bot.send_photo(
                chat_id=ADMIN_USER_ID,
                photo=media,
                caption=caption + anonymity_text,
                reply_markup=admin_markup,
            )
        elif media_type == "video":
            sent_message = await context.bot.send_video(
                chat_id=ADMIN_USER_ID,
                video=media,
                caption=caption + anonymity_text,
                reply_markup=admin_markup,
            )
    except Exception as e:
        logger.error(f"😥 Не получается отправить ваше фото на проверку. Если проблема повторится, пожалуйста, свяжитесь с поддержкой! 🆘: {e} || Текст {query.data}")
        await update.effective_message.reply_text(
            "😔 К сожалению, возникла проблема с отправкой вашего поста. Мы уже работаем над этим! Пожалуйста, попробуйте повторить попытку через некоторое время. 🙏",
            reply_markup=build_main_keyboard()
        )
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="📝 Ваш пост в очереди на рассмотрение у администратора. Мы скоро вернемся с ответом! 🕵️‍♂️", reply_markup=build_main_keyboard())
    return


async def handle_admin_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    media = context.user_data.get("media")
    media_type = context.user_data.get("media_type")
    initial_user_id = update.effective_user.id
    caption = context.user_data.get("caption")
    is_anonymous = context.user_data.get("is_anonymous")
    user_id = context.user_data.get("user_id")
    username = update.effective_user.username
    message_id = update.effective_message.message_id #Сохраняю

    if query.data == "approve":
        if is_anonymous:
            username = "Анонимно"

        try:
            if media_type == "photo":
                await context.bot.send_photo(
                    chat_id=CHANNEL_USERNAME,
                    photo=media,
                    caption=caption
                )

            elif media_type == "video":
                await context.bot.send_video(
                    chat_id=CHANNEL_USERNAME,
                    video=media,
                    caption=caption
                )
            try:
                await context.bot.send_message(
                    chat_id=initial_user_id,
                    text="📢 Отличные новости! Ваш пост опубликован и виден всем подписчикам канала! 👀",
                    reply_markup=build_main_keyboard()
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение  пользователю{e}")
                await update.message.reply_text("Пользователь не найден 😔", reply_markup=build_main_keyboard())

        except Exception as e:
            logger.error(f"При отправке произошла ошибка: {e}")
            await update.message.reply_text("🤖 Ой, что-то пошло не так... 😔 Пожалуйста, попробуйте отправить команду еще раз! 🙏", reply_markup=build_main_keyboard())

        #Удаляю кнопки у админа
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=ADMIN_USER_ID,
                message_id=message_id,
                reply_markup=None
            )
        except Exception as e:
            logger.error(f"Ошибка при удаление кнопки: {e}")
    elif query.data == "reject":
        #Отклоняю
        await handle_admin_rejection(update, context, user_id, message_id)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Упс! Что-то пошло не так. 😔 Попробуйте еще раз.",
            reply_markup=build_main_keyboard()
        )


async def handle_admin_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id = None, message_id = None) -> None:
    query = update.callback_query
    await query.answer()
    try:
        #Отклоняю
        await context.bot.send_message(
            chat_id=user_id,
            text="🥺 Нам очень жаль, но ваше сообщение отклонено.",
            reply_markup=build_main_keyboard()
        )
         #Удаляю кнопки у админа
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=ADMIN_USER_ID,
                message_id=message_id,
                reply_markup=None
            )
        except Exception as e:
            logger.error(f"Ошибка при удаление кнопки: {e}")

    except Exception as e:
        logger.error(f"Произошла ошибка {e}")

async def suggest_idea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"👋 На связи с админами! Вот как с нами связаться:  @{ADMIN_USERNAME}✨", reply_markup=build_main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    photo = update.message.photo
    video = update.message.video

    if text == "👤  Профиль  🖼️":
        await profile(update, context)
    elif text == "❓  Поддержка  🤝":
        await support(update, context)
    elif text == "📤  Отправить Пост  🖌️":
        await send_post(update, context)
    elif text == "💡  Предложить Идею  🌟":
        await suggest_idea(update, context)
    elif text == "❌ Отмена":
        context.user_data.clear()
        reply_markup = build_main_keyboard()
        await update.message.reply_text("Действие отменено. ↩️", reply_markup=reply_markup)
    elif text in HEART_EMOJIS:
        reply_text = random.choice(HEART_REPLIES)
        await update.message.reply_text(reply_text)
    elif context.user_data.get('awaiting_admin_response'):
        await handle_admin_response(update, context)
    elif context.user_data.get('awaiting_problem') == update.effective_user.id:
        await receive_problem(update, context)
    elif context.user_data.get('state') == SENDING_POST:
        if photo or video:
            await receive_media(update, context)
        else:
            await update.message.reply_text("Пожалуйста, отправьте фото или видео 🖼️, чтобы продолжить.", reply_markup=build_cancel_keyboard())
    elif context.user_data.get('state') == WAITING_FOR_QUOTE:
         await receive_quote(update, context)
    else:
        await update.message.reply_text("😅 Упс, я этого не понимаю! Жмите на кнопки внизу, там всё есть! 😉", reply_markup=build_main_keyboard())


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^❓  Поддержка  🤝$"), support))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_message))

    application.add_handler(CallbackQueryHandler(handle_anonymity_choice, pattern="^(anonymous|not_anonymous)$"))
    application.add_handler(CallbackQueryHandler(admin_reply, pattern="^admin_reply_"))
    application.add_handler(CallbackQueryHandler(admin_ignore, pattern="^admin_ignore_"))
    application.add_handler(CallbackQueryHandler(handle_admin_approval, pattern="^(approve|reject)$"))
    application.add_handler(CallbackQueryHandler(handle_admin_rejection, pattern="^reject"))

    application.run_polling()


if __name__ == "__main__":
    main()