"""
CLI Output Formatter.

Formats ResearchResult for terminal display.
"""

from __future__ import annotations

from typing import Any

from backend.engines.factor_engine import EngineError
from backend.core.factor_result import FactorResult
from backend.services.research_service import ResearchResult


SEPARATOR = "=" * 50


def format_result(result: ResearchResult) -> str:
    """Format a ResearchResult for terminal display.

    Args:
        result: The research result to format.

    Returns:
        Formatted string ready for printing.
    """
    lines: list[str] = []

    # Header
    lines.append(SEPARATOR)
    lines.append("Symbol:          %s" % result.symbol)
    lines.append("Period:          %s" % result.period)
    lines.append("Interval:        %s" % result.interval)
    lines.append("Rows:            %d" % result.rows)
    lines.append("Analysis Time:   %.1f ms" % result.execution_time_ms)
    lines.append(SEPARATOR)

    # Factor results
    if result.factor_results:
        lines.append("")
        lines.append("Factor Results:")
        lines.append("-" * 50)
        for label, fr in result.factor_results.items():
            lines.append(_format_factor(label, fr))
    else:
        lines.append("")
        lines.append("No factor results.")

    # Errors
    if result.engine_errors:
        lines.append("")
        lines.append("Errors:")
        lines.append("-" * 50)
        for err in result.engine_errors:
            lines.append("  [%s] %s" % (err.factor, err.message))

    # Metadata warnings
    warnings = result.metadata.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.append("-" * 50)
        for w in warnings:
            lines.append("  - %s" % w)

    lines.append("")
    return "\n".join(lines)


def _format_factor(label: str, fr: FactorResult) -> str:
    """Format a single factor result.

    Args:
        label: The factor label (e.g. "SMA20").
        fr:    The FactorResult to format.

    Returns:
        Formatted factor string.
    """
    lines: list[str] = []

    # Factor header
    lines.append("  %s" % label)

    # Value
    if fr.value is not None:
        lines.append("    Value:      %.4f" % fr.value)
    else:
        lines.append("    Value:      N/A")

    # Signal
    lines.append("    Signal:     %s" % fr.signal.value)

    # Confidence
    if fr.confidence is not None:
        lines.append("    Confidence: %.2f" % fr.confidence)

    # Metadata
    if fr.metadata:
        lines.append("    Metadata:")
        for k, v in fr.metadata.items():
            lines.append("      %s: %s" % (k, v))

    return "\n".join(lines)


def format_error(message: str) -> str:
    """Format an error message for display.

    Args:
        message: The error message.

    Returns:
        Formatted error string.
    """
    return "Error: %s" % message
