"""Point d'entrée de Portfolio Optimizer."""

import sys


def main() -> None:
    try:
        from src.app import run_app

        run_app()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Erreur fatale",
            f"L'application n'a pas pu démarrer :\n\n{exc}",
        )
        root.destroy()
        sys.exit(1)


if __name__ == "__main__":
    main()
