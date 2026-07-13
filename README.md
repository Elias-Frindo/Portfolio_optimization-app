# Portfolio Optimizer

A desktop application for portfolio allocation using **Modern Portfolio Theory (Markowitz mean-variance optimization)**. Choose a market, set your risk or return target, and get an optimal long-only allocation with expected return, volatility, and Sharpe ratio.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Two optimization modes**
  - **Max return** — maximize expected return for a given maximum annual volatility
  - **Min risk** — minimize volatility for a given minimum annual return
- **Multi-market support** — US stocks and Bourse de Casablanca
- **Online data sync** with offline fallback via local CSV cache
- **Dark-themed GUI** built with CustomTkinter
- **Background processing** — data sync and optimization run without freezing the UI

## Supported Markets

| Market | Source | Assets |
|--------|--------|--------|
| **US stocks** | [yfinance](https://github.com/ranaroussi/yfinance) | 45 large-cap tickers (AAPL, MSFT, GOOGL, NVDA, …) |
| **Bourse de Casablanca** | [casased](https://pypi.org/project/casased/) | 16 Moroccan stocks (IAM, BCP, ATW, …) |

Historical prices cover roughly **2 years** of daily data.

## Tech Stack

- **Python 3.10+**
- **CustomTkinter** — desktop UI
- **pandas / NumPy / SciPy** — data processing and constrained optimization (SLSQP)
- **yfinance / casased** — market data
- **PyInstaller** — optional standalone executable (`PortfolioOptimizer.spec`)

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Internet connection for the first data download (optional afterward)

### Quick run (Windows)

Double-click `run.bat` or run from a terminal:

```bat
run.bat
```

The script creates a virtual environment, installs dependencies, and launches the app.

### Manual setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

## Usage

1. **Select a market** — US or Casablanca Stock Exchange
2. **Sync data** — download or refresh price history (local CSV is used when offline)
3. **Choose a mode** — max return or min risk
4. **Set your constraint** — e.g. `15` for 15% max volatility, or `8` for 8% min return
5. **Optimize** — view portfolio weights, expected return, volatility, and Sharpe ratio

## Project Structure

```
Portfolio_optimization-app-main/
├── main.py                 # Application entry point
├── run.bat                 # Windows launcher (venv + deps + run)
├── requirements.txt
├── PortfolioOptimizer.spec # PyInstaller build config
├── data/
│   ├── us/                 # US market CSV + metadata
│   └── casa/               # Casablanca market CSV + metadata
└── src/
    ├── app.py              # CustomTkinter GUI
    ├── config.py           # Market definitions
    ├── data_manager.py     # Download, cache, and load prices
    └── optimizer.py        # Markowitz optimization
```

## Build Standalone Executable

Requires [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller PortfolioOptimizer.spec
```

The executable is written to `dist/PortfolioOptimizer.exe`.

## License

See [LICENSE](LICENSE).
