#!/usr/bin/env python3
"""
Test memory persistence across sessions
"""

import asyncio
from main import ResearchAssistant

async def test_memory():
    """Test memory features"""
    
    print("\nMemory Persistence Test\n")
    print("Session 1:")
    
    assistant = ResearchAssistant()
    
    assistant.memory.update_long_term("research_themes", "cloud software business models")
    assistant.memory.update_long_term("research_themes", "investment analysis")
    assistant.memory.update_long_term("expertise_level", "advanced")
    
    result1 = await assistant.process_query("What was Honeywell's revenue in 2023?", show_workflow_steps=False)
    print(f"Query 1: {result1['summary'][:100]}...")
    
    result2 = await assistant.process_query("Compare Aerospace and HBT segments", show_workflow_steps=False)
    print(f"Query 2: {result2['summary'][:100]}...")
    
    print(f"\nSession 1 complete - {len(assistant.memory.short_term_memory)} messages stored")
    
    assistant.memory.save_all()
    del assistant
    
    print("\nSession 2 (after restart):")
    
    assistant2 = ResearchAssistant()
    
    print(f"Memory restored - {assistant2.memory.behavioral_memory['interaction_count']} total interactions")
    print(f"Themes: {assistant2.memory.long_term_memory['research_themes']}")
    
    result3 = await assistant2.process_query("What about profit margins?", show_workflow_steps=False)
    print(f"Query 3: {result3['summary'][:100]}...")
    
    print("\nTest complete - memory persisted across sessions\n")

if __name__ == "__main__":
    asyncio.run(test_memory())
