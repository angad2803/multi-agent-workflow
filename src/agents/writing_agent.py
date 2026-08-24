"""Writing Agent for creating content based on research."""

import os
from typing import Any

from src.agents.state import WorkflowState, WorkflowStatus
from src.shared.redis_client import get_from_workspace
from src.shared.llm_provider import get_llm, invoke_llm
from src.shared.logger import log_agent_action


# Template for comparison tasks
COMPARISON_TEMPLATE = """You are a technical writer creating a comparison.

Based on the following research findings, write a clear comparison for a technical audience.

{research_context}

## Original Request:
{prompt}

Write a professional comparison that:
1. Highlights key differences between the subjects
2. Discusses strengths and weaknesses of each
3. Provides guidance on when to use each
4. Is concise but comprehensive (2-3 paragraphs)

Comparison:"""


# Template for tutorial tasks
TUTORIAL_TEMPLATE = """You are a technical writer creating a tutorial.

Based on the following research findings, write a step-by-step tutorial.

{research_context}

## Original Request:
{prompt}

Write a clear tutorial that:
1. Lists prerequisites if needed
2. Provides numbered, actionable steps
3. Explains what each step accomplishes
4. Includes practical examples
5. Is beginner-friendly but technically accurate

Tutorial:"""


# Template for analysis tasks
ANALYSIS_TEMPLATE = """You are a technical analyst creating an in-depth analysis.

Based on the following research findings, provide a comprehensive technical analysis.

{research_context}

## Original Request:
{prompt}

Write a detailed analysis that:
1. Examines key aspects in depth
2. Discusses trade-offs and considerations
3. Provides technical insights and recommendations
4. Is thorough and well-structured

Analysis:"""


# Template for summary tasks
SUMMARY_TEMPLATE = """You are a technical writer creating an informative summary.

Based on the following research findings, write a clear summary.

{research_context}

## Original Request:
{prompt}

Write a concise summary that:
1. Covers the main points from the research
2. Is well-organized and easy to understand
3. Provides actionable information
4. Is appropriate for a technical audience

Summary:"""


def select_template(task_type: str) -> str:
    """
    Select the appropriate template based on task type.
    
    Args:
        task_type: The type of task (comparison, tutorial, analysis, summary)
        
    Returns:
        Template string
    """
    templates = {
        "comparison": COMPARISON_TEMPLATE,
        "tutorial": TUTORIAL_TEMPLATE,
        "analysis": ANALYSIS_TEMPLATE,
        "summary": SUMMARY_TEMPLATE,
    }
    
    return templates.get(task_type, SUMMARY_TEMPLATE)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 4 characters for English)."""
    return len(text) // 4


def truncate_research_context(research_results: dict[str, str], max_context_tokens: int) -> str:
    """
    Format and truncate research results to stay within token budget.
    
    Intelligently limits research context by:
    1. Preserving per-topic headers and structure
    2. Truncating longest topics first if needed
    3. Ensuring important information is retained
    
    Args:
        research_results: Dict mapping topics to research findings
        max_context_tokens: Maximum tokens allowed for research context
        
    Returns:
        Formatted string with truncated research, or empty if no room
    """
    if not research_results:
        return "No research available."
    
    # Reserve tokens for headers and formatting (topic names, markdown, spacing)
    header_overhead = len(research_results) * 50  # ~50 chars per topic header
    tokens_for_content = max(max_context_tokens - header_overhead, 100)  # Minimum 100 chars
    chars_budget = tokens_for_content * 4  # Convert back to approximate characters
    
    # Sort topics by content length (longest first for truncation)
    sorted_topics = sorted(
        research_results.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    sections = []
    total_chars = 0
    
    for topic, findings in sorted_topics:
        header = f"## {topic}\n"
        header_chars = len(header)
        
        if total_chars + header_chars > chars_budget:
            # Skip this topic if no room
            continue
        
        remaining_budget = chars_budget - total_chars - header_chars
        
        if len(findings) > remaining_budget:
            # Truncate content to fit
            truncated = findings[:remaining_budget].rsplit(" ", 1)[0] + "..."
            sections.append(f"{header}{truncated}")
            total_chars = chars_budget  # Budget exhausted
            break
        else:
            sections.append(f"{header}{findings}")
            total_chars += header_chars + len(findings) + 2  # +2 for newlines
    
    if not sections:
        return "Research available but truncated to fit token limit."
    
    return "\n\n".join(sections)


def format_research_context(research_results: dict[str, str]) -> str:
    """
    Format research results into context for the LLM prompt.
    
    Args:
        research_results: Dict mapping topics to research findings
        
    Returns:
        Formatted string with all research
    """
    if not research_results:
        return "No research available."
    
    sections = []
    for topic, findings in research_results.items():
        sections.append(f"## {topic}\n{findings}")
    
    return "\n\n".join(sections)


def writing_node(state: WorkflowState) -> dict[str, Any]:
    """
    Writing node that creates content based on research and task type.
    
    Now fully dynamic - adapts to any task type and research topics.
    
    This node:
    1. Reads research from state (or Redis workspace)
    2. Selects appropriate template based on task_type
    3. Uses LLM to generate output
    4. Returns draft for approval
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with draft
    """
    task_id = state.get("task_id", "")
    prompt = state.get("prompt", "")
    task_type = state.get("task_type", "summary")
    
    log_agent_action(task_id, "WritingAgent", f"Starting {task_type} generation")
    
    # Get research results from state (new flexible format)
    research_results = state.get("research_results", {})
    
    if not research_results:
        # Fall back to Redis workspace
        log_agent_action(task_id, "WritingAgent", "Loading research from Redis workspace")
        workspace_data = get_from_workspace(task_id)
        if workspace_data:
            research_results = workspace_data.get("research_results", {})
            task_type = workspace_data.get("task_type", task_type)
    
    if not research_results:
        log_agent_action(task_id, "WritingAgent", "No research results available")
        return {
            "draft": "Error: No research results available to generate content.",
            "status": WorkflowStatus.WRITING,
        }
    
    log_agent_action(
        task_id,
        "WritingAgent",
        f"Found research for {len(research_results)} topics, using {task_type} template"
    )
    
    # Select template based on task type
    template = select_template(task_type)
    
    # Limit research context to stay within token budget
    max_context_tokens = int(os.getenv("LLM_MAX_CONTEXT_TOKENS", "5000"))
    research_context = truncate_research_context(research_results, max_context_tokens)
    context_tokens = estimate_tokens(research_context)
    log_agent_action(
        task_id,
        "WritingAgent",
        f"Research context limited to ~{context_tokens} tokens (budget: {max_context_tokens})"
    )
    
    # Generate content using LLM
    llm = get_llm(temperature=0.7)  # Higher temp for more creative writing
    
    formatted_prompt = template.format(
        research_context=research_context,
        prompt=prompt,
    )
    
    log_agent_action(task_id, "WritingAgent", "Generating content with LLM")
    response = invoke_llm(llm, formatted_prompt)
    draft = response.content
    
    log_agent_action(
        task_id,
        "WritingAgent",
        f"Generated {len(draft)} character draft for approval"
    )
    
    return {
        "draft": draft,
        "status": WorkflowStatus.WRITING,
    }
