"""
Auto-seed: 3 blok × 30 savol.
Bot ishga tushganda bir marta chaqiriladi — DB bo'sh bo'lsa yuklaydi, aks holda o'tkazib yuboradi.
"""
import json
import logging
import os

from bot.db.base import async_session_maker
from bot.db.repositories import ModuleRepository, QuestionRepository

logger = logging.getLogger(__name__)

# Bot paketi yonidagi papkalar (iq_bot/ ichida)
_HERE = os.path.dirname(os.path.dirname(__file__))  # iq_bot/

BLOCKS = [
    {
        "name": "IQ Test — Blok 1",
        "description": "Osondan qiyingacha 30 ta savol: Number Series, Odd One Out, Matrix va boshqalar.",
        "order": 1,
        "answers_file": os.path.join(_HERE, "answers.json"),
        "images_dir": os.path.join(_HERE, "images"),
    },
    {
        "name": "IQ Test — Blok 2",
        "description": "Ikkinchi blok: murakkab mantiqiy savollar.",
        "order": 2,
        "answers_file": os.path.join(_HERE, "answers-block2.json"),
        "images_dir": os.path.join(_HERE, "images-block2"),
    },
    {
        "name": "IQ Test — Blok 3",
        "description": "Uchinchi blok: eng qiyin savollar.",
        "order": 3,
        "answers_file": os.path.join(_HERE, "answers-block3.json"),
        "images_dir": os.path.join(_HERE, "images-block3"),
    },
]


async def seed_if_empty() -> None:
    async with async_session_maker() as session:
        async with session.begin():
            m_repo = ModuleRepository(session)
            existing = await m_repo.get_all()
            if existing:
                logger.info("Seed: DB already has %d modules, skipping.", len(existing))
                return

            logger.info("Seed: loading questions into DB...")
            q_repo = QuestionRepository(session)
            total_q = 0

            for block in BLOCKS:
                if not os.path.exists(block["answers_file"]):
                    logger.warning("Seed: answers file not found: %s", block["answers_file"])
                    continue

                with open(block["answers_file"], encoding="utf-8") as f:
                    data = json.load(f)

                module = await m_repo.create(
                    name=block["name"],
                    description=block["description"],
                    order=block["order"],
                )

                for ans in data["answers"]:
                    q_num = ans["q"]
                    image_path = os.path.join(block["images_dir"], f"q{q_num:02d}.png")
                    if not os.path.exists(image_path):
                        logger.warning("Seed: image not found: %s", image_path)
                        image_path = None

                    await q_repo.create(
                        module_id=module.id,
                        order=q_num,
                        correct_answer=ans["answer"],
                        options_count=ans["options"],
                        image_path=image_path,
                        q_type=ans.get("type"),
                        difficulty=ans.get("difficulty"),
                    )
                    total_q += 1

                logger.info("Seed: '%s' — %d savol yuklandi.", module.name, len(data["answers"]))

            logger.info("Seed: jami %d savol yuklandi.", total_q)
