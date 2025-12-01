import asyncio
from typing import Optional, Callable
import os

class STTHandler:
    """Speech-to-Text handler using Deepgram"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        self.client = None
        
        if self.api_key:
            try:
                from deepgram import DeepgramClient
                self.client = DeepgramClient(api_key=self.api_key)
            except Exception as e:
                pass  # Deepgram not available
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio bytes to text"""
        if not self.client:
            return "[STT not available]"
        
        try:
            # Deepgram SDK v5+ API
            options = {
                "model": "nova-2",
                "smart_format": True,
                "language": "en-US"
            }
            response = self.client.listen.rest.v("1").transcribe_file(
                {"buffer": audio_data},
                options
            )
            
            transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
            return transcript
        except Exception as e:
            return f"[Transcription error: {str(e)}]"
    
    async def transcribe_stream(self, audio_stream, callback: Callable[[str], None]):
        if not self.client:
            callback("[STT not available]")
            return
        
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
            
            if len(buffer) > 32000:
                text = await self.transcribe_audio(bytes(buffer))
                callback(text)
                buffer.clear()
