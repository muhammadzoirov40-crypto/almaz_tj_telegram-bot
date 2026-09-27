from __future__ import annotations

from contextvars import ContextVar

LANGS: tuple[str, ...] = ("tj", "ru", "en")
DEFAULT_LANG = "ru"

LANG_LABELS: dict[str, str] = {
    "tj": "🇹🇯 Тоҷикӣ",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

_lang: ContextVar[str] = ContextVar("bot_lang", default=DEFAULT_LANG)


def normalize_lang(lang: str | None) -> str:
    return lang if lang in LANGS else DEFAULT_LANG


def set_lang(lang: str | None) -> None:
    _lang.set(normalize_lang(lang))


def current_lang() -> str:
    return _lang.get()


def t(key: str, **kwargs: object) -> str:
    text = MESSAGES.get(current_lang(), {}).get(key)
    if text is None:
        text = MESSAGES[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text


def labels_for(key: str) -> set[str]:
    """Every translation of a key — used by text filters."""
    return {
        MESSAGES[lang].get(key, MESSAGES[DEFAULT_LANG].get(key, key))
        for lang in LANGS
    }


MESSAGES: dict[str, dict[str, str]] = {
    "tj": {
        # --- main menu buttons ---
        "btn.donate": "💎 Донат",
        "btn.add_balance": "💳 Пур кардани баланс",
        "btn.balance": "💰 Баланс",
        "btn.promo": "🎁 Пешниҳодҳо",
        "btn.profile": "👤 Саҳифаи ман",
        "btn.buyers": "🏆 Харидорҳо",
        "btn.support": "📞 Дастгирӣ ба админ",
        "btn.admin": "🛠 Админ",
        "btn.orders": "📦 Фармоишҳои ман",
        "btn.language": "🌐 Забон",
        "btn.back": "🔙 Бозгашт",
        "btn.back_menu": "🔙 Менюи асосӣ",
        "btn.cancel": "❌ Бекор кардан",
        "btn.menu": "🏠 Асосӣ",
        "user.name": "Ном",
        "user.balance": "Баланс",
        # --- start ---
        "start.hello": (
            "Салом, хуш омадед ба боти DANAT.TJ 🏆\n\n"
            "Арзонтарин алмаз дар Тоҷикистон\n"
            "Free Fire • PUBG • Mobile Legends\n"
            "ва дигар бозиҳо\n"
            "1-5 дақиқа • 100% беҳтар\n\n"
        ),
        "start.footer": "Лутфан аз менюи зерин интихоб кунед:",
        "start.not_registered": "❌ Шумо ҳанӯз сабт наштаед. /start кунед.",
        "alert.not_registered": "Шумо ҳанӯз сабт наштаед.",
        # --- profile ---
        "menu.title": "🏠 Менюи DANAT.TJ",
        "profile.title": "👤 <b>Профил</b>",
        "profile.finance": "💰 <b>Молия</b>",
        "profile.balance": "Баланс: <b>{balance} TJS</b>",
        "profile.topped_up": "Ҳамагӣ пур карда шуд: {amount} TJS",
        "profile.orders": "📦 <b>Фармоишҳо</b>",
        "profile.orders_total": "Ҳамагӣ: {count}",
        "profile.orders_done": "Иҷро шуд: {count}",
        "profile.orders_work": "Дар коркард: {count}",
        "profile.since": "📅 Бо мо аз {date}",
        "profile.tagline": "DANAT.TJ ⚡ — Арзонтарин алмаз дар Тоҷикистон",
        # --- promo ---
        "promo.title": "🎁 <b>Пешниҳодҳо</b>",
        "promo.body": (
            "🎁 <b>Пешниҳодҳо</b>\n\n"
            "🏆 <b>Ҷоизаи моҳина:</b> ҳар моҳ номаи он корбар, ки дар муддати "
            "1 моҳ аз ҳама зиёд донат кардааст, ғолиб эълон мешавад ва "
            "<b>туҳфа</b> мегирад!\n\n"
            '📢 Канал: <a href="https://t.me/_ff_almaz_tj_">@_ff_almaz_tj_</a>'
        ),
        # --- buyers ---
        "buyers.title": "🏆 <b>Харидорҳо</b>",
        "buyers.top": "🏆 <b>Харидорҳо — Top ҳама</b>\n",
        "buyers.orders": "{count} фармоиш",
        "error.generic": "Хатогӣ.",
        # --- orders ---
        "orders.empty": "📦 Шумо ҳанӯз фармоишҳо надоред.",
        "orders.title": "📦 <b>Фармоишҳои ман</b> — DANAT.TJ ⚡\n",
        "orders.uid": "UID",
        "orders.refreshed": "Навсозӣ шуд",
        "status.pending": "Дар интизори қабул",
        "status.paid": "Пардохт шуд",
        "status.processing": "Дар кор",
        "status.completed": "Тайёр",
        "status.failed": "Ноком",
        "status.cancelled": "Бекор",
        # --- review ---
        "review.no_channel": "Канал ҳанӯз мосланмаган. Ботни каналга админ қўшинг.",
        "review.failed": "Юбориб бўлмади. Каналга бот қўшилганлигини текширинг.",
        "review.sent": "Раҳмат! Баҳо каналга юборилди ⭐",
        # --- support ---
        "support.title": "📞 <b>Дастгирӣ — DANAT.TJ</b>",
        "support.body": (
            "📞 <b>Дастгирӣ — DANAT.TJ</b>\n\n"
            "Мавзӯи муроҷиататонро нависед (масалан: Пардохт, Донат, Дигар).\n"
            "Ё ба админ нависед: "
            '<a href="https://t.me/Muhammad_beckend">@Muhammad_beckend</a>'
        ),
        "support.write_subject": "Лутфан мавзӯро нависед.",
        "support.write_message": "✉️ Хулосаи муамморо нависед:",
        "support.empty_body": "Матн холӣ аст. Дубора нависед.",
        "support.no_subject": "Бе мавзӯъ",
        "support.error": "❌ Хатогӣ. /start кунед.",
        "support.created": "✅ Муроҷиат №{id} қабул шуд.\nДастгирӣ дар вақти наздик ҷавоб медиҳад.",
        "support.notify_admin": (
            "📞 Муроҷиати нав ба дастгирӣ\n"
            "🆔 №{id}\n"
            "👤 {user}\n"
            "📌 {subject}\n"
            "✉️ {body}"
        ),
        # --- subscribe gate ---
        "sub.join": "📢 Каналга обуна шудан",
        "sub.check": "✅ Текшириш",
        "sub.not_joined": "Шумо ҳанӯз обуна нестед. Каналро обуна шавед.",
        "sub.ok": "Обуна тасдиқ шуд!",
        "sub.text": (
            "👋 Пеш аз оғоз ба канал мо обуна шавед!\n\n"
            "1️⃣ Каналро кушоед ва тугмаи «Подписаться»-ро пахш кунед\n"
            "2️⃣ Баъд тугмаи «✅ Проверить»-ро пахш кунед\n\n"
            "Обуна шудед → менюи бот кушода мешавад."
        ),
        # --- commands ---
        "cmd.start": "Оғоз",
        "cmd.menu": "Менюи асосӣ",
        "cmd.topup": "Донат",
        "cmd.orders": "Фармоишҳо",
        "cmd.profile": "Саҳифаи ман",
        "cmd.balance": "Баланс",
        "cmd.support": "Дастгирӣ",
        "cmd.admin": "Админ",
        # --- language ---
        "lang.choose": "🌐 <b>Забони интерфейсро интихоб кунед:</b>",
        "lang.changed": "Забон тағйир ёфт ✅",
        "lang.button": "🌐 Забон",
    },
    "ru": {
        "btn.donate": "💎 Донат",
        "btn.add_balance": "💳 Пополнить баланс",
        "btn.balance": "💰 Баланс",
        "btn.promo": "🎁 Акции",
        "btn.profile": "👤 Мой профиль",
        "btn.buyers": "🏆 Покупатели",
        "btn.support": "📞 Поддержка",
        "btn.admin": "🛠 Админ",
        "btn.orders": "📦 Мои заказы",
        "btn.language": "🌐 Язык",
        "btn.back": "🔙 Назад",
        "btn.back_menu": "🔙 Главное меню",
        "btn.cancel": "❌ Отмена",
        "btn.menu": "🏠 Главная",
        "user.name": "Имя",
        "user.balance": "Баланс",
        "start.hello": (
            "Здравствуйте, добро пожаловать в бота DANAT.TJ 🏆\n\n"
            "Самые дешёвые алмазы в Таджикистане\n"
            "Free Fire • PUBG • Mobile Legends\n"
            "и другие игры\n"
            "1-5 минут • 100% лучшие\n\n"
        ),
        "start.footer": "Пожалуйста, выберите пункт меню ниже:",
        "start.not_registered": "❌ Вы ещё не зарегистрированы. Нажмите /start.",
        "alert.not_registered": "Вы ещё не зарегистрированы.",
        "menu.title": "🏠 Меню DANAT.TJ",
        "profile.title": "👤 <b>Профиль</b>",
        "profile.finance": "💰 <b>Финансы</b>",
        "profile.balance": "Баланс: <b>{balance} TJS</b>",
        "profile.topped_up": "Всего пополнено: {amount} TJS",
        "profile.orders": "📦 <b>Заказы</b>",
        "profile.orders_total": "Всего: {count}",
        "profile.orders_done": "Выполнено: {count}",
        "profile.orders_work": "В работе: {count}",
        "profile.since": "📅 С нами с {date}",
        "profile.tagline": "DANAT.TJ ⚡ — Самые дешёвые алмазы в Таджикистане",
        "promo.title": "🎁 <b>Акции</b>",
        "promo.body": (
            "🎁 <b>Акции</b>\n\n"
            "🏆 <b>Приз месяца:</b> каждый месяц пользователь, который за "
            "месяц сделал больше всего донатов, объявляется победителем и "
            "получает <b>подарок</b>!\n\n"
            '📢 Канал: <a href="https://t.me/_ff_almaz_tj_">@_ff_almaz_tj_</a>'
        ),
        "buyers.title": "🏆 <b>Покупатели</b>",
        "buyers.top": "🏆 <b>Покупатели — Top всех</b>\n",
        "buyers.orders": "{count} заказов",
        "error.generic": "Ошибка.",
        "orders.empty": "📦 У вас пока нет заказов.",
        "orders.title": "📦 <b>Мои заказы</b> — DANAT.TJ ⚡\n",
        "orders.uid": "UID",
        "orders.refreshed": "Обновлено",
        "status.pending": "Ожидает подтверждения",
        "status.paid": "Оплачено",
        "status.processing": "В работе",
        "status.completed": "Готово",
        "status.failed": "Ошибка",
        "status.cancelled": "Отменено",
        "review.no_channel": "Канал ещё не настроен. Добавьте бота в канал админом.",
        "review.failed": "Не удалось отправить. Проверьте, что бот добавлен в канал.",
        "review.sent": "Спасибо! Отзыв отправлен в канал ⭐",
        "support.title": "📞 <b>Поддержка — DANAT.TJ</b>",
        "support.body": (
            "📞 <b>Поддержка — DANAT.TJ</b>\n\n"
            "Напишите тему обращения (например: Оплата, Донат, Другое).\n"
            "Или напишите админу: "
            '<a href="https://t.me/Muhammad_beckend">@Muhammad_beckend</a>'
        ),
        "support.write_subject": "Пожалуйста, напишите тему.",
        "support.write_message": "✉️ Опишите проблему кратко:",
        "support.empty_body": "Сообщение пустое. Напишите ещё раз.",
        "support.no_subject": "Без темы",
        "support.error": "❌ Ошибка. Нажмите /start.",
        "support.created": "✅ Обращение №{id} принято.\nПоддержка ответит в ближайшее время.",
        "support.notify_admin": (
            "📞 Новое обращение в поддержку\n"
            "🆔 №{id}\n"
            "👤 {user}\n"
            "📌 {subject}\n"
            "✉️ {body}"
        ),
        "lang.choose": "🌐 <b>Выберите язык интерфейса:</b>",
        "lang.changed": "Язык изменён ✅",
        # --- subscribe gate ---
        "sub.join": "📢 Подписаться на канал",
        "sub.check": "✅ Проверить",
        "sub.not_joined": "Вы ещё не подписаны. Подпишитесь на канал.",
        "sub.ok": "Подписка подтверждена!",
        "sub.text": (
            "👋 Перед началом подпишитесь на наш канал!\n\n"
            "1️⃣ Откройте канал и нажмите «Подписаться»\n"
            "2️⃣ Затем нажмите «✅ Проверить»\n\n"
            "После подписки откроется меню бота."
        ),
        # --- commands ---
        "cmd.start": "Старт",
        "cmd.menu": "Главное меню",
        "cmd.topup": "Донат",
        "cmd.orders": "Заказы",
        "cmd.profile": "Мой профиль",
        "cmd.balance": "Баланс",
        "cmd.support": "Поддержка",
        "cmd.admin": "Админ",
        # --- language ---
        "lang.choose": "🌐 <b>Выберите язык интерфейса:</b>",
        "lang.changed": "Язык изменён ✅",
        "lang.button": "🌐 Язык",
    },
    "en": {
        "btn.donate": "💎 Top-up",
        "btn.add_balance": "💳 Top up balance",
        "btn.balance": "💰 Balance",
        "btn.promo": "🎁 Offers",
        "btn.profile": "👤 My profile",
        "btn.buyers": "🏆 Buyers",
        "btn.support": "📞 Support",
        "btn.admin": "🛠 Admin",
        "btn.orders": "📦 My orders",
        "btn.language": "🌐 Language",
        "btn.back": "🔙 Back",
        "btn.back_menu": "🔙 Main menu",
        "btn.cancel": "❌ Cancel",
        "btn.menu": "🏠 Home",
        "user.name": "Name",
        "user.balance": "Balance",
        "start.hello": (
            "Hello, welcome to the DANAT.TJ bot 🏆\n\n"
            "The cheapest diamonds in Tajikistan\n"
            "Free Fire • PUBG • Mobile Legends\n"
            "and other games\n"
            "1-5 minutes • 100% best\n\n"
        ),
        "start.footer": "Please choose an option from the menu below:",
        "start.not_registered": "❌ You are not registered yet. Tap /start.",
        "alert.not_registered": "You are not registered yet.",
        "menu.title": "🏠 DANAT.TJ menu",
        "profile.title": "👤 <b>Profile</b>",
        "profile.finance": "💰 <b>Finance</b>",
        "profile.balance": "Balance: <b>{balance} TJS</b>",
        "profile.topped_up": "Topped up in total: {amount} TJS",
        "profile.orders": "📦 <b>Orders</b>",
        "profile.orders_total": "Total: {count}",
        "profile.orders_done": "Completed: {count}",
        "profile.orders_work": "In progress: {count}",
        "profile.since": "📅 With us since {date}",
        "profile.tagline": "DANAT.TJ ⚡ — The cheapest diamonds in Tajikistan",
        "promo.title": "🎁 <b>Offers</b>",
        "promo.body": (
            "🎁 <b>Offers</b>\n\n"
            "🏆 <b>Monthly prize:</b> every month the user who topped up "
            "the most during the month is announced the winner and gets a "
            "<b>gift</b>!\n\n"
            '📢 Channel: <a href="https://t.me/_ff_almaz_tj_">@_ff_almaz_tj_</a>'
        ),
        "buyers.title": "🏆 <b>Buyers</b>",
        "buyers.top": "🏆 <b>Buyers — Top of all</b>\n",
        "buyers.orders": "{count} orders",
        "error.generic": "Error.",
        "orders.empty": "📦 You have no orders yet.",
        "orders.title": "📦 <b>My orders</b> — DANAT.TJ ⚡\n",
        "orders.uid": "UID",
        "orders.refreshed": "Refreshed",
        "status.pending": "Waiting for approval",
        "status.paid": "Paid",
        "status.processing": "Processing",
        "status.completed": "Done",
        "status.failed": "Failed",
        "status.cancelled": "Cancelled",
        "review.no_channel": "Channel is not configured yet. Add the bot as channel admin.",
        "review.failed": "Could not send. Check that the bot was added to the channel.",
        "review.sent": "Thanks! Your review was sent to the channel ⭐",
        "support.title": "📞 <b>Support — DANAT.TJ</b>",
        "support.body": (
            "📞 <b>Support — DANAT.TJ</b>\n\n"
            "Write the topic of your request (e.g. Payment, Top-up, Other).\n"
            "Or message an admin: "
            '<a href="https://t.me/Muhammad_beckend">@Muhammad_beckend</a>'
        ),
        "support.write_subject": "Please write the topic.",
        "support.write_message": "✉️ Describe the problem briefly:",
        "support.empty_body": "The message is empty. Please write again.",
        "support.no_subject": "No topic",
        "support.error": "❌ Error. Tap /start.",
        "support.created": "✅ Request №{id} received.\nSupport will reply soon.",
        "support.notify_admin": (
            "📞 New support request\n"
            "🆔 №{id}\n"
            "👤 {user}\n"
            "📌 {subject}\n"
            "✉️ {body}"
        ),
        "lang.choose": "🌐 <b>Choose the interface language:</b>",
        "lang.changed": "Language changed ✅",
                # --- subscribe gate ---
        "sub.join": "📢 Subscribe to the channel",
        "sub.check": "✅ Check",
        "sub.not_joined": "You are not subscribed yet. Please join the channel.",
        "sub.ok": "Subscription confirmed!",
        "sub.text": (
            "👋 Before you start, please subscribe to our channel!\n\n"
            "1️⃣ Open the channel and tap «Subscribe»\n"
            "2️⃣ Then tap «✅ Check»\n\n"
            "Once subscribed, the bot menu opens."
        ),
        # --- commands ---
        "cmd.start": "Start",
        "cmd.menu": "Main menu",
        "cmd.topup": "Top-up",
        "cmd.orders": "Orders",
        "cmd.profile": "My profile",
        "cmd.balance": "Balance",
        "cmd.support": "Support",
        "cmd.admin": "Admin",
        # --- language ---
        "lang.choose": "🌐 <b>Choose the interface language:</b>",
        "lang.changed": "Language changed ✅",
        "lang.button": "🌐 Language",
    },
}
