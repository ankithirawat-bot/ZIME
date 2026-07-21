"""Market regime detectors.

Rule-based, score-based, voting, HMM placeholder, and ML placeholder detectors.
"""

from __future__ import annotations

from backend.regime.models import (
    RegimeConfig,
    RegimeFeatures,
    RegimeResult,
    RegimeScore,
    RegimeType,
)

EPSILON = 1e-10


class BaseDetector:
    """Base class with shared utilities for detectors."""

    @property
    def name(self) -> str:
        return "base"

    def confidence(
        self,
        features: RegimeFeatures,
        score: RegimeScore,
    ) -> float:
        return score.confidence

    def diagnostics(
        self,
        history: tuple[RegimeResult, ...],
    ) -> dict[str, float]:
        if not history:
            return {"accuracy": 0.0, "stability": 0.0}
        regimes = [r.regime.value for r in history]
        changes = sum(
            1 for i in range(1, len(regimes)) if regimes[i] != regimes[i - 1]
        )
        stability = 1.0 - (changes / max(len(regimes) - 1, 1))
        return {
            "total_detections": float(len(history)),
            "stability": stability,
            "changes": float(changes),
        }

    def _build_competing(
        self,
        scores: dict[str, float],
    ) -> dict[str, float]:
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_scores[:3])


class RuleBasedDetector(BaseDetector):
    """Rule-based regime detector using feature thresholds."""

    @property
    def name(self) -> str:
        return "rule_based"

    def detect(
        self,
        features: RegimeFeatures,
        config: RegimeConfig,
    ) -> RegimeScore:
        evidence: dict[str, float] = {}
        scores: dict[str, float] = {}

        trend_vol = features.trend_strength
        momentum = features.momentum
        vol = features.volatility_level
        breadth = features.breadth
        dd = features.drawdown
        recovery = features.recovery_strength

        if trend_vol > 0.4 and vol < 0.4 and momentum > 0.2:
            evidence["strong_trend"] = trend_vol
            scores["TRENDING_BULL"] = 0.5 + 0.3 * trend_vol + 0.2 * (1 - vol)

        if trend_vol < -0.4 and vol > 0.5:
            evidence["bearish_trend"] = abs(trend_vol)
            scores["TRENDING_BEAR"] = 0.5 + 0.3 * abs(trend_vol) + 0.2 * vol

        if abs(trend_vol) < 0.2 and abs(momentum) < 0.1 and vol < 0.3:
            evidence["low_activity"] = 1.0 - abs(trend_vol)
            scores["SIDEWAYS"] = 0.4 + 0.3 * (1 - abs(trend_vol)) + 0.2 * (1 - vol)

        if trend_vol > 0.2 and vol < 0.3 and breadth > 0.6 and recovery > 0.7:
            evidence["accumulation"] = breadth * recovery
            scores["ACCUMULATION"] = 0.4 + 0.3 * breadth + 0.2 * recovery

        if trend_vol < -0.2 and vol > 0.3 and breadth < 0.4:
            evidence["distribution"] = (1 - breadth) * vol
            scores["DISTRIBUTION"] = 0.4 + 0.3 * (1 - breadth) + 0.2 * vol

        if dd < 0.15 and trend_vol > 0.3 and recovery > 0.6 and momentum > 0.2:
            evidence["recovering"] = recovery * trend_vol
            scores["RECOVERY"] = 0.4 + 0.3 * recovery + 0.2 * trend_vol

        if vol > 0.6:
            evidence["high_vol"] = vol
            scores["HIGH_VOLATILITY"] = 0.5 + 0.4 * vol

        if vol < 0.15:
            evidence["low_vol"] = 1 - vol
            scores["LOW_VOLATILITY"] = 0.5 + 0.3 * (1 - vol)

        if vol > 0.7 and trend_vol < -0.5 and dd > 0.2:
            evidence["panic"] = vol * dd
            scores["PANIC"] = 0.5 + 0.3 * vol + 0.2 * dd

        if trend_vol > 0.6 and momentum > 0.5 and vol > 0.4 and recovery > 0.8:
            evidence["euphoria"] = trend_vol * momentum
            scores["EUPHORIA"] = 0.5 + 0.3 * trend_vol + 0.2 * momentum

        if not scores:
            return RegimeScore(
                regime=RegimeType.UNKNOWN,
                confidence=0.0,
                evidence=evidence,
            )

        best_name = max(scores, key=scores.get)
        best_score = scores[best_name]
        confidence = min(1.0, best_score)
        competing = self._build_competing(scores)

        return RegimeScore(
            regime=RegimeType(best_name),
            confidence=confidence,
            evidence=evidence,
            competing_regimes=competing,
        )


class ScoreBasedDetector(BaseDetector):
    """Score-based detector using weighted feature combinations."""

    @property
    def name(self) -> str:
        return "score_based"

    def detect(
        self,
        features: RegimeFeatures,
        config: RegimeConfig,
    ) -> RegimeScore:
        scores: dict[str, float] = {}

        bull_score = (
            max(0, features.trend_strength) * 0.3
            + max(0, features.momentum) * 0.2
            + (1 - features.volatility_level) * 0.2
            + features.breadth * 0.15
            + features.recovery_strength * 0.15
        )
        scores["TRENDING_BULL"] = max(0.0, bull_score)

        bear_score = (
            max(0, -features.trend_strength) * 0.3
            + max(0, -features.momentum) * 0.2
            + features.volatility_level * 0.2
            + (1 - features.breadth) * 0.15
            + features.drawdown * 0.15
        )
        scores["TRENDING_BEAR"] = max(0.0, bear_score)

        sideways_score = (
            (1 - abs(features.trend_strength)) * 0.3
            + (1 - abs(features.momentum)) * 0.2
            + (1 - features.volatility_level) * 0.2
            + (1 - abs(features.volatility_change)) * 0.15
            + 0.5 * 0.15
        )
        scores["SIDEWAYS"] = max(0.0, sideways_score)

        high_vol_score = features.volatility_level * 0.5 + max(0, features.volatility_change) * 0.3 + (1 - features.liquidity_score) * 0.2
        scores["HIGH_VOLATILITY"] = max(0.0, high_vol_score)

        low_vol_score = (1 - features.volatility_level) * 0.5 + max(0, -features.volatility_change) * 0.3 + features.liquidity_score * 0.2
        scores["LOW_VOLATILITY"] = max(0.0, low_vol_score)

        panic_score = features.volatility_level * 0.3 + features.drawdown * 0.3 + max(0, -features.trend_strength) * 0.2 + max(0, -features.momentum) * 0.2
        scores["PANIC"] = max(0.0, panic_score)

        best_name = max(scores, key=scores.get)
        best_score = scores[best_name]
        confidence = min(1.0, best_score * 1.5)
        compelling = [v for k, v in scores.items() if v > best_score * 0.8 and k != best_name]
        if compelling:
            confidence = min(confidence, 0.6)

        return RegimeScore(
            regime=RegimeType(best_name),
            confidence=confidence,
            evidence=scores,
            competing_regimes=self._build_competing(scores),
        )


class VotingDetector(BaseDetector):
    """Voting detector that combines rule-based and score-based results."""

    @property
    def name(self) -> str:
        return "voting"

    def __init__(
        self,
        rule_detector: RuleBasedDetector | None = None,
        score_detector: ScoreBasedDetector | None = None,
    ) -> None:
        self._rule = rule_detector or RuleBasedDetector()
        self._score = score_detector or ScoreBasedDetector()

    def detect(
        self,
        features: RegimeFeatures,
        config: RegimeConfig,
    ) -> RegimeScore:
        rule_result = self._rule.detect(features, config)
        score_result = self._score.detect(features, config)

        votes: dict[str, float] = {}
        for regime, weight in rule_result.competing_regimes.items():
            votes[regime] = votes.get(regime, 0.0) + weight * 0.6
        for regime, weight in score_result.competing_regimes.items():
            votes[regime] = votes.get(regime, 0.0) + weight * 0.4

        combined_evidence = {}
        combined_evidence.update(rule_result.evidence)
        combined_evidence.update(score_result.evidence)

        if not votes:
            return RegimeScore(
                regime=RegimeType.UNKNOWN,
                confidence=0.0,
                evidence=combined_evidence,
            )

        best_name = max(votes, key=votes.get)
        best_vote = votes[best_name]
        total_votes = sum(votes.values()) or 1.0
        confidence = min(1.0, best_vote / total_votes * 2.0)
        confidence = max(rule_result.confidence * 0.5, score_result.confidence * 0.5, confidence)

        return RegimeScore(
            regime=RegimeType(best_name),
            confidence=confidence,
            evidence=combined_evidence,
            competing_regimes=self._build_competing(votes),
        )


class HMMPlaceholderDetector(BaseDetector):
    """Hidden Markov Model placeholder detector.

    Placeholder for future HMM-based regime detection.
    Currently returns UNKNOWN with a note.
    """

    @property
    def name(self) -> str:
        return "hmm"

    def detect(
        self,
        features: RegimeFeatures,
        config: RegimeConfig,
    ) -> RegimeScore:
        return RegimeScore(
            regime=RegimeType.UNKNOWN,
            confidence=0.3,
            evidence={"note": 1.0, "placeholder": 1.0},
            competing_regimes={"UNKNOWN": 1.0},
        )


class MLPlaceholderDetector(BaseDetector):
    """Machine Learning placeholder detector.

    Placeholder for future ML-based regime detection.
    Currently returns UNKNOWN with a note.
    """

    @property
    def name(self) -> str:
        return "ml"

    def detect(
        self,
        features: RegimeFeatures,
        config: RegimeConfig,
    ) -> RegimeScore:
        return RegimeScore(
            regime=RegimeType.UNKNOWN,
            confidence=0.2,
            evidence={"note": 1.0, "placeholder": 1.0},
            competing_regimes={"UNKNOWN": 1.0},
        )
