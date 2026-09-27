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
        "btn.share_phone": "📱 Рақами манро фиристодан",
        "btn.custom_amount": "✏️ Маблағи дигар",
        "btn.pay": "💰 Пардохт кардан",
        "btn.pay_confirm": "✅ Тасдиқи пардохт",
        "btn.pay_cancel": "❌ Бекор",
        "btn.pay_go": "🔗 Гузариш ба пардохт",
        "btn.accept": "✅ Қабул",
        "btn.reject": "❌ Рад",
        "btn.yes_account": "✅ Ҳа, ҳамин ҳисобам",
        "btn.no": "❌ Не",
        "btn.diamonds": "💎 Алмазҳо",
        "bal.start": "💳 <b>Пардохти баланс</b>\n\nМаблағро интихоб кунед ё рақам нависед (TJS):",
        "bal.amount_prompt": "✏️ <b>Маблағ</b>\n\nМаблағро бо рақам нависед (масалан: 25):",
        "bal.invalid": "Нодуруст.",
        "bal.pay_header": "💰 Маблағ: <b>{amount} TJS</b>\n\nПардохт <b>Dushanbe City</b> орқали:",
        "bal.amount_label": "💰 <b>Маблағ:</b> {amount}",
        "bal.method_label": "💳 <b>Усул:</b> {method}",
        "bal.phone_label": "📱 <b>Рақами шумо:</b> <code>{phone}</code>",
        "bal.pay_number": "📄 <b>Рақами пардохт:</b>",
        "bal.steps": "1️⃣ Ба ин рақам маблағ фиристед\n2️⃣ Пас тугмаи «✅ Тасдиқи пардохт»-ро зер кунед\n3️⃣ Бот чек (расм/матн) мепурсад\n4️⃣ Чекро фиристед → админ санҷида, баланс илова мекунад",
        "bal.amount_missing": "Маблағ ворид кунед.",
        "bal.ds_intro": "🏙 <b>Dushanbe City</b>\n\n📱 Тугмаи зеринро зер кунед ва <b>рақами худатон</b>-ро фиристед (Telegram рақами шуморо мефиристад).",
        "bal.phone_hint": "Рақами худатонро интихоб кунед:",
        "bal.amount_not_found": "❌ Маблағ ёфт нашуд. Дубора оғоз кунед.",
        "bal.phone_not_found": "❌ Рақам ёфт нашуд. Тугмаи «📱 Рақами худамро фиристодан»-ро зер кунед.",
        "bal.wrong_contact": "❌ Лутфан <b>рақами худатон</b>-ро фиристед.",
        "bal.no_phone_hint": "\nДар Telegram Settings → Profile бояд рақами телефон дошта бошед.",
        "bal.phone_ok": "✅ Рақам қабул шуд.",
        "bal.cancelled": "🚫 Пардохт бекор карда шуд.",
        "bal.phone_hint_btn": "\n\nТугмаи «📱 Рақами худамро фиристодан»-ро зер кунед ё рақами тоҷикӣ нависед.",
        "bal.amount_missing_short": "Маблағ ёфт нашуд.",
        "bal.error": "Хатогӣ. Дубора кӯшиш кунед.",
        "bal.already_processed": "Ин дархост алакай коркард шудааст.",
        "bal.receipt_request": "📸 <b>Чеки пардохт фиристед</b>\n\n📦 Дархост: №{id}\n💰 Маблағ: <b>{amount} TJS</b>\n💳 Усул: {method}\n📱 Телефон: <code>{phone}</code>\nРақами пардохт: <code>{pay_number}</code>\n\nЛутфан <b>расми чек</b> ё <b>матни чек</b> фиристед.",
        "bal.receipt_prompt": "Чекро фиристед",
        "bal.admin_request": "📩 <b>Чеки пардохти баланс</b>\n\n💰 Маблағ: <b>{amount} TJS</b>\n💳 Усул: {method}\n👤 Ном: {name}\n📱 Телефон: {phone}\n\n📦 Дархост: №{id}\n\n✉️ Чек:\n{receipt}\n\nҚабул ё рад кунед:",
        "bal.not_found": "❌ Дархост ёфт нашуд. Дубора оғоз кунед.",
        "bal.user_accepted": "✅ <b>Чек қабул шуд</b>\n\n📦 Дархост: №{id}\n\nАдмин чекро санҷида, ба баланс илова мекунад.\nДар бораи қабул/рад ба шумо хабар дода мешавад.",
        "bal.user_accepted_short": "✅ <b>Чек қабул шуд</b>\n\n📦 Дархост: №{id}\n\nАдмин чекро санҷида, ба баланс илова мекунад.",
        "btn.vouchers": "🎟️ Ваучер / Гузарнома",
        "unit.diamond": "Алмаз",
        "unit.voucher": "Ваучер",
        "unit.currency": "с.",
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
        "btn.share_phone": "📱 Отправить мой номер",
        "btn.custom_amount": "✏️ Другая сумма",
        "btn.pay": "💰 Оплатить",
        "btn.pay_confirm": "✅ Подтвердить оплату",
        "btn.pay_cancel": "❌ Отмена",
        "btn.pay_go": "🔗 Перейти к оплате",
        "btn.accept": "✅ Принять",
        "btn.reject": "❌ Отклонить",
        "btn.yes_account": "✅ Да, это мой аккаунт",
        "btn.no": "❌ Нет",
        "btn.diamonds": "💎 Алмазы",
        "bal.start": "💳 <b>Пополнение баланса</b>\n\nВыберите сумму или введите число (TJS):",
        "bal.amount_prompt": "✏️ <b>Сумма</b>\n\nВведите сумму цифрами (например: 25):",
        "bal.invalid": "Неверно.",
        "bal.pay_header": "💰 Сумма: <b>{amount} TJS</b>\n\nОплата через <b>Dushanbe City</b>:",
        "bal.amount_label": "💰 <b>Сумма:</b> {amount}",
        "bal.method_label": "💳 <b>Способ:</b> {method}",
        "bal.phone_label": "📱 <b>Ваш номер:</b> <code>{phone}</code>",
        "bal.pay_number": "📄 <b>Номер для оплаты:</b>",
        "bal.steps": "1️⃣ Отправьте сумму на этот номер\n2️⃣ Затем нажмите «✅ Подтвердить оплату»\n3️⃣ Бот попросит чек (фото/текст)\n4️⃣ Отправьте чек → админ проверит и зачислит баланс",
        "bal.amount_missing": "Введите сумму.",
        "bal.ds_intro": "🏙 <b>Dushanbe City</b>\n\n📱 Нажмите кнопку ниже и отправьте <b>свой номер</b> (Telegram пришлёт ваш номер).",
        "bal.phone_hint": "Выберите свой номер:",
        "bal.amount_not_found": "❌ Сумма не найдена. Начните заново.",
        "bal.phone_not_found": "❌ Номер не найден. Нажмите кнопку «📱 Отправить мой номер».",
        "bal.wrong_contact": "❌ Пожалуйста, отправьте <b>свой номер</b>.",
        "bal.no_phone_hint": "\nВ Telegram Settings → Profile должен быть номер телефона.",
        "bal.phone_ok": "✅ Номер принят.",
        "bal.cancelled": "🚫 Оплата отменена.",
        "bal.phone_hint_btn": "\n\nНажмите кнопку «📱 Отправить мой номер» или введите таджикский номер.",
        "bal.amount_missing_short": "Сумма не найдена.",
        "bal.error": "Ошибка. Попробуйте ещё раз.",
        "bal.already_processed": "Этот запрос уже обработан.",
        "bal.receipt_request": "📸 <b>Отправьте чек оплаты</b>\n\n📦 Запрос: №{id}\n💰 Сумма: <b>{amount} TJS</b>\n💳 Способ: {method}\n📱 Телефон: <code>{phone}</code>\nНомер оплаты: <code>{pay_number}</code>\n\nПожалуйста, отправьте <b>фото чека</b> или <b>текст чека</b>.",
        "bal.receipt_prompt": "Отправьте чек",
        "bal.admin_request": "📩 <b>Чек пополнения баланса</b>\n\n💰 Сумма: <b>{amount} TJS</b>\n💳 Способ: {method}\n👤 Имя: {name}\n📱 Телефон: {phone}\n\n📦 Запрос: №{id}\n\n✉️ Чек:\n{receipt}\n\nПринять или отклонить:",
        "bal.not_found": "❌ Запрос не найден. Начните заново.",
        "bal.user_accepted": "✅ <b>Чек принят</b>\n\n📦 Запрос: №{id}\n\nАдмин проверит чек и зачислит баланс.\nО принятии/отклонении вам сообщат.",
        "bal.user_accepted_short": "✅ <b>Чек принят</b>\n\n📦 Запрос: №{id}\n\nАдмин проверит чек и зачислит баланс.",
        "btn.vouchers": "🎟️ Ваучеры / Пропуска",
        "unit.diamond": "Алмаз",
        "unit.voucher": "Ваучер",
        "unit.currency": "с.",
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
        "btn.share_phone": "📱 Send my phone number",
        "btn.custom_amount": "✏️ Custom amount",
        "btn.pay": "💰 Pay",
        "btn.pay_confirm": "✅ Confirm payment",
        "btn.pay_cancel": "❌ Cancel",
        "btn.pay_go": "🔗 Go to payment",
        "btn.accept": "✅ Accept",
        "btn.reject": "❌ Reject",
        "btn.yes_account": "✅ Yes, this is my account",
        "btn.no": "❌ No",
        "btn.diamonds": "💎 Diamonds",
        "bal.start": "💳 <b>Top up balance</b>\n\nPick an amount or type a number (TJS):",
        "bal.amount_prompt": "✏️ <b>Amount</b>\n\nType the amount in digits (e.g. 25):",
        "bal.invalid": "Invalid.",
        "bal.pay_header": "💰 Amount: <b>{amount} TJS</b>\n\nPay via <b>Dushanbe City</b>:",
        "bal.amount_label": "💰 <b>Amount:</b> {amount}",
        "bal.method_label": "💳 <b>Method:</b> {method}",
        "bal.phone_label": "📱 <b>Your phone:</b> <code>{phone}</code>",
        "bal.pay_number": "📄 <b>Payment number:</b>",
        "bal.steps": "1️⃣ Send the amount to this number\n2️⃣ Then tap «✅ Confirm payment»\n3️⃣ The bot asks for a receipt (photo/text)\n4️⃣ Send the receipt → admin checks and credits your balance",
        "bal.amount_missing": "Enter the amount.",
        "bal.ds_intro": "🏙 <b>Dushanbe City</b>\n\n📱 Tap the button below and send <b>your phone number</b> (Telegram will share it).",
        "bal.phone_hint": "Choose your number:",
        "bal.amount_not_found": "❌ Amount not found. Start again.",
        "bal.phone_not_found": "❌ Number not found. Tap the button «📱 Send my phone number».",
        "bal.wrong_contact": "❌ Please send <b>your own number</b>.",
        "bal.no_phone_hint": "\nA phone number must be set in Telegram Settings → Profile.",
        "bal.phone_ok": "✅ Number accepted.",
        "bal.cancelled": "🚫 Payment cancelled.",
        "bal.phone_hint_btn": "\n\nTap «📱 Send my phone number» or type a Tajik number.",
        "bal.amount_missing_short": "Amount not found.",
        "bal.error": "Error. Please try again.",
        "bal.already_processed": "This request has already been processed.",
        "bal.receipt_request": "📸 <b>Send your payment receipt</b>\n\n📦 Request: №{id}\n💰 Amount: <b>{amount} TJS</b>\n💳 Method: {method}\n📱 Phone: <code>{phone}</code>\nPayment number: <code>{pay_number}</code>\n\nPlease send a <b>receipt photo</b> or <b>receipt text</b>.",
        "bal.receipt_prompt": "Send the receipt",
        "bal.admin_request": "📩 <b>Balance top-up receipt</b>\n\n💰 Amount: <b>{amount} TJS</b>\n💳 Method: {method}\n👤 Name: {name}\n📱 Phone: {phone}\n\n📦 Request: №{id}\n\n✉️ Receipt:\n{receipt}\n\nAccept or reject:",
        "bal.not_found": "❌ Request not found. Start again.",
        "bal.user_accepted": "✅ <b>Receipt accepted</b>\n\n📦 Request: №{id}\n\nAdmin will check the receipt and credit your balance.\nYou will be notified about the result.",
        "bal.user_accepted_short": "✅ <b>Receipt accepted</b>\n\n📦 Request: №{id}\n\nAdmin will check the receipt and credit your balance.",
        "btn.vouchers": "🎟️ Vouchers / Passes",
        "unit.diamond": "Diamond",
        "unit.voucher": "Voucher",
        "unit.currency": "TJS",
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
