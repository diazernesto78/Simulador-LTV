"""
Motor de Choque de Pago — Módulo 3 del Simulador LTV.

Calcula el impacto de migrar clientes de revolvente a pago fijo:
1. Pago actual (basado en Payment Rate del CFPB)
2. Pago nuevo (amortización a N meses)
3. Choque de pago (múltiplo)
4. Probabilidad de default dado el choque
5. Pérdida esperada por migración

Este módulo es independiente de modelo.py para no afectar el motor base.
"""

import pandas as pd
import numpy as np


def calcular_pago_amortizacion(saldo: float, tasa_anual_pct: float, plazo_meses: int) -> float:
    """Pago mensual fijo para amortizar el saldo en N meses."""
    if tasa_anual_pct <= 0 or plazo_meses <= 0:
        return saldo / max(plazo_meses, 1)
    r = tasa_anual_pct / 100 / 12
    return saldo * (r * (1 + r) ** plazo_meses) / ((1 + r) ** plazo_meses - 1)


def calcular_pago_actual(saldo: float, payment_rate_pct: float) -> float:
    """Pago mensual actual basado en Payment Rate anual del CFPB."""
    return saldo * (payment_rate_pct / 100) / 12


def calcular_choque_banda(
    saldo: float,
    payment_rate_pct: float,
    tasa_amortizacion_pct: float,
    plazo_meses: int,
    chargeoff_banda_pct: float,
    sensibilidad: float,
    severidad_pct: float,
) -> dict:
    """
    Calcula el choque de pago y la pérdida esperada para una banda.

    Parámetros:
        saldo: saldo promedio de la banda
        payment_rate_pct: Payment Rate anual del CFPB (%)
        tasa_amortizacion_pct: tasa del plan de pagos (%) — típicamente min(APR, tope)
        plazo_meses: plazo de amortización (12-60)
        chargeoff_banda_pct: charge-off base de la banda (%)
        sensibilidad: puntos adicionales de default por cada múltiplo de choque (0-0.20)
        severidad_pct: % del saldo que se pierde si el cliente entra en default (0-100)

    Retorna dict con métricas del choque.
    """
    pago_actual = calcular_pago_actual(saldo, payment_rate_pct)
    pago_nuevo = calcular_pago_amortizacion(saldo, tasa_amortizacion_pct, plazo_meses)

    if pago_actual > 0:
        multiplo_choque = pago_nuevo / pago_actual
    else:
        multiplo_choque = 99.0

    # Probabilidad de default: base + sensibilidad × (choque - 1)
    # El choque mínimo es 1× (sin cambio), el default adicional es 0
    base_default = chargeoff_banda_pct / 100
    choque_adicional = max(multiplo_choque - 1, 0)
    p_default = min(base_default + sensibilidad * choque_adicional, 0.95)

    # Pérdida esperada por migración
    severidad = severidad_pct / 100
    perdida_esperada = saldo * p_default * severidad

    return {
        "pago_actual_usd": round(pago_actual, 2),
        "pago_nuevo_usd": round(pago_nuevo, 2),
        "multiplo_choque": round(multiplo_choque, 2),
        "p_default_pct": round(p_default * 100, 2),
        "perdida_esperada_usd": round(perdida_esperada, 2),
    }


def calcular_choque_todas_bandas(
    df_resultados: pd.DataFrame,
    df_cfpb: pd.DataFrame,
    tope: float,
    plazo_meses: int,
    sensibilidad: float,
    severidad_pct: float,
) -> pd.DataFrame:
    """
    Calcula el choque de pago para todas las bandas que migran.

    Parámetros:
        df_resultados: DataFrame de calcular_todas_bandas()
        df_cfpb: DataFrame CFPB con Payment_Rate
        tope: nivel del tope (para tasa del plan de pagos)
        plazo_meses: plazo de amortización
        sensibilidad: sensibilidad al choque (0-0.20)
        severidad_pct: severidad de pérdida (0-100%)

    Retorna DataFrame con métricas de choque por banda.
    """
    resultados = []

    for _, row in df_resultados.iterrows():
        banda = row["Banda"]
        decision = row["Decision"]
        cfpb = df_cfpb.loc[banda]

        saldo = row["Saldo_USD"]
        apr = row["APR_Banda_pct"]
        payment_rate = float(cfpb["Payment_Rate_2024_pct"])
        pct_min_solo = float(cfpb["Tasa_Pago_Minimo_Solo_2024_pct"])
        co = row["ChargeOff_Banda_pct"]

        # Tasa del plan: la menor entre APR y tope
        tasa_plan = min(apr, tope)

        choque = calcular_choque_banda(
            saldo=saldo,
            payment_rate_pct=payment_rate,
            tasa_amortizacion_pct=tasa_plan,
            plazo_meses=plazo_meses,
            chargeoff_banda_pct=co,
            sensibilidad=sensibilidad,
            severidad_pct=severidad_pct,
        )

        # Costo de mantener = margen negativo del LTV (si migra)
        margen_ltv = row["Margen_USD"]
        costo_mantener = abs(margen_ltv) if margen_ltv < 0 else 0

        resultados.append({
            "Banda": banda,
            "Decision_LTV": decision,
            "Saldo_USD": saldo,
            "Payment_Rate_pct": payment_rate,
            "Pct_Solo_Minimo": pct_min_solo,
            "Pago_Actual_USD": choque["pago_actual_usd"],
            "Pago_Nuevo_USD": choque["pago_nuevo_usd"],
            "Multiplo_Choque": choque["multiplo_choque"],
            "P_Default_Choque_pct": choque["p_default_pct"],
            "Perdida_Migracion_USD": choque["perdida_esperada_usd"],
            "Costo_Mantener_USD": costo_mantener,
            "Margen_LTV_USD": margen_ltv,
            "Decision_Final": _decision_final(decision, costo_mantener, choque["perdida_esperada_usd"]),
        })

    return pd.DataFrame(resultados)


def _decision_final(decision_ltv: str, costo_mantener: float, perdida_migracion: float) -> str:
    """
    Decisión final considerando el choque de pago.

    Si el LTV dice MANTENER → se mantiene (no hay choque).
    Si el LTV dice MIGRAR → compara costo de mantener vs costo de migrar.
    Si FUERA DE ALCANCE → se mantiene fuera.
    """
    if decision_ltv == "MANTENER":
        return "MANTENER ✅"
    elif decision_ltv == "FUERA DE ALCANCE":
        return "FUERA DE ALCANCE ⚪"
    else:
        # MIGRAR: ¿conviene migrar o es mejor mantener con pérdida?
        if perdida_migracion > costo_mantener:
            return "MANTENER CON PÉRDIDA ⚠️"
        else:
            return "MIGRAR 🔴"
