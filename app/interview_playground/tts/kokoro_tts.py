"""
Kokoro TTS implementation using kokoro-onnx for local text-to-speech.
Runs the Kokoro-82M model locally — no API key needed.
"""

import asyncio
import numpy as np
from typing import AsyncGenerator
from pathlib import Path
import structlog

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter

from app.interview_playground.tts.base_tts import BaseTTS

logger = structlog.get_logger()


class KokoroTTSService(TTSService):
    """Pipecat-compatible TTS service using Kokoro-82M via kokoro-onnx.

    Runs entirely locally. Model files (~300MB) are auto-downloaded
    on first use to ~/.cache/kokoro-onnx/.
    """

    def __init__(
        self,
        *,
        voice: str = "af_bella",
        speed: float = 1.05,
        lang_code: str = "en-us",
        sample_rate: int = 24000,
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._voice = voice
        self._speed = speed
        self._lang_code = lang_code
        self._kokoro = None
        self._lock = asyncio.Lock()

        self.set_voice(voice)
        logger.info(
            "KokoroTTSService initialized",
            voice=voice,
            speed=speed,
            lang_code=lang_code,
            sample_rate=sample_rate,
        )

    @staticmethod
    def _resolve_model_paths() -> tuple:
        """Resolve model file paths from cache directory."""
        cache_dir = Path.home() / ".cache" / "kokoro-onnx"
        model_path = cache_dir / "kokoro-v1.0.onnx"
        voices_path = cache_dir / "voices-v1.0.bin"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Kokoro ONNX model not found at {model_path}. "
                "Download it: curl -L -o ~/.cache/kokoro-onnx/kokoro-v1.0.onnx "
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
            )
        if not voices_path.exists():
            raise FileNotFoundError(
                f"Kokoro voices file not found at {voices_path}. "
                "Download it: curl -L -o ~/.cache/kokoro-onnx/voices-v1.0.bin "
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
            )

        return str(model_path), str(voices_path)

    async def _ensure_model_loaded(self):
        """Lazily load the kokoro-onnx model on first use."""
        if self._kokoro is not None:
            return

        async with self._lock:
            if self._kokoro is not None:
                return

            logger.info("Loading Kokoro-82M ONNX model (first use — may take a moment)...")
            try:
                import kokoro_onnx
                model_path, voices_path = self._resolve_model_paths()
                self._kokoro = await asyncio.to_thread(kokoro_onnx.Kokoro, model_path, voices_path)
                logger.info("Kokoro-82M model loaded successfully", model_path=model_path)
            except Exception as e:
                logger.error("Failed to load Kokoro model", error=str(e))
                raise

    def _effective_sample_rate(self) -> int:
        """Get effective sample rate, using init value if pipeline hasn't started."""
        return self.sample_rate or self._init_sample_rate or 24000

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Convert text to audio frames using Kokoro-82M streaming API.

        Uses create_stream() for lower time-to-first-audio — yields audio
        chunks as they are generated rather than waiting for the full sentence.
        """
        try:
            await self._ensure_model_loaded()
            await self.start_ttfb_metrics()
            await self.start_tts_usage_metrics(text)

            yield TTSStartedFrame()

            sr = self._effective_sample_rate()
            chunk_size = int(sr * 0.5 * 2)  # 0.5s of 16-bit mono audio

            first_chunk = True
            async for samples, sample_rate in self._kokoro.create_stream(
                text,
                voice=self._voice,
                speed=self._speed,
                lang=self._lang_code,
            ):
                if first_chunk:
                    await self.stop_ttfb_metrics()
                    first_chunk = False

                # Convert float32 samples to int16 PCM bytes
                audio_int16 = (samples * 32767).astype(np.int16)
                audio_bytes = audio_int16.tobytes()

                # Yield in sub-chunks for smooth pipeline flow
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i : i + chunk_size]
                    yield TTSAudioRawFrame(
                        audio=chunk,
                        sample_rate=sr,
                        num_channels=1,
                    )

            yield TTSStoppedFrame()

        except Exception as e:
            logger.error("Kokoro TTS error", error=str(e), text_length=len(text))
            yield ErrorFrame(error=f"Kokoro TTS error: {str(e)}")

    def can_generate_metrics(self) -> bool:
        return True


class KokoroTTS(BaseTTS):
    """Project-level wrapper for Kokoro TTS with markdown filtering."""

    def __init__(
        self,
        voice: str = "af_bella",
        speed: float = 1.05,
        lang_code: str = "en-us",
        filter_code: bool = True,
        filter_tables: bool = True,
        enable_markdown_filter: bool = True,
    ):
        self.voice = voice
        self.speed = speed
        self.lang_code = lang_code
        self.filter_code = filter_code
        self.filter_tables = filter_tables
        self.enable_markdown_filter = enable_markdown_filter

    def setup_processor(self):
        """Return a configured KokoroTTSService FrameProcessor instance."""
        text_filters = []
        if self.enable_markdown_filter:
            text_filters.append(
                MarkdownTextFilter(
                    params=MarkdownTextFilter.InputParams(
                        enable_text_filter=True,
                        filter_code=self.filter_code,
                        filter_tables=self.filter_tables,
                    )
                )
            )

        return KokoroTTSService(
            voice=self.voice,
            speed=self.speed,
            lang_code=self.lang_code,
            text_filters=text_filters,
        )
