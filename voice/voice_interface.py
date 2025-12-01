import asyncio
import time
from typing import Optional, Callable
from .stt_handler import STTHandler
from .tts_handler import TTSHandler

class VoiceInterface:
    def __init__(self):
        self.stt = STTHandler()
        self.tts = TTSHandler()
        self.is_speaking = False
        self.interrupted = False
    
    async def process_voice_query(
        self, 
        audio_data: bytes,
        query_handler: Callable,
        on_response: Optional[Callable] = None
    ) -> dict:
        start_time = time.time()
        
        stt_start = time.time()
        text_query = await self.stt.transcribe_audio(audio_data)
        stt_latency = time.time() - stt_start
        
        process_start = time.time()
        response = await query_handler(text_query)
        process_latency = time.time() - process_start
        
        tts_start = time.time()
        response_text = response.get("summary", str(response))
        
        audio_chunks = []
        first_chunk_time = None
        
        async for chunk in self.tts.synthesize_streaming(response_text):
            if first_chunk_time is None:
                first_chunk_time = time.time()
            
            audio_chunks.append(chunk)
            
            if on_response:
                on_response(chunk)
            
            if self.interrupted:
                self.interrupted = False
                break
        
        tts_latency = time.time() - tts_start
        first_audio_latency = (first_chunk_time - start_time) if first_chunk_time else 0
        total_latency = time.time() - start_time
        
        return {
            "text_query": text_query,
            "response": response,
            "audio_chunks": audio_chunks,
            "latency": {
                "stt": round(stt_latency, 3),
                "processing": round(process_latency, 3),
                "tts": round(tts_latency, 3),
                "first_audio": round(first_audio_latency, 3),
                "total": round(total_latency, 3)
            }
        }
    
    def interrupt(self):
        self.interrupted = True
        self.tts.handle_interruption()
    
    async def text_to_speech(self, text: str) -> bytes:
        return await self.tts.synthesize(text)
    
    async def speech_to_text(self, audio_data: bytes) -> str:
        return await self.stt.transcribe_audio(audio_data)
