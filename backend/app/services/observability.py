"""
Observability: structured logging for agent runs.
Tracks tool calls, LLM calls, latency, tokens, and estimated cost.
"""

import time
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()

# GPT-4o pricing (per 1K tokens, as of 2024)
COST_PER_1K_INPUT = 0.0025
COST_PER_1K_OUTPUT = 0.01


@dataclass
class ToolTrace:
    name: str
    args: str
    result_length: int = 0
    duration_ms: int = 0


@dataclass
class LLMTrace:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: int = 0


@dataclass
class AgentTrace:
    """Collects all telemetry for a single agent run."""
    query: str = ""
    tool_traces: list[ToolTrace] = field(default_factory=list)
    llm_traces: list[LLMTrace] = field(default_factory=list)
    total_duration_ms: int = 0
    cache_hit: bool = False
    iterations: int = 0

    @property
    def total_tokens(self) -> int:
        return sum(t.total_tokens for t in self.llm_traces)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(t.prompt_tokens for t in self.llm_traces)

    @property
    def total_completion_tokens(self) -> int:
        return sum(t.completion_tokens for t in self.llm_traces)

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.total_prompt_tokens / 1000) * COST_PER_1K_INPUT
        output_cost = (self.total_completion_tokens / 1000) * COST_PER_1K_OUTPUT
        return round(input_cost + output_cost, 6)

    @property
    def tool_duration_ms(self) -> int:
        return sum(t.duration_ms for t in self.tool_traces)

    @property
    def llm_duration_ms(self) -> int:
        return sum(t.duration_ms for t in self.llm_traces)

    def log(self):
        """Emit structured log for this agent run."""
        tools_summary = [
            {"name": t.name, "duration_ms": t.duration_ms, "result_chars": t.result_length}
            for t in self.tool_traces
        ]

        logger.info(
            "agent_run",
            query=self.query[:100],
            cache_hit=self.cache_hit,
            iterations=self.iterations,
            tools_called=len(self.tool_traces),
            tools=tools_summary,
            llm_calls=len(self.llm_traces),
            total_tokens=self.total_tokens,
            prompt_tokens=self.total_prompt_tokens,
            completion_tokens=self.total_completion_tokens,
            cost_usd=self.estimated_cost_usd,
            tool_duration_ms=self.tool_duration_ms,
            llm_duration_ms=self.llm_duration_ms,
            total_duration_ms=self.total_duration_ms,
        )
