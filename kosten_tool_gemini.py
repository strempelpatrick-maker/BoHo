import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- SEITENKONFIGURATION ---
st.set_page_config(page_title="Altholz Kalkulator", layout="wide", page_icon="🌲")

st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

st.title("🌲 Altholz Kostenrechnung & Kalkulation")
st.markdown("Interaktives Tool zur Berechnung von Deckungsbeiträgen basierend auf Logistik- und Verarbeitungskosten.")
st.markdown("---")

# --- SIDEBAR (EINGABEN) ---
st.sidebar.header("⚙️ Parameter Einstellungen")

# 1. Material & Mengen
st.sidebar.subheader("1. Material Input")
menge_input = st.sidebar.number_input("Gesamtmenge pro Jahr (Einheit)", value=1000.0, step=50.0)
einheit = st.sidebar.selectbox("Einheit", ["m³", "Tonnen"])
umrechnungsfaktor = st.sidebar.number_input(
    "Umrechnungsfaktor (t/m³)", value=0.233, format="%.3f",
    help="Dichte: Wie viel wiegt ein Kubikmeter?"
)

if einheit == "m³":
    tonnage_gesamt = menge_input * umrechnungsfaktor
    volumen_gesamt = menge_input
else:
    tonnage_gesamt = menge_input
    volumen_gesamt = menge_input / umrechnungsfaktor if umrechnungsfaktor > 0 else 0

st.sidebar.info(f"Berechnete Masse: **{tonnage_gesamt:.2f} t**")

# 2. Logistik
st.sidebar.subheader("2. Logistik")
ladegewicht = st.sidebar.number_input("Ø Ladegewicht pro LKW (t)", value=20.0)
km_entfernung = st.sidebar.slider("Entfernung zum Verwerter (km)", 0, 100, 40)

def get_frachtpreis(km):
    if km <= 10: return 116.26
    elif km <= 20: return 124.52
    elif km <= 30: return 138.78
    elif km <= 40: return 153.04
    elif km <= 50: return 165.00
    else: return 153.04 + ((km - 40) * 2.5)

frachtpreis_pro_tour = st.sidebar.number_input(
    f"Preis pro Tour (bei {km_entfernung}km)",
    value=float(get_frachtpreis(km_entfernung))
)

# 3. Verarbeitung & Kosten
st.sidebar.subheader("3. Kosten & Erlöse")
durchsatz_h = st.sidebar.number_input("Durchsatz Schredder (m³/h)", value=20.5)
maschinenstundensatz = st.sidebar.number_input("Maschinenkosten (€/h)", value=180.0)
gemeinkosten_pauschale = st.sidebar.number_input("Verwaltung/Vertrieb (VAK) in %", value=12.0)
verkaufspreis_pro_t = st.sidebar.number_input("Erlös / Marktpreis (pro Tonne)", value=45.0)

# --- BERECHNUNGSLOGIK ---

# Logistik
anzahl_touren = tonnage_gesamt / ladegewicht if ladegewicht > 0 else 0
logistik_kosten_gesamt = anzahl_touren * frachtpreis_pro_tour
logistik_pro_t = logistik_kosten_gesamt / tonnage_gesamt if tonnage_gesamt > 0 else 0

# Produktion / Hackung
stunden_bedarf = volumen_gesamt / durchsatz_h if durchsatz_h > 0 else 0
produktions_kosten_gesamt = stunden_bedarf * maschinenstundensatz
produktion_pro_t = produktions_kosten_gesamt / tonnage_gesamt if tonnage_gesamt > 0 else 0

# Selbstkosten
selbstkosten_ohne_vak = logistik_kosten_gesamt + produktions_kosten_gesamt
vak_kosten = selbstkosten_ohne_vak * (gemeinkosten_pauschale / 100)
selbstkosten_gesamt = selbstkosten_ohne_vak + vak_kosten
selbstkosten_pro_t = selbstkosten_gesamt / tonnage_gesamt if tonnage_gesamt > 0 else 0

# Ergebnis
erloes_gesamt = tonnage_gesamt * verkaufspreis_pro_t
gewinn_gesamt = erloes_gesamt - selbstkosten_gesamt
gewinn_pro_t = gewinn_gesamt / tonnage_gesamt if tonnage_gesamt > 0 else 0
marge_prozent = (gewinn_gesamt / erloes_gesamt * 100) if erloes_gesamt > 0 else 0

# --- DASHBOARD LAYOUT ---

col1, col2, col3, col4 = st.columns(4)
col1.metric("Gesamtmenge (t)", f"{tonnage_gesamt:.1f} t", delta_color="off")
col2.metric("Selbstkosten / t", f"{selbstkosten_pro_t:.2f} €", f"{(vak_kosten/tonnage_gesamt if tonnage_gesamt>0 else 0):.2f} € VAK", delta_color="inverse")
col3.metric("Erlös / t", f"{verkaufspreis_pro_t:.2f} €")
col4.metric("Ergebnis / t", f"{gewinn_pro_t:.2f} €", f"{marge_prozent:.1f}% Marge", delta_color="normal")

st.markdown("---")

# ----- matplotlib Charts -----

def plot_donut(labels, values, title):
    fig, ax = plt.subplots(figsize=(5, 4))
    total = sum(values) if sum(values) != 0 else 1
    ax.pie(values, labels=labels, autopct=lambda p: f"{p:.0f}%", startangle=90,
           wedgeprops=dict(width=0.45))
    ax.set_title(title)
    ax.text(0, 0, f"{total:,.0f} €", ha="center", va="center", fontsize=12, fontweight="bold")
    fig.tight_layout()
    return fig

def plot_waterfall(title, steps):
    """
    steps: list of tuples (label, value, kind)
      kind: "start" | "cost" | "result"
      value: positive for start/result, positive cost will be drawn as negative
    """
    labels = [s[0] for s in steps]
    kinds  = [s[2] for s in steps]

    vals = []
    for _, v, k in steps:
        if k == "cost":
            vals.append(-abs(v))
        else:
            vals.append(v)

    cumulative = [0]
    for v in vals[:-1]:
        cumulative.append(cumulative[-1] + v)

    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (lab, v, k) in enumerate(zip(labels, vals, kinds)):
        if i == 0:
            bottom = 0
            height = v
        elif i == len(vals) - 1:
            bottom = 0
            height = sum(vals[:-1])  # final total = sum of previous
        else:
            bottom = cumulative[i]
            height = v

        ax.bar(i, height, bottom=bottom)
        ax.text(i, bottom + height + (0.5 if height >= 0 else -0.5), f"{height:.2f}", ha="center", va="bottom")

    ax.axhline(0, linewidth=1)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_title(title)
    fig.tight_layout()
    return fig

c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("💰 Kostenstruktur")
    labels = ['Logistik', 'Produktion/Maschine', 'VAK (Verwaltung)']
    values = [logistik_kosten_gesamt, produktions_kosten_gesamt, vak_kosten]
    fig = plot_donut(labels, values, "Kostenstruktur (Anteile)")
    st.pyplot(fig, use_container_width=True)

with c2:
    st.subheader("📊 Wasserfall-Analyse (pro Tonne)")
    vak_pro_t = (vak_kosten / tonnage_gesamt) if tonnage_gesamt > 0 else 0
    steps = [
        ("Verkaufspreis", verkaufspreis_pro_t, "start"),
        ("Logistik", logistik_pro_t, "cost"),
        ("Produktion", produktion_pro_t, "cost"),
        ("VAK", vak_pro_t, "cost"),
        ("EBIT", 0, "result"),
    ]
    fig = plot_waterfall("Wasserfall (€/t)", steps)
    st.pyplot(fig, use_container_width=True)

# Reihe 3: Tabelle & Sensitivität
st.subheader("📋 Detaillierte Kalkulation")

data = {
    "Position": ["Menge", "Logistik", "Produktion", "Zwischensumme", "VAK", "Gesamt", "Erlös", "Ergebnis"],
    "Wert Absolut (€)": [
        "-",
        f"{logistik_kosten_gesamt:.2f}",
        f"{produktions_kosten_gesamt:.2f}",
        f"{selbstkosten_ohne_vak:.2f}",
        f"{vak_kosten:.2f}",
        f"{selbstkosten_gesamt:.2f}",
        f"{erloes_gesamt:.2f}",
        f"{gewinn_gesamt:.2f}"
    ],
    "Wert pro Tonne (€)": [
        f"{tonnage_gesamt:.2f} t",
        f"{logistik_pro_t:.2f}",
        f"{produktion_pro_t:.2f}",
        f"{(selbstkosten_ohne_vak/tonnage_gesamt if tonnage_gesamt>0 else 0):.2f}",
        f"{vak_pro_t:.2f}",
        f"{selbstkosten_pro_t:.2f}",
        f"{verkaufspreis_pro_t:.2f}",
        f"{gewinn_pro_t:.2f}"
    ]
}
df_res = pd.DataFrame(data)
st.dataframe(df_res, use_container_width=True)

with st.expander("📈 Szenario-Analyse: Was passiert, wenn der Dieselpreis steigt?"):
    st.write("Simulation: Auswirkung von +/- 20% Logistikkosten auf das Ergebnis")
    range_factors = [0.8, 0.9, 1.0, 1.1, 1.2]
    sim_results = []

    for f in range_factors:
        sim_logistik = logistik_kosten_gesamt * f
        sim_gewinn = erloes_gesamt - (sim_logistik + produktions_kosten_gesamt + vak_kosten)
        sim_results.append({"Faktor": f"{int((f-1)*100)}%", "Logistikkosten": sim_logistik, "Ergebnis": sim_gewinn})

    df_sim = pd.DataFrame(sim_results).set_index("Faktor")
    st.bar_chart(df_sim["Ergebnis"])
