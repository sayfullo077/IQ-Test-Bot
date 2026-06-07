"""Redis-backed active test state per user."""
import json
import time
from redis.asyncio import Redis

REDIS_PREFIX = "iq_test:"
TTL = 3600 * 2
QUESTION_TIME_LIMIT = 60  # seconds per question


class ActiveTest:
    def __init__(
        self,
        session_id: int,
        module_id: int,
        question_ids: list[int],
        current_index: int = 0,
        answers: dict[str, str] | None = None,
        question_start_time: float | None = None,
    ):
        self.session_id = session_id
        self.module_id = module_id
        self.question_ids = question_ids
        self.current_index = current_index
        self.answers: dict[str, str] = answers or {}
        self.question_start_time: float = question_start_time or time.time()

    @property
    def total(self) -> int:
        return len(self.question_ids)

    @property
    def current_question_id(self) -> int | None:
        if self.current_index < self.total:
            return self.question_ids[self.current_index]
        return None

    @property
    def is_finished(self) -> bool:
        return self.current_index >= self.total

    @property
    def elapsed(self) -> float:
        return time.time() - self.question_start_time

    @property
    def is_timed_out(self) -> bool:
        return self.elapsed > QUESTION_TIME_LIMIT

    @property
    def remaining_seconds(self) -> int:
        return max(0, QUESTION_TIME_LIMIT - int(self.elapsed))

    def record_answer(self, question_id: int, answer: str) -> None:
        self.answers[str(question_id)] = answer.upper()
        self.current_index += 1
        self.question_start_time = time.time()

    def record_timeout(self, question_id: int) -> None:
        self.answers[str(question_id)] = "TIMEOUT"
        self.current_index += 1
        self.question_start_time = time.time()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "module_id": self.module_id,
            "question_ids": self.question_ids,
            "current_index": self.current_index,
            "answers": self.answers,
            "question_start_time": self.question_start_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActiveTest":
        return cls(
            session_id=data["session_id"],
            module_id=data["module_id"],
            question_ids=data["question_ids"],
            current_index=data["current_index"],
            answers=data.get("answers", {}),
            question_start_time=data.get("question_start_time", time.time()),
        )


class TestService:
    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, user_id: int) -> str:
        return f"{REDIS_PREFIX}{user_id}"

    async def start(self, user_id: int, test: ActiveTest) -> None:
        await self.redis.set(self._key(user_id), json.dumps(test.to_dict()), ex=TTL)

    async def get(self, user_id: int) -> ActiveTest | None:
        raw = await self.redis.get(self._key(user_id))
        if not raw:
            return None
        return ActiveTest.from_dict(json.loads(raw))

    async def save(self, user_id: int, test: ActiveTest) -> None:
        await self.redis.set(self._key(user_id), json.dumps(test.to_dict()), ex=TTL)

    async def finish(self, user_id: int) -> None:
        await self.redis.delete(self._key(user_id))

    async def has_active(self, user_id: int) -> bool:
        return bool(await self.redis.exists(self._key(user_id)))
