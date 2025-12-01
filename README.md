# Voice-Enabled Research Assistant

Multi-agent research assistant built with LlamaIndex Workflows for financial document analysis.

## Features

**Multi-Agent System**
- Query Planner: Breaks down complex queries
- Research Agent: Retrieves information from documents
- Validator: Verifies accuracy using LLM-as-judge
- Summarizer: Generates final responses

**Memory System**
- Short-term: Last 10 messages for context
- Long-term: User preferences and themes (persisted)
- Behavioral: Tracks interaction patterns

**Tools**
- Financial Metrics Extractor: Parses currencies, percentages, YoY changes
- Fact Verifier: Validates claims against PDF and internet sources

**Voice Interface**
- Sub-3s latency with Twilio STT/TTS
- Handles interruptions gracefully

## Setup

**Requirements**
- Python 3.12+
- OpenAI API key
- Honeywell-2023-Annual-Report.pdf (included)

**Installation**

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

**Running**

```bash
python startup.py              # Comprehensive demo
python main.py test            # Test case
python main.py                 # Interactive mode
python test_memory.py          # Memory persistence test
```

## Test Case

The test case analyzes YoY profit margin changes across Honeywell's segments (Aerospace, HBT, PMT, SPS) and identifies the strongest performer.

```bash
python main.py test
```

Expected output shows:
- All 4 agents working (Planner → Research → Validator → Summarizer)
- Both tools used (Financial Extractor, Fact Verifier)
- Confidence score and validation results
- Answer: HBT shows strongest improvement (+1.0% margin)

## Project Structure

```
agents/workflow.py          - Multi-agent workflow
memory/memory_manager.py    - 3-tier memory system
tools/                      - Financial extractor & fact verifier
voice/                      - STT/TTS handlers
main.py                     - Main application
config.py                   - Configuration
startup.py                  - Demo script
test_memory.py              - Memory test
twilio_simple_call.py       - Voice server
```

## How It Works

Query → Memory (context) → Query Planner → Research → Validator → Summarizer → Response

All workflow steps are visible in real-time.

## Example Usage

**Simple queries:**
```
What was Honeywell's revenue in 2023?
What are the main business segments?
```

**Complex analysis:**
```
Calculate YoY profit margin changes for all segments
Analyze Aerospace segment financial performance
```

**Memory:**
```
I'm analyzing aerospace companies for my investment thesis
Tell me about Honeywell's Aerospace segment
What was my previous question?
```

## Memory Test

```bash
python test_memory.py
```

Demonstrates:
- Memory persistence across sessions
- Context-aware responses
- User preference tracking

## Configuration

Required: Add your OpenAI API key to `.env`

```bash
cp .env.example .env
# Edit .env and add OPENAI_API_KEY
```

Optional: Add Tavily API key for internet search verification

## Performance

- Voice: 2-3 seconds
- Simple queries: 5-10 seconds
- Complex queries: 20-30 seconds
- Memory queries: <1 second

## Voice Testing

```bash
python twilio_simple_call.py        # Start server
ngrok http 8000                     # Expose with ngrok
# Update .env with ngrok URL
python twilio_simple_call.py call +your-number
```

## Implementation Details

See DESIGN_DOCUMENT.md for architecture decisions and trade-offs.
