"""
CLI Output Formatter.

Formats ResearchResult for terminal display.
"""

from __future__ import annotations

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
    lines.append(f"Symbol:          {result.symbol}")
    lines.append(f"Period:          {result.period}")
    lines.append(f"Interval:        {result.interval}")
    lines.append(f"Rows:            {result.rows}")
    lines.append(f"Analysis Time:   {result.execution_time_ms:.1f} ms")
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
            lines.append(f"  [{err.factor}] {err.message}")

    # Metadata warnings
    warnings = result.metadata.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.append("-" * 50)
        for w in warnings:
            lines.append(f"  - {w}")

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
    lines.append(f"  {label}")

    # Value
    if fr.value is not None:
        lines.append(f"    Value:      {fr.value:.4f}")
    else:
        lines.append("    Value:      N/A")

    # Signal
    lines.append(f"    Signal:     {fr.signal.value}")

    # Confidence
    if fr.confidence is not None:
        lines.append(f"    Confidence: {fr.confidence:.2f}")

    # Metadata
    if fr.metadata:
        lines.append("    Metadata:")
        for k, v in fr.metadata.items():
            lines.append(f"      {k}: {v}")

    return "\n".join(lines)


def format_error(message: str) -> str:
    """Format an error message for display.

    Args:
        message: The error message.

    Returns:
        Formatted error string.
    """
    return f"Error: {message}"
