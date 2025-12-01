# Design Document

## Overview

This document explains the key architectural decisions and trade-offs for a multi-agent research assistant built with LlamaIndex Workflows. The system handles complex financial document analysis with memory persistence and voice capabilities.

## Architecture

### Multi-Agent Workflow

The system uses four specialized agents orchestrated through LlamaIndex Workflows:

1. **Query Planner** - Breaks complex queries into sub-tasks
2. **Research Agent** - Retrieves information from documents  
3. **Validator** - Verifies accuracy using LLM-as-judge pattern
4. **Summarizer** - Generates final responses

This separation makes the system easier to test and debug. The event-driven architecture provides visibility into each step of the workflow.

```python
class ResearchWorkflow(Workflow):
    @step
    async def plan_query(self, ctx: Context, ev: StartEvent) -> QueryPlanEvent
    @step
    async def research(self, ctx: Context, ev: QueryPlanEvent) -> ResearchEvent
    @step
    async def validate(self, ctx: Context, ev: ResearchEvent) -> ValidationEvent
    @step
    async def summarize(self, ctx: Context, ev: ValidationEvent) -> StopEvent
```

### Memory System

The memory architecture has three layers:

- **Short-term**: Last 10 messages for conversation context
- **Long-term**: User preferences and research themes (persisted to JSON files)
- **Behavioral**: Interaction patterns and common topics

I chose file-based storage for simplicity, but the design allows easy migration to Redis or PostgreSQL for production use.

### Tool Integration

Two specialized tools handle financial analysis:

1. **Financial Metrics Extractor** - Parses currencies, percentages, and YoY changes from text
2. **Fact Verifier** - Validates claims against PDF context and optionally internet sources

The agents decide autonomously when to use these tools based on query content. For example, queries containing "margin" or "profit" trigger the financial extractor.

### Voice Interface

The voice system uses a dual-path approach:
- **Fast path**: Simplified query engine returns responses in 2-3 seconds
- **Background path**: Full workflow runs asynchronously for demonstration

I used Twilio's built-in STT/TTS rather than custom solutions (Deepgram + ElevenLabs) to keep the implementation simple while meeting the sub-3s latency requirement. The vector index is cached to avoid rebuilding on each query.

## Key Decisions

### Prompt Engineering

Each agent uses structured prompts with clear roles, instructions, and output formats. Anti-hallucination rules enforce that agents only use information from source documents. The prompts also suppress chain-of-thought reasoning to keep responses concise.

### Autonomous Tool Usage

Rather than hardcoding when tools run, agents decide based on query content. This reduces unnecessary API calls - for instance, the financial extractor only runs when queries mention financial terms.

### Memory Query Optimization

Memory queries like "what was my previous question?" are detected early and bypass the full workflow, returning results in under 1 second.

## Trade-offs

### Performance vs Completeness

The voice interface uses a simplified query path (2-3s) while the full workflow runs in the background (20-30s). This meets the latency requirement while still demonstrating the complete multi-agent system.

### Storage Simplicity

I used JSON files instead of a database to keep setup simple. The code is structured to make migration to Redis or PostgreSQL straightforward when needed for production.

### Voice Quality vs Implementation Time

Twilio's built-in STT/TTS was chosen over custom solutions (Deepgram + ElevenLabs) since voice was the lowest priority feature. The built-in option still achieves sub-3s latency.

### Verification Depth

The fact verifier uses PDF context by default (fast and free) but can optionally query internet sources for additional validation. The agent decides when external verification is worth the extra API cost.

## Future Improvements

Given more time, I would focus on:

**Voice Quality** - Replace Twilio's built-in STT/TTS with Deepgram and ElevenLabs for better audio quality and more natural speech.

**Memory Enhancement** - Add semantic search over conversation history using vector embeddings. Implement memory summarization to compress old conversations while preserving key information.

**Tool Expansion** - Add more financial analysis tools (ratio calculators, trend analyzers) and integrate external APIs like Bloomberg or Yahoo Finance for real-time data.

**Production Infrastructure** - Add authentication, rate limiting, structured logging, and monitoring. Implement proper testing with 90%+ coverage and set up CI/CD pipelines.

**Scalability** - Migrate to Redis for caching and memory storage, add message queues for workflow orchestration, and implement load balancing across multiple worker instances.

## Performance

Current metrics from testing:
- Voice responses: 2-3 seconds
- Simple queries: 5-10 seconds  
- Complex queries: 20-30 seconds
- Memory queries: <1 second

Validation confidence typically ranges from 0.80-1.00, with the system correctly identifying when data is incomplete or uncertain.

## Implementation Notes

The codebase emphasizes clean separation of concerns with distinct modules for agents, tools, memory, and voice. Error handling includes graceful degradation - for example, if Tavily internet search is unavailable, the system falls back to PDF-only verification.

The test suite includes files for each major component plus end-to-end integration tests. All core functionality is demonstrated through working examples.
