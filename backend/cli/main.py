"""
ZIME Command Line Interface.

Exposes the ResearchService through a CLI for quick analysis.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from backend.cli.formatter import format_error, format_result
from backend.engines.factor_engine import FactorRequest
from backend.core.constants import DEFAULT_DATA_INTERVAL, DEFAULT_DATA_PERIOD
from backend.services.research_service import (
    ResearchService,
    VALID_INTERVALS,
    VALID_PERIODS,
)


def parse_factor(factor_str: str) -> FactorRequest:
    """Parse a factor string like 'EMA:20' into a FactorRequest.

    Args:
        factor_str: Factor specification (e.g. "EMA:20", "RSI:14", "MACD").

    Returns:
        A FactorRequest instance.

    Raises:
        ValueError: If the format is invalid.
    """
    if not factor_str or not factor_str.strip():
        raise ValueError("Factor string cannot be empty")

    parts = factor_str.split(":")
    factor_name = parts[0].strip().lower()

    if not factor_name:
        raise ValueError("Factor name cannot be empty in '%s'" % factor_str)

    params: dict[str, int | float] = {}
    if len(parts) == 2:
        param_str = parts[1].strip()
        if not param_str:
            raise ValueError("Parameter value cannot be empty in '%s'" % factor_str)
        try:
            params["period"] = int(param_str)
        except ValueError:
            try:
                params["period"] = float(param_str)
            except ValueError:
                raise ValueError(
                    "Invalid parameter '%s' in '%s'. Must be a number." % (param_str, factor_str)
                )
    elif len(parts) > 2:
        raise ValueError(
            "Invalid factor format '%s'. Expected 'NAME' or 'NAME:PERIOD'." % factor_str
        )

    return FactorRequest(factor=factor_name, params=params)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ZIME CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="zime",
        description="ZIME - Evidence-driven investment research platform",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run factor analysis for a stock symbol",
    )

    analyze_parser.add_argument(
        "symbol",
        type=str,
        help="Ticker symbol (e.g. RELIANCE.NS)",
    )

    analyze_parser.add_argument(
        "--period",
        type=str,
        default=DEFAULT_DATA_PERIOD,
        help="Historical period (default: %s). Valid: %%s" % DEFAULT_DATA_PERIOD % ", ".join(sorted(VALID_PERIODS)),
    )

    analyze_parser.add_argument(
        "--interval",
        type=str,
        default=DEFAULT_DATA_INTERVAL,
        help="Data interval (default: %s). Valid: %%s" % DEFAULT_DATA_INTERVAL % ", ".join(sorted(VALID_INTERVALS)),
    )

    analyze_parser.add_argument(
        "--factor",
        type=str,
        action="append",
        default=[],
        dest="factors",
        help="Factor to compute (e.g. EMA:20, RSI:14, MACD). Multiple allowed.",
    )

    return parser


def run_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        # Parse factor requests
        factor_requests = [parse_factor(f) for f in args.factors]

        # Create service and run analysis
        service = ResearchService()
        result = service.analyze(
            symbol=args.symbol,
            factor_requests=factor_requests,
            period=args.period,
            interval=args.interval,
        )

        # Display result
        print(format_result(result))

        return 0

    except ValueError as exc:
        print(format_error(str(exc)), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAnalysis cancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(format_error("Unexpected error: %s" % exc), file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the ZIME CLI.

    Args:
        argv: Command-line arguments. Defaults to sys.argv.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "analyze":
        return run_analyze(args)

    print(format_error("Unknown command: %s" % args.command), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
