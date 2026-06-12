import os
import uuid
import hashlib
from typing import Dict, Any, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from langchain_google_genai import ChatGoogleGenerativeAI
# pyrefly: ignore [missing-import]
from langchain_core.prompts import ChatPromptTemplate
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import Evaluation
from backend.app.graphs.state import InvestmentBrief


# 1. MODELS
class EvaluationRubric(BaseModel):
    score_factual: float = Field(description="Factual consistency/accuracy score from 0.0 to 5.0 against provided sources.")
    score_clarity: float = Field(description="Narrative structure, clarity, and professional formatting score from 0.0 to 5.0.")
    score_coverage: float = Field(description="Downside risk factors and operational warning coverage score from 0.0 to 5.0.")
    rubric_justification: str = Field(description="Detailed textual justification explaining the scores awarded.")


# PROMPT
EVAL_SYSTEM_PROMPT = (
    "You are an Independent Audit Judge for a financial research department.\n"
    "Your job is to read a compiled investment brief and evaluate its quality "
    "according to a strict rubric, scoring each area from 0.0 to 5.0:\n\n"
    "RUBRIC:\n"
    "1. FACTUAL ACCURACY (score_factual): Compare assertions in the brief to raw source datasets. "
    "Check for statistical deviations or hallucinations. Higher scores represent flawless data preservation.\n"
    "2. NARRATIVE CLARITY (score_clarity): Assess readability, conciseness, grammar, and flow. "
    "Higher scores reflect professional, publishable equity research quality.\n"
    "3. RISK COVERAGE (score_coverage): Verify that downside dangers, supply chain challenges, "
    "or industry headwinds mentioned in sources are covered. Higher scores mean thorough coverage.\n\n"
    "Provide a detailed rubric_justification detailing why you awarded the scores."
)

def get_eval_prompt_hash() -> str:
    """Computes a SHA-256 hash of the evaluation prompt to track prompt-tuning version shifts."""

    return hashlib.sha256(EVAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest()

# STRUCTURED OUTPUT LLM 
def get_evaluator_llm():
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_key:
        print("[Evaluator] Using Google Gemini (gemini-1.5-pro) as Judge...")
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=google_key,
            temperature=0.0
        ).with_structured_output(EvaluationRubric)
    return None

# EVALUATOR LOGIC
async def evaluate_brief(
    brief_id: uuid.UUID,
    brief: InvestmentBrief,
    raw_news: str,
    raw_transcript: str,
    raw_quant: str,
    db_session: AsyncSession
) -> EvaluationRubric:
    """
    Evaluates the generated brief against the raw source materials and saves the scores.
    """
    llm = get_evaluator_llm()
    prompt_version_hash = get_eval_prompt_hash()
    
    if not llm:
        print("[Evaluator] Mock mode: generating mock evaluation metrics.")

        rubric = EvaluationRubric(
            score_factual=4.8,
            score_clarity=4.5,
            score_coverage=4.2,
            rubric_justification="Mock evaluation: Presumed accurate. Setup Gemini API key for real audit scores."
        )
    else:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", EVAL_SYSTEM_PROMPT),
                ("user", (
                    "Please evaluate this investment brief:\n\n"
                    "--- INVESTMENT BRIEF ---\n"
                    "Ticker: {ticker}\n"
                    "Executive Summary: {exec_summary}\n"
                    "Business Overview: {biz_overview}\n"
                    "Financial Analysis: {fin_analysis}\n"
                    "Risk Factors: {risk_factors}\n"
                    "Verdict: {verdict}\n\n"
                    "--- RAW SOURCES ---\n"
                    "Quantitative Multiples:\n{quant_data}\n\n"
                    "News Content:\n{news_data}\n\n"
                    "Earnings Call Transcripts:\n{transcript_data}\n\n"
                    "Evaluate and return the structured rubric scores."
                ))
            ])
            
            chain = prompt | llm
            rubric = await chain.ainvoke({
                "ticker": brief.ticker,
                "exec_summary": brief.executive_summary,
                "biz_overview": brief.business_overview,
                "fin_analysis": brief.financial_analysis,
                "risk_factors": brief.risk_factors,
                "verdict": brief.verdict,
                "quant_data": raw_quant,
                "news_data": raw_news,
                "transcript_data": raw_transcript
            })
        except Exception as e:
            print(f"Error during LLM evaluation: {e}. Falling back to default mock evaluation.")
            rubric = EvaluationRubric(
                score_factual=3.0,
                score_clarity=3.0,
                score_coverage=3.0,
                rubric_justification=f"Evaluation failed: {str(e)}. Fallback default applied."
            )
    # Save evaluation metrics to the database
    try:
        new_eval = Evaluation(
            brief_id=brief_id,
            prompt_version_hash=prompt_version_hash,
            score_factual=rubric.score_factual,
            score_clarity=rubric.score_clarity,
            score_coverage=rubric.score_coverage,
            rubric_justification=rubric.rubric_justification
        )
        db_session.add(new_eval)
        await db_session.commit()
        print(f"[Evaluator] Saved evaluation for brief {brief_id} successfully.")
    except Exception as e:
        print(f"Error writing evaluation details to database: {e}")
        await db_session.rollback()
    return rubric