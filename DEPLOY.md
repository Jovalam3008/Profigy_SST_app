# Desplegar PRODIGY-SST con enlace permanente

La app `app_prodigy.py` puede ejecutarse **en local** (`streamlit run app_prodigy.py`) o **en internet** con una URL estable. La opción más sencilla para Streamlit es **Streamlit Community Cloud** (gratis con cuenta de GitHub).

## Opción recomendada: Streamlit Community Cloud

1. **Sube el proyecto a un repositorio GitHub** (público en el plan gratuito; privado requiere plan de pago).
2. Entra en [share.streamlit.io](https://share.streamlit.io) e inicia sesión con GitHub.
3. **Deploy an app** → selecciona el repositorio y la rama.
4. **Main file path:** `app_prodigy.py`
5. **Requirements file:** `requirements.txt` (en *Advanced settings* si no se detecta solo).
6. **Secrets (importante para datos en vivo):**  
   En la app → **⋮ → Settings → Secrets**, pega:

```toml
DATABASE_URL = "postgresql+psycopg2://USUARIO:CONTRASEÑA@HOST:5432/postgres"
```

Usa la misma cadena que en Supabase (pooler). La app detecta `DATABASE_URL` y lee las tablas `gold.kpi_mensual_mype` y `gold.top_causas_mensual` sin subir Excel al repo.

Si **no** configuras `DATABASE_URL`, la app intentará cargar los Excel del repositorio; en ese caso debes **incluir** `gold_kpi_mensual_mype.xlsx` y `gold_top_causas_mensual.xlsx` en la raíz del repo junto a `app_prodigy.py` (o en una ruta accesible).

7. Tras el despliegue obtendrás una URL del tipo:

`https://TU-APP.streamlit.app`

Ese enlace es **permanente** mientras mantengas la app desplegada y el servicio activo.

## Alternativas

| Servicio | Notas |
|----------|--------|
| **Render / Railway / Fly.io** | Contenedor con `streamlit run app_prodigy.py`; define `DATABASE_URL` en variables de entorno. |
| **ngrok** | Solo para pruebas: `ngrok http 8501` genera una URL **temporal**, no permanente. |

## Seguridad

- No subas contraseñas al código; usa **Secrets** de Streamlit Cloud o variables de entorno.
- Limita permisos de la base de datos a **solo lectura** sobre el esquema `gold` si es posible.
