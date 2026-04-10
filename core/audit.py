import pandas as pd


def comparer_balances(df_n1, df_n):
    # Uniformiser les noms de colonnes
    df_n1.columns = df_n1.columns.str.strip().str.upper()
    df_n.columns = df_n.columns.str.strip().str.upper()

    # Garder uniquement les colonnes utiles
    df_n1 = df_n1[["COMPTE", "LIBELLE", "SOLDE"]].copy()
    df_n = df_n[["COMPTE", "LIBELLE", "SOLDE"]].copy()

    # Harmoniser le type de COMPTE
    df_n1["COMPTE"] = df_n1["COMPTE"].astype(str).str.strip()
    df_n["COMPTE"] = df_n["COMPTE"].astype(str).str.strip()

    # Ne garder que les comptes de bilan : classes 1 à 5
    df_n1 = df_n1[df_n1["COMPTE"].str[0].isin(list("12345"))].copy()
    df_n = df_n[df_n["COMPTE"].str[0].isin(list("12345"))].copy()

    # Convertir les soldes en numérique
    df_n1["SOLDE"] = pd.to_numeric(df_n1["SOLDE"], errors="coerce")
    df_n["SOLDE"] = pd.to_numeric(df_n["SOLDE"], errors="coerce")

    # Renommer avant fusion
    df_n1 = df_n1.rename(columns={
        "LIBELLE": "LIBELLE_N1",
        "SOLDE": "SOLDE_N1",
    })

    df_n = df_n.rename(columns={
        "LIBELLE": "LIBELLE_N",
        "SOLDE": "SOLDE_N",
    })

    # Fusion
    df = pd.merge(df_n1, df_n, on="COMPTE", how="outer")

    # Calcul écart
    df["ECART"] = df["SOLDE_N"].fillna(0) - df["SOLDE_N1"].fillna(0)

    # Message
    def commentaire(row):
        if pd.isna(row["SOLDE_N1"]) and not pd.isna(row["SOLDE_N"]):
            return "Existe en N, absent en N-1"
        elif pd.isna(row["SOLDE_N"]) and not pd.isna(row["SOLDE_N1"]):
            return "Existe en N-1, absent en N"
        elif row["ECART"] == 0:
            return "OK"
        else:
            return "Écart de solde"

    df["MESSAGE"] = df.apply(commentaire, axis=1)

    # Ordre des colonnes
    df = df[
        ["COMPTE", "LIBELLE_N1", "SOLDE_N1", "LIBELLE_N", "SOLDE_N", "ECART", "MESSAGE"]
    ].sort_values("COMPTE")

    return df
