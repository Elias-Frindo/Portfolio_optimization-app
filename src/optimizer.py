"""Optimisation de portefeuille Markowitz."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class PortfolioResult:
    weights: dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    mode: str

    @property
    def weights_sorted(self) -> list[tuple[str, float]]:
        return sorted(self.weights.items(), key=lambda x: x[1], reverse=True)


def _annualize(mean_daily: np.ndarray, cov_daily: np.ndarray, trading_days: int = 252):
    mu = mean_daily * trading_days
    sigma = cov_daily * trading_days
    return mu, sigma


def optimize_max_return(
    returns: pd.DataFrame,
    max_risk: float,
    risk_free_rate: float = 0.0,
) -> PortfolioResult:
    """
    Maximise le rendement sous contrainte de risque maximal (volatilité annuelle).
    max_risk : volatilité maximale acceptée (ex: 0.15 = 15 %).
    """
    if max_risk <= 0:
        raise ValueError("Le risque maximal doit être strictement positif.")

    mean_d = returns.mean().values
    cov_d = returns.cov().values
    n = len(mean_d)
    mu, sigma = _annualize(mean_d, cov_d)

    def portfolio_vol(w):
        return float(np.sqrt(w @ sigma @ w))

    def neg_return(w):
        return -float(w @ mu)

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "ineq", "fun": lambda w: max_risk**2 - w @ sigma @ w},
    ]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n

    result = minimize(
        neg_return,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 2000, "ftol": 1e-12},
    )

    if not result.success:
        raise ValueError(
            "Optimisation impossible : contrainte de risque trop restrictive. "
            "Augmentez le risque maximal ou changez de marché."
        )

    w = result.x
    exp_ret = float(w @ mu)
    vol = portfolio_vol(w)
    sharpe = (exp_ret - risk_free_rate) / vol if vol > 1e-10 else 0.0

    weights = {col: float(weight) for col, weight in zip(returns.columns, w) if weight > 1e-4}

    return PortfolioResult(
        weights=weights,
        expected_return=exp_ret,
        volatility=vol,
        sharpe_ratio=sharpe,
        mode="Rendement maximal (risque fixé)",
    )


def optimize_min_risk(
    returns: pd.DataFrame,
    min_return: float,
    risk_free_rate: float = 0.0,
) -> PortfolioResult:
    """
    Minimise le risque sous contrainte de rendement minimal annuel.
    min_return : rendement annuel minimal souhaité (ex: 0.08 = 8 %).
    """
    mean_d = returns.mean().values
    cov_d = returns.cov().values
    n = len(mean_d)
    mu, sigma = _annualize(mean_d, cov_d)

    max_achievable = float(np.max(mu))
    min_achievable = float(np.min(mu))

    if min_return > max_achievable + 1e-6:
        raise ValueError(
            f"Rendement cible ({min_return:.1%}) trop élevé. "
            f"Maximum historique individuel : {max_achievable:.1%}."
        )

    def portfolio_vol(w):
        return float(np.sqrt(w @ sigma @ w))

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "ineq", "fun": lambda w: w @ mu - min_return},
    ]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n

    result = minimize(
        portfolio_vol,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 2000, "ftol": 1e-12},
    )

    if not result.success:
        raise ValueError(
            "Optimisation impossible : rendement cible trop ambitieux. "
            f"Essayez une valeur entre {min_achievable:.1%} et {max_achievable:.1%}."
        )

    w = result.x
    exp_ret = float(w @ mu)
    vol = portfolio_vol(w)
    sharpe = (exp_ret - risk_free_rate) / vol if vol > 1e-10 else 0.0

    weights = {col: float(weight) for col, weight in zip(returns.columns, w) if weight > 1e-4}

    return PortfolioResult(
        weights=weights,
        expected_return=exp_ret,
        volatility=vol,
        sharpe_ratio=sharpe,
        mode="Risque minimal (rendement fixé)",
    )
