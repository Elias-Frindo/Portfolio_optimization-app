from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

MARKETS = {
    "casa": {
        "label": "Bourse de Casablanca",
        "folder": "casa",
        "source": "casased",
        # Identifiants Medias24 / casased (ticker affiché -> nom API)
        "tickers": {
            "IAM": "IAM",
            "BCP": "BCP",
            "BOA": "BOA",
            "CIH": "CIH",
            "CDM": "CDM",
            "CFG": "CFG",
            "CMG": "CMG",
            "SMI": "SMI",
            "ATW": "Attijariwafa",
            "ADH": "Addoha",
            "SNP": "Sonasid",
            "JET": "Jet Contractors",
            "RIS": "Risma",
            "COL": "Colorado",
            "DRI": "Disway",
            "LES": "Lesieur Cristal",
        },
    },
    "us": {
        "label": "Bourse américaine (internationale)",
        "folder": "us",
        "source": "yfinance",
        "tickers": [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
            "JPM", "V", "UNH", "XOM", "JNJ", "WMT", "PG", "MA", "HD", "CVX",
            "MRK", "ABBV", "PEP", "KO", "COST", "AVGO", "LLY", "TMO", "MCD",
            "CSCO", "ACN", "ABT", "DHR", "NKE", "TXN", "NEE", "PM", "ORCL",
            "CRM", "AMD", "INTC", "QCOM", "IBM", "GE", "CAT", "BA", "DIS",
        ],
    },
}
