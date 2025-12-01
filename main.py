import asyncio
import os
from pathlib import Path
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from agents.workflow import ResearchWorkflow
from memory.memory_manager import MemoryManager
from tools.financial_extractor import create_financial_extractor_tool
from tools.fact_verifier import create_fact_verifier_tool
from voice.voice_interface import VoiceInterface
import config

class ResearchAssistant:
    """Voice-enabled research assistant with multi-agent workflow"""
    
    def __init__(self):
        Settings.llm = OpenAI(
            model=config.LLM_MODEL,
            temperature=config.TEMPERATURE,
            api_key=config.OPENAI_API_KEY
        )
        Settings.embed_model = OpenAIEmbedding(
            model=config.EMBEDDING_MODEL,
            api_key=config.OPENAI_API_KEY
        )
        
        self.memory = MemoryManager(config.MEMORY_DIR)
        self.voice_interface = VoiceInterface()
        self.document_index = self._load_or_create_document_index()
        
        self.workflow = ResearchWorkflow(
            index=self.document_index,
            llm=Settings.llm,
            timeout=120
        )
        
        self.tools = {
            "financial_extractor": create_financial_extractor_tool(),
            "fact_verifier": create_fact_verifier_tool(config.TAVILY_API_KEY)
        }
    
    def _load_or_create_document_index(self) -> VectorStoreIndex:
        """Load existing document index from storage or create new one from PDF"""
        storage_path = Path(config.STORAGE_DIR)
        
        if storage_path.exists() and (storage_path / "docstore.json").exists():
            from llama_index.core import StorageContext, load_index_from_storage
            storage_context = StorageContext.from_defaults(persist_dir=str(storage_path))
            return load_index_from_storage(storage_context)
        
        documents = SimpleDirectoryReader(input_files=[config.PDF_PATH]).load_data()
        document_index = VectorStoreIndex.from_documents(documents)
        
        storage_path.mkdir(exist_ok=True)
        document_index.storage_context.persist(persist_dir=str(storage_path))
        
        return document_index
    
    async def process_query(self, user_query: str, show_workflow_steps: bool = True) -> dict:
        """Process user query through multi-agent workflow"""
        normalized_query = user_query.lower()
        memory_related_keywords = ["previous question", "what did i ask", "last question", "earlier", "before"]
        
        if any(keyword in normalized_query for keyword in memory_related_keywords):
            previous_question = self.memory.get_previous_question()
            conversation_history = self.memory.get_conversation_history(limit=5)
            
            response_summary = f"Your previous question was: '{previous_question}'. "
            if len(conversation_history) > 2:
                response_summary += f"We've had {len(conversation_history)//2} exchanges in this session. "
                response_summary += "Would you like me to elaborate on any of our previous discussions?"
            
            return {
                "summary": response_summary,
                "confidence": 1.0,
                "workflow_steps": ["Retrieved conversation history"],
                "is_memory_query": True
            }
        
        self.memory.add_to_short_term("user", user_query)
        conversation_context = self.memory.get_context_summary()
        
        query_topic = self._extract_topic_from_query(user_query)
        self.memory.track_behavior(user_query, query_topic)
        self._extract_and_store_user_preferences(user_query)
        
        workflow_result = await self.workflow.run(query=user_query, context=conversation_context)
        
        if show_workflow_steps:
            print("\nWorkflow steps:")
            for step in workflow_result.get("workflow_steps", []):
                print(f"  {step}")
        
        response_summary = workflow_result.get("summary", "")
        self.memory.add_to_short_term("assistant", response_summary)
        
        return workflow_result
    
    def _extract_topic_from_query(self, user_query: str) -> str:
        topic_keywords = {
            "financial": ["profit", "revenue", "margin", "income", "financial"],
            "aerospace": ["aerospace", "aviation", "aircraft"],
            "segment": ["segment", "division", "business unit"],
            "comparison": ["compare", "versus", "vs", "difference", "yoy"]
        }
        
        query_lower = user_query.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return topic
        return "general"
    
    def _extract_and_store_user_preferences(self, user_query: str):
        query_lower = user_query.lower()
        
        if any(w in query_lower for w in ["investment", "thesis", "analyzing"]):
            self.memory.update_long_term("research_themes", "investment_analysis")
            self.memory.update_long_term("expertise_level", "advanced")
        
        if "cloud software" in query_lower or "saas" in query_lower:
            self.memory.update_long_term("research_themes", "cloud_software")
        
        if "aerospace" in query_lower:
            self.memory.update_long_term("research_themes", "aerospace")
        
        if any(w in query_lower for w in ["detailed", "comprehensive", "in-depth"]):
            self.memory.update_long_term("expertise_level", "advanced")
        elif any(w in query_lower for w in ["simple", "basic", "overview"]):
            self.memory.update_long_term("expertise_level", "beginner")
    
    async def process_voice_query(self, audio_data: bytes) -> dict:
        return await self.voice_interface.process_voice_query(
            audio_data,
            query_handler=lambda q: self.process_query(q, show_workflow_steps=False)
        )
    
    def start_interactive_mode(self):
        """Start interactive command-line interface for queries"""
        print("\nInteractive Mode (type 'exit' to quit)\n")
        
        while True:
            try:
                user_input = input("Question: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                query_result = asyncio.run(self.process_query(user_input))
                
                print(f"\n{query_result.get('summary', 'No summary available')}")
                print(f"Confidence: {query_result.get('confidence', 0):.2f}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as error:
                print(f"Error: {error}")
    
    def run_test_case(self):
        query = """For Honeywell, calculate the YoY change in segment profit margin for 
        Aerospace, HBT, PMT, and SPS from 2022 to 2023, reconcile these changes against 
        segment revenue, operating income, and adjustment line items, and identify which 
        segment shows the strongest underlying operational improvement."""
        
        print(f"\nTest: {query}\n")
        result = asyncio.run(self.process_query(query))
        print(f"\n{result.get('summary', 'No summary')}")
        print(f"Confidence: {result.get('confidence', 0):.2f}\n")
        return result

def main():
    assistant = ResearchAssistant()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "test":
            assistant.run_test_case()
        elif command == "query":
            user_query = " ".join(sys.argv[2:])
            query_result = asyncio.run(assistant.process_query(user_query))
            print("\n" + query_result.get("summary", ""))
    else:
        assistant.start_interactive_mode()

if __name__ == "__main__":
    main()
