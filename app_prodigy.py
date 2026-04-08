"""
PRODIGY-SST: Tablero de Control
Analítica descriptiva sobre capa Gold — alineado a analisis.ipynb, Ley 29783 y DS 005-2021-TR.

IF/IS = por millón de HHT (definición Gold).

Ejecutar (local): streamlit run app_prodigy.py

Enlace permanente (internet): despliega en Streamlit Community Cloud u otro host;
configura el secreto DATABASE_URL para leer Gold en Supabase. Ver DEPLOY.md.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

# DS 005-2021-TR — límites máximos tolerables (misma base que capa Gold)
IF_LEGAL = 45
IS_LEGAL = 100
# Metas intermedias proyecto (6 meses)
IF_META = 50
IS_META = 120

# Catálogo MYPE — San Román (razón social)
MYPE_NOMBRES: dict[str, str] = {
    "MYPE-SR-001": "Constructora Altiplano SAC",
    "MYPE-SR-002": "Servicios Puno Andino EIRL",
    "MYPE-SR-003": "Obras San Román SRL",
    "MYPE-SR-004": "Estructuras Titicaca SAC",
    "MYPE-SR-005": "Logística Collao SRL",
    "MYPE-SR-006": "Montajes Juliaca EIRL",
    "MYPE-SR-007": "Vías del Sur Andino SAC",
    "MYPE-SR-008": "Mantenimiento Pucará SRL",
}


def nombre_mype(mype_id: str) -> str:
    return MYPE_NOMBRES.get(str(mype_id), str(mype_id))


def agregar_columna_empresa(df: pd.DataFrame) -> pd.DataFrame:
    """Inserta columna `empresa` después de `mype_id` si existe."""
    if df.empty or "mype_id" not in df.columns:
        return df
    out = df.copy()
    if "empresa" in out.columns:
        return out
    pos = out.columns.get_loc("mype_id") + 1
    out.insert(pos, "empresa", out["mype_id"].map(nombre_mype))
    return out


st.set_page_config(
    page_title="PRODIGY-SST — Tablero de Control",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)


def _get_database_url() -> str | None:
    """URL PostgreSQL/Supabase: variable de entorno o Streamlit Secrets (despliegue en la nube)."""
    u = os.environ.get("DATABASE_URL", "").strip()
    if u:
        return u
    try:
        if hasattr(st, "secrets"):
            u = (st.secrets.get("DATABASE_URL") or "").strip()
            if u:
                return u
    except Exception:
        pass
    return None


def _with_sslmode(url: str) -> str:
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}sslmode=require"
    return url


def _load_data_from_excel() -> tuple[pd.DataFrame, pd.DataFrame]:
    kpi_path = BASE_DIR / "gold_kpi_mensual_mype.xlsx"
    causas_path = BASE_DIR / "gold_top_causas_mensual.xlsx"
    if not kpi_path.is_file():
        raise FileNotFoundError(f"No se encuentra: {kpi_path}")
    if not causas_path.is_file():
        raise FileNotFoundError(f"No se encuentra: {causas_path}")
    df_kpi = pd.read_excel(kpi_path)
    df_causas = pd.read_excel(causas_path)
    df_kpi["fecha"] = pd.to_datetime(df_kpi["codmes"].astype(str) + "01", format="%Y%m%d")
    df_causas["fecha"] = pd.to_datetime(df_causas["codmes"].astype(str) + "01", format="%Y%m%d")
    return df_kpi, df_causas


def _load_data_from_database(url: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    from sqlalchemy import create_engine, text

    engine = create_engine(_with_sslmode(url), pool_pre_ping=True)
    df_kpi = pd.read_sql(text("SELECT * FROM gold.kpi_mensual_mype_corregido"), engine)
    df_causas = pd.read_sql(text("SELECT * FROM gold.top_causas_mensual"), engine)
    df_kpi["fecha"] = pd.to_datetime(df_kpi["codmes"].astype(str) + "01", format="%Y%m%d")
    df_causas["fecha"] = pd.to_datetime(df_causas["codmes"].astype(str) + "01", format="%Y%m%d")
    return df_kpi, df_causas


@st.cache_data(show_spinner="Cargando datos Gold…", ttl=300)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prioridad: `DATABASE_URL` (nube/Supabase) → si no, Excel en carpeta del proyecto."""
    url = _get_database_url()
    if url:
        return _load_data_from_database(url)
    return _load_data_from_excel()


def fuente_datos_label() -> str:
    return "PostgreSQL / Supabase (tablas gold.*)" if _get_database_url() else "Archivos Excel locales"


def generar_reporte_ejecutivo(df_kpi: pd.DataFrame, df_causas: pd.DataFrame) -> str:
    """Reporte texto alineado a PRODIGY-SST y analisis.ipynb."""
    total_accidentes = int(df_kpi["n_accidentes"].sum())
    total_dias = int(df_kpi["dias_perdidos"].sum())
    if_global = float(df_kpi["ifrecuencia"].mean())
    is_global = float(df_kpi["isevidad"].mean())
    n = len(df_kpi)
    pct_if_legal = 100 * ((df_kpi["ifrecuencia"] > IF_LEGAL).sum()) / max(n, 1)
    pct_is_legal = 100 * ((df_kpi["isevidad"] > IS_LEGAL).sum()) / max(n, 1)

    mype_critica = df_kpi.groupby("mype_id")["isevidad"].mean().idxmax()
    nombre_critica = nombre_mype(str(mype_critica))
    is_critica = float(df_kpi[df_kpi["mype_id"] == mype_critica]["isevidad"].mean())

    if df_causas.empty or df_causas["n_accidentes"].sum() == 0:
        causa_top, n_causa_top = "N/D", 0
    else:
        causa_top = df_causas.groupby("causa_especifica")["n_accidentes"].sum().idxmax()
        n_causa_top = int(df_causas[df_causas["causa_especifica"] == causa_top]["n_accidentes"].sum())

    meses_recientes = sorted(df_kpi["codmes"].unique())[-3:]
    tendencia_reciente = df_kpi[df_kpi["codmes"].isin(meses_recientes)].groupby("codmes")["ifrecuencia"].mean()
    if len(tendencia_reciente) >= 2:
        direccion = "📈 ALZA" if tendencia_reciente.iloc[-1] > tendencia_reciente.iloc[0] else "📉 MEJORA"
    else:
        direccion = "N/D"

    return f"""
---
**PRODIGY-SST | Reporte ejecutivo** · San Román, Puno · Ley 29783 / DS 005-2021-TR · {datetime.now().strftime("%Y-%m-%d %H:%M")}

### Métricas globales
- Accidentes registrados: **{total_accidentes:,}** · Días perdidos: **{total_dias:,}**
- IF medio: **{if_global:.2f}** · IS medio: **{is_global:.2f}** *(por millón HHT, capa Gold)*

### Cumplimiento normativo (IF≤{IF_LEGAL}, IS≤{IS_LEGAL})
- Registros MYPE-mes con IF > {IF_LEGAL}: **{pct_if_legal:.1f}%**
- Registros MYPE-mes con IS > {IS_LEGAL}: **{pct_is_legal:.1f}%**
- Metas intermedias (6 meses): IF≤{IF_META}, IS≤{IS_META}

### Alerta prioritaria
- Empresa crítica (IS medio): **{nombre_critica}** · `{mype_critica}` (IS ≈ **{is_critica:.2f}**)

### Causa raíz frecuente
- **{causa_top}** → **{n_causa_top}** accidentes (causa específica)

### Tendencia reciente IF: {direccion}
- Meses: {", ".join(map(str, meses_recientes))}

### Acciones sugeridas
1. Intervención en **{nombre_critica}** (auditoría SST).
2. Campaña sobre **{causa_top}** en MYPEs seleccionadas.
3. Cerrar brecha vs. **IF≤{IF_LEGAL}** e **IS≤{IS_LEGAL}**; revisión estadística si IF>{if_global * 1.5:.1f} o IS>{is_global * 1.5:.1f}.
---
"""


def main() -> None:
    st.title("PRODIGY-SST: Tablero de Control")
    st.caption(
        f"Capa Gold · MYPEs construcción · San Román (Puno) · IF/IS por millón HHT · "
        f"Umbrales: IF≤{IF_LEGAL}, IS≤{IS_LEGAL} (DS 005-2021-TR) · "
        f"Fuente: {fuente_datos_label()}"
    )

    try:
        df_kpi_full, df_causas_full = load_data()
    except FileNotFoundError as e:
        st.error(str(e))
        st.info(
            "Opciones: (1) Coloca `gold_kpi_mensual_mype.xlsx` y `gold_top_causas_mensual.xlsx` en "
            f"`{BASE_DIR}` · (2) En la nube, configura el secreto **DATABASE_URL** (PostgreSQL/Supabase) "
            "en *Streamlit Community Cloud → App settings → Secrets*."
        )
        return
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        st.info(
            "Si usas base de datos, comprueba `DATABASE_URL`, red y que existan `gold.kpi_mensual_mype` "
            "y `gold.top_causas_mensual`."
        )
        return

    all_mypes = sorted(df_kpi_full["mype_id"].unique())
    all_meses = sorted(df_kpi_full["codmes"].unique())

    with st.sidebar:
        st.header("Filtros")
        selected_mypes = st.multiselect(
            "MYPEs",
            options=all_mypes,
            default=all_mypes,
            format_func=lambda x: f"{x} — {nombre_mype(x)}",
        )
        mes_min, mes_max = st.select_slider(
            "Rango codmes",
            options=all_meses,
            value=(all_meses[0], all_meses[-1]),
        )
        st.divider()
        st.markdown("**Normativa**")
        st.caption(f"DS 005-2021-TR: IF ≤ {IF_LEGAL}, IS ≤ {IS_LEGAL}")
        st.caption(f"Metas proyecto: IF ≤ {IF_META}, IS ≤ {IS_META}")

    if not selected_mypes:
        st.warning("Selecciona al menos una MYPE.")
        return

    df_kpi = df_kpi_full[
        (df_kpi_full["mype_id"].isin(selected_mypes))
        & (df_kpi_full["codmes"] >= mes_min)
        & (df_kpi_full["codmes"] <= mes_max)
    ].copy()
    df_causas = df_causas_full[
        (df_causas_full["mype_id"].isin(selected_mypes))
        & (df_causas_full["codmes"] >= mes_min)
        & (df_causas_full["codmes"] <= mes_max)
    ].copy()

    if df_kpi.empty:
        st.warning("No hay registros KPI con los filtros actuales.")
        return

    n_kpi = len(df_kpi)
    viol_if = (df_kpi["ifrecuencia"] > IF_LEGAL).sum()
    viol_is = (df_kpi["isevidad"] > IS_LEGAL).sum()
    viol_both = ((df_kpi["ifrecuencia"] > IF_LEGAL) | (df_kpi["isevidad"] > IS_LEGAL)).sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Registros KPI", f"{n_kpi:,}")
    c2.metric("MYPEs", len(selected_mypes))
    c3.metric("IF medio", f"{df_kpi['ifrecuencia'].mean():.2f}")
    c4.metric("IS medio", f"{df_kpi['isevidad'].mean():.2f}")
    c5.metric(f"% IF > {IF_LEGAL}", f"{100 * viol_if / n_kpi:.1f}%")
    c6.metric(f"% IS > {IS_LEGAL}", f"{100 * viol_is / n_kpi:.1f}%")

    st.info(
        f"Registros MYPE-mes con incumplimiento IF o IS legal: **{viol_both}** "
        f"({100 * viol_both / n_kpi:.1f}% del filtro)."
    )

    tab_kpi, tab_causas, tab_cruzado, tab_reporte = st.tabs(
        ["KPI y tendencias", "Causas", "KPI × causas", "Reporte ejecutivo"]
    )

    with tab_kpi:
        st.subheader("Ranking de MYPEs por severidad (IS)")
        resumen_mype = (
            df_kpi.groupby("mype_id")
            .agg(
                hht=("hht", "sum"),
                n_accidentes=("n_accidentes", "sum"),
                dias_perdidos=("dias_perdidos", "sum"),
                ifrecuencia=("ifrecuencia", "mean"),
                isevidad=("isevidad", "mean"),
            )
            .round(2)
            .sort_values("isevidad", ascending=False)
            .reset_index()
        )
        resumen_mype.insert(1, "empresa", resumen_mype["mype_id"].map(nombre_mype))
        st.dataframe(resumen_mype, use_container_width=True)

        st.subheader("Evolución mensual de IF e IS")
        tendencia = (
            df_kpi.groupby("fecha")
            .agg(
                ifrecuencia=("ifrecuencia", "mean"),
                isevidad=("isevidad", "mean"),
                n_accidentes=("n_accidentes", "sum"),
            )
            .reset_index()
        )
        fig, ax1 = plt.subplots(figsize=(14, 5))
        ax1.set_xlabel("Mes")
        ax1.set_ylabel("IF", color="tab:blue")
        ax1.plot(tendencia["fecha"], tendencia["ifrecuencia"], color="tab:blue", marker="o", label="IF")
        ax1.tick_params(axis="y", labelcolor="tab:blue")
        ax1.grid(True, alpha=0.3)
        ax2 = ax1.twinx()
        ax2.set_ylabel("IS", color="tab:red")
        ax2.plot(tendencia["fecha"], tendencia["isevidad"], color="tab:red", marker="s", label="IS")
        ax2.tick_params(axis="y", labelcolor="tab:red")
        plt.title("Evolución mensual IF / IS — PRODIGY-SST")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        tendencia["mes"] = tendencia["fecha"].dt.month
        tendencia["temporada_lluvias"] = tendencia["mes"].isin([12, 1, 2, 3])
        comp = tendencia.groupby("temporada_lluvias")[["ifrecuencia", "isevidad"]].mean().round(2)
        comp.index = comp.index.map({True: "Temporada lluvias (dic–mar)", False: "Resto del año"})
        st.markdown("**Temporada de lluvias (exploratorio, dic–mar)**")
        st.dataframe(comp, use_container_width=True)

        st.subheader("Heatmap IS por MYPE y mes (codmes)")
        heatmap_data = df_kpi.pivot_table(
            values="isevidad", index="mype_id", columns="codmes", aggfunc="mean"
        ).fillna(0)
        heatmap_data.index = [nombre_mype(str(i)) for i in heatmap_data.index]
        fig2, ax = plt.subplots(figsize=(14, max(5, 0.45 * len(heatmap_data.index))))
        sns.heatmap(
            heatmap_data,
            annot=True,
            fmt=".1f",
            cmap="YlOrRd",
            center=heatmap_data.values.mean() if heatmap_data.size else 0,
            ax=ax,
        )
        ax.set_title("Severidad (IS) por empresa y mes (codmes)")
        ax.set_ylabel("Empresa")
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

        umbral_p90 = df_kpi["isevidad"].quantile(0.9)
        alertas_p90 = df_kpi[df_kpi["isevidad"] > umbral_p90][
            ["mype_id", "codmes", "isevidad", "ifrecuencia", "n_accidentes"]
        ].sort_values("isevidad", ascending=False)
        alertas_p90 = agregar_columna_empresa(alertas_p90)
        st.markdown(f"**Alertas por alto IS (percentil 90 ≈ {umbral_p90:.2f})**")
        st.dataframe(alertas_p90.head(25), use_container_width=True)

        st.subheader(f"Cumplimiento legal — IF > {IF_LEGAL} o IS > {IS_LEGAL} (DS 005-2021-TR)")
        violaciones = df_kpi[
            (df_kpi["ifrecuencia"] > IF_LEGAL) | (df_kpi["isevidad"] > IS_LEGAL)
        ][["mype_id", "codmes", "ifrecuencia", "isevidad", "hht", "n_accidentes", "dias_perdidos"]].sort_values(
            ["isevidad", "ifrecuencia"], ascending=False
        )
        violaciones = agregar_columna_empresa(violaciones)
        st.dataframe(violaciones, use_container_width=True)

    with tab_causas:
        if df_causas.empty:
            st.info("No hay datos de causas para el filtro.")
        else:
            st.subheader("Accidentes por categoría de causa")
            causas_categoria = (
                df_causas.groupby("causa_categoria")
                .agg(
                    Total_Accidentes=("n_accidentes", "sum"),
                    Promedio_por_Registro=("n_accidentes", "mean"),
                    Frecuencia_Registros=("n_accidentes", "count"),
                )
                .round(2)
                .sort_values("Total_Accidentes", ascending=False)
            )
            st.dataframe(causas_categoria, use_container_width=True)
            cc = causas_categoria.reset_index()
            fig3, ax = plt.subplots(figsize=(10, 5))
            sns.barplot(
                data=cc,
                x="causa_categoria",
                y="Total_Accidentes",
                hue="causa_categoria",
                palette="viridis",
                legend=False,
                ax=ax,
            )
            plt.xticks(rotation=45, ha="right")
            fig3.tight_layout()
            st.pyplot(fig3)
            plt.close(fig3)

            st.subheader("Top 10 causas específicas")
            top_causas = (
                df_causas.groupby(["causa_categoria", "causa_especifica"])
                .agg(n_accidentes=("n_accidentes", "sum"))
                .reset_index()
                .sort_values("n_accidentes", ascending=False)
                .head(10)
            )
            st.dataframe(top_causas, use_container_width=True)
            fig4, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=top_causas, y="causa_especifica", x="n_accidentes", palette="coolwarm", ax=ax)
            fig4.tight_layout()
            st.pyplot(fig4)
            plt.close(fig4)

            st.subheader("Causa dominante por empresa (% accidentes)")
            perfil = df_causas.groupby(["mype_id", "causa_categoria"])["n_accidentes"].sum().reset_index()
            perfil["porcentaje"] = (
                perfil.groupby("mype_id")["n_accidentes"].transform(lambda x: x / x.sum() * 100).round(1)
            )
            causa_dom = perfil.loc[perfil.groupby("mype_id")["porcentaje"].idxmax()].copy()
            causa_dom = agregar_columna_empresa(causa_dom)
            st.dataframe(causa_dom, use_container_width=True)
            fig5, ax = plt.subplots(figsize=(12, 5))
            sns.barplot(
                data=causa_dom,
                x="empresa",
                y="porcentaje",
                hue="causa_categoria",
                palette="Set2",
                ax=ax,
            )
            ax.set_title("Causa dominante por empresa")
            ax.set_xlabel("Empresa")
            ax.set_ylabel("% de accidentes")
            plt.xticks(rotation=55, ha="right", fontsize=8)
            fig5.tight_layout()
            st.pyplot(fig5)
            plt.close(fig5)

    with tab_cruzado:
        st.subheader("Severidad (IS) según causa principal (modal por MYPE–mes)")
        agg_c = (
            df_causas.groupby(["mype_id", "codmes"])
            .agg(
                accidentes_causas=("n_accidentes", "sum"),
                causa_principal=("causa_categoria", lambda x: x.value_counts().idxmax()),
            )
            .reset_index()
        )
        df_completo = df_kpi.merge(agg_c, on=["mype_id", "codmes"], how="left")
        if df_completo["causa_principal"].notna().any():
            severidad_por_causa = (
                df_completo.dropna(subset=["causa_principal"])
                .groupby("causa_principal")["isevidad"]
                .mean()
                .sort_values(ascending=False)
            )
            st.dataframe(severidad_por_causa.round(2).to_frame("IS medio"), use_container_width=True)
            fig6, ax = plt.subplots(figsize=(10, 4))
            sns.barplot(x=severidad_por_causa.index, y=severidad_por_causa.values, palette="Reds_r", ax=ax)
            plt.xticks(rotation=45, ha="right")
            ax.set_title("IS medio asociado a causa principal")
            fig6.tight_layout()
            st.pyplot(fig6)
            plt.close(fig6)
        else:
            st.info("Sin datos cruzados suficientes.")

    with tab_reporte:
        st.markdown(generar_reporte_ejecutivo(df_kpi, df_causas))


if __name__ == "__main__":
    main()
