# app/providers/gemini_provider.py

import logging
import google.generativeai as genai
from app.providers.llm.base_llm import BaseLLMProvider
from app.core.config import settings

logger = logging.getLogger("app.providers.gemini_provider")

class GeminiLLMProvider(BaseLLMProvider):


    def __init__(self, model_name: str = "gemini-3.1-flash-lite"):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Proveedor Gemini inicializado con el modelo {model_name}")

    def generate_response(
            self,
            system_instruction: str,
            user_message: str,
            temperature: float = 0.2
    ) -> str:
        try:
            dynamic_model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction  # El constructor sí lo acepta en tu versión
            )


            # La llamada queda limpia y sin argumentos inesperados
            response = dynamic_model.generate_content(
                contents=[
                    {"role": "user", "parts": [user_message]}
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                )
            )
            return response.text

        except Exception as e:
            logger.error(f"Error en la API de Gemini: {str(e)}")
            raise e