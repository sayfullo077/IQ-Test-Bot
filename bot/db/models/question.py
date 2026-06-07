from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Telegram file_id (cached after first send) or local path for seeding
    image_file_id: Mapped[str | None] = mapped_column(String(256))
    image_path: Mapped[str | None] = mapped_column(String(512))

    options_count: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    correct_answer: Mapped[str] = mapped_column(String(2), nullable=False)
    q_type: Mapped[str | None] = mapped_column(String(64))
    difficulty: Mapped[str | None] = mapped_column(String(32))

    module: Mapped["Module"] = relationship(back_populates="questions")
