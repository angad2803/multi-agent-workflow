# Multi-Agent System Architecture

This document describes the current implementation of the asynchronous research-and-writing workflow. It is intentionally precise about which state is durable and which state is process-local.

## System Overview

```mermaid
graph TB
    subgraph "Multi-Agent System - General Purpose"
        User[User] -->|Any Prompt| API[FastAPI API]
        API -->|Create Task| DB[(PostgreSQL)]
        API -->|Queue Task| Celery[Celery Worker]

        Celery -->|Execute| Workflow[LangGraph Workflow]

        subgraph "Dynamic Workflow"
            Workflow --> Analyzer[Prompt Analyzer<br/>LLM-guided]
            Analyzer -->|topics + task_type| Research[Research Agent]

            Research -->|Select Tool| ToolRegistry[Tool Registry]
            ToolRegistry -->|Real Search| RealTool[LLM Research Tool]
            RealTool -->|Temporary findings| Redis2[(Redis Workspace)]

            Redis2 --> Writing[Writing Agent]
            Writing -->|Select Template| TemplateEngine[Template Engine]
            TemplateEngine -->|Dynamic Prompt| LLM[LLM]
            LLM --> Draft[Draft Content]

            Draft --> Approval[Human Approval<br/>Interrupt/Resume]
            Approval -->|Approved| Finalize[Finalize]
        end

        Finalize --> DB
        API -.->|WebSocket| User
    end

    style ToolRegistry fill:#4ecdc4
    style RealTool fill:#4ecdc4
    style Analyzer fill:#95e1d3
    style TemplateEngine fill:#95e1d3
```

## Complete Task Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING: POST /api/v1/tasks
    PENDING --> RUNNING: Celery picks up task
    RUNNING --> ANALYZING: Prompt Analyzer

    state ANALYZING {
        [*] --> ParsePrompt: LLM analyzes prompt
        ParsePrompt --> ExtractTopics: Extract research topics
        ExtractTopics --> DetermineType: comparison/tutorial/analysis/summary
        DetermineType --> [*]
    }

    ANALYZING --> RESEARCHING: Research Agent

    state RESEARCHING {
        [*] --> SelectTool: Get tool from registry
        SelectTool --> ResearchLoop: For each topic
        ResearchLoop --> RealSearch: Call LLM research tool
        RealSearch --> SaveResults: Save to research_results dict
        SaveResults --> [*]
    }

    RESEARCHING --> WRITING: Writing Agent

    state WRITING {
        [*] --> LoadResults: Get research_results from Redis
        LoadResults --> SelectTemplate: Based on task_type
        SelectTemplate --> BuildPrompt: Format template with research
        BuildPrompt --> LLMCall: Generate with LLM
        LLMCall --> [*]
    }

    WRITING --> AWAITING_APPROVAL: Draft ready
    AWAITING_APPROVAL --> RESUMED: POST /api/v1/tasks/{id}/approve
    RESUMED --> COMPLETED: Save result to DB
    AWAITING_APPROVAL --> FAILED: Rejected or error
    COMPLETED --> [*]
    FAILED --> [*]
```

## Data Flow: From Prompt to Result

```mermaid
graph LR
    subgraph "Input - ANY PROMPT"
        P1[Compare Redis vs PostgreSQL]
        P2[Tutorial: Docker setup]
        P3[Analyze Kubernetes]
    end

    subgraph "Prompt Analyzer"
        PA[PromptAnalyzer<br/>LLM-powered]

        PA -->|Extract| Meta["topics: ['Redis', 'PostgreSQL']<br/>task_type: 'comparison'"]
    end

    subgraph "Research Agent"
        RA[Research Agent]
        TR[Tool Registry]
        Tool[llm_research]

        Meta --> RA
        RA -->|Select tool| TR
        TR --> Tool
        Tool -->|For each topic| Results["Redis findings<br/>PostgreSQL findings"]
    end

    subgraph "Redis Workspace"
        R[(Redis)]
        Dict["research_results: {<br/>  'Redis': '...',<br/>  'PostgreSQL': '...'<br/>}"]

        Results --> Dict
        Dict --> R
    end

    subgraph "Writing Agent"
        WA[Writing Agent]
        TE[Template Engine]
        Templates["● COMPARISON_TEMPLATE<br/>● TUTORIAL_TEMPLATE<br/>● ANALYSIS_TEMPLATE<br/>● SUMMARY_TEMPLATE"]

        R --> WA
        Meta --> TE
        TE -->|Select| Templates
        Templates -->|Format + LLM| Draft[Draft Content]
    end

    P1 --> PA
    P2 --> PA
    P3 --> PA
    Draft --> Output[Final Result]

    style PA fill:#95e1d3
    style Tool fill:#4ecdc4
    style Dict fill:#4ecdc4
    style Templates fill:#95e1d3
```

## Component Architecture

```mermaid
classDiagram
    class WorkflowState {
        +str task_id
        +str prompt
        +dict~str,Any~ research_results
        +list~str~ research_queries
        +str task_type
        +str draft
        +str result
        +bool approved
        +str feedback
        +str error
    }

    class PromptAnalyzer {
        +LLM llm
        +analyze(prompt) dict
        -_fallback_analysis(prompt) dict
    }

    class ResearchAgent {
        +research_node(state) dict
        +research_with_retry(tool, query) str
        +get_research_tool() Tool
    }

    class ToolRegistry {
        +dict tools
        +get_tool(name) Tool
        +list_available_tools() list
    }

    class WritingAgent {
        +writing_node(state) dict
        +select_template(task_type) str
        +format_research_context(results) str
    }

    class RealTools {
        +llm_research(query) str
        +search_general(query) str
        +web_search(query) str
    }

    class LangGraphWorkflow {
        +create_workflow() StateGraph
        +run_workflow(task_id, prompt) dict
        +resume_workflow(task_id, command) dict
    }

    PromptAnalyzer --> WorkflowState : Populates task_type & queries
    ResearchAgent --> PromptAnalyzer : Uses analysis
    ResearchAgent --> ToolRegistry : Selects tools
    ResearchAgent --> WorkflowState : Updates research_results
    ToolRegistry --> RealTools : Provides tools
    WritingAgent --> WorkflowState : Reads research_results
    LangGraphWorkflow --> ResearchAgent : Orchestrates
    LangGraphWorkflow --> WritingAgent : Orchestrates

    note for WorkflowState "Flexible schema<br/>supports any topics"
    note for RealTools "Returns actual data<br/>from LLM/web"
    note for PromptAnalyzer "LLM extracts topics<br/>from any prompt"
```

## Request and Resume Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Celery
    participant LangGraph
    participant Analyzer as Prompt Analyzer
    participant Research as Research Agent
    participant Writing as Writing Agent
    participant DB as PostgreSQL
    participant Redis
    participant WS as WebSocket

    Client->>FastAPI: POST /api/v1/tasks<br/>{prompt: "Compare X vs Y"}
    FastAPI->>DB: Create task (status=PENDING)
    FastAPI->>Celery: Queue execute_workflow(task_id)
    FastAPI-->>Client: 202 Accepted {task_id}

    Celery->>DB: Update status=RUNNING
    Celery->>LangGraph: run_workflow(task_id, prompt)

    LangGraph->>Analyzer: Analyze prompt
    Analyzer->>Analyzer: LLM extracts topics + type
    Analyzer-->>LangGraph: {topics: ["X", "Y"], type: "comparison"}

    LangGraph->>Research: research_node(state)
    loop For each topic
        Research->>Research: llm_research(topic)
    end
    Research->>Redis: Save research_results dict
    Research-->>LangGraph: Updated state

    LangGraph->>Writing: writing_node(state)
    Writing->>Redis: Load research_results
    Writing->>Writing: Select COMPARISON_TEMPLATE
    Writing->>Writing: LLM generates draft
    Writing-->>LangGraph: Draft ready

    LangGraph->>LangGraph: interrupt() - wait for approval
    LangGraph->>DB: Update status=AWAITING_APPROVAL
    LangGraph->>WS: Broadcast status update
    WS-->>Client: Task awaiting approval
    LangGraph-->>Celery: Return (paused)

    Client->>FastAPI: POST /tasks/{id}/approve<br/>{approved: true}
    FastAPI->>Celery: Queue resume_workflow(task_id)
    Celery->>LangGraph: resume_workflow(task_id, approved=true)

    LangGraph->>DB: Save result, status=COMPLETED
    LangGraph->>WS: Broadcast completion
    WS-->>Client: Task completed

    Client->>FastAPI: GET /tasks/{id}
    FastAPI->>DB: Fetch task
    FastAPI-->>Client: Full task with result
```

## State and Persistence

PostgreSQL is the durable system of record for the task prompt, status, result, timestamps, and JSON agent log. Redis is an operational store: it carries Celery messages and holds rate-limit counters, idempotency claims, duplicate-execution claims, and a task workspace with a 24-hour TTL.

LangGraph is compiled with `MemorySaver`. Its checkpoint data is therefore held in the worker process rather than persisted to PostgreSQL or Redis. The approval flow works while that process remains available, but a worker restart can lose the interrupted graph state even though the PostgreSQL task row remains. Durable checkpoint storage is a future production-hardening item.

## Failure and Recovery Behavior

1. The API creates a `PENDING` task, then queues `execute_workflow`.
2. The worker claims the task in Redis and sets `RUNNING`.
3. Transient workflow failures are retried up to three times with bounded exponential backoff and jitter. Configuration, authentication, and token-limit failures become `FAILED` without retry.
4. Celery late acknowledgements and worker-lost rejection reduce the chance of silently losing a delivery. The Redis execution claim prevents concurrent duplicate execution for the same task.
5. A draft produces `AWAITING_APPROVAL`. Approval queues `resume_workflow`; approval or rejection is then persisted as `COMPLETED` or `FAILED`.
6. LLM calls use a timeout and a process-local circuit breaker. Redis and database outages are not hidden by the health endpoint and should be monitored separately in production.

## Technology Stack

### Core Framework

- **FastAPI**: Async REST API
- **LangGraph**: Multi-agent workflow orchestration
- **Celery**: Async task queue
- **PostgreSQL**: Task persistence
- **Redis**: Celery broker/result backend, coordination controls, and temporary agent workspace

### AI/ML

- **LangChain**: LLM integration & tools
- **Groq/OpenAI**: LLM providers (configurable)

### Reliability and Operations

- **Tenacity**: Research-tool retries with exponential backoff
- **Structured logging**: JSON agent activity logs
- **Rate limiting and idempotency**: Redis-backed API controls
- **Circuit breaker and timeouts**: LLM failure containment

### Infrastructure

- **Docker Compose**: Service orchestration
- **WebSockets**: Real-time updates
- **Tenacity**: Retry logic

## Project Structure

```
src/
├── agents/
│   ├── state.py               # Flexible WorkflowState schema
│   ├── prompt_analyzer.py     # LLM-based prompt analysis
│   ├── research_agent.py      # Dynamic topic research
│   ├── writing_agent.py       # Template-based generation
│   ├── workflow.py            # LangGraph orchestration
│   └── tools.py               # Real LLM-based tools
├── api/
│   ├── main.py                # FastAPI app
│   ├── routes/tasks.py        # Task endpoints
│   └── websocket.py           # WebSocket manager
├── database/
│   ├── models.py              # SQLAlchemy models
│   ├── connection.py          # DB connection
│   └── crud.py                # Database operations
├── worker/
│   └── celery_app.py          # Celery worker & tasks
└── shared/
    ├── redis_client.py        # Redis workspace operations
    ├── logger.py              # Structured JSON logging
    └── llm_provider.py        # LLM factory (Groq/OpenAI)
```

## Key Design Decisions

### 1. Flexible State Schema

**Problem**: Hardcoded `research_langgraph` and `research_crewai` fields  
**Solution**: Generic `research_results: dict[str, Any]` supports any topics

### 2. LLM-Guided Analysis

**Problem**: Couldn't handle prompts outside hardcoded topics  
**Solution**: `PromptAnalyzer` uses LLM to extract topics from ANY prompt

### 3. Real Research Tools

**Problem**: Tools returned static, predetermined strings  
**Solution**: `llm_research` tool uses LLM to generate dynamic, real research

### 4. Template Engine

**Problem**: Only one hardcoded comparison template  
**Solution**: 4 templates (comparison, tutorial, analysis, summary) selected based on task type

### 5. Tool Registry

**Problem**: Research agent called specific, hardcoded tools  
**Solution**: Tool registry with dynamic selection based on configuration

## Capabilities: Before vs After

| Capability       | Before (Hardcoded)               | After (Generalized)                               |
| ---------------- | -------------------------------- | ------------------------------------------------- |
| **Topics**       | 2 only (LangGraph, CrewAI)       | ∞ (LLM extracts any)                              |
| **Task Types**   | Comparison only                  | 4 types (comparison, tutorial, analysis, summary) |
| **Tools**        | 2 mock tools with static strings | Registry of real LLM-based tools                  |
| **State**        | Hardcoded field names            | Flexible dict structure                           |
| **Prompts**      | 1 template                       | 4+ templates with dynamic selection               |
| **Research**     | Predetermined responses          | Real, variable content                            |
| **Adaptability** | One use case only                | General-purpose framework                         |

## Example Workflows

### Example 1: Comparison Task

```
Prompt: "Compare Redis vs PostgreSQL for caching"
  ↓
Analyzer extracts: topics=["Redis", "PostgreSQL"], type="comparison"
  ↓
Research Agent researches each topic with llm_research
  ↓
Writing Agent selects COMPARISON_TEMPLATE
  ↓
LLM generates comparison summary
  ↓
Human approves → Result saved
```

### Example 2: Tutorial Task

```
Prompt: "Create a Docker setup tutorial for beginners"
  ↓
Analyzer extracts: topics=["Docker"], type="tutorial"
  ↓
Research Agent researches Docker
  ↓
Writing Agent selects TUTORIAL_TEMPLATE
  ↓
LLM generates step-by-step tutorial
  ↓
Human approves → Result saved
```

## Production Readiness

### Implemented

- Flexible, general-purpose architecture
- Real research tools (not mocks)
- Dynamic prompt analysis
- Multiple task type support
- Comprehensive error handling
- Retry logic at multiple levels
- Structured logging
- WebSocket real-time updates
- Async task processing
- Human-in-the-loop workflow

### Known Gaps and Future Roadmap

- Replace `MemorySaver` with a shared durable LangGraph checkpointer.
- Add API authentication and authorization.
- Replace process-local metrics and circuit-breaker state with shared production observability.
- Tool result caching and parallel research for independent topics.
- Additional search providers and source-aware evaluation.

---
