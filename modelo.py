"""
Motor de cálculo del Simulador LTV — Tarjetas de Crédito bajo Topes de Tasa.

Contiene:
- Carga de datos macro (FRED) y por banda (CFPB)
- Motor LTV a 60 meses con descuento por banda
- Motor de decisión (LTV vs hurdle)
- Motor de sensibilidades (nivel tope × duración)
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

# Multiplicadores de charge-off por banda sobre la tasa agregada FRED.
# Calibración basada en dispersión relativa de pérdida neta reportada
# por CFPB (2025) y Fed (CORCCT100S) para portafolios Tier 1.
MULT_CHARGEOFF = {
    "Deep Subprime": 2.50,
    "Subprime":      2.00,
    "Near-Prime":    1.40,
    "Prime":         0.80,
    "Prime Plus":    0.40,
    "Superprime":    0.15,
}

# Spreads default (bps) sobre Rf para tasa de descuento por banda.
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
    """Lee datos_macro_consolidados.xlsx y devuelve última observación de cada variable."""
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
    """Lee CFPB_datos_por_banda_FICO.xlsx y devuelve DataFrame indexado por banda."""
    if path is None:
        path = DATOS_DIR / "CFPB_datos_por_banda_FICO.xlsx"
    df = pd.read_excel(path, sheet_name="Datos_FICO")
    df = df.set_index("Banda_FICO")
    return df


# ──────────────────────────────────────────────
# Motor LTV — 60 meses
# ──────────────────────────────────────────────

def calcular_tasa_efectiva(apr_banda: float, tope: float, duracion_tope: int, mes: int) -> float:
    """Tasa efectiva anual para un mes dado, limitada por el tope durante su vigencia."""
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
    """
    Calcula LTV, hurdle y flujos netos para una banda a 60 meses.

    Retorna dict con:
        ltv: valor presente de flujos netos
        hurdle: valor presente del rendimiento mínimo exigido
        flujos_netos: lista de 60 flujos netos nominales
        flujos_descontados: lista de 60 flujos descontados
        decision: 'MANTENER' o 'MIGRAR'
    """
    r_m = r_descuento / 100 / 12  # tasa de descuento mensual

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
    decision = "MANTENER" if ltv >= hurdle else "MIGRAR"

    return {
        "ltv": ltv,
        "hurdle": hurdle,
        "flujos_netos": flujos_netos,
        "flujos_descontados": flujos_descontados,
        "decision": decision,
    }


def calcular_todas_bandas(
    datos_macro: dict,
    df_cfpb: pd.DataFrame,
    tope: float,
    duracion_tope: int,
    spreads_bps: dict,
) -> pd.DataFrame:
    """
    Ejecuta el motor LTV para las 6 bandas FICO.

    Parámetros:
        datos_macro: dict con última observación macro
        df_cfpb: DataFrame CFPB indexado por banda
        tope: nivel del tope regulatorio (%)
        duracion_tope: duración del tope en meses
        spreads_bps: dict {banda: spread en bps}

    Retorna DataFrame con resultados por banda.
    """
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
        spread = spreads_bps[banda] / 100  # bps a porcentaje
        r_desc = rf + spread

        res = calcular_ltv_banda(
            saldo=saldo,
            pct_revolvers=pct_rev,
            apr_banda=apr,
            chargeoff_banda=chargeoff,
            fondeo=fondeo,
            r_descuento=r_desc,
            tope=tope,
            duracion_tope=duracion_tope,
        )

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
            "Decision": res["decision"],
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
    """
    Calcula la decisión (MANTENER/MIGRAR) para cada combinación de
    nivel de tope × duración × banda.

    Retorna DataFrame con columnas: Tope_pct, Duracion_meses, Banda, LTV, Hurdle, Decision
    """
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
