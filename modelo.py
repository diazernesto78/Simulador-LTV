"""
Motor de cálculo del Simulador LTV — Tarjetas de Crédito bajo Topes de Tasa.

Nota: El modelo mide el componente de ingresos por intereses revolventes.
Prime Plus y Superprime quedan fuera del análisis de decisión porque su
rentabilidad depende de ingresos transaccionales no disponibles por banda.
"""

import pandas as pd
import numpy as np
from pathlib import Path

HORIZONTE_MESES = 60

BANDAS = [
    "Deep Subprime", "Subprime", "Near-Prime",
    "Prime", "Prime Plus", "Superprime",
]

BANDAS_ANALISIS = ["Deep Subprime", "Subprime", "Near-Prime", "Prime"]
BANDAS_EXCLUIDAS = ["Prime Plus", "Superprime"]

MULT_CHARGEOFF_DEFAULTS = {
    "Deep Subprime": 2.50,
    "Subprime":      2.00,
    "Near-Prime":    1.40,
    "Prime":         0.80,
    "Prime Plus":    0.40,
    "Superprime":    0.15,
}

SPREAD_DEFAULTS_BPS = {
    "Deep Subprime": 800,
    "Subprime":      650,
    "Near-Prime":    450,
    "Prime":         300,
    "Prime Plus":    150,
    "Superprime":     75,
}

DATOS_DIR = Path(__file__).parent / "datos"


def cargar_datos_macro(path=None):
    if path is None:
        path = DATOS_DIR / "datos_macro_consolidados.xlsx"
    df = pd.read_excel(path, sheet_name="Series_Diarias")
    u = df.iloc[-1]
    return {
        "fecha": str(u["fecha"]),
        "APR_pct": float(u["APR_pct"]),
        "ChargeOff_pct": float(u["ChargeOff_pct"]),
        "Treasury10Y_pct": float(u["Treasury10Y_pct"]),
        "Fondeo_pct": float(u["Fondeo_pct"]),
    }


def cargar_datos_cfpb(path=None):
    if path is None:
        path = DATOS_DIR / "CFPB_datos_por_banda_FICO.xlsx"
    df = pd.read_excel(path, sheet_name="Datos_FICO")
    return df.set_index("Banda_FICO")


def calcular_tasa_efectiva(apr, tope, dur_tope, mes):
    return min(apr, tope) if mes <= dur_tope else apr


def calcular_ltv_banda(saldo, pct_rev, apr, co, fondeo, r_desc, tope, dur_tope):
    r_m = r_desc / 100 / 12
    fn_desc, h_desc = [], []
    for m in range(1, HORIZONTE_MESES + 1):
        te = calcular_tasa_efectiva(apr, tope, dur_tope, m)
        ing = saldo * pct_rev * (te / 100) / 12
        prd = saldo * (co / 100) / 12
        fnd = saldo * (fondeo / 100) / 12
        fn = ing - prd - fnd
        fd = (1 + r_m) ** m
        fn_desc.append(fn / fd)
        h_desc.append((saldo * r_m) / fd)
    return {"ltv": sum(fn_desc), "hurdle": sum(h_desc)}


def calcular_todas_bandas(datos_macro, df_cfpb, tope, dur_tope, spreads_bps, mult_co):
    rf = datos_macro["Treasury10Y_pct"]
    fondeo = datos_macro["Fondeo_pct"]
    co_base = datos_macro["ChargeOff_pct"]
    resultados = []
    for banda in BANDAS:
        row = df_cfpb.loc[banda]
        saldo = float(row["Saldo_Promedio_GP_2024_USD"])
        pct_rev = float(row["Pct_Revolvers_2024"])
        apr = float(row["APR_Promedio_NuevasCuentas_2024_pct"])
        co = co_base * mult_co[banda]
        r_desc = rf + spreads_bps[banda] / 100
        res = calcular_ltv_banda(saldo, pct_rev, apr, co, fondeo, r_desc, tope, dur_tope)
        decision = "FUERA DE ALCANCE" if banda in BANDAS_EXCLUIDAS else (
            "MANTENER" if res["ltv"] >= res["hurdle"] else "MIGRAR")
        resultados.append({
            "Banda": banda, "Saldo_USD": saldo, "Pct_Revolvers": pct_rev,
            "APR_Banda_pct": apr, "ChargeOff_Banda_pct": round(co, 2),
            "Tasa_Efectiva_M1_pct": calcular_tasa_efectiva(apr, tope, dur_tope, 1),
            "r_Descuento_pct": round(r_desc, 2),
            "LTV_USD": round(res["ltv"], 2), "Hurdle_USD": round(res["hurdle"], 2),
            "Margen_USD": round(res["ltv"] - res["hurdle"], 2), "Decision": decision,
        })
    return pd.DataFrame(resultados)


def calcular_sensibilidades(datos_macro, df_cfpb, spreads_bps, mult_co,
                            niveles_tope=None, duraciones=None):
    if niveles_tope is None:
        niveles_tope = list(range(10, 31))
    if duraciones is None:
        duraciones = [3, 6, 9, 12]
    registros = []
    for tope in niveles_tope:
        for dur in duraciones:
            df = calcular_todas_bandas(datos_macro, df_cfpb, tope, dur, spreads_bps, mult_co)
            for _, r in df.iterrows():
                registros.append({
                    "Tope_pct": tope, "Duracion_meses": dur, "Banda": r["Banda"],
                    "LTV_USD": r["LTV_USD"], "Hurdle_USD": r["Hurdle_USD"],
                    "Margen_USD": r["Margen_USD"], "Decision": r["Decision"],
                })
    return pd.DataFrame(registros)
