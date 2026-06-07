# Project Implementation Plan
## Financial Research Analyst Platform

This document lays out the step-by-step implementation plan for building the **Financial Research Analyst Platform**. 

The plan is divided into seven logical phases. Each phase contains granular subphases, a **dedicated testing subphase** to verify that the requirements have been met, and a defined expected output. Frontend development is isolated into its own phase, and we have dedicated a phase to production-grade attributes (scalability, security, observability, and caching).

---

## Phase 1: Environment, Database, & Workspace Setup

Establish the core application infrastructure, container orchestration, and base schema.

### Subphases
*   **Subphase 1.1: Local Environment & Docker Orchestration**
    *   Initialize the project workspace directories (`backend/` and `frontend/`).
    *   Create a `docker-compose.yml` file configuring:
        *   **PostgreSQL** with `pgvector` enabled (using image `pgvector/pgvector:16-pgdg`).
        *   **PGAdmin** for database monitoring and validation.
    *   Initialize a Python virtual environment in `backend/` and install base libraries: `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `pydantic`, `langgraph`, and `langgraph-checkpoint-postgres`.
    *   Initialize the React frontend in `frontend/` using Vite + TypeScript: `npx -y create-vite@latest frontend --template react-ts`. Install Tailwind CSS and Lucide React.
*   **Subphase 1.2: Database Migrations & Application Models**
    *   Set up SQLAlchemy models representing:
        *   `Users` (for analyst accounts and auth).
        *   `Threads` (for session logging and grouping runs).
        *   `Briefs` (for structured Pydantic brief results).
        *   `Annotations` (for storing human comments per brief section).
        *   `Evaluations` (for storing LLM-as-judge scores and feedback).
        *   `CostMetrics` (for tracking API token counts and latency).
        *   `LongTermMemory` (table with `vector` type for storing preference embeddings).
*   **Subphase 1.3: Testing Phase (Infrastructure Verification)**
    *   Run docker-compose and verify that PostgreSQL and PGAdmin containers start successfully.
    *   Execute a database migration script and query the PostgreSQL system tables to verify that the `pgvector` extension is active and tables are created.
    *   Run test database connection scripts (asyncpg) to confirm connection pooling works and handles connections properly.

### Expected Output
*   A running docker container setup with PostgreSQL + `pgvector`.
*   Functional backend (FastAPI) and frontend (React) boilerplate servers.
*   Database tables successfully created and verified via connection test scripts.

---

## Phase 2: Core Worker Subgraphs & Financial Tools (Backend)

Implement the data-harvesting and quantitative worker agents as isolated subgraphs.

### Subphases
*   **Subphase 2.1: Web Scraper Subgraph**
    *   Create `backend/app/graphs/workers/scraper.py` defining the Scraper StateGraph.
    *   Implement standard Python scraping tools:
        *   `fetch_sec_filings(ticker, form_type)`: Fetches SEC 10-K/10-Q documents. Must configure a valid user-agent string to comply with SEC rules.
        *   `scrape_news(query, n_results)`: Integrates Tavily Search API.
        *   `get_earnings_transcripts(ticker, quarter)`: Scrapes public earnings transcripts.
    *   Structure output into a unified Pydantic model (`ScraperOutput`) containing lists of news entries and filings metadata.
*   **Subphase 2.2: Quant Analytical Subgraph**
    *   Create `backend/app/graphs/workers/quant.py` defining the Quant StateGraph.
    *   Implement data retrieval tools using `yfinance` to pull historical close prices and financial reports.
    *   Build mathematical logic to calculate standard multiples inline (P/E, EV/EBITDA, Debt/Equity, ROE).
    *   Implement peer-group comparison tool fetching competitor multiples.
    *   Structure results into a Pydantic model (`QuantOutput`).
*   **Subphase 2.3: Testing Phase (Tools & Data Verification)**
    *   Write unit tests (using `pytest`) to verify financial calculations (e.g. check calculated ratios against known ticker data).
    *   Write scraper tests verifying parsing of SEC filings and news returns (using mock HTTP responses with `pytest-mock` to avoid API token consumption during test runs).
    *   Execute the standalone Scraper and Quant subgraphs and assert that output Pydantic schemas are successfully populated without missing fields.

### Expected Output
*   Two functional LangGraph subgraphs: **Scraper Subgraph** and **Quant Subgraph**.
*   A suite of unit tests passing with 100% success for financial calculations and web scraping outputs.

---

## Phase 3: Synthesis, Risk-Check, & Evaluator Subgraphs (Backend)

Build the LLM report generator, factual verification agent, and LLM-as-judge scoring pipelines.

### Subphases
*   **Subphase 3.1: Synthesis Brief Subgraph**
    *   Create `backend/app/graphs/workers/synthesis.py` defining the Synthesis StateGraph.
    *   Implement prompt templates dividing the brief generation into sections (Executive Summary, Business Overview, Financial Analysis, Risk Factors, Verdict).
    *   Implement structured JSON output parsing using Claude 3.5 / GPT-4o mapping to a Pydantic `InvestmentBrief` model.
*   **Subphase 3.2: Risk-Check Subgraph (Claims Factual Verification)**
    *   Create `backend/app/graphs/workers/risk_check.py` defining the Risk-Check StateGraph.
    *   Write a claim extraction node using LLM structured output to find all numerical claims.
    *   Write a validation node checking claims against the raw Scraper and Quant database records.
    *   Assign severity flags (Low/Medium/High). If High severity flags exceed the threshold, configure a routing edge to auto-reject the brief and send it back to the Synthesis subgraph with discrepancy logs.
*   **Subphase 3.3: LLM-as-Judge Evaluator Subgraph**
    *   Create `backend/app/services/evaluator.py`.
    *   Configure an LLM scoring model using a structured evaluation rubric (Factual Consistency, Completeness, Clarity, Risk Coverage).
    *   Define database log writing logic that saves scores to `eval_runs` mapped to the prompt template hash.
*   **Subphase 3.4: Testing Phase (Verification & Prompt Testing)**
    *   Write tests that supply the Risk-Check subgraph with factual discrepancies (e.g., passing a synthesis brief stating "Revenue is $10B" when quant data states "Revenue is $1B") and verify the subgraph raises correct warnings and rejects.
    *   Validate the structured output parser by testing Synthesis output with malformed LLM responses to verify the parser correctly formats, retries, or raises clear exceptions.
    *   Write unit tests to verify the Evaluator LLM writes correct structures to the `eval_runs` database table.

### Expected Output
*   Completed **Synthesis**, **Risk-Check**, and **Evaluation** subgraphs.
*   Test logs validating the auto-rejection trigger and fallback handling for malformed LLM outputs.

---

## Phase 4: Multi-Agent Orchestration & State Resiliency (Backend)

Connect the nested subgraphs under a unified supervisor and establish long-term memory and interrupt control patterns.

### Subphases
*   **Subphase 4.1: Ticker & Portfolio Supervisor Graphs**
    *   Implement the **Ticker Supervisor Graph** coordinating execution between the Scraper, Quant, Synthesis, and Risk-Check subgraphs via LangGraph `Command` routing.
    *   Implement the **Portfolio Supervisor Graph** using the `Send` API to parallelize Ticker Graphs for multi-ticker searches.
    *   Implement the Fan-in node to combine individual briefs and generate comparative tables.
*   **Subphase 4.2: Human-in-the-Loop Interrupt & Revisions**
    *   Configure a LangGraph `interrupt()` breakpoint inside the Ticker Graph immediately before the brief is published.
    *   Set up state hooks in the graph to capture annotations.
    *   Create a `revision_count` variable in state. Force an exit if loops exceed 3 to prevent infinite run loops.
*   **Subphase 4.3: Testing Phase (Orchestration & State Durability)**
    *   Write integration tests that invoke the Portfolio Graph with multiple tickers (e.g. `["AAPL", "MSFT"]`) and verify that parallel subgraphs run concurrently.
    *   Implement a state persistence test: Start a thread run, trigger the `interrupt()` node, simulate a server restart, reload the state from the `PostgresSaver` checkpointer using the `thread_id`, and resume with a approval/rejection command. Verify state remains uncorrupted.
    *   Verify the revision threshold: Trigger a mock analyst rejection 4 times in a row and assert that the graph correctly exits with a "max revisions exceeded" status rather than looping infinitely.

### Expected Output
*   Fully integrated multi-agent graph with parallel fan-out capabilities.
*   State checkpoints persisted in PostgreSQL with verified cross-session durability.
*   Test logs proving the interrupt/resume flow works, and limits loop iterations to a maximum of three.

---

## Phase 5: Backend API Layer & Event Streaming

Build REST APIs for thread management and real-time streaming capabilities.

### Subphases
*   **Subphase 5.1: REST API Controllers**
    *   Implement FastAPI routes for:
        *   `POST /api/research/start`: Begins the multi-agent graph.
        *   `POST /api/research/resume`: Handles analyst approval/rejection comments.
        *   `GET /api/research/threads`: Fetches past run sessions.
        *   `GET /api/research/briefs/{thread_id}`: Retrieves completed briefs and comparative stats.
*   **Subphase 5.2: Server-Sent Events (SSE) Stream Controller**
    *   Create backend routes to open SSE streams (`GET /api/research/stream/{thread_id}`).
    *   Capture events using LangGraph's `astream_events(..., version="v2")`.
    *   Filter events to extract node updates, tool parameters (e.g. "fetching SEC 10-Q"), and LLM token deltas, formatting them as `text/event-stream` chunks.
*   **Subphase 5.3: Testing Phase (API & SSE Validation)**
    *   Implement endpoint verification tests using HTTP clients (`httpx` in Python tests).
    *   Assert that starting research returns a valid UUID `thread_id` and registers in the database.
    *   Connect a test client to the SSE route and read the streamed output. Verify that events (`node_start`, `tool_start`, `token_stream`, `interrupt`) parse correctly as JSON and maintain order.

### Expected Output
*   An active FastAPI server serving REST APIs and SSE streams.
*   Automated endpoint tests checking status codes, JSON models, and SSE data structures.

---

## Phase 6: Frontend Development (React Web Client)

Build the dashboard UI, real-time research cockpit, interactive editor, and analytics panels.

### Subphases
*   **Subphase 6.1: Layout, UI Shell & Authentication Pages**
    *   Create the main dashboard layout shell (Sidebar navigation, Header, Theme controller).
    *   Build the Login and Registration views. Implement client-side JWT storage and route guards preventing unauthorized navigation.
*   **Subphase 6.2: Research Cockpit & SSE Event Timeline**
    *   Build the search view permitting inputs of ticker lists.
    *   Write a custom `useSSE` hook in TypeScript using the web `EventSource` API.
    *   Construct a real-time progress timeline component displaying active agents, running tool names, and dynamic progress bar.
    *   Build a streaming text viewport showing LLM thoughts using typing animations.
*   **Subphase 6.3: Brief Viewer, Annotator & Revision Workspace**
    *   Build an interactive document view for the completed `InvestmentBrief`.
    *   Implement comment nodes. Clicking any section opens a feedback card to write annotations.
    *   Implement action controls ("Approve" / "Reject & Send to Revision").
*   **Subphase 6.4: Workspace Dashboard & Comparison Workspace**
    *   Construct the threads history listing (sortable by date, tickers, status).
    *   Build a side-by-side comparison screen to inspect performance parameters of a company across different quarters.
*   **Subphase 6.5: Testing Phase (UI & Integration Verification)**
    *   Verify React layout styling and responsive breakpoints (Mobile, Tablet, Desktop) using browser inspections.
    *   Mock SSE stream inputs and API responses (using Mock Service Worker - MSW) to test the UI's behavior under loading, stream success, and connection error states.
    *   Verify JWT token expiration flows: assert that expired tokens redirect to the login screen and wipe out cache data.

### Expected Output
*   A responsive React single page application with navigation, authentication, and layouts.
*   Interactive review cards, real-time logging screens, and comparison tables.
*   Front-end mock test logs showing successful component layouts and stream representations.

---

## Phase 7: Production Readiness: Scalability, Observability, & Hardening

Scale database querying, secure communication channels, apply rate limits, and implement production logging.

### Subphases
*   **Subphase 7.1: Observability & LangSmith Tracing**
    *   Configure production-grade LangSmith tracing metadata: label traces with `thread_id`, `user_id`, and `git_commit_hash`.
    *   Implement custom logger formats capturing system errors, API execution times, and database anomalies, routing them to centralized output.
*   **Subphase 7.2: Token Tracking & Financial Cost Monitoring**
    *   Implement background calculations on the FastAPI server to count prompt and completion tokens.
    *   Compute USD cost per agent run based on active provider rates, writing logs to the database.
    *   Feed the costs metrics to the frontend Analytics dashboard.
*   **Subphase 7.3: Scale & Resilience Hardening**
    *   Implement a token-bucket rate limiter decorator on the SEC EDGAR and Tavily API scraper tools to prevent 429 rate limit failures.
    *   Set up database indices on PostgreSQL (`threads.user_id`, `briefs.thread_id`) and create a vector index (e.g. HNSW or IVFFlat) on `long_term_memory.embedding` for fast semantic lookup.
    *   Implement global exception handler middleware in FastAPI to intercept and format any unexpected server faults.
*   **Subphase 7.4: Testing Phase (Production Audit & Load Simulation)**
    *   Conduct load testing by executing 10 parallel portfolio runs (e.g., 30 tickers fanning out concurrently) to verify that rate limiters successfully queue requests and the Postgres connection pool handles concurrent writes without query drops.
    *   Validate the database semantic retrieval: verify pgvector returns accurate historical recommendations under less than 50ms latency.
    *   Verify token counters: test LLM calls and verify calculated token costs match actual token counts in API headers.

### Expected Output
*   An optimized, secure, and production-grade application deployment setup.
*   Full instrumentation for cost logging, performance tracking, and system tracing.
*   Load-testing audits proving system resilience during high concurrency.
