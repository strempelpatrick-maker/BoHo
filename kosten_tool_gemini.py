import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- SEITENKONFIGURATION ---
st.set_page_config(page_title="Altholz Kalkulator", layout="wide", page_icon="🌲")

# CSS für besseres Styling
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

# --- TITEL ---
st.title("🌲 Altholz Kostenrechnung & Kalkulation")
st.markdown("Interaktives Tool zur Berechnung von Deckungsbeiträgen basierend auf Logistik- und Verarbeitungskosten.")
st.markdown("---")

# --- SIDEBAR (EINGABEN) ---
st.sidebar.header("⚙️ Parameter Einstellungen")

# 1. Material & Mengen
st.sidebar.subheader("1. Material Input")
menge_input = st.sidebar.number_input("Gesamtmenge pro Jahr (Einheit)", value=1000.0, step=50.0)
einheit = st.sidebar.selectbox("Einheit", ["m³", "Tonnen"])
umrechnungsfaktor = st.sidebar.number_input("Umrechnungsfaktor (t/m³)", value=0.233, format="%.3f", help="Dichte: Wie viel wiegt ein Kubikmeter?")

# Berechnung der Tonnage für weitere Schritte
if einheit == "m³":
    tonnage_gesamt = menge_input * umrechnungsfaktor
    volumen_gesamt = menge_input
else:
    tonnage_gesamt = menge_input
    volumen_gesamt = menge_input / umrechnungsfaktor

st.sidebar.info(f"Berechnete Masse: **{tonnage_gesamt:.2f} t**")

# 2. Logistik
st.sidebar.subheader("2. Logistik")
ladegewicht = st.sidebar.number_input("Ø Ladegewicht pro LKW (t)", value=20.0)
km_entfernung = st.sidebar.slider("Entfernung zum Verwerter (km)", 0, 100, 40)

# Frachttabelle (Simuliert aus CSV Daten)
# Logik: Einfache Staffelung basierend auf CSV Snippet
def get_frachtpreis(km):
    # Preise basierend auf "Cont-Zug" aus der CSV
    if km <= 10: return 116.26
    elif km <= 20: return 124.52
    elif km <= 30: return 138.78
    elif km <= 40: return 153.04
    elif km <= 50: return 165.00 # Geschätzt
    else: return 153.04 + ((km-40)*2.5) # Linearer Anstieg danach

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

# Reihe 1: Top KPIs
col1, col2, col3, col4 = st.columns(4)

col1.metric("Gesamtmenge (t)", f"{tonnage_gesamt:.1f} t", delta_color="off")
col2.metric("Selbstkosten / t", f"{selbstkosten_pro_t:.2f} €", f"{vak_kosten/tonnage_gesamt:.2f} € VAK", delta_color="inverse")
col3.metric("Erlös / t", f"{verkaufspreis_pro_t:.2f} €")
col4.metric("Ergebnis / t", f"{gewinn_pro_t:.2f} €", f"{marge_prozent:.1f}% Marge", delta_color="normal")

st.markdown("---")

# Reihe 2: Grafiken
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("💰 Kostenstruktur")
    # Donut Chart
    labels = ['Logistik', 'Produktion/Maschine', 'VAK (Verwaltung)']
    values = [logistik_kosten_gesamt, produktions_kosten_gesamt, vak_kosten]
    
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
    fig_donut.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_donut, use_container_width=True)

with c2:
    st.subheader("📊 Wasserfall-Analyse (pro Tonne)")
    # Waterfall Chart für Marge
    fig_waterfall = go.Figure(go.Waterfall(
        name = "20", orientation = "v",
        measure = ["relative", "relative", "relative", "total", "relative", "total"],
        x = ["Verkaufspreis", "Logistik", "Produktion", "Deckungsbeitrag 1", "VAK", "EBIT"],
        textposition = "outside",
        text = [f"{x:.2f}" for x in [verkaufspreis_pro_t, -logistik_pro_t, -produktion_pro_t, (verkaufspreis_pro_t - logistik_pro_t - produktion_pro_t), - (vak_kosten/tonnage_gesamt), gewinn_pro_t]],
        y = [verkaufspreis_pro_t, -logistik_pro_t, -produktion_pro_t, 0, -(vak_kosten/tonnage_gesamt), 0],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
    ))
    # Fix Waterfall Totals logic manually for display clarity
    fig_waterfall.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig_waterfall, use_container_width=True)

# Reihe 3: Detaillierte Tabelle & Sensitivität
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
        f"{selbstkosten_ohne_vak/tonnage_gesamt:.2f}", 
        f"{vak_kosten/tonnage_gesamt:.2f}", 
        f"{selbstkosten_pro_t:.2f}", 
        f"{verkaufspreis_pro_t:.2f}", 
        f"{gewinn_pro_t:.2f}"
    ]
}
df_res = pd.DataFrame(data)
st.dataframe(df_res, use_container_width=True)

# Sensitivitätsanalyse (Optional Expander)
with st.expander("📈 Szenario-Analyse: Was passiert, wenn der Dieselpreis steigt?"):
    st.write("Simulation: Auswirkung von +/- 20% Logistikkosten auf das Ergebnis")
    
    range_factors = [0.8, 0.9, 1.0, 1.1, 1.2]
    sim_results = []
    
    for f in range_factors:
        sim_logistik = logistik_kosten_gesamt * f
        sim_gewinn = erloes_gesamt - (sim_logistik + produktions_kosten_gesamt + vak_kosten)
        sim_results.append({"Faktor": f"{int((f-1)*100)}%", "Logistikkosten": sim_logistik, "Ergebnis": sim_gewinn})
    
    df_sim = pd.DataFrame(sim_results)
    st.bar_chart(df_sim.set_index("Faktor")["Ergebnis"])