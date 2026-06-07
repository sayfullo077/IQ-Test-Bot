# IQ Test Bot

Aiogram 3 + PostgreSQL + Redis asosidagi Telegram IQ test boti.

## Ishga tushirish

### 1. Muhitni sozlash
```bash
cp .env.example .env
# .env faylini tahrirlang: BOT_TOKEN va ADMIN_IDS ni to'ldiring
```

### 2. Docker orqali (tavsiya etiladi)
```bash
docker compose up -d db redis
# Keyin seed qiling:
python -m scripts.seed
# Botni ishga tushiring:
docker compose up bot
```

### 3. Lokal ishga tushirish
```bash
pip install -r requirements.txt

# PostgreSQL va Redis ishlab turishi kerak
# .env faylida DATABASE_URL va REDIS_URL ni to'g'rilang

python -m scripts.seed   # DB ga savollarni yuklash (bir marta)
python -m bot            # Botni ishga tushirish
```

## Loyiha tuzilmasi

```
iq_bot/
├── bot/
│   ├── core/           # Config, Bot/Dispatcher/Redis loader
│   ├── db/
│   │   ├── models/     # User, Module, Question, TestSession
│   │   └── repositories/  # CRUD lar
│   ├── handlers/
│   │   ├── user/       # /start, test oqimi
│   │   └── admin/      # Admin panel
│   ├── keyboards/      # Inline tugmalar
│   ├── middlewares/    # DB session, admin tekshiruv
│   ├── services/       # TestService (Redis), IQ kalkulyator
│   └── utils/          # FSM states
└── scripts/
    └── seed.py         # Mavjud 3 blok savollari import
```

## Admin buyruqlari

- `/admin` — Admin panelni ochish

Admin panelda:
- **Modullar** — yaratish, tahrirlash, o'chirish, yoqish/o'chirish
- **Savollar** — har bir modul uchun savol qo'shish/tahrirlash/o'chirish
- **Statistika** — foydalanuvchilar va test natijalari

## IQ ball hisobi

| To'g'ri javoblar | IQ ball |
|---|---|
| 29-30 | 145 |
| 27-29 | 135 |
| 25-27 | 128 |
| 22-25 | 120 |
| 19-22 | 112 |
| 16-19 | 105 |
| 13-16 | 97 |
| 10-13 | 90 |
| 7-10 | 83 |
| 4-7 | 76 |
| 0-4 | 70 |
