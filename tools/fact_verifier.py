from typing import Dict, Optional
from llama_index.core.tools import FunctionTool
import os
import re

class FactVerifier:
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.tavily_client = None
        
        if self.tavily_api_key and self.tavily_api_key != "your-tavily-api-key-here":
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=self.tavily_api_key)
            except Exception as e:
                print(f"Tavily not available: {e}")
    
    def verify_claim(self, claim: str, context: str) -> Dict[str, any]:
        result = {
            "claim": claim,
            "verified": False,
            "confidence": 0.0,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "method": "context_analysis",
            "status": "unknown"
        }
        
        claim_keywords = [w for w in claim.lower().split() if len(w) > 3]
        context_lower = context.lower()
        
        exact_matches = sum(1 for word in claim_keywords if word in context_lower)
        claim_numbers = re.findall(r'\d+(?:\.\d+)?', claim)
        context_numbers = re.findall(r'\d+(?:\.\d+)?', context)
        number_matches = sum(1 for num in claim_numbers if num in context_numbers)
        
        keyword_confidence = exact_matches / max(len(claim_keywords), 1)
        number_confidence = number_matches / max(len(claim_numbers), 1) if claim_numbers else 0.5
        
        if claim_numbers:
            confidence = (keyword_confidence * 0.4) + (number_confidence * 0.6)
        else:
            confidence = keyword_confidence
        
        result["confidence"] = round(min(confidence, 1.0), 2)
        
        if result["confidence"] >= 0.7:
            result["verified"] = True
            result["status"] = "verified"
        elif result["confidence"] >= 0.4:
            result["status"] = "partially_verified"
        elif result["confidence"] < 0.2:
            result["status"] = "cannot_verify"
        else:
            result["status"] = "uncertain"
        
        if result["confidence"] > 0.3:
            sentences = context.split('.')
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(word in sentence_lower for word in claim_keywords if len(word) > 3):
                    result["supporting_evidence"].append(sentence.strip())
                    if len(result["supporting_evidence"]) >= 3:
                        break
        
        if not result["supporting_evidence"]:
            result["status"] = "cannot_verify"
            result["supporting_evidence"] = ["No supporting evidence found in context"]
        
        return result
    
    def verify_with_search(self, claim: str, company: str = "Honeywell") -> Dict[str, any]:
        if not self.tavily_client:
            return {
                "claim": claim,
                "verified": False,
                "confidence": 0.0,
                "error": "Internet search not available",
                "method": "search_unavailable"
            }
        
        try:
            query = f"{company} {claim}"
            response = self.tavily_client.search(query, max_results=3)
            
            results = response.get('results', [])
            if results:
                return {
                    "claim": claim,
                    "verified": True,
                    "confidence": 0.8,
                    "supporting_evidence": [r.get('content', '')[:200] for r in results[:2]],
                    "sources": [r.get('url', '') for r in results[:2]],
                    "method": "internet_search"
                }
        except Exception as e:
            return {
                "claim": claim,
                "verified": False,
                "confidence": 0.0,
                "error": str(e),
                "method": "search_failed"
            }
        
        return {
            "claim": claim,
            "verified": False,
            "confidence": 0.0,
            "method": "no_results"
        }

def create_fact_verifier_tool(tavily_api_key: Optional[str] = None) -> FunctionTool:
    verifier = FactVerifier(tavily_api_key)
    
    def verify_fact(claim: str, context: str = "") -> str:
        return str(verifier.verify_claim(claim, context))
    
    return FunctionTool.from_defaults(
        fn=verify_fact,
        name="fact_verifier",
        description="Verifies claims against context with confidence levels"
    )
