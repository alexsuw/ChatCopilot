import google.generativeai as genai
import logging
import asyncio
from typing import Optional
from src.settings import settings

genai.configure(api_key=settings.google_api_key.get_secret_value())

# Set up the model
generation_config = {
  "temperature": 0.7,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
]

model = genai.GenerativeModel(model_name="gemini-1.5-flash",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

async def get_answer(context: str, question: str) -> str:
    """
    Получает ответ от Google Gemini с обработкой ошибок и повторными попытками
    
    Args:
        context: Контекст для ответа
        question: Вопрос пользователя
        
    Returns:
        str: Ответ от Gemini или сообщение об ошибке
    """
    prompt_parts = [
        "CONTEXT:\n"
        f"{context}\n\n"
        "QUESTION:\n"
        f"{question}\n\n"
        "You are a helpful AI assistant for a team. Your name is ChatCopilot. "
        "Based on the CONTEXT which contains pieces of conversations from team chats, "
        "answer the QUESTION. If the context is not enough, say that you don't have enough information. "
        "Respond in Russian language."
    ]
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            logging.info(f"🤖 Gemini request attempt {attempt + 1}/{max_retries}")
            logging.debug(f"Question: {question[:100]}...")
            logging.debug(f"Context length: {len(context)} chars")
            
            # Делаем запрос к Gemini
            response = model.generate_content(prompt_parts)
            
            # Проверяем, есть ли ответ
            if not response or not response.text:
                logging.warning(f"⚠️ Gemini returned empty response on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return "❌ Извините, не удалось получить ответ от ИИ. Попробуйте переформулировать вопрос."
            
            # Проверяем на блокировку контента
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if response.prompt_feedback.block_reason:
                    logging.warning(f"🚫 Content blocked by safety filters: {response.prompt_feedback.block_reason}")
                    return "❌ Запрос заблокирован фильтрами безопасности. Попробуйте переформулировать вопрос."
            
            # Успешный ответ
            logging.info(f"✅ Gemini response received successfully (length: {len(response.text)} chars)")
            return response.text
            
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            
            logging.error(f"❌ Gemini error on attempt {attempt + 1}: {error_type}: {error_message}")
            
            # Специфичные ошибки
            if "quota" in error_message.lower() or "429" in error_message:
                logging.error("🚫 Google API quota exceeded")
                return "❌ Превышен лимит запросов к Google API. Попробуйте позже."
            
            elif "api_key" in error_message.lower() or "401" in error_message:
                logging.error("🚫 Invalid Google API key")
                return "❌ Проблема с API ключом Google. Обратитесь к администратору."
            
            elif "network" in error_message.lower() or "timeout" in error_message.lower():
                logging.error("🚫 Network or timeout error")
                if attempt < max_retries - 1:
                    logging.info(f"🔄 Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return "❌ Проблема с подключением к сервису ИИ. Попробуйте позже."
            
            else:
                logging.error(f"🚫 Unknown Gemini error: {error_type}: {error_message}")
                if attempt < max_retries - 1:
                    logging.info(f"🔄 Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return f"❌ Неизвестная ошибка ИИ: {error_type}. Попробуйте позже."
    
    # Если все попытки исчерпаны
    return "❌ Не удалось получить ответ от ИИ после нескольких попыток. Попробуйте позже." 