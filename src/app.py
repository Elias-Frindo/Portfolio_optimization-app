"""Interface graphique CustomTkinter pour l'optimiseur de portefeuille."""

from __future__ import annotations

import threading
import tkinter.messagebox as messagebox
from typing import Optional

import customtkinter as ctk
import pandas as pd

from src.config import MARKETS
from src.data_manager import (
    check_internet,
    data_exists,
    get_last_update,
    prices_to_returns,
    sync_market_data,
)
from src.optimizer import PortfolioResult, optimize_max_return, optimize_min_risk

# Thème
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg": "#0f1419",
    "card": "#1a2332",
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
}


class PortfolioOptimizerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Portfolio Optimizer")
        self.geometry("960x720")
        self.minsize(860, 640)
        self.configure(fg_color=COLORS["bg"])

        self._prices: Optional[pd.DataFrame] = None
        self._market_key = ctk.StringVar(value="us")
        self._mode = ctk.StringVar(value="max_return")
        self._status_text = ctk.StringVar(value="Bienvenue — sélectionnez un marché.")
        self._busy = False

        self._build_ui()
        self.after(300, self._startup_sync_prompt)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0, height=72)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="📊 Portfolio Optimizer",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, padx=24, pady=16, sticky="w")

        self._sync_btn = ctk.CTkButton(
            header,
            text="⟳ Mettre à jour les données",
            width=200,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._prompt_sync,
        )
        self._sync_btn.grid(row=0, column=2, padx=24, pady=16, sticky="e")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        self._build_market_card(body)
        self._build_mode_card(body)
        self._build_params_card(body)
        self._build_results_card(body)

        footer = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0, height=40)
        footer.grid(row=2, column=0, sticky="ew")
        ctk.CTkLabel(
            footer,
            textvariable=self._status_text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
        ).pack(side="left", padx=16, pady=8)

    def _card(self, parent, title: str, row: int, col: int, colspan: int = 1) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12)
        frame.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=6, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")
        return frame

    def _build_market_card(self, parent) -> None:
        card = self._card(parent, "Marché boursier", row=0, col=0)
        for i, (key, info) in enumerate(MARKETS.items()):
            ctk.CTkRadioButton(
                card,
                text=info["label"],
                variable=self._market_key,
                value=key,
                font=ctk.CTkFont(size=13),
                command=self._on_market_change,
            ).grid(row=i + 1, column=0, padx=20, pady=6, sticky="w")

        self._update_label = ctk.CTkLabel(
            card,
            text="Dernière MAJ : —",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["muted"],
        )
        self._update_label.grid(row=len(MARKETS) + 1, column=0, padx=20, pady=(4, 14), sticky="w")

    def _build_mode_card(self, parent) -> None:
        card = self._card(parent, "Mode d'optimisation", row=0, col=1)
        modes = [
            ("max_return", "Rendement maximal — risque fixé par vous"),
            ("min_risk", "Risque minimal — rendement fixé par vous"),
        ]
        for i, (val, label) in enumerate(modes):
            ctk.CTkRadioButton(
                card,
                text=label,
                variable=self._mode,
                value=val,
                font=ctk.CTkFont(size=13),
                command=self._on_mode_change,
            ).grid(row=i + 1, column=0, padx=20, pady=8, sticky="w")

        desc = ctk.CTkLabel(
            card,
            text="Markowitz : allocation optimale long-only,\ncontraintes selon votre objectif.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["muted"],
            justify="left",
        )
        desc.grid(row=3, column=0, padx=20, pady=(4, 14), sticky="w")

    def _build_params_card(self, parent) -> None:
        card = self._card(parent, "Paramètres", row=1, col=0, colspan=2)

        self._param_label = ctk.CTkLabel(
            card,
            text="Risque maximal annuel (volatilité, ex: 15 pour 15 %) :",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text"],
        )
        self._param_label.grid(row=1, column=0, padx=20, pady=(4, 4), sticky="w")

        entry_row = ctk.CTkFrame(card, fg_color="transparent")
        entry_row.grid(row=2, column=0, padx=20, pady=4, sticky="ew")
        entry_row.grid_columnconfigure(0, weight=1)

        self._param_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="15",
            height=38,
            font=ctk.CTkFont(size=14),
        )
        self._param_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self._param_entry.insert(0, "15")

        self._optimize_btn = ctk.CTkButton(
            entry_row,
            text="Optimiser le portefeuille",
            width=220,
            height=38,
            fg_color=COLORS["success"],
            hover_color="#16a34a",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._run_optimization,
        )
        self._optimize_btn.grid(row=0, column=1)

        hint = ctk.CTkLabel(
            card,
            text="Les valeurs sont en pourcentage annuel. Exemple : 10 = 10 %.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["muted"],
        )
        hint.grid(row=3, column=0, padx=20, pady=(4, 14), sticky="w")

    def _build_results_card(self, parent) -> None:
        card = self._card(parent, "Résultats", row=2, col=0, colspan=2)

        metrics = ctk.CTkFrame(card, fg_color="transparent")
        metrics.grid(row=1, column=0, padx=16, pady=4, sticky="ew")
        for c in range(3):
            metrics.grid_columnconfigure(c, weight=1)

        self._ret_label = self._metric_box(metrics, "Rendement attendu", "—", 0)
        self._vol_label = self._metric_box(metrics, "Volatilité", "—", 1)
        self._sharpe_label = self._metric_box(metrics, "Ratio de Sharpe", "—", 2)

        ctk.CTkLabel(
            card,
            text="Composition du portefeuille",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=2, column=0, padx=16, pady=(12, 4), sticky="w")

        self._results_text = ctk.CTkTextbox(
            card,
            height=220,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#0d1117",
            text_color=COLORS["text"],
        )
        self._results_text.grid(row=3, column=0, padx=16, pady=(4, 16), sticky="ew")
        self._results_text.insert("1.0", "Les résultats s'afficheront ici après optimisation.")
        self._results_text.configure(state="disabled")

    def _metric_box(self, parent, title: str, value: str, col: int) -> ctk.CTkLabel:
        box = ctk.CTkFrame(parent, fg_color="#0d1117", corner_radius=8)
        box.grid(row=0, column=col, padx=6, pady=4, sticky="ew")
        ctk.CTkLabel(
            box,
            text=title,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["muted"],
        ).pack(padx=12, pady=(10, 0))
        lbl = ctk.CTkLabel(
            box,
            text=value,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["accent"],
        )
        lbl.pack(padx=12, pady=(0, 10))
        return lbl

    def _on_market_change(self) -> None:
        self._refresh_update_label()
        self._prices = None
        market = MARKETS[self._market_key.get()]["label"]
        self._set_status(f"Marché : {market}. Chargez ou mettez à jour les données.")

    def _on_mode_change(self) -> None:
        if self._mode.get() == "max_return":
            self._param_label.configure(
                text="Risque maximal annuel (volatilité, ex: 15 pour 15 %) :"
            )
            self._param_entry.delete(0, "end")
            self._param_entry.insert(0, "15")
        else:
            self._param_label.configure(
                text="Rendement minimal annuel souhaité (ex: 8 pour 8 %) :"
            )
            self._param_entry.delete(0, "end")
            self._param_entry.insert(0, "8")

    def _refresh_update_label(self) -> None:
        last = get_last_update(self._market_key.get())
        if last:
            self._update_label.configure(text=f"Dernière MAJ : {last}")
        elif data_exists(self._market_key.get()):
            self._update_label.configure(text="Dernière MAJ : données locales disponibles")
        else:
            self._update_label.configure(text="Dernière MAJ : aucune donnée locale")

    def _set_status(self, msg: str) -> None:
        self._status_text.set(msg)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self._optimize_btn.configure(state=state)
        self._sync_btn.configure(state=state)

    def _startup_sync_prompt(self) -> None:
        market = self._market_key.get()
        self._refresh_update_label()
        has_local = data_exists(market)
        online = check_internet()

        if has_local:
            msg = (
                "Des données CSV locales sont disponibles.\n\n"
                "Voulez-vous télécharger les données les plus récentes ?"
            )
            if not online:
                msg += "\n\n⚠ Pas de connexion Internet — les données locales seront conservées."
        else:
            if online:
                msg = (
                    "Aucune donnée locale trouvée.\n\n"
                    "Voulez-vous télécharger les données boursières maintenant ?"
                )
            else:
                messagebox.showerror(
                    "Connexion requise",
                    "Aucune donnée locale et pas de connexion Internet.\n"
                    "Connectez-vous pour le premier téléchargement.",
                )
                return

        if messagebox.askyesno("Synchronisation des données", msg):
            self._do_sync(force_update=True)
        elif has_local:
            self._load_local_silent()

    def _prompt_sync(self) -> None:
        if self._busy:
            return
        market_label = MARKETS[self._market_key.get()]["label"]
        online = check_internet()
        msg = f"Mettre à jour les données pour {market_label} ?"
        if not online:
            msg += (
                "\n\n⚠ Pas de connexion Internet.\n"
                "Les données locales seront conservées."
            )
        if messagebox.askyesno("Mise à jour", msg):
            self._do_sync(force_update=True)

    def _load_local_silent(self) -> None:
        try:
            prices, msg = sync_market_data(self._market_key.get(), force_update=False)
            self._prices = prices
            self._refresh_update_label()
            self._set_status(msg)
        except Exception as exc:
            self._set_status(f"Erreur : {exc}")

    def _do_sync(self, force_update: bool = True) -> None:
        if self._busy:
            return
        market_key = self._market_key.get()
        self._set_busy(True)
        self._set_status("Synchronisation en cours…")

        def task():
            try:
                prices, msg = sync_market_data(market_key, force_update=force_update)
                self.after(0, lambda: self._on_sync_done(prices, msg, None))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_sync_done(None, "", e))

        threading.Thread(target=task, daemon=True).start()

    def _on_sync_done(
        self,
        prices: Optional[pd.DataFrame],
        msg: str,
        error: Optional[Exception],
    ) -> None:
        self._set_busy(False)
        if error:
            messagebox.showerror("Synchronisation", str(error))
            self._set_status(f"Échec : {error}")
            if data_exists(self._market_key.get()):
                self._load_local_silent()
            return
        self._prices = prices
        self._refresh_update_label()
        self._set_status(msg)
        messagebox.showinfo("Synchronisation", msg)

    def _parse_param(self) -> float:
        raw = self._param_entry.get().strip().replace(",", ".")
        if not raw:
            raise ValueError("Veuillez saisir une valeur.")
        value = float(raw)
        if value <= 0:
            raise ValueError("La valeur doit être strictement positive.")
        return value / 100.0

    def _run_optimization(self) -> None:
        if self._busy:
            return

        try:
            constraint = self._parse_param()
        except ValueError as exc:
            messagebox.showwarning("Paramètre invalide", str(exc))
            return

        if self._prices is None:
            try:
                self._prices, _ = sync_market_data(
                    self._market_key.get(), force_update=False
                )
            except Exception as exc:
                messagebox.showerror(
                    "Données manquantes",
                    f"{exc}\n\nMettez à jour les données d'abord.",
                )
                return

        self._set_busy(True)
        self._set_status("Optimisation en cours…")
        mode = self._mode.get()
        prices = self._prices.copy()

        def task():
            try:
                returns = prices_to_returns(prices)
                if mode == "max_return":
                    result = optimize_max_return(returns, max_risk=constraint)
                else:
                    result = optimize_min_risk(returns, min_return=constraint)
                self.after(0, lambda r=result, ret=returns: self._on_optimize_done(r, ret, None))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_optimize_done(None, None, e))

        threading.Thread(target=task, daemon=True).start()

    def _on_optimize_done(
        self,
        result: Optional[PortfolioResult],
        returns: Optional[pd.DataFrame],
        error: Optional[Exception],
    ) -> None:
        
        self._set_busy(False)
        if error:
            messagebox.showerror("Optimisation", str(error))
            self._set_status(f"Échec : {error}")
            return

        assert result is not None
        self._ret_label.configure(text=f"{result.expected_return:.2%}")
        self._vol_label.configure(text=f"{result.volatility:.2%}")
        self._sharpe_label.configure(text=f"{result.sharpe_ratio:.2f}")

        lines = [
            f"Mode : {result.mode}",
            f"Marché : {MARKETS[self._market_key.get()]['label']}",
            "",
            f"{'Actif':<12} {'Poids':>8}",
            "─" * 22,
        ]
        for ticker, weight in result.weights_sorted:
            bar = "█" * int(weight * 30)
            lines.append(f"{ticker:<12} {weight:>7.2%}  {bar}")

        total = sum(result.weights.values())
        lines.append("─" * 22)
        lines.append(f"{'Total':<12} {total:>7.2%}")

        self._results_text.configure(state="normal")
        self._results_text.delete("1.0", "end")
        self._results_text.insert("1.0", "\n".join(lines))
        self._results_text.configure(state="disabled")
        self._set_status("Optimisation terminée avec succès.")


def run_app() -> None:
    app = PortfolioOptimizerApp()
    app.mainloop()
