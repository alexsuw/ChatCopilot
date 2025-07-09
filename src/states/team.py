from aiogram.fsm.state import StatesGroup, State

class CreateTeam(StatesGroup):
    name = State()

class JoinTeam(StatesGroup):
    invite_code = State()

class ChatWithTeam(StatesGroup):
    active = State()

class SetSystemMessage(StatesGroup):
    message = State() 