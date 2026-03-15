# Simulador LTV — Tarjetas de Crédito bajo Topes de Tasa

Simulador interactivo que evalúa qué bandas FICO mantienen un LTV sostenible en crédito revolvente bajo un tope regulatorio temporal de tasa, y cuáles deberían migrar a un esquema de pago fijo.

## Cómo correr

La app corre en [Streamlit Community Cloud](https://streamlit.io/cloud). No requiere instalación local.

## Estructura

```
├── app.py                  # Interfaz Streamlit
├── modelo.py               # Motores LTV, decisión y sensibilidades
├── datos/
│   ├── datos_macro_consolidados.xlsx
│   └── CFPB_datos_por_banda_FICO.xlsx
└── requirements.txt
```

## Fuentes de datos
- FRED: TERMCBCCALLNS, CORCCT100S, DGS10, SOFR
- CFPB Credit Card Market Report 2025
