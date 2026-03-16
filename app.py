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
    SPREAD_DEFAULTS_BPS, MULT_CHARGEOFF_DEFAULTS,
)

st.set_page_config(page_title="Simulador LTV — Topes de Tasa", page_icon="💳", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
    .stApp { background: linear-gradient(180deg, #0a0f1a 0%, #111827 100%); color: #f1f5f9; }

    /* Sidebar - dark background, all text white */
    [data-testid="stSidebar"] { background: #0f172a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSidebar"] .stSlider > div > div > div > div { background: #3b82f6 !important; }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(251, 191, 36, 0.15) !important;
        border: 2px solid #fbbf24 !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #ffffff !important; font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stSidebar"] .stCaption p { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stRadio > div { flex-direction: row !important; gap: 8px !important; }
    [data-testid="stSidebar"] .stRadio label { 
        background: rgba(30, 41, 59, 0.8) !important; 
        border: 1px solid rgba(71, 85, 105, 0.5) !important;
        border-radius: 8px !important; padding: 6px 12px !important;
        color: #ffffff !important; font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stRadio [data-checked="true"] label {
        background: rgba(59, 130, 246, 0.3) !important;
        border-color: #3b82f6 !important;
    }
    [data-testid="stSidebar"] .stTooltipIcon svg { color: #60a5fa !important; }
    /* Tooltip popup */
    [data-testid="stTooltipContent"] { background: #1e293b !important; color: #ffffff !important; border: 1px solid #3b82f6 !important; }
    [data-testid="stTooltipContent"] p { color: #ffffff !important; }
    div[data-baseweb="tooltip"] div { background: #1e293b !important; color: #ffffff !important; }
    div[data-baseweb="tooltip"] div p { color: #ffffff !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(71, 85, 105, 0.5) !important; }

    /* Typography - bigger, clearer, WHITE not grey */
    h1, h2, h3 { font-family: 'DM Sans', sans-serif !important; color: #ffffff !important; }
    p, li, span, div { font-size: 1rem; color: #f1f5f9; }

    /* Metrics */
    [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 2rem !important; color: #60a5fa !important; }
    [data-testid="stMetricLabel"] { font-family: 'DM Sans', sans-serif !important; color: #e2e8f0 !important; font-size: 0.9rem !important; text-transform: uppercase; letter-spacing: 0.5px; }
    [data-testid="stMetric"] { background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(71, 85, 105, 0.4); border-radius: 12px; padding: 18px 22px; }

    .block-container { padding-top: 2rem; max-width: 1300px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: rgba(30, 41, 59, 0.5); border-radius: 12px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; color: #e2e8f0; font-family: 'DM Sans', sans-serif; font-weight: 600; font-size: 1rem; }
    .stTabs [aria-selected="true"] { background: rgba(59, 130, 246, 0.25) !important; color: #60a5fa !important; }

    .stSlider > div > div > div > div { background: #3b82f6 !important; }
    .stSlider label { color: #ffffff !important; font-size: 0.95rem !important; font-weight: 600 !important; }
    .stSlider [data-testid="stTickBarMin"], .stSlider [data-testid="stTickBarMax"] { color: #cbd5e1 !important; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    hr { border-color: rgba(71, 85, 105, 0.3) !important; margin: 2rem 0 !important; }

    /* ALL labels and text WHITE */
    label, .stTextInput label, .stSlider label, .stNumberInput label { color: #ffffff !important; font-size: 0.95rem !important; }
    .stMarkdown p { color: #e2e8f0 !important; }
    [data-testid="stWidgetLabel"] p { color: #ffffff !important; font-weight: 500 !important; }

    /* Selectbox - VISIBLE */
    .stSelectbox > div > div {
        background: rgba(251, 191, 36, 0.15) !important;
        border: 2px solid #fbbf24 !important;
        color: #fbbf24 !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    .stSelectbox label { color: #fbbf24 !important; font-weight: 600 !important; font-size: 1rem !important; }

    /* Expander - WHITE */
    .streamlit-expanderHeader { font-size: 1.05rem !important; color: #ffffff !important; font-weight: 600 !important; }
    [data-testid="stExpander"] summary span { color: #ffffff !important; }
    [data-testid="stExpander"] summary p { color: #ffffff !important; }

    /* Caption - visible */
    .stCaption p { color: #e2e8f0 !important; font-size: 0.92rem !important; }

    /* Hero */
    .hero-badge { display: inline-block; background: rgba(59, 130, 246, 0.15); color: #60a5fa; padding: 6px 16px; border-radius: 20px; font-size: 0.85rem; font-weight: 700; font-family: 'DM Sans', sans-serif; margin-bottom: 14px; letter-spacing: 0.5px; }
    .hero-title { font-family: 'DM Sans', sans-serif; font-size: 2.8rem; font-weight: 700; color: #f1f5f9; margin-bottom: 6px; letter-spacing: -0.5px; }
    .hero-subtitle { font-family: 'DM Sans', sans-serif; font-size: 1.15rem; color: #e2e8f0; line-height: 1.7; max-width: 850px; }

    /* Section titles */
    .section-title {
        font-family: 'DM Sans', sans-serif; font-size: 1.6rem; font-weight: 700; color: #f1f5f9;
        padding: 12px 0 4px 0; border-bottom: 3px solid #3b82f6; margin-bottom: 16px; display: inline-block;
    }

    /* Badges */
    .badge-mantener { background: rgba(34, 197, 94, 0.2); color: #4ade80; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem; font-family: 'DM Sans', sans-serif; display: inline-block; }
    .badge-migrar { background: rgba(239, 68, 68, 0.2); color: #f87171; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem; font-family: 'DM Sans', sans-serif; display: inline-block; }
    .badge-excluida { background: rgba(148, 163, 184, 0.15); color: #94a3b8; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem; font-family: 'DM Sans', sans-serif; display: inline-block; }

    .note-box { background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 12px; padding: 18px 22px; margin: 16px 0; font-family: 'DM Sans', sans-serif; font-size: 0.95rem; color: #e2e8f0; line-height: 1.7; }
    .note-box strong { color: #60a5fa; }
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

# ══════════════════════════════════════
# 1. INPUTS — EN SIDEBAR
# ══════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Escenario Regulatorio")
    tope = st.slider("Nivel del tope regulatorio (%)", 10.0, 30.0, 20.0, 0.5,
        help="Propuesta Trump: 10%. Propuesta Sanders-Hawley (S.381): 10%. APR promedio actual de la industria: 21.39%. Un tope por debajo del APR de una banda comprime su margen financiero.")
    duracion_tope = st.radio("\u23F1\uFE0F Duraci\u00F3n del tope", [3, 6, 9, 12], index=1,
        format_func=lambda x: f"{x} meses", horizontal=True)

    st.markdown("---")
    st.markdown("### \U0001F39A\uFE0F Spreads (bps sobre Rf)")
    st.caption(f"Rf = {datos_macro['Treasury10Y_pct']:.2f}%")
    spreads_bps = {}
    spread_helps = {
        "Deep Subprime": "Default 800 bps. Hurdle impl\u00EDcito: 12.1%. Refleja la prima de riesgo m\u00E1s alta del portafolio. Un banco Tier 1 exige mayor rendimiento para compensar el charge-off de ~10%.",
        "Subprime": "Default 650 bps. Hurdle impl\u00EDcito: 10.6%. Riesgo alto pero menor que Deep Subprime. El banco a\u00FAn exige prima significativa.",
        "Near-Prime": "Default 450 bps. Hurdle impl\u00EDcito: 8.6%. Segmento en transici\u00F3n con riesgo moderado. Prima de riesgo intermedia.",
        "Prime": "Default 300 bps. Hurdle impl\u00EDcito: 7.1%. Segmento est\u00E1ndar, menor prima. Es la banda m\u00E1s resiliente del portafolio.",
    }
    for b in BANDAS_ANALISIS:
        spreads_bps[b] = st.slider(b, 0, 1000, SPREAD_DEFAULTS_BPS[b], 25, key=f"sp_{b}",
            help=spread_helps[b])
    for b in BANDAS_EXCLUIDAS:
        spreads_bps[b] = SPREAD_DEFAULTS_BPS[b]

    st.markdown("---")
    st.markdown("### \U0001F4CA Multiplicadores Charge-Off")
    st.caption(f"Base FRED: {datos_macro['ChargeOff_pct']:.2f}%")
    mult_co = {}
    co_helps = {
        "Deep Subprime": f"Default 2.5\u00D7 = {datos_macro['ChargeOff_pct']*2.5:.1f}% charge-off. Un banco Tier 1 t\u00EDpicamente no origina en este segmento. B\u00E1jalo a 2.0\u00D7 para simular mejor gesti\u00F3n de riesgo.",
        "Subprime": f"Default 2.0\u00D7 = {datos_macro['ChargeOff_pct']*2.0:.1f}% charge-off. Alto riesgo pero manejable con pol\u00EDticas de cobranza agresivas.",
        "Near-Prime": f"Default 1.4\u00D7 = {datos_macro['ChargeOff_pct']*1.4:.1f}% charge-off. Riesgo moderado. Clientes reconstruyendo historial o j\u00F3venes con historial corto.",
        "Prime": f"Default 0.8\u00D7 = {datos_macro['ChargeOff_pct']*0.8:.1f}% charge-off. Bajo riesgo. Es el segmento que absorbe mejor los topes de tasa.",
    }
    for b in BANDAS_ANALISIS:
        mult_co[b] = st.slider(f"{b}", 0.1, 4.0, MULT_CHARGEOFF_DEFAULTS[b], 0.1, key=f"mc_{b}",
            help=co_helps[b])
    for b in BANDAS_EXCLUIDAS:
        mult_co[b] = MULT_CHARGEOFF_DEFAULTS[b]

    st.markdown("---")
    st.markdown("### \U0001F4A5 Choque de Pago")
    plazo_amort = st.radio("Plazo amortizaci\u00F3n", [12, 24, 36, 48, 60], index=2,
        format_func=lambda x: f"{x} meses", horizontal=True)
    sensibilidad_choque = st.slider("Sensibilidad al choque", 0.01, 0.20, 0.05, 0.01,
        help="Controla cu\u00E1ntos clientes adicionales caen en default por cada m\u00FAltiplo de choque. Ejemplo: con sensibilidad 0.05 y choque de 5\u00D7, el default adicional es 20 puntos porcentuales sobre la tasa base.")
    severidad = st.slider("Severidad de p\u00E9rdida (%)", 20.0, 100.0, 80.0, 5.0,
        help="Complemento de la tasa de recuperaci\u00F3n hist\u00F3rica. Con 80% de severidad, el banco solo recupera 20 centavos por d\u00F3lar en default. Un Tier 1 con buena cobranza opera entre 50-60% de severidad.")

# ══════════════════════════════════════
# CÁLCULO
# ══════════════════════════════════════
df_resultados = calcular_todas_bandas(datos_macro, df_cfpb, tope, duracion_tope, spreads_bps, mult_co)
df_analisis = df_resultados[df_resultados["Decision"] != "FUERA DE ALCANCE"]
df_excluidas = df_resultados[df_resultados["Decision"] == "FUERA DE ALCANCE"]

# ══════════════════════════════════════
# 2. DECISIÓN POR BANDA
# ══════════════════════════════════════
st.markdown('<div class="section-title">📊 Decisión por Banda FICO</div>', unsafe_allow_html=True)
st.markdown("")
card_cols = st.columns(4)

for i, (_, row) in enumerate(df_analisis.iterrows()):
    banda = row["Banda"]
    color = BAND_COLORS[banda]
    badge = "badge-mantener" if row["Decision"] == "MANTENER" else "badge-migrar"
    badge_text = "✅ MANTENER" if row["Decision"] == "MANTENER" else "🔴 MIGRAR"
    ltv_show = round(row["LTV_USD"])
    hur_show = round(row["Hurdle_USD"])
    mar_show = ltv_show - hur_show
    mc = "#4ade80" if mar_show >= 0 else "#f87171"
    co_pct = row["ChargeOff_Banda_pct"]

    with card_cols[i]:
        st.markdown(f"""
        <div style="background:rgba(30,41,59,0.6);border:1px solid {color}50;border-top:4px solid {color};
            border-radius:14px;padding:18px 16px;text-align:center;min-height:280px;">
            <div style="font-family:'DM Sans';font-weight:700;color:{color};font-size:1.05rem;margin-bottom:10px;">{banda}</div>
            <div class="{badge}" style="margin-bottom:14px;">{badge_text}</div>
            <div style="font-family:'IBM Plex Mono';font-size:0.95rem;color:#cbd5e1;line-height:2.2;">
                <div>LTV <span style="color:#f1f5f9;font-weight:600;">${ltv_show:,.0f}</span></div>
                <div>Hurdle <span style="color:#f1f5f9;font-weight:600;">${hur_show:,.0f}</span></div>
                <div>Margen <span style="color:{mc};font-weight:700;">${mar_show:,.0f}</span></div>
                <div style="margin-top:6px;font-size:0.8rem;color:#cbd5e1;">
                    {row["Pct_Revolvers"]:.0%} rev · ${row["Saldo_USD"]:,.0f} · CO {co_pct:.1f}%
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("")
cs1, cs2 = st.columns(2)
cs1.metric("Bandas revolventes viables", f"{(df_analisis['Decision']=='MANTENER').sum()} de 4")
cs2.metric("Bandas que migran a pago fijo", f"{(df_analisis['Decision']=='MIGRAR').sum()} de 4")

# ── Bandas excluidas ──
st.markdown("")
ec = st.columns(2)
for i, (_, row) in enumerate(df_excluidas.iterrows()):
    b, color = row["Banda"], BAND_COLORS[row["Banda"]]
    with ec[i]:
        st.markdown(f"""
        <div style="background:rgba(30,41,59,0.3);border:1px solid rgba(71,85,105,0.3);border-top:3px solid {color}50;
            border-radius:12px;padding:14px;text-align:center;">
            <div style="font-family:'DM Sans';font-weight:700;color:{color}90;font-size:0.95rem;margin-bottom:6px;">{b}</div>
            <div class="badge-excluida">FUERA DE ALCANCE</div>
            <div style="font-family:'IBM Plex Mono';font-size:0.8rem;color:#cbd5e1;margin-top:8px;">
                {row["Pct_Revolvers"]:.0%} revolvers · ${row["Saldo_USD"]:,.0f} · Totaleros
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("""
<div class="note-box">
    <strong>¿Por qué Prime Plus y Superprime están fuera del análisis?</strong><br>
    Son mayoritariamente totaleros (42% y 20% revuelven). Su rentabilidad proviene de interchange y anualidad,
    ingresos no capturados en este modelo. No existen datos públicos de interchange por banda FICO.
    Para un banco con datos internos, el modelo funcionaría para las 6 bandas sin modificación.
</div>
""", unsafe_allow_html=True)

with st.expander("📋 Tabla detallada — todas las bandas", expanded=False):
    dd = df_resultados.copy()
    dd["Decisión"] = dd["Decision"].apply(lambda d: "✅ MANTENER" if d == "MANTENER" else ("🔴 MIGRAR" if d == "MIGRAR" else "⚪ FUERA DE ALCANCE"))
    dd["LTV ($)"] = dd["LTV_USD"].apply(lambda x: f"${round(x):,}")
    dd["Hurdle ($)"] = dd["Hurdle_USD"].apply(lambda x: f"${round(x):,}")
    dd["Margen ($)"] = dd.apply(lambda r: f"${round(r['LTV_USD']) - round(r['Hurdle_USD']):,}", axis=1)
    dd["Tasa Ef."] = dd["Tasa_Efectiva_M1_pct"].apply(lambda x: f"{x:.1f}%")
    dd["r Desc."] = dd["r_Descuento_pct"].apply(lambda x: f"{x:.2f}%")
    dd["CO (%)"] = dd["ChargeOff_Banda_pct"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(dd[["Banda","Saldo_USD","Pct_Revolvers","APR_Banda_pct","CO (%)","Tasa Ef.","r Desc.","LTV ($)","Hurdle ($)","Margen ($)","Decisión"]].rename(
        columns={"Saldo_USD":"Saldo ($)","Pct_Revolvers":"% Rev","APR_Banda_pct":"APR (%)"}
    ), use_container_width=True, hide_index=True)

st.markdown("---")

# ══════════════════════════════════════
# 3. GRÁFICA LTV vs HURDLE
# ══════════════════════════════════════
st.markdown('<div class="section-title">📈 LTV vs Hurdle por Banda</div>', unsafe_allow_html=True)
st.markdown("")

fig = go.Figure()
fig.add_trace(go.Bar(
    name="Barra = LTV",
    x=df_analisis["Banda"], y=df_analisis["LTV_USD"],
    marker_color=[BAND_COLORS[b] for b in df_analisis["Banda"]],
    showlegend=True, opacity=0.9,
    hovertemplate="LTV: $%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    name="\u25C6 = Hurdle",
    x=df_analisis["Banda"], y=df_analisis["Hurdle_USD"],
    mode="markers+lines",
    marker=dict(size=14, color="#fbbf24", symbol="diamond", line=dict(width=2, color="#1e293b")),
    line=dict(color="#fbbf24", width=3, dash="dash"),
    hovertemplate="Hurdle: $%{y:,.0f}<extra></extra>",
))
for _, row in df_analisis.iterrows():
    ltv_r = round(row["LTV_USD"])
    hur_r = round(row["Hurdle_USD"])
    mar_r = ltv_r - hur_r
    mc2 = "#4ade80" if mar_r >= 0 else "#f87171"
    ms = "+" if mar_r >= 0 else ""
    fig.add_annotation(x=row["Banda"], y=ltv_r, text=f"  ${ltv_r:,}  ", showarrow=False,
        font=dict(size=14, family="IBM Plex Mono", color="#ffffff"),
        bgcolor="rgba(15,23,42,0.8)", borderpad=3, yshift=22)
    y_off = -30 if abs(ltv_r - hur_r) < 250 else 25
    fig.add_annotation(x=row["Banda"], y=hur_r, text=f"  ${hur_r:,}  ", showarrow=False,
        font=dict(size=12, family="IBM Plex Mono", color="#ffffff"),
        bgcolor="rgba(15,23,42,0.85)", bordercolor="#fbbf24", borderwidth=1, borderpad=3, yshift=y_off)
    fig.add_annotation(x=row["Banda"], y=max(ltv_r, 0) / 2, text=f"  {ms}${abs(mar_r):,}  ", showarrow=False,
        font=dict(size=16, family="IBM Plex Mono", color=mc2),
        bgcolor="rgba(15,23,42,0.7)", borderpad=4)
fig.update_layout(
    yaxis_title="USD (valor presente a 60 meses)", xaxis_title="", height=560,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
        font=dict(family="DM Sans", size=14, color="#f1f5f9"), bgcolor="rgba(0,0,0,0)"),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", size=13, color="#e2e8f0"),
    xaxis=dict(tickfont=dict(size=14, color="#f1f5f9")),
    yaxis=dict(gridcolor="rgba(71,85,105,0.3)", zerolinecolor="rgba(71,85,105,0.5)", tickprefix="$", tickformat=",", tickfont=dict(size=12)),
    margin=dict(t=60, b=40),
)
st.plotly_chart(fig, use_container_width=True)
st.markdown("---")

# ══════════════════════════════════════
# 4. MOTOR DE CHOQUE DE PAGO
# ══════════════════════════════════════
from motor_choque import calcular_choque_todas_bandas

st.markdown('<div class="section-title">💥 Choque de Pago por Migración</div>', unsafe_allow_html=True)
st.markdown(
    '<span style="color:#e2e8f0;font-size:1rem;">'
    'Si un cliente migra de revolvente a pago fijo, ¿cuánto sube su pago mensual y cuántos caen en default? '
    'Ajusta los parámetros de choque en el panel izquierdo.'
    '</span>', unsafe_allow_html=True)
st.markdown("")

df_choque = calcular_choque_todas_bandas(df_resultados, df_cfpb, tope, plazo_amort, sensibilidad_choque, severidad)
df_ch_analisis = df_choque[df_choque["Decision_LTV"].isin(["MANTENER", "MIGRAR"])]

# Cards de choque
st.markdown("")
ch_cards = st.columns(4)
for i, (_, row) in enumerate(df_ch_analisis.iterrows()):
    banda = row["Banda"]
    color = BAND_COLORS[banda]
    dec = row["Decision_Final"]

    if "MANTENER ✅" in dec:
        badge_cls, badge_txt = "badge-mantener", "✅ MANTENER"
    elif "PÉRDIDA" in dec:
        badge_html = '<span style="background:rgba(234,179,8,0.2);color:#fbbf24;padding:5px 14px;border-radius:20px;font-weight:700;font-size:0.9rem;font-family:DM Sans;display:inline-block;">⚠️ MANTENER CON PÉRDIDA</span>'
        badge_cls = None
    else:
        badge_cls, badge_txt = "badge-migrar", "🔴 MIGRAR"

    pago_a = row["Pago_Actual_USD"]
    pago_n = round(row["Pago_Nuevo_USD"])
    mult = row["Multiplo_Choque"]
    p_def = row["P_Default_Choque_pct"]
    perd = round(row["Perdida_Migracion_USD"])
    costo_m = round(row["Costo_Mantener_USD"])

    if badge_cls:
        badge_html = f'<div class="{badge_cls}">{badge_txt}</div>'

    with ch_cards[i]:
        st.markdown(f"""
        <div style="background:rgba(30,41,59,0.6);border:1px solid {color}50;border-top:4px solid {color};
            border-radius:14px;padding:18px 16px;text-align:center;min-height:320px;">
            <div style="font-family:'DM Sans';font-weight:700;color:{color};font-size:1.05rem;margin-bottom:10px;">{banda}</div>
            {badge_html}
            <div style="font-family:'IBM Plex Mono';font-size:0.85rem;color:#cbd5e1;line-height:2;margin-top:12px;">
                <div>Pago actual <span style="color:#f1f5f9;font-weight:600;">${pago_a:,.0f}/mes</span></div>
                <div>Pago nuevo <span style="color:#fbbf24;font-weight:600;">${pago_n:,.0f}/mes</span></div>
                <div>Choque <span style="color:#f87171;font-weight:700;">{mult:.1f}×</span></div>
                <div>P(default) <span style="color:#f87171;font-weight:600;">{p_def:.1f}%</span></div>
                <div style="margin-top:6px;border-top:1px solid rgba(71,85,105,0.3);padding-top:6px;">
                    <div>Pérdida migrar <span style="color:#f87171;font-weight:600;">${perd:,}</span></div>
                    <div>Costo mantener <span style="color:#fbbf24;font-weight:600;">${costo_m:,}</span></div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("""
<div class="note-box">
    <strong>¿Cómo leer esta sección?</strong><br>
    Cuando el Motor 2 (LTV) dice MIGRAR, este motor calcula cuánto cuesta realmente migrar al cliente.
    Si la pérdida por migración es mayor que el costo de mantenerlo en revolvente con margen negativo,
    la decisión óptima es <strong>mantener con pérdida</strong> — es el menor de dos males.<br><br>
    El choque de pago es el múltiplo entre el pago nuevo (amortización fija) y el pago actual (mínimo revolvente).
    A mayor choque, mayor probabilidad de que el cliente deje de pagar al ser migrado.
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════
# 5. HEATMAP SENSIBILIDADES
# ══════════════════════════════════════
st.markdown('<div class="section-title">🗺️ Mapa de Sensibilidades</div>', unsafe_allow_html=True)
st.markdown(
    '<span style="color:#cbd5e1;font-size:1rem;">'
    '<span style="color:#4ade80;">■</span> MANTENER · '
    '<span style="color:#f87171;">■</span> MIGRAR · '
    'Valor = margen LTV − Hurdle (USD) · Bandas Deep Subprime a Prime</span>', unsafe_allow_html=True)

with st.spinner("Calculando sensibilidades..."):
    niveles = list(range(10, 31))
    df_sens = calcular_sensibilidades(datos_macro, df_cfpb, spreads_bps, mult_co, niveles, [3, 6, 9, 12])

df_sf = df_sens[df_sens["Banda"].isin(BANDAS_ANALISIS)]

tabs = st.tabs([f"⏱️ {d} meses" for d in [3, 6, 9, 12]])
for tab, dur in zip(tabs, [3, 6, 9, 12]):
    with tab:
        dd = df_sf[df_sf["Duracion_meses"] == dur]
        pv = dd.pivot_table(index="Tope_pct", columns="Banda", values="Margen_USD")[BANDAS_ANALISIS]
        fig_hm = go.Figure(data=go.Heatmap(
            z=pv.values, x=pv.columns.tolist(),
            y=[f"{int(t)}%" for t in pv.index],
            colorscale=[[0,"#dc2626"],[0.35,"#f87171"],[0.5,"#334155"],[0.65,"#4ade80"],[1,"#16a34a"]],
            zmid=0,
            text=np.round(pv.values, 0).astype(int).astype(str),
            texttemplate="%{text}",
            textfont=dict(size=12, family="IBM Plex Mono", color="#f1f5f9"),
            colorbar=dict(title=dict(text="Margen ($)", font=dict(color="#cbd5e1", size=13)),
                tickfont=dict(color="#cbd5e1", size=11), tickprefix="$", bgcolor="rgba(0,0,0,0)"),
            hovertemplate="<b>%{x}</b><br>Tope: %{y}<br>Margen: $%{z:,.0f}<extra></extra>",
            xgap=2, ygap=2,
        ))
        fig_hm.update_layout(
            yaxis_title="Nivel del tope (%)", xaxis_title="", height=620,
            yaxis=dict(dtick=1, tickfont=dict(size=12, color="#cbd5e1")),
            xaxis=dict(tickfont=dict(size=14, color="#f1f5f9")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans", size=13, color="#cbd5e1"), margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_hm, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════
# 5. CALIBRACIÓN
# ══════════════════════════════════════
st.markdown('<div class="section-title">🔬 Datos de Calibración</div>', unsafe_allow_html=True)
st.markdown("")

with st.expander("Datos CFPB por banda FICO (2024)", expanded=False):
    dc = df_cfpb[["Rango_Score","Pct_Revolvers_2024","Saldo_Promedio_GP_2024_USD",
        "APR_Promedio_NuevasCuentas_2024_pct","Payment_Rate_2024_pct"]].copy()
    dc.index.name = "Banda"
    dc.columns = ["Rango Score","% Revolvers","Saldo Promedio ($)","APR Nuevas Cuentas (%)","Payment Rate (%)"]
    st.dataframe(dc, use_container_width=True)

with st.expander("Multiplicadores de charge-off actuales", expanded=False):
    st.dataframe(pd.DataFrame({
        "Banda": BANDAS,
        "Multiplicador": [f"{mult_co[b]:.2f}×" for b in BANDAS],
        "Charge-Off Implícito": [f"{datos_macro['ChargeOff_pct']*mult_co[b]:.2f}%" for b in BANDAS],
    }), use_container_width=True, hide_index=True)

with st.expander("Supuestos y limitaciones del modelo", expanded=False):
    st.markdown("""
**Supuestos:**
1. Comportamiento del cliente (% revolvers) **estático** durante el tope
2. Tasa de pérdida neta base **estática** durante el tope
3. Portafolios de **banca Tier 1** en Estados Unidos
4. Datos FICO del CFPB (2024) como **parámetros fijos**
5. Rf y fondeo: **última observación** FRED
6. Horizonte: **60 meses**

**Limitaciones:**
- Solo mide **ingresos por intereses revolventes** — no incluye interchange, anualidades ni fees
- Prime Plus y Superprime **fuera del análisis**: su valor viene de ingresos transaccionales
- Se intentó incorporar comisiones vía Costo Total de Crédito del CFPB, pero la métrica no captura el ingreso del emisor en segmentos premium
- Extensión futura: datos de interchange (Fed Regulation II) + purchase volume por banda del CFPB
- Con datos internos de un banco, el modelo cubre **las 6 bandas** sin cambio estructural
    """)

st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#64748b;font-size:0.85rem;font-family:DM Sans;padding:10px 0 30px;">'
    'Simulador LTV · Proyecto Final · Maestría en Finanzas · EGADE Business School<br>'
    'Fuentes: FRED (TERMCBCCALLNS, CORCCT100S, DGS10, SOFR) · CFPB Credit Card Market Report 2025'
    '</div>', unsafe_allow_html=True)
