# app/providers/base_llm.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseLLMProvider(ABC):

    @abstractmethod
    def generate_response(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 0.2
    ) -> str:
        """
        Recibe las instrucciones del sistema (con el contexto RAG) y la pregunta.
        Debe retornar únicamente el string con la respuesta de texto.
        """
        pass