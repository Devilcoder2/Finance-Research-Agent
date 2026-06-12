import os
import uuid
import json
import asyncio
from typing import List, Dict, Any, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
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
from backend.app.db.models import Thread, Brief, Annotation, Evaluation
from backend.app.graphs.supervisor import portfolio_builder
from backend.app.graphs.state import SectionAnnotation, PortfolioState

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
async def start_research(req: ResearchStartRequest, db: AsyncSession = Depends(get_db)):
    # Default analyst user ID seeded in DB init
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    thread_id = uuid.uuid4()
    
    # Create thread entry
    db_thread = Thread(
        thread_id=thread_id,
        user_id=default_user_id,
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
async def list_threads(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Thread).order_by(Thread.created_at.desc()))
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
async def get_briefs(thread_id: str, db: AsyncSession = Depends(get_db)):
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
        
    result = await db.execute(select(Thread).where(Thread.thread_id == thread_uuid))
    db_thread = result.scalar_one_or_none()
    if not db_thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
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
async def resume_research(req: ResearchResumeRequest, db: AsyncSession = Depends(get_db)):
    try:
        thread_uuid = uuid.UUID(req.thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
        
    result = await db.execute(select(Thread).where(Thread.thread_id == thread_uuid))
    db_thread = result.scalar_one_or_none()
    if not db_thread:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    pool = await get_pool()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    compiled_app = portfolio_builder.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": req.thread_id}}
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
            await db.commit()
            
    try:
        db_thread.status = "initiated"
        await db.commit()
        
        # Invoke LangGraph resume
        await compiled_app.ainvoke(Command(resume=resume_map), config=config)
        
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
async def stream_research(thread_id: str):
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread_id format")
        
    async def event_generator():
        async with async_session() as session:
            result = await session.execute(select(Thread).where(Thread.thread_id == thread_uuid))
            db_thread = result.scalar_one_or_none()
            if not db_thread:
                yield f"data: {json.dumps({'event': 'error', 'message': 'Thread not found'})}\n\n"
                return
            tickers = db_thread.tickers
            
        pool = await get_pool()
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        compiled_app = portfolio_builder.compile(checkpointer=checkpointer)
        
        config = {"configurable": {"thread_id": thread_id}}
        state = PortfolioState(tickers=tickers)
        
        try:
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
                
        except Exception as e:
            async with async_session() as session:
                result = await session.execute(select(Thread).where(Thread.thread_id == thread_uuid))
                db_thread = result.scalar_one()
                db_thread.status = "failed"
                await session.commit()
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
