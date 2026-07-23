"""Widgets package public API.

All workspace widgets must be exported here to allow clean imports:
  from frontend.widgets import EquityCurveWidget, StrategySelector, ...
"""

from frontend.widgets.analytics_summary_card import AnalyticsSummaryCard
from frontend.widgets.chart_placeholder_widget import ChartPlaceholderWidget
from frontend.widgets.equity_curve_widget import EquityCurveWidget
from frontend.widgets.market_health_card import MarketHealthCard
from frontend.widgets.metrics_grid import MetricsGrid
from frontend.widgets.performance_metrics_grid import PerformanceMetricsGrid
from frontend.widgets.performance_summary_card import PerformanceSummaryCard
from frontend.widgets.recommendation_card import RecommendationCard
from frontend.widgets.report_status_card import ReportStatusCard
from frontend.widgets.strategy_comparison_table import StrategyComparisonTable
from frontend.widgets.strategy_selector import StrategySelector
from frontend.widgets.signal_table import SignalTable
from frontend.widgets.trades_table import TradesTable

__all__ = [
    "AnalyticsSummaryCard",
    "ChartPlaceholderWidget",
    "EquityCurveWidget",
    "MarketHealthCard",
    "MetricsGrid",
    "PerformanceMetricsGrid",
    "PerformanceSummaryCard",
    "RecommendationCard",
    "ReportStatusCard",
    "StrategyComparisonTable",
    "StrategySelector",
    "SignalTable",
    "TradesTable",
]
