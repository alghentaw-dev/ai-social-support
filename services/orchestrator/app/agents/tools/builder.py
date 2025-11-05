# services/orchestrator/app/agents/tools/builder.py
from typing import Dict

# Import your real tool implementations here:
from app.agents.tools_impl import (  # ← this is your old tools.py, now tools_impl.py
    ExtractBatchTool,
    ValidateTool,
    ScoreTool,
    AskUserTool,
)

def build_default_tools() -> Dict[str, object]:
    # Instantiate and return your actual tools
    return {
        "extract_batch": ExtractBatchTool(),
        "run_validation": ValidateTool(),
        "score_application": ScoreTool(),
        "ask_user_for_clarification": AskUserTool(),
    }
