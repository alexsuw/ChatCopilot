import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
from src.settings import settings

async def get_answer(context: str, question: str) -> str:
    """
    Получает ответ от vLLM с обработкой ошибок и повторными попытками
    
    Args:
        context: Контекст для ответа
        question: Вопрос пользователя
        
    Returns:
        str: Ответ от vLLM или сообщение об ошибке
    """
    prompt = f"""CONTEXT:
{context}

QUESTION:
{question}

You are a helpful AI assistant for a team. Your name is ChatCopilot. 
Based on the CONTEXT which contains pieces of conversations from team chats, 
answer the QUESTION. If the context is not enough, say that you don't have enough information. 
Respond in Russian language.

ANSWER:"""
    
    # Подготавливаем данные для запроса
    payload = {
        "model": settings.vllm_model_name,
        "prompt": prompt,
        "max_tokens": settings.vllm_max_tokens,
        "temperature": settings.vllm_temperature,
        "stop": ["</s>", "<|endoftext|>"]
    }
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            logging.info(f"🤖 vLLM request attempt {attempt + 1}/{max_retries}")
            logging.debug(f"Question: {question[:100]}...")
            logging.debug(f"Context length: {len(context)} chars")
            logging.debug(f"Prompt length: {len(prompt)} chars")
            
            # Делаем запрос к vLLM
            async with httpx.AsyncClient(timeout=settings.vllm_timeout) as client:
                response = await client.post(
                    f"{settings.vllm_url}/v1/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Проверяем статус ответа
                if response.status_code != 200:
                    logging.error(f"❌ vLLM HTTP error {response.status_code}: {response.text}")
                    
                    if response.status_code == 503:
                        logging.warning("🔄 vLLM server temporarily unavailable")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            return "❌ Сервер ИИ временно недоступен. Попробуйте позже."
                    
                    elif response.status_code == 422:
                        logging.error("🚫 Invalid request parameters")
                        return "❌ Неверные параметры запроса. Обратитесь к администратору."
                    
                    elif response.status_code == 504:
                        logging.error("🕒 Request timeout")
                        return "❌ Превышено время ожидания. Попробуйте сократить вопрос."
                    
                    else:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            return f"❌ Ошибка сервера ИИ: {response.status_code}. Попробуйте позже."
                
                # Парсим ответ
                try:
                    response_data = response.json()
                except Exception as e:
                    logging.error(f"❌ Failed to parse JSON response: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return "❌ Некорректный ответ от сервера ИИ. Попробуйте позже."
                
                # Извлекаем текст ответа
                if "choices" not in response_data or not response_data["choices"]:
                    logging.warning("⚠️ vLLM returned empty choices")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return "❌ Получен пустой ответ от ИИ. Попробуйте переформулировать вопрос."
                
                answer_text = response_data["choices"][0].get("text", "").strip()
                
                if not answer_text:
                    logging.warning("⚠️ vLLM returned empty text")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return "❌ Получен пустой ответ от ИИ. Попробуйте переформулировать вопрос."
                
                # Успешный ответ
                logging.info(f"✅ vLLM response received successfully (length: {len(answer_text)} chars)")
                
                # Дополнительная обработка ответа
                if answer_text.startswith("ANSWER:"):
                    answer_text = answer_text[7:].strip()
                
                return answer_text
                
        except httpx.ConnectError:
            logging.error(f"❌ Connection error to vLLM server on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                logging.info(f"🔄 Retrying connection in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                return "❌ Не удалось подключиться к серверу ИИ. Проверьте, что vLLM запущен."
        
        except httpx.TimeoutException:
            logging.error(f"❌ Timeout error on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                logging.info(f"🔄 Retrying after timeout in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                return "❌ Превышено время ожидания. Попробуйте сократить вопрос."
        
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            
            logging.error(f"❌ vLLM error on attempt {attempt + 1}: {error_type}: {error_message}")
            
            if attempt < max_retries - 1:
                logging.info(f"🔄 Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                return f"❌ Неизвестная ошибка ИИ: {error_type}. Попробуйте позже."
    
    return "❌ Не удалось получить ответ от ИИ после нескольких попыток."


async def check_vllm_health() -> Dict[str, Any]:
    """
    Проверяет состояние vLLM сервера
    
    Returns:
        Dict с информацией о состоянии сервера
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Проверяем health endpoint
            response = await client.get(f"{settings.vllm_url}/health")
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "url": settings.vllm_url,
                    "model": settings.vllm_model_name,
                    "message": "vLLM server is running"
                }
            else:
                return {
                    "status": "unhealthy",
                    "url": settings.vllm_url,
                    "model": settings.vllm_model_name,
                    "message": f"Health check failed: {response.status_code}"
                }
                
    except httpx.ConnectError:
        return {
            "status": "connection_error",
            "url": settings.vllm_url,
            "model": settings.vllm_model_name,
            "message": "Cannot connect to vLLM server"
        }
    except Exception as e:
        return {
            "status": "error",
            "url": settings.vllm_url,
            "model": settings.vllm_model_name,
            "message": f"Health check error: {str(e)}"
        }


async def test_vllm_simple() -> str:
    """
    Простой тест vLLM сервера
    
    Returns:
        str: Результат теста
    """
    test_context = "Тестовый контекст: обсуждение работы команды"
    test_question = "Как дела?"
    
    try:
        answer = await get_answer(test_context, test_question)
        return answer
    except Exception as e:
        return f"❌ Ошибка при тестировании: {str(e)}" 