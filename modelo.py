"""
Motor de cálculo del Simulador LTV — Tarjetas de Crédito bajo Topes de Tasa.

Contiene:
- Carga de datos macro (FRED) y por banda (CFPB)
- Motor LTV a 60 meses con descuento por banda
- Motor de decisión (LTV vs hurdle)
- Motor de sensibilidades (nivel tope × duración)

Nota: El modelo mide exclusivamente el componente de ingresos por intereses
revolventes. Las bandas Prime Plus y Superprime quedan fuera del análisis
de decisión porque su rentabilidad depende de ingresos transaccionales
(interchange, anualidad) que no están disponibles por banda en fuentes públicas.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────

HORIZONTE_MESES = 60

BANDAS = [
    "Deep Subprime",
    "Subprime",
    "Near-Prime",
    "Prime",
    "Prime Plus",
    "Superprime",
]

# Bandas incluidas en el análisis de decisión mantener/migrar.
# Prime Plus y Superprime se excluyen: con <50% de revolvers,
# su LTV por intereses no refleja la rentabilidad real de la cuenta.
BANDAS_ANALISIS = [
    "Deep Subprime",
    "Subprime",
    "Near-Prime",
    "Prime",
]

BANDAS_EXCLUIDAS = ["Prime Plus", "Superprime"]

MULT_CHARGEOFF = {
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


# ──────────────────────────────────────────────
# Carga de datos
# ──────────────────────────────────────────────

def cargar_datos_macro(path: Path | None = None) -> dict:
    if path is None:
        path = DATOS_DIR / "datos_macro_consolidados.xlsx"
    df = pd.read_excel(path, sheet_name="Series_Diarias")
    ultimo = df.iloc[-1]
    return {
        "fecha":          str(ultimo["fecha"]),
        "APR_pct":        float(ultimo["APR_pct"]),
        "ChargeOff_pct":  float(ultimo["ChargeOff_pct"]),
        "Treasury10Y_pct": float(ultimo["Treasury10Y_pct"]),
        "Fondeo_pct":     float(ultimo["Fondeo_pct"]),
    }


def cargar_datos_cfpb(path: Path | None = None) -> pd.DataFrame:
    if path is None:
        path = DATOS_DIR / "CFPB_datos_por_banda_FICO.xlsx"
    df = pd.read_excel(path, sheet_name="Datos_FICO")
    df = df.set_index("Banda_FICO")
    return df


# ──────────────────────────────────────────────
# Motor LTV — 60 meses
# ──────────────────────────────────────────────

def calcular_tasa_efectiva(apr_banda: float, tope: float, duracion_tope: int, mes: int) -> float:
    if mes <= duracion_tope:
        return min(apr_banda, tope)
    return apr_banda


def calcular_ltv_banda(
    saldo: float,
    pct_revolvers: float,
    apr_banda: float,
    chargeoff_banda: float,
    fondeo: float,
    r_descuento: float,
    tope: float,
    duracion_tope: int,
) -> dict:
    r_m = r_descuento / 100 / 12

    flujos_netos = []
    flujos_descontados = []
    hurdle_flujos = []

    for mes in range(1, HORIZONTE_MESES + 1):
        tasa_ef = calcular_tasa_efectiva(apr_banda, tope, duracion_tope, mes)

        ingreso   = saldo * pct_revolvers * (tasa_ef / 100) / 12
        perdida   = saldo * (chargeoff_banda / 100) / 12
        costo_fon = saldo * (fondeo / 100) / 12

        fn = ingreso - perdida - costo_fon
        factor_desc = (1 + r_m) ** mes

        flujos_netos.append(fn)
        flujos_descontados.append(fn / factor_desc)
        hurdle_flujos.append((saldo * r_m) / factor_desc)

    ltv = sum(flujos_descontados)
    hurdle = sum(hurdle_flujos)

    return {
        "ltv": ltv,
        "hurdle": hurdle,
        "flujos_netos": flujos_netos,
        "flujos_descontados": flujos_descontados,
    }


def calcular_todas_bandas(
    datos_macro: dict,
    df_cfpb: pd.DataFrame,
    tope: float,
    duracion_tope: int,
    spreads_bps: dict,
) -> pd.DataFrame:
    rf = datos_macro["Treasury10Y_pct"]
    fondeo = datos_macro["Fondeo_pct"]
    chargeoff_base = datos_macro["ChargeOff_pct"]

    resultados = []

    for banda in BANDAS:
        row = df_cfpb.loc[banda]
        saldo = float(row["Saldo_Promedio_GP_2024_USD"])
        pct_rev = float(row["Pct_Revolvers_2024"])
        apr = float(row["APR_Promedio_NuevasCuentas_2024_pct"])
        chargeoff = chargeoff_base * MULT_CHARGEOFF[banda]
        spread = spreads_bps[banda] / 100
        r_desc = rf + spread

        res = calcular_ltv_banda(
            saldo=saldo, pct_revolvers=pct_rev, apr_banda=apr,
            chargeoff_banda=chargeoff, fondeo=fondeo, r_descuento=r_desc,
            tope=tope, duracion_tope=duracion_tope,
        )

        # Decisión solo para bandas en análisis
        if banda in BANDAS_ANALISIS:
            decision = "MANTENER" if res["ltv"] >= res["hurdle"] else "MIGRAR"
        else:
            decision = "FUERA DE ALCANCE"

        resultados.append({
            "Banda": banda,
            "Saldo_USD": saldo,
            "Pct_Revolvers": pct_rev,
            "APR_Banda_pct": apr,
            "ChargeOff_Banda_pct": round(chargeoff, 2),
            "Tasa_Efectiva_M1_pct": calcular_tasa_efectiva(apr, tope, duracion_tope, 1),
            "r_Descuento_pct": round(r_desc, 2),
            "LTV_USD": round(res["ltv"], 2),
            "Hurdle_USD": round(res["hurdle"], 2),
            "Margen_USD": round(res["ltv"] - res["hurdle"], 2),
            "Decision": decision,
        })

    return pd.DataFrame(resultados)


# ──────────────────────────────────────────────
# Motor de sensibilidades
# ──────────────────────────────────────────────

def calcular_sensibilidades(
    datos_macro: dict,
    df_cfpb: pd.DataFrame,
    spreads_bps: dict,
    niveles_tope: list[float] | None = None,
    duraciones: list[int] | None = None,
) -> pd.DataFrame:
    if niveles_tope is None:
        niveles_tope = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
    if duraciones is None:
        duraciones = [3, 6, 12]

    registros = []
    for tope in niveles_tope:
        for dur in duraciones:
            df_res = calcular_todas_bandas(datos_macro, df_cfpb, tope, dur, spreads_bps)
            for _, row in df_res.iterrows():
                registros.append({
                    "Tope_pct": tope,
                    "Duracion_meses": dur,
                    "Banda": row["Banda"],
                    "LTV_USD": row["LTV_USD"],
                    "Hurdle_USD": row["Hurdle_USD"],
                    "Margen_USD": row["Margen_USD"],
                    "Decision": row["Decision"],
                })

    return pd.DataFrame(registros)
