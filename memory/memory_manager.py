import json
import os
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

class MemoryManager:
    def __init__(self, memory_dir: str = "memory_store"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        self.short_term_memory = self._load_short_term()  
        self.long_term_memory = self._load_long_term()
        self.behavioral_memory = self._load_behavioral()
    
    def _load_short_term(self) -> List:
        path = self.memory_dir / "short_term.json"
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return []
        
    def _load_long_term(self) -> Dict:
        path = self.memory_dir / "long_term.json"
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return {
            "user_preferences": {},
            "research_themes": [],
            "key_entities": [],
            "expertise_level": "intermediate"
        }
    
    def _load_behavioral(self) -> Dict:
        path = self.memory_dir / "behavioral.json"
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return {
            "query_patterns": [],
            "interaction_count": 0,
            "preferred_depth": "detailed",
            "common_topics": []
        }
    
    def save_all(self):
        with open(self.memory_dir / "short_term.json", 'w') as f:
            json.dump(self.short_term_memory, f, indent=2)
        
        with open(self.memory_dir / "long_term.json", 'w') as f:
            json.dump(self.long_term_memory, f, indent=2)
        
        with open(self.memory_dir / "behavioral.json", 'w') as f:
            json.dump(self.behavioral_memory, f, indent=2)
    
    def add_to_short_term(self, role: str, content: str):
        self.short_term_memory.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self.short_term_memory) > 10:
            self.short_term_memory = self.short_term_memory[-10:]
        
        self.save_all()
    
    def update_long_term(self, key: str, value: Any):
        if key in self.long_term_memory:
            if isinstance(self.long_term_memory[key], list):
                if value not in self.long_term_memory[key]:
                    self.long_term_memory[key].append(value)
            else:
                self.long_term_memory[key] = value
        self.save_all()
    
    def track_behavior(self, query: str, topic: str):
        self.behavioral_memory["interaction_count"] += 1
        self.behavioral_memory["query_patterns"].append({
            "query": query[:100],
            "topic": topic,
            "timestamp": datetime.now().isoformat()
        })
        
        if topic not in self.behavioral_memory["common_topics"]:
            self.behavioral_memory["common_topics"].append(topic)
        
        self.save_all()
    
    def get_context_summary(self) -> str:
        context = []
        
        if self.short_term_memory:
            recent = self.short_term_memory[-3:]
            history = []
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                history.append(f"{role}: {msg['content'][:100]}")
            context.append(f"Recent conversation: {' | '.join(history)}")
        
        if self.long_term_memory.get("research_themes"):
            context.append(f"User research themes: {', '.join(self.long_term_memory['research_themes'][:3])}")
        
        if self.behavioral_memory.get("common_topics"):
            context.append(f"Common topics: {', '.join(self.behavioral_memory['common_topics'][:3])}")
        
        context.append(f"Expertise level: {self.long_term_memory.get('expertise_level', 'intermediate')}")
        
        return " | ".join(context)
    
    def get_previous_question(self) -> str:
        for msg in reversed(self.short_term_memory):
            if msg["role"] == "user":
                return msg["content"]
        return "No previous question found"
    
    def get_conversation_history(self, limit: int = 5) -> List[Dict]:
        return self.short_term_memory[-limit:]
    
    def clear_session(self):
        self.short_term_memory = []
