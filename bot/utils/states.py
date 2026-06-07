from aiogram.fsm.state import State, StatesGroup


class TestStates(StatesGroup):
    choosing_module = State()
    in_test = State()


class AdminModuleStates(StatesGroup):
    waiting_name = State()
    waiting_description = State()
    waiting_order = State()
    editing_name = State()
    editing_description = State()
    editing_order = State()


class AdminQuestionStates(StatesGroup):
    waiting_image = State()
    waiting_correct_answer = State()
    waiting_options_count = State()
    waiting_type = State()
    waiting_difficulty = State()


class AdminUserStates(StatesGroup):
    sending_message = State()


class AdminBroadcastStates(StatesGroup):
    waiting_message = State()
    waiting_confirm = State()


class FeedbackStates(StatesGroup):
    waiting_message = State()
    waiting_reply = State()


class AdminReplyStates(StatesGroup):
    waiting_reply = State()
