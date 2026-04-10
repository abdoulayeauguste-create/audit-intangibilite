"""
Contrôle d'intangibilité du bilan : compare les soldes clôture N-1 et ouverture N.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _to_numeric(series: pd.Series) -> pd.Series:
    """Convertit une colonne en nombres (gère virgule décimale et espaces)."""
    cleaned = (
        series.astype(str)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _soldes_egaux(a: float, b: float) -> bool:
    """Comparaison comptable en centimes (arrondi 2 décimales)."""
    return round(a - b, 2) == 0.0


def comparer_balances(
    df_n1: pd.DataFrame,
    df_n: pd.DataFrame,
    col_compte: str = "Compte",
    col_solde_n1: str = "Solde_cloture_N1",
    col_solde_n: str = "Solde_ouverture_N",
) -> pd.DataFrame:
    """
    Joint les deux balances sur le numéro de compte (clé externe complète).

    Retourne un DataFrame avec : Compte, Solde_N1, Solde_N, Ecart, Message
    """
    for name, df in ("N-1", df_n1), ("N", df_n):
        if col_compte not in df.columns:
            raise KeyError(f"Colonne '{col_compte}' absente dans la balance {name}. Colonnes : {list(df.columns)}")

    n1 = df_n1[[col_compte, col_solde_n1]].copy()
    n1 = n1.rename(columns={col_solde_n1: "Solde_N1"})
    n = df_n[[col_compte, col_solde_n]].copy()
    n = n.rename(columns={col_solde_n: "Solde_N"})

    n1[col_compte] = n1[col_compte].astype(str).str.strip()
    n[col_compte] = n[col_compte].astype(str).str.strip()

    n1["Solde_N1"] = _to_numeric(n1["Solde_N1"])
    n["Solde_N"] = _to_numeric(n["Solde_N"])

    # Un compte dupliqué dans un fichier : on agrège (somme) pour éviter des lignes ambiguës
    n1 = n1.groupby(col_compte, as_index=False)["Solde_N1"].sum(min_count=1)
    n = n.groupby(col_compte, as_index=False)["Solde_N"].sum(min_count=1)

    merged = pd.merge(n1, n, on=col_compte, how="outer")

    def message_row(row: pd.Series) -> str:
        s1, sn = row["Solde_N1"], row["Solde_N"]
        if pd.isna(s1) and pd.notna(sn):
            return "Existe en N, absent en N-1"
        if pd.notna(s1) and pd.isna(sn):
            return "Existe en N-1, absent en N"
        if pd.isna(s1) and pd.isna(sn):
            return "Sans solde (données manquantes)"
        if _soldes_egaux(float(s1), float(sn)):
            return "OK"
        return "Écart de solde"

    merged["Ecart"] = merged.apply(
        lambda r: (r["Solde_N"] - r["Solde_N1"])
        if pd.notna(r["Solde_N1"]) and pd.notna(r["Solde_N"])
        else pd.NA,
        axis=1,
    )
    merged["Message"] = merged.apply(message_row, axis=1)
    merged = merged.rename(columns={col_compte: "Compte"})
    return merged[
        ["Compte", "Solde_N1", "Solde_N", "Ecart", "Message"]
    ]


def lire_balance(chemin: Path, feuille: str | int = 0) -> pd.DataFrame:
    """Lit un fichier .xlsx / .xls ou .csv (séparateur ; ou , détecté)."""
    suffix = chemin.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(chemin, sep=None, engine="python", dtype=object)
    return pd.read_excel(chemin, sheet_name=feuille, dtype=object)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Contrôle intangibilité : balance clôture N-1 vs ouverture N (fichiers Excel)."
    )
    parser.add_argument("fichier_n1", type=Path, help="Excel balance N-1 (clôture)")
    parser.add_argument("fichier_n", type=Path, help="Excel balance N (ouverture)")
    parser.add_argument(
        "-o",
        "--sortie",
        type=Path,
        default=None,
        help="Fichier Excel de sortie (défaut : rapport_intangibilite.xlsx dans le dossier courant)",
    )
    parser.add_argument("--col-compte", default="Compte", help="Nom colonne numéro de compte (défaut : Compte)")
    parser.add_argument(
        "--col-solde-n1",
        default="Solde_cloture_N1",
        help="Nom colonne solde clôture N-1 (défaut : Solde_cloture_N1)",
    )
    parser.add_argument(
        "--col-solde-n",
        default="Solde_ouverture_N",
        help="Nom colonne solde ouverture N (défaut : Solde_ouverture_N)",
    )
    parser.add_argument("--feuille-n1", default=0, help="Feuille N-1 : index ou nom")
    parser.add_argument("--feuille-n", default=0, help="Feuille N : index ou nom")
    args = parser.parse_args()

    sortie = args.sortie or Path("rapport_intangibilite.xlsx")

    df_n1 = lire_balance(args.fichier_n1, args.feuille_n1)
    df_n = lire_balance(args.fichier_n, args.feuille_n)

    resultat = comparer_balances(
        df_n1,
        df_n,
        col_compte=args.col_compte,
        col_solde_n1=args.col_solde_n1,
        col_solde_n=args.col_solde_n,
    )

    anomalies = resultat[resultat["Message"] != "OK"]
    print(resultat.to_string(index=False))
    print(f"\n--- Résumé : {len(anomalies)} ligne(s) à examiner (hors OK) sur {len(resultat)} ---")

    with pd.ExcelWriter(sortie, engine="openpyxl") as writer:
        resultat.to_excel(writer, sheet_name="Controle", index=False)
        anomalies.to_excel(writer, sheet_name="Anomalies", index=False)

    print(f"Rapport écrit : {sortie.resolve()}")


if __name__ == "__main__":
    main()
