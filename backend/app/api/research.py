import os
import uuid
import json
import asyncio
import time
import subprocess

def get_git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
    except Exception:
        return "unknown"
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy import select, update
# pyrefly: ignore [missing-import]
from psycopg_pool import AsyncConnectionPool
# pyrefly: ignore [missing-import]
from psycopg.rows import dict_row
# pyrefly: ignore [missing-import]
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# pyrefly: ignore [missing-import]
from langgraph.types import Command

from backend.app.db.session import get_db, DATABASE_URL, async_session
from backend.app.db.models import Thread, Brief, Annotation, Evaluation, User, CostMetric
from backend.app.graphs.supervisor import portfolio_builder
from backend.app.graphs.state import SectionAnnotation, PortfolioState, InvestmentBrief
from backend.app.services.vector_store import save_memory
from backend.app.services.evaluator import evaluate_brief
from backend.app.services.cost_tracker import TokenTrackerCallback, save_cost_metric
from backend.app.api.auth import get_current_user, get_user_from_token_string

router = APIRouter()

# Convert asyncpg style DB URL to psycopg standard connection string
DB_CONNINFO = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Global postgres connection pool for LangGraph PostgresSaver checkpointer
global_pool: Optional[AsyncConnectionPool] = None

async def get_pool() -> AsyncConnectionPool:
    global global_pool
    if global_pool is None:
        global_pool = AsyncConnectionPool(
            conninfo=DB_CONNINFO,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": True, "row_factory": dict_row}
        )
        await global_pool.open()
    return global_pool

async def close_pool():
    global global_pool
    if global_pool is not None:
        await global_pool.close()
        global_pool = None

async def run_evaluation_for_briefs(db: AsyncSession, thread_uuid: uuid.UUID, state_values: dict):
    """
    Retrieves briefs and raw sources from state, formats them, and runs the LLM evaluator to persist audit scores.
    """
    briefs = state_values.get("ticker_briefs", {})
    scraped_data_dict = state_values.get("ticker_scraped_data", {})
    quant_data_dict = state_values.get("ticker_quant_data", {})
    
    print(f"[API Evaluator] Running audit evaluations for briefs in thread {thread_uuid}...")
    for ticker, brief in briefs.items():
        brief_res = await db.execute(
            select(Brief).where(Brief.thread_id == thread_uuid, Brief.ticker == ticker)
        )
        db_brief = brief_res.scalar_one_or_none()
        if not db_brief:
            print(f"[API Evaluator] Warning: Brief record for {ticker} not found in DB. Skipping.")
            continue
            
        scraped_data = scraped_data_dict.get(ticker)
        quant_data = quant_data_dict.get(ticker)
        
        # 1. Format raw news
        news_list = []
        if scraped_data and hasattr(scraped_data, "news") and scraped_data.news:
            for n in scraped_data.news:
                news_list.append(f"Title: {n.title}\nSource: {n.source}\nContent: {n.content}")
        raw_news_str = "\n---\n".join(news_list) if news_list else "No raw news sources available."

        # 2. Format transcript
        raw_transcript_str = "No transcript available."
        if scraped_data and hasattr(scraped_data, "transcript") and scraped_data.transcript:
            raw_transcript_str = scraped_data.transcript.content

        # 3. Format quant
        raw_quant_str = "No quantitative metrics available."
        if quant_data:
            r = quant_data.ratios
            raw_quant_str = (
                f"Price History: {quant_data.price_history_summary}\n"
                f"P/E: {r.pe_ratio or 'N/A'}\n"
                f"EV/EBITDA: {r.ev_ebitda or 'N/A'}\n"
                f"Debt/Equity: {r.debt_to_equity or 'N/A'}\n"
                f"ROE: {r.roe or 'N/A'}\n"
                f"FCF Yield: {r.free_cash_flow_yield or 'N/A'}"
            )
            
        brief_model = InvestmentBrief(
            ticker=ticker,
            executive_summary=brief.executive_summary if hasattr(brief, "executive_summary") else brief.get("executive_summary", ""),
            business_overview=brief.business_overview if hasattr(brief, "business_overview") else brief.get("business_overview", ""),
            financial_analysis=brief.financial_analysis if hasattr(brief, "financial_analysis") else brief.get("financial_analysis", ""),
            risk_factors=brief.risk_factors if hasattr(brief, "risk_factors") else brief.get("risk_factors", ""),
            verdict=brief.verdict if hasattr(brief, "verdict") else brief.get("verdict", "")
        )
        
        try:
            await evaluate_brief(
                brief_id=db_brief.id,
                brief=brief_model,
                raw_news=raw_news_str,
                raw_transcript=raw_transcript_str,
                raw_quant=raw_quant_str,
                db_session=db
            )
        except Exception as e:
            print(f"[API Evaluator] Error evaluating brief for ticker {ticker}: {e}")

# Pydantic schemas for REST controller requests
class ResearchStartRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, description="List of stock tickers to research")

class ResearchResumeRequest(BaseModel):
    thread_id: str = Field(..., description="UUID of the research thread")
    ticker: str = Field(..., description="Stock ticker that analyst reviewed")
    action: str = Field(..., description="Approval action: 'approve' or 'reject'")
    feedback: List[SectionAnnotation] = Field(default_factory=list, description="Optional annotations for rejection")

# 1. Start research run session
@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_research(
    req: ResearchStartRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    thread_id = uuid.uuid4()
    
    # Create thread entry
    db_thread = Thread(
        thread_id=thread_id,
        user_id=current_user.id,
        name=f"Research: {', '.join(req.tickers)}",
        tickers=req.tickers,
        status="initiated"
    )
    db.add(db_thread)
    await db.commit()
    
    return {
        "thread_id": str(thread_id),
        "status": "initiated"
    }

# 2. Get past run sessions (threads)
@router.get("/threads")
async def list_threads(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Thread)
        .where(Thread.user_id == current_user.id)
        .order_by(Thread.created_at.desc())
    )
    threads = result.scalars().all()
    
    # Format response payload
    return [
        {
            "thread_id": str(t.thread_id),
            "name": t.name,
            "tickers": t.tickers,
            "status": t.status,
            "created_at": t.created_at.isoformat()
        } for t in threads
    ]

# 3. Get completed briefs and stats for a thread
@router.get("/briefs/{thread_id}")
async def get_briefs(
    thread_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
        
    result = await db.execute(
        select(Thread)
        .where(Thread.thread_id == thread_uuid, Thread.user_id == current_user.id)
    )
    db_thread = result.scalar_one_or_none()
    if not db_thread:
        raise HTTPException(status_code=404, detail="Thread not found or access denied")
        
    briefs_result = await db.execute(select(Brief).where(Brief.thread_id == thread_uuid))
    briefs = briefs_result.scalars().all()
    
    response_data = []
    for brief in briefs:
        eval_result = await db.execute(select(Evaluation).where(Evaluation.brief_id == brief.id))
        evaluations = eval_result.scalars().all()
        
        ann_result = await db.execute(select(Annotation).where(Annotation.brief_id == brief.id))
        annotations = ann_result.scalars().all()
        
        response_data.append({
            "id": str(brief.id),
            "ticker": brief.ticker,
            "brief_content": brief.brief_content,
            "revision_count": brief.revision_count,
            "created_at": brief.created_at.isoformat(),
            "evaluations": [
                {
                    "score_factual": ev.score_factual,
                    "score_clarity": ev.score_clarity,
                    "score_coverage": ev.score_coverage,
                    "rubric_justification": ev.rubric_justification
                } for ev in evaluations
            ],
            "annotations": [
                {
                    "section_id": ann.section_id,
                    "comment": ann.comment,
                    "created_at": ann.created_at.isoformat()
                } for ann in annotations
            ]
        })
    return response_data

# 4. Resume research run session
@router.post("/resume")
async def resume_research(
    req: ResearchResumeRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        thread_uuid = uuid.UUID(req.thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
        
    result = await db.execute(
        select(Thread)
        .where(Thread.thread_id == thread_uuid, Thread.user_id == current_user.id)
    )
    db_thread = result.scalar_one_or_none()
    if not db_thread:
        raise HTTPException(status_code=404, detail="Thread not found or access denied")
        
    pool = await get_pool()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    compiled_app = portfolio_builder.compile(checkpointer=checkpointer)
    
    user_id = str(db_thread.user_id)
    git_commit_hash = get_git_commit_hash()
    tracker = TokenTrackerCallback()
    config = {
        "configurable": {"thread_id": req.thread_id},
        "callbacks": [tracker],
        "tags": [f"thread-{req.thread_id}", f"user-{user_id}"],
        "metadata": {
            "thread_id": req.thread_id,
            "user_id": user_id,
            "git_commit_hash": git_commit_hash
        }
    }
    state_info = await compiled_app.aget_state(config)
    
    resume_map = {}
    for task in state_info.tasks:
        for val in task.interrupts:
            ticker = None
            if isinstance(val.value, dict):
                ticker = val.value.get("ticker")
            if ticker == req.ticker:
                resume_map[val.id] = {
                    "action": req.action,
                    "feedback": [fb.model_dump() for fb in req.feedback]
                }
                
    if not resume_map:
        raise HTTPException(status_code=400, detail=f"No pending analyst review found for ticker '{req.ticker}' in thread.")
        
    # Save annotations to DB if rejecting the brief
    if req.action == "reject" and req.feedback:
        brief_result = await db.execute(
            select(Brief).where(Brief.thread_id == thread_uuid, Brief.ticker == req.ticker)
        )
        db_brief = brief_result.scalar_one_or_none()
        if db_brief:
            for fb in req.feedback:
                db_ann = Annotation(
                    brief_id=db_brief.id,
                    section_id=fb.section_id,
                    comment=fb.comment
                )
                db.add(db_ann)
                
                # Save annotation feedback as a long-term memory embedding
                await save_memory(
                    db=db,
                    user_id=db_thread.user_id,
                    ticker=req.ticker,
                    section_id=fb.section_id,
                    comment=fb.comment
                )
            await db.commit()
            
    try:
        db_thread.status = "initiated"
        await db.commit()
        
        start_time = time.time()
        # Invoke LangGraph resume
        await compiled_app.ainvoke(Command(resume=resume_map), config=config)
        latency = time.time() - start_time
        
        # Inspect state after run
        state_info = await compiled_app.aget_state(config)
        if state_info.next:
            db_thread.status = "paused"
        else:
            db_thread.status = "completed"
            
            # Save final fanned-in briefs
            briefs = state_info.values.get("ticker_briefs", {})
            for ticker, brief in briefs.items():
                existing_brief_res = await db.execute(
                    select(Brief).where(Brief.thread_id == thread_uuid, Brief.ticker == ticker)
                )
                existing_brief = existing_brief_res.scalar_one_or_none()
                brief_dict = brief.model_dump() if hasattr(brief, "model_dump") else brief
                if existing_brief:
                    existing_brief.brief_content = brief_dict
                    existing_brief.revision_count = state_info.values.get("revision_count", 0)
                else:
                    db_brief = Brief(
                        thread_id=thread_uuid,
                        ticker=ticker,
                        brief_content=brief_dict,
                        revision_count=state_info.values.get("revision_count", 0)
                    )
                    db.add(db_brief)
        await db.commit()
        if not state_info.next:
            await run_evaluation_for_briefs(db, thread_uuid, state_info.values)
            await save_cost_metric(db, thread_uuid, tracker, latency)
        
        return {
            "status": db_thread.status,
            "message": f"Thread resumed successfully for ticker '{req.ticker}'."
        }
    except Exception as e:
        db_thread.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to resume graph: {str(e)}")

# 5. SSE progress and token streaming endpoint
@router.get("/stream/{thread_id}")
async def stream_research(thread_id: str, request: Request, token: Optional[str] = None):
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
        
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
    async def event_generator():
        async with async_session() as session:
            user = await get_user_from_token_string(token, session)
            if not user:
                yield f"data: {json.dumps({'event': 'error', 'message': 'Unauthorized'})}\n\n"
                return
                
            result = await session.execute(
                select(Thread)
                .where(Thread.thread_id == thread_uuid, Thread.user_id == user.id)
            )
            db_thread = result.scalar_one_or_none()
            if not db_thread:
                yield f"data: {json.dumps({'event': 'error', 'message': 'Thread not found or access denied'})}\n\n"
                return
            tickers = db_thread.tickers
            user_id = str(db_thread.user_id)
            
        pool = await get_pool()
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        compiled_app = portfolio_builder.compile(checkpointer=checkpointer)
        
        git_commit_hash = get_git_commit_hash()
        tracker = TokenTrackerCallback()
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [tracker],
            "tags": [f"thread-{thread_id}", f"user-{user_id}"],
            "metadata": {
                "thread_id": thread_id,
                "user_id": user_id,
                "git_commit_hash": git_commit_hash
            }
        }
        state = PortfolioState(tickers=tickers)
        
        try:
            start_time = time.time()
            async for event in compiled_app.astream_events(state, config=config, version="v2"):
                # Handle node starts
                if event["event"] == "on_chain_start" and "langgraph_node" in event.get("metadata", {}):
                    node_name = event["metadata"]["langgraph_node"]
                    yield f"data: {json.dumps({'event': 'node_start', 'node': node_name})}\n\n"
                    
                # Handle tool starts (e.g. news query, filing scraper parameters)
                elif event["event"] == "on_tool_start":
                    yield f"data: {json.dumps({'event': 'tool_start', 'tool': event['name'], 'input': event['data'].get('input')})}\n\n"
                    
                # Handle streaming tokens
                elif event["event"] == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'event': 'token', 'text': chunk.content})}\n\n"
                        
            latency = time.time() - start_time
            # Final state verification
            state_info = await compiled_app.aget_state(config)
            async with async_session() as session:
                result = await session.execute(select(Thread).where(Thread.thread_id == thread_uuid))
                db_thread = result.scalar_one()
                
                if state_info.next:
                    db_thread.status = "paused"
                    interrupts = []
                    for task in state_info.tasks:
                        for val in task.interrupts:
                            interrupts.append({
                                "id": val.id,
                                "value": val.value.get("ticker") if isinstance(val.value, dict) else val.value
                            })
                    yield f"data: {json.dumps({'event': 'interrupt', 'interrupts': interrupts})}\n\n"
                else:
                    db_thread.status = "completed"
                    
                    # Save briefs
                    briefs = state_info.values.get("ticker_briefs", {})
                    for ticker, brief in briefs.items():
                        existing_brief_res = await session.execute(
                            select(Brief).where(Brief.thread_id == thread_uuid, Brief.ticker == ticker)
                        )
                        existing_brief = existing_brief_res.scalar_one_or_none()
                        brief_dict = brief.model_dump() if hasattr(brief, "model_dump") else brief
                        if existing_brief:
                            existing_brief.brief_content = brief_dict
                            existing_brief.revision_count = state_info.values.get("revision_count", 0)
                        else:
                            db_brief = Brief(
                                thread_id=thread_uuid,
                                ticker=ticker,
                                brief_content=brief_dict,
                                revision_count=state_info.values.get("revision_count", 0)
                            )
                            session.add(db_brief)
                    yield f"data: {json.dumps({'event': 'completed'})}\n\n"
                await session.commit()
                if not state_info.next:
                    await run_evaluation_for_briefs(session, thread_uuid, state_info.values)
                    await save_cost_metric(session, thread_uuid, tracker, latency)
                
        except Exception as e:
            async with async_session() as session:
                result = await session.execute(select(Thread).where(Thread.thread_id == thread_uuid))
                db_thread = result.scalar_one()
                db_thread.status = "failed"
                await session.commit()
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# 6. Analytics cost and latency endpoint
@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Retrieve cost metrics for all threads belonging to the current user
    # threads are linked to user_id, cost_metrics are linked to thread_id
    result = await db.execute(
        select(CostMetric, Thread.name)
        .join(Thread, Thread.thread_id == CostMetric.thread_id)
        .where(Thread.user_id == current_user.id)
        .order_by(CostMetric.created_at.desc())
    )
    rows = result.all()
    
    metrics = [row[0] for row in rows]
    thread_names = {row[0].thread_id: row[1] for row in rows}
    
    total_cost = sum(m.estimated_cost_usd for m in metrics)
    total_prompt = sum(m.prompt_tokens for m in metrics)
    total_completion = sum(m.completion_tokens for m in metrics)
    avg_latency = (sum(m.latency_seconds for m in metrics) / len(metrics)) if metrics else 0.0
    
    return {
        "summary": {
            "total_runs": len(metrics),
            "total_cost_usd": total_cost,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "average_latency_seconds": avg_latency
        },
        "details": [
            {
                "id": str(m.id),
                "thread_id": str(m.thread_id),
                "thread_name": thread_names.get(m.thread_id, "Unknown Thread"),
                "prompt_tokens": m.prompt_tokens,
                "completion_tokens": m.completion_tokens,
                "estimated_cost_usd": m.estimated_cost_usd,
                "latency_seconds": m.latency_seconds,
                "created_at": m.created_at.isoformat()
            } for m in metrics
        ]
    }
