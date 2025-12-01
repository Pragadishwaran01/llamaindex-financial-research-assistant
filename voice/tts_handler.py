import asyncio
from typing import Optional, AsyncGenerator
import os

class TTSHandler:
    """Text-to-Speech handler using ElevenLabs"""
    
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.client = None
        
        if self.api_key:
            try:
                from elevenlabs.client import ElevenLabs
                self.client = ElevenLabs(api_key=self.api_key)
            except Exception as e:
                pass  # ElevenLabs not available
    
    async def synthesize_streaming(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream TTS audio for low latency"""
        if not self.client:
            yield b"[TTS not available]"
            return
        
        try:
            # ElevenLabs v1+ streaming API
            audio_stream = self.client.text_to_speech.convert_as_stream(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_turbo_v2"
            )
            
            for chunk in audio_stream:
                yield chunk
                
        except Exception as e:
            yield b""
    
    async def synthesize(self, text: str) -> bytes:
        """Generate complete audio (non-streaming)"""
        if not self.client:
            return b""
        
        try:
            audio = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_turbo_v2"
            )
            return b"".join(audio)
        except Exception as e:
            return b""
    
    def handle_interruption(self):
        """Handle voice interruption"""
        # In production, this would stop current audio playback
        pass
