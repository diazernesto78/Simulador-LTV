"""
Simulador LTV — Tarjetas de Crédito bajo Topes de Tasa
Interfaz Streamlit

Pantallas:
1. Panel de inputs (sliders de escenario y spreads por banda)
2. Tabla de resultados (LTV vs hurdle por banda, semáforo)
3. Gráfica LTV vs hurdle (barras por banda)
4. Heatmap de sensibilidades (nivel tope × duración)
5. Datos de calibración (valores del Excel)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from modelo import (
    cargar_datos_macro,
    cargar_datos_cfpb,
    calcular_todas_bandas,
    calcular_sensibilidades,
    BANDAS,
    SPREAD_DEFAULTS_BPS,
    MULT_CHARGEOFF,
)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Simulador LTV — Topes de Tasa",
    page_icon="💳",
    layout="wide",
)

# ──────────────────────────────────────────────
# Carga de datos (cacheada)
# ──────────────────────────────────────────────

@st.cache_data
def load_macro():
    return cargar_datos_macro()

@st.cache_data
def load_cfpb():
    return cargar_datos_cfpb()

datos_macro = load_macro()
df_cfpb = load_cfpb()

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────

st.title("💳 Simulador LTV — Tarjetas de Crédito bajo Topes de Tasa")
st.markdown(
    "¿Qué bandas FICO mantienen un LTV sostenible bajo un tope regulatorio temporal, "
    "y cuáles deberían migrar a pago fijo?"
)
st.divider()

# ──────────────────────────────────────────────
# 1. Panel de inputs
# ──────────────────────────────────────────────

st.header("1 · Escenario regulatorio")

col_esc1, col_esc2 = st.columns(2)

with col_esc1:
    tope = st.slider(
        "Nivel del tope regulatorio (%)",
        min_value=10.0,
        max_value=30.0,
        value=20.0,
        step=0.5,
        help="Tasa máxima permitida durante la vigencia del tope",
    )

with col_esc2:
    duracion_tope = st.selectbox(
        "Duración del tope (meses)",
        options=[3, 6, 12],
        index=1,
        help="Período durante el cual aplica el tope regulatorio",
    )

st.subheader("Spreads por banda (bps sobre Rf)")
st.caption(
    f"Rf actual (Treasury 10Y): **{datos_macro['Treasury10Y_pct']:.2f}%** — "
    "El spread determina la tasa de descuento (hurdle rate) de cada banda."
)

spread_cols = st.columns(6)
spreads_bps = {}
for i, banda in enumerate(BANDAS):
    with spread_cols[i]:
        spreads_bps[banda] = st.slider(
            banda,
            min_value=0,
            max_value=1000,
            value=SPREAD_DEFAULTS_BPS[banda],
            step=25,
            key=f"spread_{banda}",
        )

st.divider()

# ──────────────────────────────────────────────
# Cálculo principal
# ──────────────────────────────────────────────

df_resultados = calcular_todas_bandas(
    datos_macro, df_cfpb, tope, duracion_tope, spreads_bps
)

# ──────────────────────────────────────────────
# 2. Tabla de resultados
# ──────────────────────────────────────────────

st.header("2 · Resultados por banda")

def semaforo(decision):
    return "✅ MANTENER" if decision == "MANTENER" else "🔴 MIGRAR"

df_display = df_resultados.copy()
df_display["Decisión"] = df_display["Decision"].apply(semaforo)
df_display["LTV ($)"] = df_display["LTV_USD"].apply(lambda x: f"${x:,.0f}")
df_display["Hurdle ($)"] = df_display["Hurdle_USD"].apply(lambda x: f"${x:,.0f}")
df_display["Margen ($)"] = df_display["Margen_USD"].apply(lambda x: f"${x:,.0f}")
df_display["Tasa Efectiva M1 (%)"] = df_display["Tasa_Efectiva_M1_pct"].apply(lambda x: f"{x:.1f}%")
df_display["r Descuento (%)"] = df_display["r_Descuento_pct"].apply(lambda x: f"{x:.2f}%")
df_display["Charge-Off (%)"] = df_display["ChargeOff_Banda_pct"].apply(lambda x: f"{x:.2f}%")

cols_show = [
    "Banda", "Saldo_USD", "Pct_Revolvers", "APR_Banda_pct",
    "Charge-Off (%)", "Tasa Efectiva M1 (%)", "r Descuento (%)",
    "LTV ($)", "Hurdle ($)", "Margen ($)", "Decisión"
]
df_show = df_display[cols_show].rename(columns={
    "Saldo_USD": "Saldo ($)",
    "Pct_Revolvers": "% Revolvers",
    "APR_Banda_pct": "APR Banda (%)",
})

st.dataframe(df_show, use_container_width=True, hide_index=True)

# Resumen rápido
n_mantener = (df_resultados["Decision"] == "MANTENER").sum()
n_migrar = (df_resultados["Decision"] == "MIGRAR").sum()

col_m1, col_m2 = st.columns(2)
col_m1.metric("Bandas que se mantienen", f"{n_mantener} de 6", delta=None)
col_m2.metric("Bandas que migran a pago fijo", f"{n_migrar} de 6", delta=None)

st.divider()

# ──────────────────────────────────────────────
# 3. Gráfica LTV vs Hurdle
# ──────────────────────────────────────────────

st.header("3 · LTV vs Hurdle por banda")

fig_bar = go.Figure()

colors_ltv = [
    "#2ecc71" if d == "MANTENER" else "#e74c3c"
    for d in df_resultados["Decision"]
]

fig_bar.add_trace(go.Bar(
    name="LTV (VP flujos netos)",
    x=df_resultados["Banda"],
    y=df_resultados["LTV_USD"],
    marker_color=colors_ltv,
    text=df_resultados["LTV_USD"].apply(lambda x: f"${x:,.0f}"),
    textposition="outside",
))

fig_bar.add_trace(go.Scatter(
    name="Hurdle (rendimiento mínimo exigido)",
    x=df_resultados["Banda"],
    y=df_resultados["Hurdle_USD"],
    mode="markers+lines",
    marker=dict(size=12, color="#f39c12", symbol="diamond"),
    line=dict(color="#f39c12", width=2, dash="dash"),
    text=df_resultados["Hurdle_USD"].apply(lambda x: f"${x:,.0f}"),
    textposition="top center",
))

fig_bar.update_layout(
    yaxis_title="USD (valor presente 60 meses)",
    xaxis_title="Banda FICO",
    barmode="group",
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    plot_bgcolor="rgba(0,0,0,0)",
)
fig_bar.update_yaxes(gridcolor="rgba(128,128,128,0.2)")

st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ──────────────────────────────────────────────
# 4. Heatmap de sensibilidades
# ──────────────────────────────────────────────

st.header("4 · Heatmap de sensibilidades")
st.caption(
    "Verde = MANTENER revolvente · Rojo = MIGRAR a pago fijo. "
    "Cada celda muestra el margen (LTV − Hurdle) en USD."
)

with st.spinner("Calculando sensibilidades..."):
    niveles = list(np.arange(10, 31, 1))
    df_sens = calcular_sensibilidades(
        datos_macro, df_cfpb, spreads_bps,
        niveles_tope=niveles,
        duraciones=[3, 6, 12],
    )

# Un heatmap por duración
tabs_dur = st.tabs([f"Duración: {d} meses" for d in [3, 6, 12]])

for tab, dur in zip(tabs_dur, [3, 6, 12]):
    with tab:
        df_d = df_sens[df_sens["Duracion_meses"] == dur]
        pivot = df_d.pivot_table(
            index="Tope_pct", columns="Banda", values="Margen_USD"
        )
        pivot = pivot[BANDAS]

        # Color: verde positivo, rojo negativo
        fig_hm = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[f"{int(t)}%" for t in pivot.index],
            colorscale=[
                [0, "#e74c3c"],
                [0.5, "#ffeaa7"],
                [1, "#2ecc71"],
            ],
            zmid=0,
            text=np.round(pivot.values, 0).astype(int).astype(str),
            texttemplate="%{text}",
            textfont={"size": 11},
            colorbar=dict(title="Margen ($)"),
            hovertemplate="Banda: %{x}<br>Tope: %{y}<br>Margen: $%{z:,.0f}<extra></extra>",
        ))

        fig_hm.update_layout(
            yaxis_title="Nivel del tope (%)",
            xaxis_title="Banda FICO",
            height=550,
            yaxis=dict(dtick=1),
        )

        st.plotly_chart(fig_hm, use_container_width=True)

st.divider()

# ──────────────────────────────────────────────
# 5. Datos de calibración
# ──────────────────────────────────────────────

st.header("5 · Datos de calibración")

st.subheader("Datos macroeconómicos (última observación)")
col_c1, col_c2, col_c3, col_c4 = st.columns(4)
col_c1.metric("APR agregado", f"{datos_macro['APR_pct']:.2f}%")
col_c2.metric("Charge-Off (Top 100)", f"{datos_macro['ChargeOff_pct']:.2f}%")
col_c3.metric("Treasury 10Y (Rf)", f"{datos_macro['Treasury10Y_pct']:.2f}%")
col_c4.metric("Fondeo (SOFR)", f"{datos_macro['Fondeo_pct']:.2f}%")
st.caption(f"Fecha de última observación: {datos_macro['fecha']}")

st.subheader("Datos CFPB por banda FICO (2024)")
df_cfpb_display = df_cfpb[
    ["Rango_Score", "Pct_Revolvers_2024", "Saldo_Promedio_GP_2024_USD",
     "APR_Promedio_NuevasCuentas_2024_pct", "Payment_Rate_2024_pct"]
].copy()
df_cfpb_display.index.name = "Banda"
df_cfpb_display.columns = [
    "Rango Score", "% Revolvers", "Saldo Promedio ($)", "APR Nuevas Cuentas (%)", "Payment Rate (%)"
]
st.dataframe(df_cfpb_display, use_container_width=True)

st.subheader("Multiplicadores de charge-off por banda")
df_mult = pd.DataFrame({
    "Banda": BANDAS,
    "Multiplicador": [MULT_CHARGEOFF[b] for b in BANDAS],
    "Charge-Off Implícito (%)": [round(datos_macro["ChargeOff_pct"] * MULT_CHARGEOFF[b], 2) for b in BANDAS],
})
st.dataframe(df_mult, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────

st.divider()
st.caption(
    "Simulador LTV · Proyecto Final Maestría en Finanzas EGADE · "
    "Fuentes: FRED (TERMCBCCALLNS, CORCCT100S, DGS10, SOFR), CFPB Credit Card Market Report 2025"
)
