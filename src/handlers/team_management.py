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
# from src.services.vector_db import test_team_vector_creation, get_namespace_stats  # ОТКЛЮЧЕНО
from src.handlers.message_ingestion import message_buffer
from src.settings import settings

router = Router()

def generate_invite_code(length=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

async def get_or_create_user(user: types.User):
    existing_user = await get_user_by_id(user.id)
    if not existing_user:
        user_data = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
        }
        await create_user(user_data)
        return user_data
    return existing_user

# --- Debug System Handler ---
@router.message(Command("check_buffers"))
async def check_buffers_command(message: Message):
    """Показать текущее состояние буферов сообщений"""
    
    result = "📊 **Состояние буферов сообщений:**\n\n"
    
    if not message_buffer:
        result += "📭 Буферы пусты\n\n"
        result += "**Возможные причины:**\n"
        result += "• Бот недавно перезапущен\n"
        result += "• Нет привязанных чатов\n"
        result += "• Нет сообщений в групповых чатах\n"
        result += "• Проблемы с обработкой сообщений\n\n"
        result += "**Что проверить:**\n"
        result += "• `/debug_system` - полная диагностика\n"
        result += "• `/monitor_messages` - мониторинг в реальном времени\n"
        result += "• Убедитесь, что чаты привязаны (`/link_chat`)"
    else:
        total_messages = sum(len(msgs) for msgs in message_buffer.values())
        result += f"✅ Активных буферов: {len(message_buffer)}\n"
        result += f"📝 Всего сообщений в буферах: {total_messages}\n\n"
        
        for team_id, messages in message_buffer.items():
            result += f"**Команда {team_id[:8]}...:**\n"
            result += f"• Сообщений в буфере: {len(messages)}/5\n"
            
            if messages:
                result += f"• Последние сообщения:\n"
                for msg in messages[-2:]:  # Показать последние 2 сообщения
                    preview = msg[:40] + "..." if len(msg) > 40 else msg
                    result += f"  - {preview}\n"
            result += "\n"
        
        result += "💡 **Подсказка:** Буфер обрабатывается при накоплении 5 сообщений"
    
    await message.answer(result, parse_mode="Markdown")

@router.message(Command("force_process_buffers"))
async def force_process_buffers_command(message: Message):
    """Принудительно обработать все буферы (для админов)"""
    
    user_id = message.from_user.id
    
    try:
        # Проверяем, что пользователь админ хотя бы одной команды
        admin_teams = await get_user_admin_teams(user_id)
        
        if not admin_teams:
            await message.answer("❌ У вас нет прав администратора команд.")
            return
        
        if not message_buffer:
            await message.answer("📭 Буферы пусты - нечего обрабатывать.")
            return
        
        await message.answer("🔄 Запуск принудительной обработки буферов...")
        
        processed_count = 0
        for team_id, messages in list(message_buffer.items()):
            if messages:  # Если есть сообщения
                try:
                    # Принудительная обработка любого количества сообщений
                    chunk_text = "\n".join(messages)
                    
                    if len(chunk_text.strip()) == 0:
                        continue
                    
                    # Импортируем необходимые функции
                    from src.services.vector_db import get_embedding, upsert_vector
                    import uuid
                    
                    # Создаем эмбеддинг
                    vector = await get_embedding(chunk_text)
                    
                    # Сохраняем в Pinecone
                    vector_id = str(uuid.uuid4())
                    upsert_vector(vector_id, vector, team_id, chunk_text)
                    
                    # Очищаем буфер
                    message_buffer[team_id] = []
                    
                    processed_count += 1
                    await message.answer(
                        f"✅ Команда {team_id[:8]}...: обработано {len(messages)} сообщений\n"
                        f"📄 Создан вектор: {vector_id[:8]}..."
                    )
                    
                except Exception as e:
                    await message.answer(f"❌ Ошибка обработки команды {team_id}: {e}")
        
        if processed_count > 0:
            await message.answer(f"✅ Обработано буферов: {processed_count}")
        else:
            await message.answer("⚠️ Нет буферов для обработки.")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка при принудительной обработке: {e}")

@router.message(Command("debug_system"))
async def debug_system_command(message: Message):
    await message.answer("🔧 **Диагностика системы RAG**\n\nПроверяю все компоненты...")
    
    result = "🔧 **Результаты диагностики системы:**\n\n"
    
    # 1. Check environment variables
    result += "**1. Переменные окружения:**\n"
    try:
        # Check if keys are set (but don't expose them)
        openai_key = settings.openai_api_key.get_secret_value()
        pinecone_key = settings.pinecone_api_key.get_secret_value()
        google_key = settings.google_api_key.get_secret_value()
        
        result += f"• OpenAI API: {'✅ Настроен' if openai_key and len(openai_key) > 10 else '❌ Не настроен'}\n"
        result += f"• Pinecone API: {'✅ Настроен' if pinecone_key and len(pinecone_key) > 10 else '❌ Не настроен'}\n"
        result += f"• Google AI API: {'✅ Настроен' if google_key and len(google_key) > 10 else '❌ Не настроен'}\n"
        result += f"• Pinecone Host: {'✅ ' + settings.pinecone_host if settings.pinecone_host else '❌ Не настроен'}\n"
        
    except Exception as e:
        result += f"❌ Ошибка проверки переменных: {e}\n"
    
    # 2. Check linked chats
    result += "\n**2. Привязанные чаты:**\n"
    try:
        from src.services.supabase_client import supabase
        linked_chats = supabase.table("linked_chats").select("*").execute()
        
        if linked_chats.data:
            result += f"✅ Найдено {len(linked_chats.data)} привязанных чатов:\n"
            for chat in linked_chats.data[:3]:  # Show first 3
                chat_title = chat.get('title', 'Unknown')
                result += f"  • Chat {chat['id']} ({chat_title}) → Team {chat['team_id']}\n"
            if len(linked_chats.data) > 3:
                result += f"  • ... и еще {len(linked_chats.data) - 3} чатов\n"
        else:
            result += "❌ Нет привязанных чатов\n"
            
    except Exception as e:
        result += f"❌ Ошибка проверки чатов: {e}\n"
    
    # 3. Check message buffers
    result += "\n**3. Буферы сообщений:**\n"
    if message_buffer:
        result += f"✅ Активных буферов: {len(message_buffer)}\n"
        for team_id, messages in message_buffer.items():
            result += f"  • Team {team_id}: {len(messages)} сообщений\n"
    else:
        result += "⚠️ Буферы пусты (нормально, если недавно перезапустили)\n"
    
    # 4. Check teams
    result += "\n**4. Команды в системе:**\n"
    try:
        from src.services.supabase_client import supabase
        teams = supabase.table("teams").select("*").execute()
        
        if teams.data:
            result += f"✅ Найдено {len(teams.data)} команд:\n"
            for team in teams.data[:3]:  # Show first 3
                result += f"  • {team['name']} (ID: {team['id'][:8]}...)\n"
            if len(teams.data) > 3:
                result += f"  • ... и еще {len(teams.data) - 3} команд\n"
        else:
            result += "❌ Нет команд в системе\n"
            
    except Exception as e:
        result += f"❌ Ошибка проверки команд: {e}\n"
    
    # 5. Test Pinecone connection
    result += "\n**5. Подключение к Pinecone:**\n"
    try:
        from src.services.vector_db import pinecone_index
        stats = pinecone_index.describe_index_stats()
        
        total_vectors = stats.get('total_vector_count', 0)
        namespaces = stats.get('namespaces', {})
        
        result += f"✅ Подключение успешно\n"
        result += f"• Общее количество векторов: {total_vectors}\n"
        result += f"• Количество namespace: {len(namespaces)}\n"
        
        if namespaces:
            result += "• Активные namespace:\n"
            for ns, ns_stats in list(namespaces.items())[:3]:
                result += f"  - {ns}: {ns_stats.get('vector_count', 0)} векторов\n"
                
    except Exception as e:
        result += f"❌ Ошибка подключения к Pinecone: {e}\n"
    
    result += "\n**💡 Рекомендации:**\n"
    result += "• Убедитесь, что чат привязан к команде (/link_chat)\n"
    result += "• Напишите 5+ сообщений в групповом чате\n"
    result += "• Проверьте логи бота в Digital Ocean\n"
    result += "• Используйте /test_pinecone для проверки создания векторов"
    
    await message.answer(result, parse_mode="Markdown")

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
        
        # Combine all teams for chat selection
        all_teams = []
        
        # Add admin teams
        for team in admin_teams:
            team_copy = team.copy()
            team_copy['role'] = 'admin'
            all_teams.append(team_copy)
        
        # Add member teams (excluding admin teams to avoid duplicates)
        admin_team_ids = [t['id'] for t in admin_teams]
        for team in teams:
            if team['id'] not in admin_team_ids:
                team_copy = team.copy()
                team_copy['role'] = 'member'
                all_teams.append(team_copy)
        
        if not all_teams:
            await message.answer("📭 У вас нет команд. Создайте новую командой /create_team или присоединитесь к существующей командой /join_team")
            return
        
        # Build response text with team info
        response = "👥 **Ваши команды:**\n\n"
        
        # Show admin teams info
        if admin_teams:
            response += "🔹 **Команды, где вы администратор:**\n"
            for team in admin_teams:
                response += f"• {team['name']} (ID: `{team['id']}`)\n"
                response += f"  🔑 Код: `{team['invite_code']}`\n\n"
        
        # Show member teams info
        member_teams = [t for t in teams if t['id'] not in admin_team_ids]
        if member_teams:
            response += "🔸 **Команды, где вы участник:**\n"
            for team in member_teams:
                response += f"• {team['name']} (ID: `{team['id']}`)\n\n"
        
        response += "💬 **Выберите команду для начала диалога с ИИ-ассистентом:**"
        
        # Create keyboard for chat selection
        keyboard = select_chat_team_keyboard(all_teams)
        await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении списка команд: {e}")

# --- Test Pinecone Handler (ОТКЛЮЧЕНО) ---
@router.message(Command("test_pinecone"))
async def test_pinecone_command(message: Message):
    """Команда отключена в упрощенной версии"""
    await message.answer(
        "❌ **Команда отключена**\n\n"
        "Тестирование Pinecone недоступно в упрощенной версии без векторной базы данных.\n\n"
        "Для проверки системы используйте:\n"
        "• `/diagnostic` - общая диагностика\n"
        "• `/test_vllm` - тест vLLM сервера",
        parse_mode="Markdown"
    )

# # --- Test Pinecone Handler (ОТКЛЮЧЕНО) ---
# @router.message(Command("test_pinecone"))
# async def test_pinecone_command(message: Message):
#     user_id = message.from_user.id
#     
#     try:
#         # Ensure user exists in database
#         await get_or_create_user(message.from_user)
#         
#         # Get user's admin teams
#         admin_teams = await get_user_admin_teams(user_id)
#         
#         if not admin_teams:
#             await message.answer("❌ У вас нет команд для тестирования. Создайте команду командой /create_team")
#             return
#         
#         await message.answer("🔄 Тестирование Pinecone...")
#         
#         results = []
#         for team in admin_teams:
#             team_id = team['id']
#             team_name = team['name']
#             
#             # Get current stats
#             stats_before = get_namespace_stats(team_id)
#             
#             # Test vector creation
#             test_result = await test_team_vector_creation(team_id)
#             
#             # Get stats after
#             stats_after = get_namespace_stats(team_id)
#             
#             results.append({
#                 'team': team_name,
#                 'team_id': team_id,
#                 'before': stats_before,
#                 'test': test_result,
#                 'after': stats_after
#             })
#         
#         # Format response
#         response = "🧪 **Результаты тестирования Pinecone:**\n\n"
#         
#         for result in results:
#             response += f"📁 **{result['team']}** (`{result['team_id']}`)\n"
#             response += f"• До теста: {result['before']['vector_count']} векторов\n"
#             
#             if result['test']['success']:
#                 response += f"• ✅ Тест успешен (ID: `{result['test']['vector_id']}`)\n"
#                 response += f"• После теста: {result['after']['vector_count']} векторов\n"
#             else:
#                 response += f"• ❌ Тест неудачен: {result['test'].get('error', 'Unknown error')}\n"
#             
#             response += "\n"
#         
#         await message.answer(response, parse_mode="Markdown")
# 
#     except Exception as e:
#         await message.answer(f"❌ Ошибка при тестировании Pinecone: {e}")

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