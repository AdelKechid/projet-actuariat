import os
import math
import pandas as pd
import streamlit as st

from loan_core import tableau_amortissement

st.set_page_config(page_title="Emprunt + assurance décès (mensuel)", layout="wide")
st.title("📊 Emprunt + assurance décès — CRD fin mois du décès + primes début de mois (annuity-due)")

TABLE_DECES_FILENAME = "TableDeces.xlsx"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TABLE_DECES_PATH = os.path.join(BASE_DIR, TABLE_DECES_FILENAME)

# ======================================================
# Table de décès (qx) — lecture automatique
# ======================================================
def load_qx_from_tabledeces(path: str):
    """
    Lit TableDeces.xlsx (Feuil1) et renvoie:
      - dict {age: qx}
      - omega = âge terminal max

    Convention:
      - qx ∈ [0,1]
      - q_omega peut être = 1 (âge terminal), ailleurs qx=1 interdit
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Fichier '{TABLE_DECES_FILENAME}' introuvable.\n"
            f"➡️ Mets '{TABLE_DECES_FILENAME}' dans le même dossier que app_updated.py.\n"
            f"Chemin attendu: {path}"
        )

    df = pd.read_excel(path, sheet_name="Feuil1")
    if df.shape[1] < 3:
        raise ValueError("Table décès: format inattendu (moins de 3 colonnes).")

    df = df.rename(columns={df.columns[0]: "Age", df.columns[2]: "qx"})
    df = df.iloc[1:].copy()  # skip mini-header row

    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["qx"] = pd.to_numeric(df["qx"], errors="coerce")
    df = df.dropna(subset=["Age", "qx"])

    df["Age"] = df["Age"].astype(int)
    omega = int(df["Age"].max())

    if (df["qx"] < 0).any():
        bad = df[df["qx"] < 0][["Age", "qx"]].head(10)
        raise ValueError(f"Table décès: qx < 0. Exemples:\n{bad}")

    if (df["qx"] > 1).any():
        bad = df[df["qx"] > 1][["Age", "qx"]].head(10)
        raise ValueError(f"Table décès: qx > 1. Exemples:\n{bad}")

    bad_eq1 = df[(df["qx"] == 1) & (df["Age"] != omega)]
    if not bad_eq1.empty:
        bad = bad_eq1[["Age", "qx"]].head(10)
        raise ValueError(f"Table décès: qx=1 autorisé uniquement à l'âge terminal ({omega}). Exemples:\n{bad}")

    return dict(zip(df["Age"].tolist(), df["qx"].tolist())), omega

# ======================================================
# Mensuel: conversion q annuels -> probas décès mensuelles
# Hypothèse: force de mortalité constante sur chaque année
# ======================================================
def monthly_death_probs_from_annual_q(q_by_year: list[float]) -> list[float]:
    """
    Convertit q annuels en P(décès pendant le mois m) sur 12n mois.
    """
    probs = []
    surv_to_year_start = 1.0
    for q in q_by_year:
        mu = -math.log(max(1e-15, 1.0 - q))
        for m in range(1, 13):
            p_month_cond = math.exp(-mu * (m - 1) / 12.0) - math.exp(-mu * m / 12.0)
            probs.append(surv_to_year_start * p_month_cond)
        surv_to_year_start *= (1.0 - q)
    return probs

def monthly_survival_to_month_start_from_annual_q(q_by_year: list[float]) -> list[float]:
    """
    Survie au DÉBUT de chaque mois (annuity-due) sur 12n mois.
    """
    surv_list = []
    surv_to_year_start = 1.0
    for q in q_by_year:
        mu = -math.log(max(1e-15, 1.0 - q))
        for j in range(1, 13):  # month 1..12
            surv_start_month = surv_to_year_start * math.exp(-mu * ((j - 1) / 12.0))
            surv_list.append(surv_start_month)
        surv_to_year_start *= (1.0 - q)
    return surv_list

# ======================================================
# Actuarial present values
# ======================================================
def single_premium_monthly(crd_end_of_month: list[float], death_probs_monthly: list[float], i_annual: float) -> float:
    """
    Prime unique nette avec prestation payée FIN DU MOIS du décès.
    """
    if len(crd_end_of_month) != len(death_probs_monthly):
        raise ValueError("Dimensions incohérentes: CRD mensuel vs probas décès mensuelles.")

    U = 0.0
    for m, (crd_m, p_death_m) in enumerate(zip(crd_end_of_month, death_probs_monthly), start=1):
        disc = (1.0 + i_annual) ** (-m / 12.0)
        U += disc * p_death_m * crd_m
    return U

def pv_monthly_premiums_due(survival_to_month_start: list[float], i_annual: float) -> float:
    """
    VA de 1€ payé AU DÉBUT de chaque mois tant que vivant (annuity-due).
    """
    pv = 0.0
    for idx, s_start in enumerate(survival_to_month_start):
        m = idx  # m=0..12n-1
        pv += (1.0 + i_annual) ** (-m / 12.0) * s_start
    return pv

# ======================================================
# UI
# ======================================================
with st.sidebar:
    st.header("Paramètres du prêt")
    capital = st.number_input("Capital emprunté (€)", min_value=1.0, value=200000.0, step=1000.0)
    duree = st.number_input("Durée (années)", min_value=1, value=20, step=1)
    taux = st.number_input("Taux annuel prêt (%)", min_value=0.0, value=3.5, step=0.1)

    st.divider()
    st.header("Assurance décès")
    age_x = st.number_input("Âge à l'adhésion x", min_value=0, max_value=120, value=50, step=1)
    taux_ass = st.number_input("Taux technique assurance (%)", min_value=0.0, value=float(taux), step=0.1)

    st.caption(f"Table décès lue automatiquement : **{TABLE_DECES_FILENAME}**")
    calculer = st.button("✅ Calculer")

# ======================================================
# Compute
# ======================================================
if calculer:
    try:
        # Charge table décès
        qx_map, omega = load_qx_from_tabledeces(TABLE_DECES_PATH)

        # Amortissement
        mensualite, df, total_int, cout_total = tableau_amortissement(
            capital=float(capital),
            duree_annees=int(duree),
            taux_annuel=float(taux) / 100.0
        )
        n_years = int(duree)
        n_months = 12 * n_years

        st.subheader(f"Mensualité du prêt : **{mensualite:,.2f} €**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total intérêts", f"{total_int:,.2f} €")
        c2.metric("Coût total du crédit", f"{cout_total:,.2f} €")
        c3.metric("Durée", f"{n_years} ans ({n_months} mois)")

        st.divider()
        st.subheader("Tableau d'amortissement (CRD fin de mois)")
        st.dataframe(df, use_container_width=True, height=420)

        # ===== q annuels utilisés (x..x+n-1) — sans affichage
        ages = list(range(int(age_x), int(age_x) + n_years))
        if max(ages) > omega:
            raise ValueError(f"Durée trop longue: table dispo jusqu'à {omega}, mais tu demandes {max(ages)}.")

        missing = [a for a in ages if a not in qx_map]
        if missing:
            raise ValueError(f"Âges manquants dans la table décès: {missing[:10]} (et peut-être plus).")

        q_by_year = [float(qx_map[a]) for a in ages]

        # ===== Modèle mensuel
        death_probs_monthly = monthly_death_probs_from_annual_q(q_by_year)                 # length 12n
        survival_to_month_start = monthly_survival_to_month_start_from_annual_q(q_by_year) # length 12n

        # ===== CRD mensuel: fin de mois m (issu du tableau)
        crd_end_of_month = df["CRD"].tolist()[:n_months]  # length 12n

        i_ass = float(taux_ass) / 100.0

        # Single premium: prestation = CRD fin du mois de décès
        U = single_premium_monthly(crd_end_of_month, death_probs_monthly, i_ass)

        # PV des primes: primes payées au début de mois (annuity-due)
        pv_prem_1e = pv_monthly_premiums_due(survival_to_month_start, i_ass)
        P = U / pv_prem_1e if pv_prem_1e > 0 else float("nan")

        st.divider()
        st.subheader("📌 Assurance décès (mensuel)")
        st.caption("Prestation: CRD fin du mois de décès. Primes: début de mois (annuity-due).")

        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Single premium (prime unique nette)", f"{U:,.2f} €")
        cc2.metric("Prime mensuelle nivelée (début de mois)", f"{P:,.2f} € / mois")
        cc3.metric("PV(1€/mois due)", f"{pv_prem_1e:,.6f}")

        # ===== Détail mensuel
        details = []
        for m in range(1, n_months + 1):
            disc = (1.0 + i_ass) ** (-m / 12.0)
            term = disc * death_probs_monthly[m - 1] * crd_end_of_month[m - 1]
            details.append({
                "Mois m": m,
                "Année": (m - 1) // 12 + 1,
                "CRD_m (fin mois)": round(crd_end_of_month[m - 1], 2),
                "Prob DC mois": death_probs_monthly[m - 1],
                "Discount (1+i)^(-m/12)": disc,
                "Terme VA": term,
            })

        details_df = pd.DataFrame(details)
        details_df["Prob DC mois"] = details_df["Prob DC mois"].round(12)
        details_df["Discount (1+i)^(-m/12)"] = details_df["Discount (1+i)^(-m/12)"].round(12)
        details_df["Terme VA"] = details_df["Terme VA"].round(8)

        with st.expander("Voir le détail mensuel (Terme VA par mois)"):
            st.dataframe(details_df, use_container_width=True, height=420)

        st.download_button(
            "⬇️ Télécharger le détail mensuel (CSV)",
            data=details_df.to_csv(index=False).encode("utf-8"),
            file_name="detail_single_premium_mensuel.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info(f"Assure-toi que **{TABLE_DECES_FILENAME}** est dans le même dossier que `app_updated.py`, puis clique sur **Calculer**.")
