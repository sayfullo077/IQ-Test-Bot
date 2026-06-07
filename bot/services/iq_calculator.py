def calculate_iq(correct: int, total: int = 30) -> int:
    ratio = correct / total if total else 0
    if ratio >= 0.97:   return 145
    elif ratio >= 0.90: return 135
    elif ratio >= 0.83: return 128
    elif ratio >= 0.73: return 120
    elif ratio >= 0.63: return 112
    elif ratio >= 0.53: return 105
    elif ratio >= 0.43: return 97
    elif ratio >= 0.33: return 90
    elif ratio >= 0.23: return 83
    elif ratio >= 0.13: return 76
    else:               return 70


# (percentile, label, famous_example)
_IQ_TABLE = [
    (145, 99.9, "Daho",           "Albert Einstein, Leonardo da Vinci"),
    (135, 99,   "Juda yuqori",    "Stephen Hawking, Elon Musk"),
    (128, 97,   "Yuqori",         "Bill Gates, Mark Zuckerberg"),
    (120, 91,   "Yuqori o'rta",   "Barack Obama darajasi"),
    (112, 79,   "O'rtachadan yuqori", "Muhandislar, shifokorlarning ko'pchiligi"),
    (105, 63,   "O'rta+",         "Universitet bitiruvchilari o'rtachasi"),
    ( 97, 42,   "O'rta",          "Aholining yarmi siz bilan bir darajada"),
    ( 90, 25,   "O'rtacha",       "Aholining 75% sizdan yuqori"),
    ( 83, 13,   "O'rtachadan past","Rivojlanish uchun ko'proq mashq kerak"),
    ( 76,  5,   "Past",           "Rivojlanish uchun muntazam mashq tavsiya etiladi"),
    ( 70,  2,   "Juda past",      "Mutaxassis bilan maslahatlashish tavsiya etiladi"),
]


def iq_full_result(iq: int, correct: int, total: int, timed_out: int = 0) -> str:
    row = next((r for r in _IQ_TABLE if iq >= r[0]), _IQ_TABLE[-1])
    _, percentile, label, famous = row

    top_pct = 100 - percentile
    if top_pct < 1:
        rank_line = f"Siz aholining eng yuqori <b>0.1%</b> qatoriga kirasiz! 🏆"
    elif top_pct < 5:
        rank_line = f"Siz aholining eng yuqori <b>{top_pct:.0f}%</b> orasidasisiz 🌟"
    else:
        rank_line = f"Siz aholining <b>{percentile:.0f}%</b> ini o'zib o'tdingiz 📊"

    timeout_line = f"\n⏰ Vaqt tugagan: <b>{timed_out}</b> ta savol" if timed_out > 0 else ""

    return (
        f"🎉 <b>Test yakunlandi!</b>\n\n"
        f"✅ To'g'ri javoblar: <b>{correct}/{total}</b>"
        f"{timeout_line}\n"
        f"🧠 IQ ball: <b>{iq}</b>\n"
        f"📈 Daraja: <b>{label}</b>\n\n"
        f"{rank_line}\n\n"
        f"👤 Mashhur odamlar misoli:\n"
        f"<i>{famous}</i>\n\n"
        f"💡 <b>IQ haqida:</b> O'rtacha IQ — 100. "
        f"Har 15 ball farq aholining ~14% ni ajratadi."
    )
