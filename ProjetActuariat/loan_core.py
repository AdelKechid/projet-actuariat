import pandas as pd

def tableau_amortissement(capital: float, duree_annees: int, taux_annuel: float):
    """
    Tableau d'amortissement à mensualités constantes.
    Paiements en fin de mois.
    Retourne : mensualité, df, total intérêts, coût total du crédit.

    df contient CRD = capital restant dû en fin de mois.
    """
    n_mois = int(duree_annees) * 12
    if n_mois <= 0:
        raise ValueError("La durée doit être positive.")

    i_m = float(taux_annuel) / 12.0

    # Mensualité
    if abs(i_m) < 1e-12:
        mensualite = float(capital) / n_mois
    else:
        mensualite = float(capital) * (i_m / (1.0 - (1.0 + i_m) ** (-n_mois)))

    mensualite = round(mensualite, 2)

    rows = []
    crd = float(capital)

    for m in range(1, n_mois + 1):
        interets = crd * i_m
        capital_remb = mensualite - interets
        crd_next = crd - capital_remb

        # Ajustement dernière mensualité pour tomber exactement à 0 (arrondis)
        if m == n_mois:
            capital_remb = crd
            valeur_mensualite = interets + capital_remb
            crd_next = 0.0
        else:
            valeur_mensualite = mensualite

        rows.append({
            "Mois": m,
            "Valeur mensualité": valeur_mensualite,
            "Intérêts": interets,
            "Capital remboursé": capital_remb,
            "CRD": crd_next
        })

        crd = crd_next

    df = pd.DataFrame(rows)
    cols = ["Valeur mensualité", "Intérêts", "Capital remboursé", "CRD"]
    df[cols] = df[cols].round(2)

    total_interets = round(float(df["Intérêts"].sum()), 2)
    cout_total = round(float(df["Valeur mensualité"].sum()) - float(capital), 2)

    return mensualite, df, total_interets, cout_total
