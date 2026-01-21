import pandas as pd

def tableau_amortissement(
    capital: float,
    duree_annees: int,
    taux_annuel: float
) -> tuple[float, pd.DataFrame, float, float]:
    """
    Calcule la mensualité et le tableau d'amortissement.
    Retourne :
      - mensualité
      - dataframe du tableau
      - total des intérêts
      - coût total du crédit (intérêts totaux, basé sur les mensualités arrondies)
    """

    if capital <= 0:
        raise ValueError("Le capital doit être > 0.")
    if duree_annees <= 0:
        raise ValueError("La durée doit être > 0.")
    if taux_annuel < 0:
        raise ValueError("Le taux annuel doit être >= 0.")

    nbr_mensualites = 12 * duree_annees
    taux_mensuel = taux_annuel / 12

    # Cas taux = 0 : mensualité = capital / N
    if taux_mensuel == 0:
        valeur_mensualite = round(capital / nbr_mensualites, 2)
    else:
        valeur_mensualite = capital * (taux_mensuel / (1 - (1 + taux_mensuel) ** (-nbr_mensualites)))
        valeur_mensualite = round(valeur_mensualite, 2)

    capital_restant_du = []
    interets = []
    mensualites = []
    capital_rembourse = []
    part_interets = []

    for m in range(nbr_mensualites + 1):
        if m == 0:
            capital_restant_du.append(capital)
            interets.append(0.0)
            capital_rembourse.append(0.0)
            mensualites.append(0.0)
            part_interets.append(0.0)
        else:
            i = capital_restant_du[m - 1] * taux_mensuel
            interets.append(i)

            mensualites.append(valeur_mensualite)

            c = mensualites[m] - interets[m]
            capital_rembourse.append(c)

            crd = capital_restant_du[m - 1] - capital_rembourse[m]
            capital_restant_du.append(crd)

            if mensualites[m] == 0:
                part_interets.append(0.0)
            else:
                part_interets.append(round((interets[m] / mensualites[m]) * 100, 2))

    df = pd.DataFrame({
        "Mensualité": list(range(nbr_mensualites + 1)),
        "Intérêts": interets,
        "Capital remboursé": capital_rembourse,
        "Valeur mensualité": mensualites,
        "Capital restant dû": capital_restant_du,
        "% intérêts dans la mensualité": part_interets
    })

    # Arrondis d'affichage
    cols_money = ["Intérêts", "Capital remboursé", "Valeur mensualité", "Capital restant dû"]
    df[cols_money] = df[cols_money].round(2)

    # ✅ Ajouts demandés (hors ligne 0)
    total_interets = float(df.loc[df["Mensualité"] > 0, "Intérêts"].sum())
    total_rembourse = float(df.loc[df["Mensualité"] > 0, "Valeur mensualité"].sum())
    cout_total_credit = total_rembourse - capital  # en pratique = intérêts totaux si mensualité constante

    total_interets = round(total_interets, 2)
    cout_total_credit = round(cout_total_credit, 2)

    return valeur_mensualite, df, total_interets, cout_total_credit
