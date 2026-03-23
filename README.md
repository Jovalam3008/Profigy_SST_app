# PRODIGY-SST — Tablero (Streamlit)

App mínima para el tablero **PRODIGY-SST**: datos Gold, umbrales DS 005-2021-TR (IF≤45, IS×10⁶/HHT≤100), carga vía **PostgreSQL/Supabase** (`DATABASE_URL`) o **Excel** en la misma carpeta que `app_prodigy.py`.

## Requisitos

- Python 3.10+ recomendado

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Ejecutar en local

```bash
streamlit run app_prodigy.py
```

- **Con base de datos:** define `DATABASE_URL` (variable de entorno) o copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y edita la URL (no subas `secrets.toml` a un repo público).
- **Solo Excel:** coloca `gold_kpi_mensual_mype.xlsx` y `gold_top_causas_mensual.xlsx` junto a `app_prodigy.py`. Por defecto `.gitignore` ignora `*.xlsx`; quita esa línea si versionas los datos en GitHub.

## Despliegue (URL permanente)

Ver [DEPLOY.md](DEPLOY.md) (Streamlit Community Cloud y alternativas).

Además, el repositorio incluye `docs/index.html` + workflow de GitHub Pages para publicar un portal web en:

`https://Jovalam3008.github.io/Profigy_SST_app/`

Nota: GitHub Pages publica contenido estático; la ejecución de Streamlit se mantiene en Streamlit Community Cloud.
