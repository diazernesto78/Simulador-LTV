"""
Simulador LTV — Tarjetas de Crédito bajo Topes de Tasa
Interfaz Streamlit — EGADE Business School
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from modelo import (
    cargar_datos_macro, cargar_datos_cfpb, calcular_todas_bandas,
    calcular_sensibilidades, BANDAS, BANDAS_ANALISIS, BANDAS_EXCLUIDAS,
    SPREAD_DEFAULTS_BPS, MULT_CHARGEOFF,
)

st.set_page_config(page_title="Simulador LTV — Topes de Tasa", page_icon="💳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    .stApp { background: linear-gradient(180deg, #0a0f1a 0%, #111827 100%); color: #e2e8f0; }
    h1, h2, h3 { font-family: 'DM Sans', sans-serif !important; color: #f1f5f9 !important; }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-size: 1.8rem !important; color: #60a5fa !important; }
    [data-testid="stMetricLabel"] { font-family: 'DM Sans', sans-serif !important; color: #94a3b8 !important; font-size: 0.85rem !important; text-transform: uppercase; letter-spacing: 0.5px; }
    [data-testid="stMetric"] { background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(71, 85, 105, 0.4); border-radius: 12px; padding: 16px 20px; }
    .block-container { padding-top: 2rem; max-width: 1300px; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: rgba(30, 41, 59, 0.5); border-radius: 12px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; color: #94a3b8; font-family: 'DM Sans', sans-serif; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: rgba(59, 130, 246, 0.2) !important; color: #60a5fa !important; }
    .stSlider > div > div > div > div { background: #3b82f6 !important; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    hr { border-color: rgba(71, 85, 105, 0.3) !important; margin: 2rem 0 !important; }
    .stSelectbox > div > div { background: rgba(30, 41, 59, 0.7); border-color: rgba(71, 85, 105, 0.4); }
    .hero-badge { display: inline-block; background: rgba(59, 130, 246, 0.15); color: #60a5fa; padding: 4px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; font-family: 'DM Sans', sans-serif; margin-bottom: 12px; letter-spacing: 0.5px; }
    .hero-title { font-family: 'DM Sans', sans-serif; font-size: 2.4rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; letter-spacing: -0.5px; }
    .hero-subtitle { font-family: 'DM Sans', sans-serif; font-size: 1.05rem; color: #94a3b8; line-height: 1.6; max-width: 800px; }
    .badge-mantener { background: rgba(34, 197, 94, 0.15); color: #4ade80; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; font-family: 'DM Sans', sans-serif; display: inline-block; }
    .badge-migrar { background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; font-family: 'DM Sans', sans-serif; display: inline-block; }
    .badge-excluida { background: rgba(148, 163, 184, 0.15); color: #94a3b8; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; font-family: 'DM Sans', sans-serif; display: inline-block; }
    .note-box { background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 12px; padding: 16px 20px; margin: 16px 0; font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #94a3b8; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# ── Data ──
@st.cache_data
def load_macro(): return cargar_datos_macro()
@st.cache_data
def load_cfpb(): return cargar_datos_cfpb()

datos_macro = load_macro()
df_cfpb = load_cfpb()

BAND_COLORS = {
    "Deep Subprime": "#ef4444", "Subprime": "#f97316",
    "Near-Prime": "#eab308", "Prime": "#22c55e",
    "Prime Plus": "#3b82f6", "Superprime": "#8b5cf6",
}

# ── Header ──
st.markdown('<div class="hero-badge">EGADE BUSINESS SCHOOL · PROYECTO FINAL</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">💳 Simulador LTV — Topes de Tasa</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">¿Qué bandas FICO mantienen un LTV sostenible en crédito revolvente bajo un tope regulatorio temporal, y cuáles deberían migrar a un esquema de pago fijo?</div>', unsafe_allow_html=True)
st.markdown("")
st.markdown("---")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("APR Agregado", f"{datos_macro['APR_pct']:.2f}%")
kpi2.metric("Charge-Off Top 100", f"{datos_macro['ChargeOff_pct']:.2f}%")
kpi3.metric("Treasury 10Y (Rf)", f"{datos_macro['Treasury10Y_pct']:.2f}%")
kpi4.metric("Fondeo SOFR", f"{datos_macro['Fondeo_pct']:.2f}%")
st.caption(f"Datos FRED · Última observación: {datos_macro['fecha']}")
st.markdown("---")

# ── 1. Inputs ──
st.markdown("### ⚙️ Escenario regulatorio")
col_esc1, col_esc2 = st.columns([3, 1])
with col_esc1:
    tope = st.slider("Nivel del tope regulatorio (%)", 10.0, 30.0, 20.0, 0.5,
        help="Tasa máxima permitida durante la vigencia del tope.")
with col_esc2:
    duracion_tope = st.selectbox("Duración (meses)", [3, 6, 12], index=1)

st.markdown("")
with st.expander("🎚️ Spreads por banda (bps sobre Rf) — click para ajustar", expanded=False):
    st.caption(f"Rf actual = {datos_macro['Treasury10Y_pct']:.2f}%. El spread determina el hurdle rate de cada banda.")
    spread_cols = st.columns(4)
    spreads_bps = {}
    for i, banda in enumerate(BANDAS_ANALISIS):
        with spread_cols[i]:
            spreads_bps[banda] = st.slider(banda, 0, 1000, SPREAD_DEFAULTS_BPS[banda], 25, key=f"spread_{banda}")
    # Defaults for excluded bands (not shown as sliders)
    for banda in BANDAS_EXCLUIDAS:
        spreads_bps[banda] = SPREAD_DEFAULTS_BPS[banda]

st.markdown("---")

# ── Cálculo ──
df_resultados = calcular_todas_bandas(datos_macro, df_cfpb, tope, duracion_tope, spreads_bps)
df_analisis = df_resultados[df_resultados["Decision"] != "FUERA DE ALCANCE"]
df_excluidas = df_resultados[df_resultados["Decision"] == "FUERA DE ALCANCE"]

# ── 2. Decision cards — 4 bandas en análisis ──
st.markdown("### 📊 Decisión por banda FICO")
card_cols = st.columns(4)

for i, (_, row) in enumerate(df_analisis.iterrows()):
    banda = row["Banda"]
    color = BAND_COLORS[banda]
    badge = "badge-mantener" if row["Decision"] == "MANTENER" else "badge-migrar"
    badge_text = "✅ MANTENER" if row["Decision"] == "MANTENER" else "🔴 MIGRAR"
    margen_color = "#4ade80" if row["Margen_USD"] >= 0 else "#f87171"

    with card_cols[i]:
        st.markdown(f"""
        <div style="background:rgba(30,41,59,0.6);border:1px solid {color}40;border-top:3px solid {color};
            border-radius:12px;padding:16px 14px;text-align:center;min-height:240px;">
            <div style="font-family:'DM Sans';font-weight:700;color:{color};font-size:0.9rem;margin-bottom:8px;">{banda}</div>
            <div class="{badge}" style="margin-bottom:12px;">{badge_text}</div>
            <div style="font-family:'JetBrains Mono';font-size:0.8rem;color:#94a3b8;line-height:2;">
                <div>LTV <span style="color:#e2e8f0;font-weight:500;">${row["LTV_USD"]:,.0f}</span></div>
                <div>Hurdle <span style="color:#e2e8f0;font-weight:500;">${row["Hurdle_USD"]:,.0f}</span></div>
                <div>Margen <span style="color:{margen_color};font-weight:600;">${row["Margen_USD"]:,.0f}</span></div>
                <div style="margin-top:4px;font-size:0.7rem;color:#64748b;">{row["Pct_Revolvers"]:.0%} rev · ${row["Saldo_USD"]:,.0f}</div>
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("")
n_mantener = (df_analisis["Decision"] == "MANTENER").sum()
n_migrar = (df_analisis["Decision"] == "MIGRAR").sum()
col_s1, col_s2 = st.columns(2)
col_s1.metric("Bandas revolventes viables", f"{n_mantener} de 4")
col_s2.metric("Bandas que migran a pago fijo", f"{n_migrar} de 4")

# ── Bandas excluidas ──
st.markdown("")
exc_cols = st.columns(2)
for i, (_, row) in enumerate(df_excluidas.iterrows()):
    banda = row["Banda"]
    color = BAND_COLORS[banda]
    with exc_cols[i]:
        st.markdown(f"""
        <div style="background:rgba(30,41,59,0.3);border:1px solid rgba(71,85,105,0.3);border-top:3px solid {color}40;
            border-radius:12px;padding:14px;text-align:center;">
            <div style="font-family:'DM Sans';font-weight:700;color:{color}80;font-size:0.85rem;margin-bottom:6px;">{banda}</div>
            <div class="badge-excluida">FUERA DE ALCANCE</div>
            <div style="font-family:'JetBrains Mono';font-size:0.75rem;color:#64748b;margin-top:8px;">
                {row["Pct_Revolvers"]:.0%} revolvers · ${row["Saldo_USD"]:,.0f} · Totaleros
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("""
<div class="note-box">
    <strong>¿Por qué Prime Plus y Superprime están fuera del análisis?</strong><br>
    Estos segmentos son mayoritariamente "totaleros" — pagan su saldo completo cada mes (solo 42% y 20% revuelven, respectivamente).
    Su rentabilidad para el banco proviene de ingresos transaccionales (interchange, anualidad) que no están capturados en este modelo,
    el cual mide exclusivamente el valor presente de ingresos por intereses revolventes.<br><br>
    No existen datos públicos de interchange por banda FICO. Para un banco con acceso a su información interna de comisiones
    y volumen transaccional por segmento, este modelo funcionaría para las 6 bandas sin modificación.
</div>
""", unsafe_allow_html=True)

with st.expander("📋 Tabla detallada — todas las bandas", expanded=False):
    df_display = df_resultados.copy()
    df_display["Decisión"] = df_display["Decision"].apply(lambda d: "✅ MANTENER" if d == "MANTENER" else ("🔴 MIGRAR" if d == "MIGRAR" else "⚪ FUERA DE ALCANCE"))
    df_display["LTV ($)"] = df_display["LTV_USD"].apply(lambda x: f"${x:,.0f}")
    df_display["Hurdle ($)"] = df_display["Hurdle_USD"].apply(lambda x: f"${x:,.0f}")
    df_display["Margen ($)"] = df_display["Margen_USD"].apply(lambda x: f"${x:,.0f}")
    df_display["Tasa Ef. M1"] = df_display["Tasa_Efectiva_M1_pct"].apply(lambda x: f"{x:.1f}%")
    df_display["r Desc."] = df_display["r_Descuento_pct"].apply(lambda x: f"{x:.2f}%")
    df_display["CO (%)"] = df_display["ChargeOff_Banda_pct"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(df_display[["Banda","Saldo_USD","Pct_Revolvers","APR_Banda_pct","CO (%)","Tasa Ef. M1","r Desc.","LTV ($)","Hurdle ($)","Margen ($)","Decisión"]].rename(
        columns={"Saldo_USD":"Saldo ($)","Pct_Revolvers":"% Rev","APR_Banda_pct":"APR (%)"}
    ), use_container_width=True, hide_index=True)

st.markdown("---")

# ── 3. Gráfica LTV vs Hurdle — solo bandas en análisis ──
st.markdown("### 📈 LTV vs Hurdle por banda")

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    name="LTV (VP flujos netos a 60m)",
    x=df_analisis["Banda"], y=df_analisis["LTV_USD"],
    marker_color=[BAND_COLORS[b] for b in df_analisis["Banda"]],
    marker_line=dict(width=0),
    text=df_analisis["LTV_USD"].apply(lambda x: f"${x:,.0f}"),
    textposition="outside",
    textfont=dict(size=12, family="JetBrains Mono", color="#e2e8f0"),
    opacity=0.9,
))
fig_bar.add_trace(go.Scatter(
    name="Hurdle (rendimiento mínimo exigido)",
    x=df_analisis["Banda"], y=df_analisis["Hurdle_USD"],
    mode="markers+lines+text",
    marker=dict(size=10, color="#fbbf24", symbol="diamond", line=dict(width=2, color="#1e293b")),
    line=dict(color="#fbbf24", width=2.5, dash="dash"),
    text=df_analisis["Hurdle_USD"].apply(lambda x: f"${x:,.0f}"),
    textposition="top center",
    textfont=dict(size=11, family="JetBrains Mono", color="#fbbf24"),
))
fig_bar.update_layout(
    yaxis_title="USD (valor presente a 60 meses)", xaxis_title="",
    height=520,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
        font=dict(family="DM Sans", size=12, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94a3b8"),
    xaxis=dict(tickfont=dict(size=12, color="#e2e8f0")),
    yaxis=dict(gridcolor="rgba(71,85,105,0.3)", zerolinecolor="rgba(71,85,105,0.5)", tickprefix="$", tickformat=","),
    margin=dict(t=60, b=40),
)
st.plotly_chart(fig_bar, use_container_width=True)
st.markdown("---")

# ── 4. Heatmap — solo bandas en análisis ──
st.markdown("### 🗺️ Mapa de sensibilidades")
st.markdown(
    '<span style="color:#94a3b8;font-size:0.9rem;">'
    '<span style="color:#4ade80;">■</span> MANTENER · '
    '<span style="color:#f87171;">■</span> MIGRAR · '
    'Valor = margen LTV − Hurdle (USD) · Solo bandas Deep Subprime a Prime</span>', unsafe_allow_html=True)

with st.spinner("Calculando sensibilidades..."):
    niveles = list(np.arange(10, 31, 1))
    df_sens = calcular_sensibilidades(datos_macro, df_cfpb, spreads_bps, niveles_tope=niveles, duraciones=[3, 6, 12])

# Filter to only analysis bands
df_sens_filt = df_sens[df_sens["Banda"].isin(BANDAS_ANALISIS)]

tabs_dur = st.tabs([f"⏱️ {d} meses" for d in [3, 6, 12]])
for tab, dur in zip(tabs_dur, [3, 6, 12]):
    with tab:
        df_d = df_sens_filt[df_sens_filt["Duracion_meses"] == dur]
        pivot = df_d.pivot_table(index="Tope_pct", columns="Banda", values="Margen_USD")[BANDAS_ANALISIS]

        fig_hm = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns.tolist(),
            y=[f"{int(t)}%" for t in pivot.index],
            colorscale=[[0,"#991b1b"],[0.3,"#ef4444"],[0.5,"#1e293b"],[0.7,"#22c55e"],[1,"#166534"]],
            zmid=0,
            text=np.round(pivot.values, 0).astype(int).astype(str),
            texttemplate="%{text}",
            textfont=dict(size=11, family="JetBrains Mono", color="#e2e8f0"),
            colorbar=dict(title=dict(text="Margen ($)", font=dict(color="#94a3b8")),
                tickfont=dict(color="#94a3b8"), tickprefix="$", bgcolor="rgba(0,0,0,0)"),
            hovertemplate="<b>%{x}</b><br>Tope: %{y}<br>Margen: $%{z:,.0f}<extra></extra>",
            xgap=2, ygap=2,
        ))
        fig_hm.update_layout(
            yaxis_title="Nivel del tope (%)", xaxis_title="", height=600,
            yaxis=dict(dtick=1, tickfont=dict(size=11)),
            xaxis=dict(tickfont=dict(size=12, color="#e2e8f0")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans", color="#94a3b8"), margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_hm, use_container_width=True)

st.markdown("---")

# ── 5. Calibración ──
st.markdown("### 🔬 Datos de calibración")

with st.expander("Datos CFPB por banda FICO (2024)", expanded=False):
    df_cfpb_display = df_cfpb[["Rango_Score","Pct_Revolvers_2024","Saldo_Promedio_GP_2024_USD",
        "APR_Promedio_NuevasCuentas_2024_pct","Payment_Rate_2024_pct"]].copy()
    df_cfpb_display.index.name = "Banda"
    df_cfpb_display.columns = ["Rango Score","% Revolvers","Saldo Promedio ($)","APR Nuevas Cuentas (%)","Payment Rate (%)"]
    st.dataframe(df_cfpb_display, use_container_width=True)

with st.expander("Multiplicadores de charge-off por banda", expanded=False):
    st.dataframe(pd.DataFrame({
        "Banda": BANDAS,
        "Multiplicador": [f"{MULT_CHARGEOFF[b]:.2f}×" for b in BANDAS],
        "Charge-Off Implícito": [f"{datos_macro['ChargeOff_pct']*MULT_CHARGEOFF[b]:.2f}%" for b in BANDAS],
    }), use_container_width=True, hide_index=True)

with st.expander("Supuestos y limitaciones del modelo", expanded=False):
    st.markdown("""
**Supuestos:**
1. El comportamiento del cliente (% revolvers) **no cambia** durante la vigencia del tope
2. La tasa de pérdida neta base **no cambia** durante la vigencia del tope
3. Portafolios con perfil de **banca Tier 1** en Estados Unidos
4. Datos FICO del CFPB (2024) como **parámetros fijos**
5. Rf y fondeo: **última observación** disponible en FRED
6. Horizonte de análisis: **60 meses**

**Limitaciones:**
- El modelo mide exclusivamente **ingresos por intereses revolventes**. No incluye interchange, anualidades ni otros fees.
- Las bandas Prime Plus y Superprime se excluyen del análisis de decisión porque su rentabilidad depende de ingresos transaccionales no capturados.
- Se intentó incorporar comisiones usando el Costo Total de Crédito del CFPB, pero esta métrica no captura adecuadamente el ingreso del emisor en segmentos premium (el costo total resulta inferior al APR por la dilución del promedio entre totaleros).
- No existen datos públicos de interchange por banda FICO. Una extensión futura requeriría datos internos del banco o datos de la Fed (Regulation II) combinados con purchase volume por banda del CFPB.
- Para un banco con acceso a sus datos internos de comisiones y volumen transaccional por segmento, este modelo cubriría las 6 bandas sin modificación estructural.
    """)

# ── Footer ──
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#475569;font-size:0.8rem;font-family:DM Sans;padding:10px 0 30px;">'
    'Simulador LTV · Proyecto Final · Maestría en Finanzas EGADE Business School<br>'
    'Fuentes: FRED (TERMCBCCALLNS, CORCCT100S, DGS10, SOFR) · CFPB Credit Card Market Report 2025'
    '</div>', unsafe_allow_html=True)
