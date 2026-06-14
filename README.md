# AI-Powered Financial Research Analyst Platform

An advanced, hierarchical multi-agent platform designed to automate and augment equity research workflows. Using **LangGraph** for orchestration and a modern **React (Vite + TS)** interface, the platform performs parallelized research across multiple tickers, programmatically verifies quantitative metrics to prevent hallucinations, and implements a structured human-in-the-loop review pipeline.

---

## 1. Problem & Solution

### The Problem
Traditional equity research is bottlenecked by manual, error-prone processes:
*   **Data Fragmentation**: Analysts spend hours gathering financial reports from the SEC EDGAR system, reading news headlines, and digging up transcripts.
*   **Quantitative Overload**: Manually calculating core valuation ratios (P/E, EV/EBITDA, Debt/Equity, FCF Yield) and peer group benchmarks.
*   **Hallucination & Inaccuracies**: Language models (LLMs) often hallucinate financial figures when summarizing reports, creating extreme risks for investment briefs.
*   **Rigid Orchestration**: Standard linear pipelines cannot handle complex revision feedback or parallel ticker analysis with structural error boundaries.

### The Solution
This platform automates the research collection and synthesis while keeping the human analyst in control:
*   **Parallel Multi-Agent Execution**: Fans out concurrent ticker analysis graphs to collect news, filings, transcripts, and market data in parallel.
*   **Programmatic & LLM-Driven Verification**: The **Risk-Check Agent** extracts numerical claims from synthesized briefs, programmatically compares them to raw database metrics, and uses LLM fact-checkers to auto-reject briefs containing severe hallucinations.
*   **Human-In-The-Loop Revision Loops**: Pauses graph execution right before publication. Analysts can click specific report sections, leave feedback annotations, and reject briefs, routing them back to synthesis (limited to 3 revisions to avoid infinite token loops).
*   **Real-time Event Streaming**: Streams agent states, active tool parameters, and raw LLM token outputs in real time via Server-Sent Events (SSE).

---

## 2. Tech Stack

### Frontend
*   **React (Vite + TypeScript)**: Fast, single-page client application with component modularity.
*   **Vanilla CSS + CSS Variables**: Harmonic dark theme HSL color scheme with modern typography (Outfit & Inter fonts) and glassmorphism styling.
*   **Lucide React**: Clean vector indicators.
*   **SSE Client**: Consumes streaming updates directly via the HTML5 `EventSource` API.

### Backend
*   **FastAPI (Python)**: High-performance ASGI web server hosting REST APIs and SSE controllers.
*   **LangGraph**: Hierarchical multi-agent state management orchestrating supervisors and worker subgraphs via dynamic `Command` routing.
*   **yFinance & BeautifulSoup4**: Financial quantitative retrieval and scraper tools.
*   **Tavily Search API**: News parsing and earnings transcript lookup.
*   **LangChain**: Interface wrappers supporting Google Gemini (`gemini-1.5-pro` and `gemini-1.5-flash`), Claude, and GPT models.

### Database & Persistence
*   **PostgreSQL**: Base application database storage.
*   **pgvector Extension**: Stores embeddings of user research preferences for semantic long-term memory retrieval.
*   **LangGraph PostgresSaver Checkpointer**: Cross-session state persistence, allowing pause/resume operations across server restarts.

---

## 3. System Architecture & Flow

### System Architecture
The application is structured as a decoupled three-tier system:

```mermaid
graph TD
    subgraph Frontend [React SPA Client]
        UI[Dashboard / Cockpit]
        EV[EventSource SSE Client]
    end

    subgraph Backend [FastAPI Server]
        API[REST API Endpoints]
        LGE[LangGraph Orchestration Engine]
        Stream[SSE Streaming Controller]
        Scrapers[Data Pipeline Scrapers]
        QuantTools[Quant Analytics Tools]
    end

    subgraph DB [PostgreSQL Layer]
        AppDB[(Application Tables)]
        PGV[(pgvector Long-Term Memory)]
        Checkpoints[(LangGraph Checkpoints)]
    end

    subgraph External [External APIs]
        SEC[SEC EDGAR API]
        Tavily[Tavily Search API]
        yFinance[yFinance API]
        OpenAI[OpenAI / Anthropic APIs]
        LangSmith[LangSmith Tracing]
    end

    UI <-->|HTTPS REST| API
    EV <-->|SSE Stream| Stream
    API <--> LGE
    LGE --> Stream
    LGE <--> Checkpoints
    LGE <--> AppDB
    LGE <--> PGV
    
    LGE --> Scrapers
    LGE --> QuantTools
    
    Scrapers --> SEC
    Scrapers --> Tavily
    QuantTools --> yFinance
    LGE --> OpenAI
    LGE --> LangSmith
```

### LangGraph Agent State Flow
Each researched ticker runs a nested subgraph containing scrapers, quant calculators, prompt synthesis, and verification boundaries, fanning back in to a portfolio evaluator:

```mermaid
stateDiagram-v2
    [*] --> Start
    Start --> ParseTickers : Receive Tickers List
    ParseTickers --> LoadLongTermMemory : Query pgvector
    
    state Parallel_Ticker_Research {
        direction TB
        [*] --> TickerSupervisor
        
        state Scraper_Subgraph {
            [*] --> fetch_sec_filings
            fetch_sec_filings --> scrape_news
            scrape_news --> get_earnings_transcripts
            get_earnings_transcripts --> collate_scraped_data
        }
        
        state Quant_Subgraph {
            [*] --> fetch_market_data
            fetch_market_data --> calculate_ratios
            calculate_ratios --> fetch_peer_data
            fetch_peer_data --> format_quant_pydantic
        }
        
        state Synthesis_Subgraph {
            [*] --> load_templates
            load_templates --> generate_draft_sections
            generate_draft_sections --> validate_brief_format
        }
        
        state RiskCheck_Subgraph {
            [*] --> extract_numerical_claims
            extract_numerical_claims --> verify_claims_against_sources
            verify_claims_against_sources --> score_discrepancy_severity
        }

        TickerSupervisor --> Scraper_Subgraph : Command(goto=scraper)
        TickerSupervisor --> Quant_Subgraph : Command(goto=quant)
        
        Scraper_Subgraph --> TickerSupervisor : Return ScrapeData Pydantic
        Quant_Subgraph --> TickerSupervisor : Return QuantData Pydantic
        
        TickerSupervisor --> Synthesis_Subgraph : Command(goto=synthesis)
        Synthesis_Subgraph --> RiskCheck_Subgraph : Route for Verification
        
        RiskCheck_Subgraph --> Synthesis_Subgraph : High-Severity Discrepancies (Auto-Reject)
        RiskCheck_Subgraph --> TickerSupervisor : Verification Complete
        
        TickerSupervisor --> HumanInterrupt : interrupt()
        
        state HumanInterrupt {
            [*] --> AwaitingAnalystApproval
        }
        
        HumanInterrupt --> RevisionLoop : Rejection (resume=feedback)
        RevisionLoop --> Synthesis_Subgraph : revision_count <= 3
        RevisionLoop --> [*] : revision_count > 3 (Abort/Review)
        
        HumanInterrupt --> DoneTicker : Approval (resume=approve)
        DoneTicker --> [*]
    }
    
    ParseTickers --> Parallel_Ticker_Research : Send(Ticker 1..N)
    Parallel_Ticker_Research --> FanInAggregation : Wait for all tickers
    FanInAggregation --> PortfolioSummaryNode : Generate Comparative Report
    PortfolioSummaryNode --> LLM_as_Judge : Run Evaluator
    LLM_as_Judge --> [*] : Save Final State
```

---

## 4. Folder Structure

```text
financial-research-analyst/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── research.py      # REST APIs (start, resume, list) & SSE stream route
│   │   ├── db/
│   │   │   ├── init_db.py       # DB table setup & vector extension initialization
│   │   │   ├── models.py        # SQLAlchemy schema definitions
│   │   │   └── session.py       # PostgreSQL async database connection pools
│   │   ├── graphs/
│   │   │   ├── state.py         # Global and sub-graph typed Pydantic states
│   │   │   ├── supervisor.py    # Top-level portfolio & ticker supervisor graphs
│   │   │   └── workers/
│   │   │       ├── scraper.py   # Scraper StateGraph & tools (SEC, news)
│   │   │       ├── quant.py     # Quant StateGraph & tools (yFinance metrics)
│   │   │       ├── synthesis.py # Synthesis StateGraph & prompt schemas
│   │   │       └── risk_check.py# Claim validator StateGraph & math comparators
│   │   ├── services/
│   │   │   └── evaluator.py     # LLM-as-judge scoring pipelines
│   │   └── main.py              # FastAPI app initialization
│   ├── tests/                   # Pytest integration & unit test suite
│   ├── requirements.txt         # Python dependencies listing
│   └── Dockerfile               # Backend container configuration
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.tsx        # Analyst session login card
│   │   │   ├── Dashboard.tsx    # Board overview, history list, and stats
│   │   │   ├── ResearchCockpit.tsx # Ticker triggers and live streaming terminals
│   │   │   ├── BriefReview.tsx  # Document review workspace & annotation cards
│   │   │   └── Comparison.tsx   # Valuation multiples matrix compare view
│   │   ├── hooks/
│   │   │   └── useSSE.ts        # Custom EventSource parser hook
│   │   ├── services/
│   │   │   └── api.ts           # Axios wrapper communicating with FastAPI
│   │   ├── App.tsx              # Main layouts & view routers
│   │   ├── index.css            # Base styles, glass theme variables, animations
│   │   └── main.tsx             # React DOM injection point
│   ├── tsconfig.json            # TypeScript configuration
│   └── vite.config.ts           # Vite build parameters
├── docker-compose.yml           # Database and PGAdmin services definitions
├── plan.md                      # Roadmap timeline markdown
└── srd.md                       # Software requirements specification
```

---

## 5. Setup & Running Locally

### Prerequisites
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/)
*   Python 3.11+
*   Node.js v18+ & npm
*   A Google Gemini API Key (or OpenAI / Anthropic keys depending on model switches)
*   A Tavily API Key (for news scraping and transcripts search)

### Step 1: Clone the Repository & Configure Environments
Create a `.env` file in the root of the project (or make sure these environment variables are exported):
```env
# Database Credentials
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5435/financial_analyst

# API Keys
GEMINI_API_KEY=your_google_gemini_api_key
TAVILY_API_KEY=your_tavily_search_api_key

# Optional: LangSmith Tracing
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your_langsmith_key
# LANGCHAIN_PROJECT=financial-research-analyst
```

### Step 2: Boot Database Services via Docker
Start the PostgreSQL container with `pgvector` pre-installed:
```bash
docker compose up -d
```
You can verify the database container status using `docker ps`. The DB runs on port `5435`.

### Step 3: Configure and Seed the Database Tables
Set up your virtual environment, install requirements, and execute the init script to create the necessary tables and seeds:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run table creation and user seeding
PYTHONPATH=.. python app/db/init_db.py
```

### Step 4: Run the FastAPI Server
With your virtual environment active, launch the backend application:
```bash
PYTHONPATH=.. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The REST documentation will be available at `http://localhost:8000/docs`.

### Step 5: Install and Run the Frontend Client
In a new terminal window, navigate to the frontend directory, install dependencies, and launch Vite's dev server:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. You can log in using the seeded credentials:
*   **Email**: `analyst@example.com`
*   **Password**: `scrypt:32768:8:1$default_hash_value` (Or any value, as the demo frontend bypasses strict hashing verification).

### Step 6: Running the Pytest Suite
Run the test suite from the project root to ensure everything matches requirements:
```bash
PYTHONPATH=. backend/venv/bin/pytest
```

---

## 6. Primary Use Cases

1.  **Rapid Ticker Screening**: Asset managers can trigger parallel runs for several competitors in a sector, generating unified comparative matrices and analysis in minutes.
2.  **Factual Equity Research Auditing**: High-stakes environments where financial reporting errors are costly. The programmatic Risk-Check agent ensures LLM summaries match actual SEC submissions.
3.  **Cross-Quarter Valuations Comparison**: Spotting changes in ratios (such as P/E or ROE) over time using historical scraping parameters.
4.  **Feedback-Loop Collaboration**: Team leads can annotate sections, rejecting drafts until they meet specific criteria before publish authorization.

---

## 7. Future Enhancements

*   **Dynamic DCF Modeling**: Build a quantitative calculations engine that generates full Discounted Cash Flow models in Excel format.
*   **pgvector Memory Matching**: Implement advanced similarity searches on user-preference embeddings to retrieve and inject custom writing style sheets.
*   **Financial Chart Visualizations**: Add interactive financial charting panels (via Recharts or D3.js) plotting pricing ranges, peer averages, and multiple trajectories.
*   **SEC Filing RSS Integration**: Set up real-time triggers that automatically launch analysis runs when a sector company submits a new 10-K or 10-Q filing.
