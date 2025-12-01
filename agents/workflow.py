from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
    Event,
    Context
)
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from typing import List, Dict, Any, Optional
import json
import config

class QueryPlanEvent(Event):
    plan: Dict[str, Any]
    original_query: str

class ResearchEvent(Event):
    results: List[Dict[str, Any]]
    plan: Dict[str, Any]

class ValidationEvent(Event):
    validated_results: Dict[str, Any]
    is_valid: bool

class SummaryEvent(Event):
    summary: str
    workflow_steps: List[str]

class ResearchWorkflow(Workflow):
    
    def __init__(self, index: VectorStoreIndex, llm: OpenAI, **kwargs):
        super().__init__(**kwargs)
        self.index = index
        self.llm = llm
        self.query_engine = index.as_query_engine(llm=llm, similarity_top_k=5)
        self.workflow_steps = []
    
    @step
    async def plan_query(self, ctx: Context, ev: StartEvent) -> QueryPlanEvent:
        user_query = ev.get("query")
        conversation_context = ev.get("context", "")
        
        self.workflow_steps.append("Planning query decomposition")
        
        planning_prompt = config.QUERY_PLANNER_PROMPT.format(
            context=conversation_context,
            query=user_query
        )

        llm_response = await self.llm.acomplete(planning_prompt)
        
        try:
            query_plan = json.loads(str(llm_response))
        except:
            query_plan = {
                "objective": user_query,
                "sub_queries": [user_query],
                "data_points": ["segment data", "financial metrics"],
                "analysis_steps": ["retrieve data", "calculate changes", "compare"]
            }
        
        num_sub_queries = len(query_plan.get('sub_queries', []))
        self.workflow_steps.append(f"Created {num_sub_queries} sub-queries")
        
        return QueryPlanEvent(plan=query_plan, original_query=user_query)
    
    @step
    async def research(self, ctx: Context, ev: QueryPlanEvent) -> ResearchEvent:
        query_plan = ev.plan
        
        self.workflow_steps.append("Retrieving information")
        
        research_results = []
        sub_queries = query_plan.get("sub_queries", [ev.original_query])
        
        should_extract_financial_data = any(
            keyword in ev.original_query.lower() 
            for keyword in ['margin', 'profit', 'revenue', 'yoy', 'financial', 'segment']
        )
        
        for query_index, sub_query in enumerate(sub_queries[:5]):
            self.workflow_steps.append(f"  Query {query_index+1}: {sub_query[:60]}...")
            
            query_response = self.query_engine.query(sub_query)
            answer_text = str(query_response)
            
            query_result = {
                "sub_query": sub_query,
                "answer": answer_text,
                "source_nodes": len(query_response.source_nodes) if hasattr(query_response, 'source_nodes') else 0
            }
            
            if should_extract_financial_data and query_index == 0:
                self.workflow_steps.append("  Using financial extractor")
                from tools.financial_extractor import FinancialMetricsExtractor
                metrics_extractor = FinancialMetricsExtractor()
                extracted_metrics = metrics_extractor.extract_metrics(answer_text)
                query_result["extracted_metrics"] = extracted_metrics
                
                if extracted_metrics.get("segments"):
                    segment_names = ', '.join(extracted_metrics['segments'])
                    self.workflow_steps.append(f"  Extracted segments: {segment_names}")
                if extracted_metrics.get("percentages"):
                    percentage_count = len(extracted_metrics['percentages'])
                    self.workflow_steps.append(f"  Found {percentage_count} percentages")
            
            research_results.append(query_result)
        
        self.workflow_steps.append(f"Research complete: {len(research_results)} queries processed")
        
        return ResearchEvent(results=research_results, plan=query_plan)
    
    @step
    async def validate(self, ctx: Context, ev: ResearchEvent) -> ValidationEvent:
        research_results = ev.results
        query_plan = ev.plan
        
        self.workflow_steps.append("Validating results")
        
        fact_verification_results = []
        if research_results and len(research_results) > 0:
            self.workflow_steps.append("  Running fact verifier")
            from tools.fact_verifier import FactVerifier
            import os
            
            fact_verifier = FactVerifier(tavily_api_key=os.getenv("TAVILY_API_KEY"))
            first_research_result = research_results[0]
            answer_text = first_research_result.get("answer", "")
            
            answer_sentences = answer_text.split('.')
            for sentence in answer_sentences[:2]:
                if any(char.isdigit() for char in sentence):
                    pdf_verification_result = fact_verifier.verify_claim(sentence.strip(), answer_text)
                    pdf_verification_result["source"] = "PDF"
                    fact_verification_results.append(pdf_verification_result)
                    
                    if pdf_verification_result.get("status") == "verified":
                        confidence_score = pdf_verification_result.get('confidence', 0)
                        self.workflow_steps.append(f"  PDF verification: {confidence_score:.2f}")
                    
                    if fact_verifier.tavily_client and "revenue" in sentence.lower() or "profit" in sentence.lower():
                        try:
                            internet_verification_result = fact_verifier.verify_with_search(sentence.strip()[:50], "Honeywell")
                            internet_verification_result["source"] = "Internet"
                            fact_verification_results.append(internet_verification_result)
                            
                            if internet_verification_result.get("verified"):
                                confidence_score = internet_verification_result.get('confidence', 0)
                                self.workflow_steps.append(f"  Internet verification: {confidence_score:.2f}")
                        except Exception as search_error:
                            error_message = str(search_error)[:50]
                            self.workflow_steps.append(f"  Search unavailable: {error_message}")
                    
                    break
        
        validation_prompt = config.VALIDATOR_PROMPT.format(
            objective=query_plan.get('objective', 'N/A'),
            results=json.dumps(research_results, indent=2)[:2000],
            fact_verifications=json.dumps(fact_verification_results, indent=2) if fact_verification_results else 'No fact verifications performed'
        )

        llm_response = await self.llm.acomplete(validation_prompt)
        
        try:
            validation_result = json.loads(str(llm_response))
        except:
            if fact_verification_results:
                average_confidence = sum(v.get("confidence", 0) for v in fact_verification_results) / len(fact_verification_results)
            else:
                average_confidence = 0.8
                
            validation_result = {
                "is_valid": True,
                "confidence": average_confidence,
                "issues": [],
                "validated_data": {"results": research_results},
                "fact_verifications": fact_verification_results
            }
        
        validation_result["fact_verifications"] = fact_verification_results
        
        is_valid = validation_result.get("is_valid", True)
        confidence_score = validation_result.get("confidence", 0.8)
        
        validation_status = 'passed' if is_valid else 'failed'
        self.workflow_steps.append(f"Validation {validation_status} (confidence: {confidence_score:.2f})")
        
        return ValidationEvent(
            validated_results=validation_result,
            is_valid=is_valid
        )
    
    @step
    async def summarize(self, ctx: Context, ev: ValidationEvent) -> StopEvent:
        validated_results = ev.validated_results
        
        self.workflow_steps.append("Creating summary")
        
        summary_prompt = config.SUMMARIZER_PROMPT.format(
            validated_results=json.dumps(validated_results, indent=2)[:2000]
        )

        llm_response = await self.llm.acomplete(summary_prompt)
        final_summary = str(llm_response)
        
        self.workflow_steps.append("Summary complete")
        
        return StopEvent(result={
            "summary": final_summary,
            "workflow_steps": self.workflow_steps.copy(),
            "validation": validated_results,
            "confidence": validated_results.get("confidence", 0.0)
        })
