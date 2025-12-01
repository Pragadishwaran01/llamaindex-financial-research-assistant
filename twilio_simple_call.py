#!/usr/bin/env python3
import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from fastapi import FastAPI, Request, Form
from fastapi.responses import Response
import uvicorn
from main import ResearchAssistant
import asyncio

app = FastAPI()
assistant = None

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
SERVER_URL = os.getenv("SERVER_URL", "http://your-ngrok-url.ngrok.io")

@app.on_event("startup")
async def startup_event():
    global assistant
    
    from llama_index.core import Settings
    from llama_index.llms.openai import OpenAI
    
    Settings.llm = OpenAI(
        model="gpt-3.5-turbo",
        temperature=0.1,
        max_tokens=300,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    assistant = ResearchAssistant()
    print("Server ready")

@app.post("/voice")
async def voice_webhook():
    response = VoiceResponse()
    
    response.say(
        "Hi! I'm your Honeywell research assistant. What would you like to know?",
        voice='Polly.Joanna',
        language='en-US'
    )
    
    gather = Gather(
        input='speech',
        action='/process-speech',
        method='POST',
        speech_timeout='auto',
        language='en-US',
        timeout=5
    )
    response.append(gather)
    response.say("I didn't catch that. Feel free to call back anytime. Goodbye!")
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/process-speech")
async def process_speech(request: Request, SpeechResult: str = Form(None)):
    import time
    import random
    
    start_time = time.time()
    response = VoiceResponse()
    
    if not SpeechResult:
        response.say("I didn't catch that. Please try again.")
        response.redirect('/voice')
        return Response(content=str(response), media_type="application/xml")
    
    print(f"User: {SpeechResult}")
    
    try:
        acknowledgments = [
            "Interesting question! Let me pull that up for you.",
            "Great question. Give me just a second.",
            "Absolutely, let me check the report.",
            "Sure thing! Looking into that now.",
            "Good question. Let me find that information.",
            "Hmm, let me see what I can find.",
            "Alright, checking that for you.",
            "Perfect, let me grab those details.",
            "Got it! Pulling up the data now.",
            "Let me take a look at that."
        ]
        
        response.say(random.choice(acknowledgments), voice='Polly.Joanna', language='en-US')
        
        query_lower = SpeechResult.lower()
        memory_keywords = ["previous question", "what did i ask", "last question", "earlier question",
                          "before", "my question", "my last question", "what was my", "previous query",
                          "last query", "what i asked", "what did i just ask", "my earlier question"]
        
        is_memory_query = any(keyword in query_lower for keyword in memory_keywords) or (
            ("previous" in query_lower or "last" in query_lower or "earlier" in query_lower) and
            ("question" in query_lower or "ask" in query_lower or "query" in query_lower)
        )
        
        if is_memory_query:
            prev_question = assistant.memory.get_previous_question()
            answer = f"Your previous question was: {prev_question}"
            assistant.memory.add_to_short_term("user", SpeechResult)
            assistant.memory.add_to_short_term("assistant", answer)
        else:
            query_engine = assistant.document_index.as_query_engine(
                llm=assistant.workflow.llm,
                similarity_top_k=2,
                response_mode="compact"
            )
            
            try:
                result = query_engine.query(SpeechResult)
            except Exception as query_error:
                print(f"Query error: {query_error}")
                answer = "I'm having trouble finding that information. Could you try asking differently?"
                assistant.memory.add_to_short_term("user", SpeechResult)
                assistant.memory.add_to_short_term("assistant", answer)
                response.say(answer, voice='Polly.Joanna', language='en-US')
                return Response(content=str(response), media_type="application/xml")
            
            answer = str(result)[:400]
            assistant.memory.add_to_short_term("user", SpeechResult)
            assistant.memory.add_to_short_term("assistant", answer)
            assistant._extract_and_store_user_preferences(SpeechResult)
            
            asyncio.create_task(assistant.process_query(SpeechResult, show_workflow_steps=False))
        
        response.say(answer, voice='Polly.Joanna', language='en-US')
        
        gather = Gather(
            input='speech',
            action='/process-speech',
            method='POST',
            speech_timeout='auto',
            language='en-US',
            timeout=5
        )
        response.append(gather)
        response.say("Thank you for using the research assistant. Goodbye!")
        
        print(f"Response time: {time.time() - start_time:.2f}s\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
        error_msg = str(e).lower()
        if "rate" in error_msg or "quota" in error_msg:
            response.say("I'm experiencing high demand. Please try again in a moment.")
        elif "timeout" in error_msg:
            response.say("That's taking longer than expected. Let me try a simpler approach.")
        else:
            response.say("I encountered an issue. Could you rephrase your question?")
    
    return Response(content=str(response), media_type="application/xml")

def make_call(to_number: str = "+917598078188"):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    try:
        call = client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{SERVER_URL}/voice",
            method="POST"
        )
        print(f"Call initiated: {to_number} (SID: {call.sid})")
        return call.sid
    except Exception as e:
        print(f"Call failed: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "call":
        to_number = sys.argv[2] if len(sys.argv) > 2 else "+917598078188"
        
        if not SERVER_URL or "your-ngrok-url" in SERVER_URL:
            print("Error: Set SERVER_URL in .env")
            sys.exit(1)
        
        make_call(to_number)
    else:
        print("Starting server on http://0.0.0.0:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
