import streamlit as st
from loan_core import tableau_amortissement

st.set_page_config(page_title="Emprunt bancaire", layout="wide")
st.title("📊 Tableau d'amortissement — Emprunt bancaire")

with st.sidebar:
    st.header("Paramètres du prêt")
    capital = st.number_input("Capital emprunté (€)", min_value=1.0, value=200000.0, step=1000.0)
    duree = st.number_input("Durée (années)", min_value=1, value=20, step=1)
    taux_pourcent = st.number_input("Taux annuel (%)", min_value=0.0, value=3.5, step=0.1)

    calculer = st.button("✅ Calculer")

if calculer:
    try:
        taux_annuel = taux_pourcent / 100.0
        mensualite, df, total_interets, cout_total = tableau_amortissement(capital, int(duree), taux_annuel)

        st.subheader(f"Mensualité : **{mensualite:,.2f} €**")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Durée", f"{int(duree)} ans", f"{int(duree)*12} mensualités")
        with col2:
            st.metric("Taux annuel", f"{taux_pourcent:.2f} %")
        with col3:
            st.metric("Capital emprunté", f"{capital:,.0f} €")
        with col4:
            st.metric("Intérêts totaux", f"{total_interets:,.2f} €")
        with col5:
            st.metric("Coût total du crédit", f"{cout_total:,.2f} €")

        st.divider()

        st.subheader("Tableau d'amortissement")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Téléchargement CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Télécharger en CSV",
            data=csv,
            file_name="tableau_amortissement.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("Renseigne les paramètres du prêt dans la barre latérale, puis clique sur **Calculer**.")
