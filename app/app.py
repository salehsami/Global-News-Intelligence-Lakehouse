import os
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config


# ============================================================
# APP CONFIG
# ============================================================

st.set_page_config(
    page_title="Global News Intelligence",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Global News Intelligence Lakehouse")
st.caption(
    "GDELT event analytics • anomaly detection • retrieval-augmented intelligence"
)


# ============================================================
# AUTHENTICATION
# ============================================================

def get_connection():
    cfg = Config()

    warehouse_id = os.environ.get(
        "DATABRICKS_WAREHOUSE_ID"
    )

    if not warehouse_id:
        raise RuntimeError(
            "DATABRICKS_WAREHOUSE_ID is not configured."
        )

    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    return sql.connect(
        server_hostname=urlparse(cfg.host).netloc,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )


def run_query(query, parameters=None):
    """
    Execute a parameterized SQL query and return a DataFrame.
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:

            if parameters:
                cursor.execute(
                    query,
                    parameters
                )
            else:
                cursor.execute(query)

            rows = cursor.fetchall()

            columns = [
                column[0]
                for column in cursor.description
            ]

    return pd.DataFrame(
        rows,
        columns=columns
    )


# ============================================================
# TAB 1 — ANOMALY MONITOR
# ============================================================

anomaly_tab, rag_tab = st.tabs(
    [
        "🔎 Anomaly Monitor",
        "💬 News Intelligence RAG",
    ]
)


with anomaly_tab:

    st.header("Anomalous News Activity")

    positive_only = st.checkbox(
        "Show positive-volume anomalies only",
        value=True,
    )

    if positive_only:

        anomaly_sql = """
        SELECT
            AddedDate,
            CountryCode,
            EventCount,
            EventCountChange,
            EventCountRatio,
            RollingMean7,
            RollingZScore,
            TotalMentions,
            TotalSources,
            TotalArticles,
            AvgGoldsteinScale,
            AvgTone,
            anomaly_score,
            PositiveVolumeAnomaly
        FROM workspace.gold.anomaly_results
        WHERE is_anomaly = true
          AND PositiveVolumeAnomaly = true
        ORDER BY anomaly_score ASC
        LIMIT 50
        """

        anomalies = run_query(anomaly_sql)

    else:

        anomaly_sql = """
        SELECT
            AddedDate,
            CountryCode,
            EventCount,
            EventCountChange,
            EventCountRatio,
            RollingMean7,
            RollingZScore,
            TotalMentions,
            TotalSources,
            TotalArticles,
            AvgGoldsteinScale,
            AvgTone,
            anomaly_score,
            PositiveVolumeAnomaly
        FROM workspace.gold.anomaly_results
        WHERE is_anomaly = true
        ORDER BY anomaly_score ASC
        LIMIT 50
        """

        anomalies = run_query(anomaly_sql)

    # --------------------------------------------------------
    # KPI cards
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Detected anomalies",
        len(anomalies),
    )

    if len(anomalies) > 0:

        positive_count = int(
            anomalies["PositiveVolumeAnomaly"]
            .fillna(False)
            .astype(bool)
            .sum()
        )

        col2.metric(
            "Positive-volume anomalies",
            positive_count,
        )

        col3.metric(
            "Countries represented",
            anomalies["CountryCode"].nunique(),
        )

    # --------------------------------------------------------
    # Results table
    # --------------------------------------------------------

    if len(anomalies) > 0:

        display_df = anomalies.copy()

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Top anomaly")

        top = anomalies.iloc[0]

        st.write(
            f"**{top['CountryCode']} on {top['AddedDate']}**"
        )

        st.write(
            f"Event volume: **{int(top['EventCount']):,}**"
        )

        st.write(
            f"Rolling baseline: "
            f"**{top['RollingMean7']:,.0f}**"
        )

        st.write(
            f"Rolling Z-score: "
            f"**{top['RollingZScore']:.2f}**"
        )

        st.write(
            f"Event-count change: "
            f"**{top['EventCountChange']:+,}**"
        )

    else:

        st.info(
            "No anomalies match the selected filter."
        )


# ============================================================
# TAB 2 — RAG
# ============================================================

with rag_tab:

    st.header("News Intelligence Assistant")

    st.write(
        "Ask a question about the indexed GDELT news documents."
    )

    question = st.chat_input(
        "Ask about recent news activity..."
    )

    if question:

        with st.spinner(
            "Searching the news corpus..."
        ):

            search_sql = """
            SELECT
                chunk_id,
                doc_id,
                CountryCode,
                url,
                chunk_text
            FROM vector_search(
                index => 'workspace.gold.news_chunks_index',
                query_text => ?,
                num_results => 5
            )
            """

            retrieved = run_query(
                search_sql,
                [question]
            )

        if retrieved.empty:

            st.warning(
                "No relevant documents were retrieved."
            )

        else:

            # ----------------------------------------------
            # Build context for the LLM
            # ----------------------------------------------

            context_parts = []

            for i, row in retrieved.iterrows():

                context_parts.append(
                    f"""
SOURCE {i + 1}

Country:
{row['CountryCode']}

URL:
{row['url']}

Content:
{row['chunk_text']}
"""
                )

            context = "\n\n".join(
                context_parts
            )

            prompt = f"""
You are a news intelligence assistant.

Answer the user's question using ONLY the
retrieved news context below.

Do not invent facts.

If the retrieved context does not contain
enough information to answer the question,
say that the available indexed documents
are insufficient.

Include relevant source URLs when useful.

USER QUESTION:
{question}

RETRIEVED CONTEXT:
{context}
"""

            with st.spinner(
                "Generating grounded answer..."
            ):

                answer_df = run_query(
                    """
                    SELECT ai_query(
                        'system.ai.meta-llama-3-3-70b-instruct',
                        ?
                    ) AS answer
                    """,
                    [prompt]
                )

            answer = str(
                answer_df.iloc[0]["answer"]
            )

            st.subheader("Answer")

            st.write(answer)

            st.subheader(
                "Retrieved sources"
            )

            for i, row in retrieved.iterrows():

                with st.expander(
                    f"Source {i + 1} — "
                    f"{row['CountryCode']}"
                ):

                    st.write(
                        row["chunk_text"]
                    )

                    st.markdown(
                        f"[Open source article]({row['url']})"
                    )