import secrets
import string
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberUpdated, CallbackQuery

from src.states.team import CreateTeam, JoinTeam, SetSystemMessage
from src.keyboards.inline import select_team_keyboard, select_chat_team_keyboard, select_team_for_system_message_keyboard
from src.services.supabase_client import (
    create_team, create_user, get_team_by_invite_code, add_user_to_team, 
    get_user_teams, get_user_admin_teams, get_user_by_id, link_chat_to_team,
    update_team_system_message
)
from src.services.vector_db import test_team_vector_creation, get_namespace_stats

router = Router()

def generate_invite_code(length=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

async def get_or_create_user(user: types.User):
    """Get or create user in database"""
    try:
        existing_user = await get_user_by_id(user.id)
        if existing_user:
            return existing_user
        else:
            # User doesn't exist, create it
            return await create_user(user.id, user.username, user.first_name)
    except Exception as e:
        raise e

# --- Create Team Handler ---
@router.message(Command("create_team"))
async def create_team_command(message: Message, state: FSMContext):
    await message.answer("Введите название команды:")
    await state.set_state(CreateTeam.name)

@router.message(CreateTeam.name)
async def process_team_name(message: Message, state: FSMContext):
    team_name = message.text
    user_id = message.from_user.id
    
    try:
        # Ensure user exists in database
        await get_or_create_user(message.from_user)
        
        # Generate invite code
        invite_code = generate_invite_code()
        
        # Create team
        team = await create_team(team_name, user_id, invite_code)
        team_id = team['id']
        
        # Add creator as admin to the team
        await add_user_to_team(user_id, team_id, "admin")
        
        await message.answer(
            f"✅ Команда '{team_name}' успешно создана!\n"
            f"🔑 Код приглашения: `{invite_code}`\n"
            f"📋 ID команды: `{team_id}`\n\n"
            f"Поделитесь кодом приглашения с участниками команды.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании команды: {e}")
    
    await state.clear()

# --- Join Team Handler ---
@router.message(Command("join_team"))
async def join_team_command(message: Message, state: FSMContext):
    await message.answer("Введите код приглашения в команду:")
    await state.set_state(JoinTeam.invite_code)

@router.message(JoinTeam.invite_code)
async def process_join_team(message: Message, state: FSMContext):
    invite_code = message.text.strip()
    user_id = message.from_user.id
    
    try:
        # Ensure user exists in database
        await get_or_create_user(message.from_user)
        
        # Find team by invite code
        team = await get_team_by_invite_code(invite_code)
        
        if not team:
            await message.answer("❌ Команда с таким кодом приглашения не найдена.")
            await state.clear()
            return
        
        team_id = team['id']
        team_name = team['name']
        
        # Add user to team
        await add_user_to_team(user_id, team_id, "member")
        
        await message.answer(
            f"✅ Вы успешно присоединились к команде '{team_name}'!\n"
            f"📋 ID команды: `{team_id}`",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при присоединении к команде: {e}")
    
    await state.clear()

# --- My Teams Handler ---
@router.message(Command("my_teams"))
async def my_teams_command(message: Message):
    user_id = message.from_user.id
    
    try:
        # Ensure user exists in database
        await get_or_create_user(message.from_user)
        
        # Get user teams (both as member and admin)
        teams = await get_user_teams(user_id)
        admin_teams = await get_user_admin_teams(user_id)
        
        if not teams and not admin_teams:
            await message.answer("📭 У вас нет команд. Создайте новую командой /create_team или присоединитесь к существующей командой /join_team")
            return
        
        response = "👥 **Ваши команды:**\n\n"
        
        # Show admin teams
        if admin_teams:
            response += "🔹 **Команды, где вы администратор:**\n"
            for team in admin_teams:
                response += f"• {team['name']} (ID: `{team['id']}`)\n"
                response += f"  🔑 Код: `{team['invite_code']}`\n\n"
        
        # Show member teams (excluding admin teams)
        admin_team_ids = [t['id'] for t in admin_teams]
        member_teams = [t for t in teams if t['id'] not in admin_team_ids]
        
        if member_teams:
            response += "🔸 **Команды, где вы участник:**\n"
            for team in member_teams:
                response += f"• {team['name']} (ID: `{team['id']}`)\n\n"
        
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении списка команд: {e}")

# --- Test Pinecone Handler ---
@router.message(Command("test_pinecone"))
async def test_pinecone_command(message: Message):
    user_id = message.from_user.id
    
    try:
        # Ensure user exists in database
        await get_or_create_user(message.from_user)
        
        # Get user's admin teams
        admin_teams = await get_user_admin_teams(user_id)
        
        if not admin_teams:
            await message.answer("❌ У вас нет команд для тестирования. Создайте команду командой /create_team")
            return
        
        await message.answer("🔄 Тестирование Pinecone...")
        
        results = []
        for team in admin_teams:
            team_id = team['id']
            team_name = team['name']
            
            # Get current stats
            stats_before = get_namespace_stats(team_id)
            
            # Test vector creation
            test_result = await test_team_vector_creation(team_id)
            
            # Get stats after
            stats_after = get_namespace_stats(team_id)
            
            results.append({
                'team': team_name,
                'team_id': team_id,
                'before': stats_before,
                'test': test_result,
                'after': stats_after
            })
        
        # Format response
        response = "🧪 **Результаты тестирования Pinecone:**\n\n"
        
        for result in results:
            response += f"📁 **{result['team']}** (`{result['team_id']}`)\n"
            response += f"• До теста: {result['before']['vector_count']} векторов\n"
            
            if result['test']['success']:
                response += f"• ✅ Тест успешен (ID: `{result['test']['vector_id']}`)\n"
                response += f"• После теста: {result['after']['vector_count']} векторов\n"
            else:
                response += f"• ❌ Тест неудачен: {result['test'].get('error', 'Unknown error')}\n"
            
            response += "\n"
        
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при тестировании Pinecone: {e}")

# --- Link Chat Handler ---
@router.message(Command("link_chat"))
async def link_chat_command(message: Message):
    if message.chat.type == "private":
        await message.answer("❌ Эта команда работает только в групповых чатах.")
        return
    
    user_id = message.from_user.id
    
    try:
        # Ensure user exists in database
        await get_or_create_user(message.from_user)
        
        # Get user's admin teams
        admin_teams = await get_user_admin_teams(user_id)
        
        if not admin_teams:
            await message.answer("❌ У вас нет команд для привязки к этому чату. Создайте команду командой /create_team")
            return
        
        # Create keyboard with teams
        keyboard = select_team_keyboard(admin_teams)
        await message.answer("Выберите команду для привязки к этому чату:", reply_markup=keyboard)
        
    except KeyError as e:
        await message.answer(f"❌ Ошибка в структуре данных команды. Обратитесь к администратору.\nТехническая информация: отсутствует поле {e}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении списка команд.\nВозможные причины:\n• Проблема с подключением к базе данных\n• Временные неполадки сервиса\n\nПопробуйте позже или обратитесь к администратору.\nТехническая информация: {e}")

# --- System Message Handler ---
@router.message(Command("set_system_message"))
async def set_system_message_command(message: Message):
    user_id = message.from_user.id
    
    try:
        # Ensure user exists in database
        await get_or_create_user(message.from_user)
        
        # Get user's admin teams
        admin_teams = await get_user_admin_teams(user_id)
        
        if not admin_teams:
            await message.answer("❌ У вас нет команд для настройки системного сообщения. Создайте команду командой /create_team")
            return
        
        # Create keyboard with teams
        keyboard = select_team_for_system_message_keyboard(admin_teams)
        await message.answer("Выберите команду для настройки системного сообщения:", reply_markup=keyboard)
        
    except KeyError as e:
        await message.answer(f"❌ Ошибка в структуре данных команды. Обратитесь к администратору.\nТехническая информация: отсутствует поле {e}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении списка команд.\nВозможные причины:\n• Проблема с подключением к базе данных\n• Временные неполадки сервиса\n\nПопробуйте позже или обратитесь к администратору.\nТехническая информация: {e}")

# --- Callback Handlers ---
@router.callback_query(F.data.startswith("link_chat:"))
async def process_link_chat(callback: CallbackQuery):
    team_id = callback.data.split(":")[1]
    chat_id = callback.message.chat.id
    chat_title = callback.message.chat.title
    
    try:
        # Create or update linked chat
        await link_chat_to_team(chat_id, team_id, chat_title)
        
        await callback.message.edit_text("✅ Чат успешно привязан к команде!")
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при привязке чата к команде.\n"
            f"Возможные причины:\n"
            f"• Проблема с подключением к базе данных\n"
            f"• Команда была удалена\n"
            f"• У вас нет прав администратора команды\n\n"
            f"Попробуйте позже или обратитесь к администратору.\n"
            f"Техническая информация: {e}"
        )

@router.callback_query(F.data.startswith("set_system_message:"))
async def process_set_system_message(callback: CallbackQuery, state: FSMContext):
    team_id = callback.data.split(":")[1]
    
    await state.update_data(team_id=team_id)
    await state.set_state(SetSystemMessage.message)
    
    await callback.message.edit_text("Введите системное сообщение для команды:")

@router.message(SetSystemMessage.message)
async def process_system_message(message: Message, state: FSMContext):
    data = await state.get_data()
    team_id = data['team_id']
    system_message = message.text
    
    try:
        # Update team with system message
        await update_team_system_message(team_id, system_message)
        
        await message.answer("✅ Системное сообщение успешно установлено!")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при установке системного сообщения: {e}")
    
    await state.clear() 