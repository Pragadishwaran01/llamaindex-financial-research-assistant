#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

async def main():
    print("\n=== Voice-Enabled Research Assistant - Startup Test ===\n")
    
    from main import ResearchAssistant
    assistant = ResearchAssistant()
    
    print("Test 1: Simple Query")
    result1 = await assistant.process_query("What was Honeywell's revenue in 2023?", show_workflow_steps=True)
    print(f"Confidence: {result1.get('confidence', 0):.2f}\n")
    
    print("Test 2: Complex Query")
    result2 = await assistant.process_query(
        "Calculate YoY change in segment profit margin for Aerospace, HBT, PMT, and SPS from 2022 to 2023",
        show_workflow_steps=True
    )
    print(f"Confidence: {result2.get('confidence', 0):.2f}\n")
    
    workflow_steps = result2.get("workflow_steps", [])
    financial_tool = any("financial extractor" in step.lower() for step in workflow_steps)
    fact_verifier = any("fact verifier" in step.lower() for step in workflow_steps)
    
    print(f"Tools used: Financial={financial_tool}, Verifier={fact_verifier}\n")
    
    print("Test 3: Memory")
    await assistant.process_query("I'm analyzing aerospace companies for my investment thesis", show_workflow_steps=False)
    print(f"Themes: {assistant.memory.long_term_memory.get('research_themes', [])}")
    print(f"Expertise: {assistant.memory.long_term_memory.get('expertise_level', '')}\n")
    
    print("Test 4: Memory Recall")
    result4 = await assistant.process_query("What was my previous question?", show_workflow_steps=False)
    print(f"{result4.get('summary', '')}\n")
    
    print("=== All Tests Complete ===")
    print(f"Short-term: {len(assistant.memory.short_term_memory)} messages")
    print(f"Interactions: {assistant.memory.behavioral_memory.get('interaction_count', 0)}")
    
    memory_dir = Path("memory_store")
    if memory_dir.exists():
        files = list(memory_dir.glob("*.json"))
        print(f"Memory files: {len(files)}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
