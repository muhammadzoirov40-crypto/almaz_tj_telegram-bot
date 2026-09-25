# DANAT.TJ ⚡ — Free Fire / PUBG / Stars ва дигар бозиҳо Top-Up Bot

Telegram-бот барои пур кардани (донат) бозиҳо дар Тоҷикистон (aiogram 3 + SQLAlchemy async).

**DANAT.TJ ⚡** — Арзонтарин алмаз дар Тоҷикистон  
Free Fire • PUBG • Stars  
ва дигар бозиҳо  
1-5 дақиқа • 100% беҳтар  
Канал: [@_ff_almaz_tj_](https://t.me/_ff_almaz_tj_)  
Muhammad: +992 002119831

## Оғози зуд

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # BOT_TOKEN, DATABASE_URL, ADMIN_IDSро танзим кунед
python main.py
```

Ҳангоми оғоз бот ҷадвалҳо (агар набошанд) месозад ва маҳсулотҳоро (Free Fire, PUBG, Stars) ворид мекунад.  
Барои истеҳсолот аз Alembic истифода баред:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

## Танзим (.env)

| Мутағайир | Тавсиф |
|---|---|
| `BOT_TOKEN` | Токени Telegram-бот |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` |
| `ADMIN_IDS` | IDҳои администратор бо вергул ҷудошуда |
| `PAYMENT_PROVIDER` | `mock` (таҳия) ё `real` |
| `TOPUP_PROVIDER` | `mock` (таҳия) ё `real` |
| `FIRELOOT_API_KEY` | Kalidi FireLoot partner (`https://partner.firelootshop.com`) барои номи ҳақиқии бозигар |
| `PAYMENT_ALIF_NUMBER` | Raqami pardoхt (намуна: `+992 002119831`) |

## Меъморӣ

```
main.py                 нуқтаи вуруди асосӣ (polling)
app/bot/handlers/       start, menu, topup (FSM), balance, orders, support, admin
app/bot/keyboards/      клавиатураҳои inline
app/bot/middlewares/    DatabaseMiddleware → UserMiddleware
app/services/           order / payment / topup / user / notification
app/providers/          абстрактсияҳои пардохт ва пуркуни (mock/real)
app/database/           моделҳо, репозиторияҳо, session factory
```

## Роҳи фармоиш

1. 💎 Донат → бозӣ (🔥 Free Fire • 🎯 PUBG • ⭐ Stars)
2. UID (8–12 рақам) → бот лақабро санҷад → корбар ҳисобро тасдиқ мекунад
3. Маҳсулот → нарх + рақами корта (нусхабардорӣ) → корбар берун аз бот пардохт мекунад
4. Корбар чек (расм/матн) мефиристад → админ ✅ Қабул / ❌ Рад мегирад
5. Қабул → `TopUpService.process_order` → ✅ ба корбар хабар дода мешавад
6. Рад → фармоиш бекор (пардохти корта: баланс барқарор намешавад) → ❌ ба корбар хабар дода мешавад

Баланс аввал бурида **намешавад**; пардохт бо корта + чек сурат мегирад.

## Пур кардани баланс

1. 💰 Баланс → 💳 Шарҷ кунед → маблағ
2. 🏙 Dushanbe City (телефон) ё 💳 Alif
3. Бот **рақами пардохт** нишон медиҳад → корбар маблағ мефиристад
4. ✅ Тасдиқ → бот <b>чек</b> (расм/матн) мепурсад
5. Чек → **админ** (бо ҳама маълумот: маблағ, усул, телефон, ref)
6. Админ ✅ Қабул → `UserService.add_balance` | ❌ Рад → огоҳӣ ба корбар

`.env`:

```
PAYMENT_ALIF_NUMBER=002119831
PAYMENT_ALIF_HOLDER=Muhammad
PAYMENT_DS_PHONE=002119831
```

Mock-пуркуни агар UID бо `0000` оянад, қатъӣ ноком мешавад (роҳи санҷиш).

## Корти пардохт

Дар `.env` танзим кунед:

```
PAYMENT_CARD_NUMBER=992000000000000
PAYMENT_CARD_HOLDER=Muhammad
```
