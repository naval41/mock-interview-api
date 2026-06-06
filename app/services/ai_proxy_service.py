import time
from typing import AsyncGenerator, List, Optional

import google.generativeai as genai

from app.core.config import settings

MAX_HISTORY_CHARS = 3000


class AiProxyService:
    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def _build_chat_messages(
        self, request, history: Optional[List[dict]] = None
    ) -> list:
        """Build message list with system context, conversation history, and current message.

        Args:
            request: The chat request containing message, code_context, language.
            history: Optional list of prior conversation turns as
                     {"role": "user"|"model", "parts": [str]} dicts.
        """
        messages = []

        # System context as the opening exchange
        system_parts = [
            "You are a coding assistant in a technical interview. "
            "Help the candidate with their coding task. "
            "Be concise. Provide code suggestions when appropriate. "
            f"The candidate is writing in {request.language}."
        ]
        if request.code_context:
            system_parts.append(
                f"Current code context:\n```{request.language}\n{request.code_context}\n```"
            )
        messages.append({"role": "user", "parts": system_parts})
        messages.append(
            {"role": "model", "parts": ["Understood. I'm ready to help with your code."]}
        )

        # Insert truncated conversation history
        if history:
            truncated = self._truncate_history(history)
            messages.extend(truncated)

        # Current user message
        messages.append({"role": "user", "parts": [request.message]})

        return messages

    @staticmethod
    def _truncate_history(
        history: List[dict], max_chars: int = MAX_HISTORY_CHARS
    ) -> List[dict]:
        """Drop oldest entries from history until total char count fits within budget."""
        total_chars = sum(
            sum(len(p) for p in entry["parts"]) for entry in history
        )
        truncated = list(history)
        while total_chars > max_chars and len(truncated) >= 2:
            # Remove oldest pair (user + model) to keep conversation coherent
            removed_user = truncated.pop(0)
            removed_model = truncated.pop(0) if truncated else {"parts": []}
            total_chars -= sum(len(p) for p in removed_user["parts"])
            total_chars -= sum(len(p) for p in removed_model["parts"])
        # If a single entry still exceeds, keep it anyway (better than empty history)
        return truncated

    async def chat_completion(
        self, request, history: Optional[List[dict]] = None
    ) -> dict:
        messages = self._build_chat_messages(request, history=history)

        start_ms = int(time.time() * 1000)
        response = await self.model.generate_content_async(
            messages,
            generation_config=genai.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.3,
            ),
        )
        latency_ms = int(time.time() * 1000) - start_ms

        return {
            "response": response.text,
            "tokens_input": response.usage_metadata.prompt_token_count,
            "tokens_output": response.usage_metadata.candidates_token_count,
            "latency_ms": latency_ms,
        }

    async def chat_completion_stream(
        self, request, history: Optional[List[dict]] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat completion chunks. Yields dicts with either:
          - {"type": "token", "text": "..."} for incremental text
          - {"type": "done", "tokens_input": N, "tokens_output": N, "latency_ms": N, "full_response": "..."}
            at the end
        """
        messages = self._build_chat_messages(request, history=history)

        start_ms = int(time.time() * 1000)
        response = await self.model.generate_content_async(
            messages,
            generation_config=genai.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.3,
            ),
            stream=True,
        )

        full_response = ""
        tokens_input = 0
        tokens_output = 0
        async for chunk in response:
            if chunk.text:
                full_response += chunk.text
                yield {"type": "token", "text": chunk.text}
            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                tokens_input = chunk.usage_metadata.prompt_token_count or 0
                tokens_output = chunk.usage_metadata.candidates_token_count or 0

        latency_ms = int(time.time() * 1000) - start_ms

        # Fallback: estimate tokens if usage_metadata wasn't available in chunks
        if tokens_input == 0 and tokens_output == 0:
            try:
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    tokens_input = response.usage_metadata.prompt_token_count or 0
                    tokens_output = response.usage_metadata.candidates_token_count or 0
            except Exception:
                pass
            if tokens_output == 0:
                tokens_output = len(full_response) // 4

        yield {
            "type": "done",
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "latency_ms": latency_ms,
            "full_response": full_response,
        }

    async def inline_completion(self, request) -> dict:
        prompt = (
            f"Complete the following {request.language} code. "
            "Return ONLY the code to insert, no explanation.\n\n"
        )
        if request.instruction:
            prompt += f"Instruction: {request.instruction}\n\n"
        prompt += f"Code before cursor:\n```\n{request.prefix}\n```\n\n"
        prompt += f"Code after cursor:\n```\n{request.suffix}\n```"

        start_ms = int(time.time() * 1000)
        response = await self.model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.2,
            ),
        )
        latency_ms = int(time.time() * 1000) - start_ms

        return {
            "suggestion": response.text.strip().strip("`"),
            "tokens_input": response.usage_metadata.prompt_token_count,
            "tokens_output": response.usage_metadata.candidates_token_count,
            "latency_ms": latency_ms,
        }
