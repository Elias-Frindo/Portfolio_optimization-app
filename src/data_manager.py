"""Gestion des données boursières CSV et synchronisation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from src.config import DATA_DIR, MARKETS


def check_internet(timeout: float = 5.0) -> bool:
    """Vérifie la connectivité Internet."""
    try:
        response = requests.head("https://www.google.com", timeout=timeout)
        return response.status_code < 500
    except (requests.RequestException, OSError):
        return False


def _market_paths(market_key: str) -> tuple[Path, Path]:
    folder = DATA_DIR / MARKETS[market_key]["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "prices.csv", folder / "meta.json"


def get_last_update(market_key: str) -> Optional[str]:
    """Retourne la date de dernière mise à jour ou None."""
    _, meta_path = _market_paths(market_key)
    if not meta_path.exists():
        return None
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("last_update")
    except (json.JSONDecodeError, OSError):
        return None


def data_exists(market_key: str) -> bool:
    csv_path, _ = _market_paths(market_key)
    return csv_path.exists() and csv_path.stat().st_size > 0


def _download_us_prices(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """Télécharge les cours US via yfinance."""
    raw = yf.download(
        tickers,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    if raw.empty:
        raise ValueError("Aucune donnée reçue du serveur.")

    closes: dict[str, pd.Series] = {}

    if len(tickers) == 1:
        col = "Close" if "Close" in raw.columns else raw.columns[0]
        series = raw[col].dropna()
        if not series.empty:
            closes[tickers[0]] = series
    else:
        for ticker in tickers:
            try:
                if ticker in raw.columns.get_level_values(0):
                    series = raw[ticker]["Close"].dropna()
                    if len(series) >= 30:
                        closes[ticker] = series
            except (KeyError, TypeError):
                continue

    if len(closes) < 2:
        raise ValueError(
            "Données insuffisantes : au moins 2 actifs valides sont requis."
        )

    prices = pd.DataFrame(closes).dropna(how="all").ffill().dropna()
    if prices.shape[1] < 2 or prices.shape[0] < 30:
        raise ValueError("Historique trop court ou trop peu d'actifs disponibles.")
    return prices


def _download_casa_prices(ticker_map: dict[str, str]) -> pd.DataFrame:
    """Télécharge les cours Casa via casased (Medias24)."""
    import casased as cas
    from datetime import datetime, timedelta

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    closes: dict[str, pd.Series] = {}

    for display, api_name in ticker_map.items():
        try:
            hist = cas.get_history(api_name, start=start, end=end)
            if hist is None or hist.empty or "Value" not in hist.columns:
                continue
            series = hist["Value"].dropna()
            if len(series) >= 30:
                closes[display] = series
        except Exception:
            continue

    if len(closes) < 2:
        raise ValueError(
            "Données Casa insuffisantes : vérifiez votre connexion Internet "
            "et réessayez la synchronisation."
        )

    prices = pd.DataFrame(closes).dropna(how="all").ffill().dropna()
    if prices.shape[1] < 2 or prices.shape[0] < 30:
        raise ValueError("Historique Casa trop court ou trop peu d'actifs disponibles.")
    return prices


def download_market_data(market_key: str, period: str = "2y") -> pd.DataFrame:
    """Télécharge les cours et retourne un DataFrame des prix de clôture."""
    market = MARKETS[market_key]
    source = market.get("source", "yfinance")

    if source == "casased":
        return _download_casa_prices(market["tickers"])
    return _download_us_prices(market["tickers"], period=period)


def save_market_data(market_key: str, prices: pd.DataFrame) -> None:
    """Sauvegarde les prix et les métadonnées."""
    csv_path, meta_path = _market_paths(market_key)
    prices.to_csv(csv_path)
    meta = {
        "last_update": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tickers": list(prices.columns),
        "rows": int(prices.shape[0]),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def load_market_data(market_key: str) -> pd.DataFrame:
    """Charge les prix depuis le CSV local."""
    csv_path, _ = _market_paths(market_key)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Aucune base locale pour {MARKETS[market_key]['label']}. "
            "Connectez-vous à Internet et mettez à jour les données."
        )
    prices = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    if prices.shape[1] < 2:
        raise ValueError("Le fichier CSV local ne contient pas assez d'actifs.")
    return prices


def sync_market_data(market_key: str, force_update: bool = False) -> tuple[pd.DataFrame, str]:
    """
    Synchronise les données du marché.
    Retourne (prices, message_status).
    """
    if force_update:
        if not check_internet():
            if data_exists(market_key):
                return load_market_data(market_key), (
                    "Pas de connexion Internet — utilisation des données locales."
                )
            raise ConnectionError(
                "Connexion Internet requise pour le premier téléchargement."
            )
        prices = download_market_data(market_key)
        save_market_data(market_key, prices)
        return prices, "Données mises à jour avec succès."

    if data_exists(market_key):
        return load_market_data(market_key), "Données locales chargées."

    if not check_internet():
        raise ConnectionError(
            "Aucune donnée locale et pas de connexion Internet."
        )
    prices = download_market_data(market_key)
    save_market_data(market_key, prices)
    return prices, "Premier téléchargement effectué."


def prices_to_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Convertit les prix en rendements logarithmiques quotidiens."""
    returns = prices.pct_change().dropna(how="all")
    returns = returns.dropna(axis=1, thresh=int(len(returns) * 0.8))
    returns = returns.dropna()
    if returns.shape[1] < 2:
        raise ValueError("Pas assez d'actifs avec un historique complet.")
    return returns
