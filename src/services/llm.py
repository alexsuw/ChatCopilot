import google.generativeai as genai
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
    prompt_parts = [
        "CONTEXT:\n"
        f"{context}\n\n"
        "QUESTION:\n"
        f"{question}\n\n"
        "You are a helpful AI assistant for a team. Your name is ChatCopilot. "
        "Based on the CONTEXT which contains pieces of conversations from team chats, "
        "answer the QUESTION. If the context is not enough, say that you don't have enough information."
    ]

    response = model.generate_content(prompt_parts)
    return response.text 