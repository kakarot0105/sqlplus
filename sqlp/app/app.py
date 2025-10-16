import io
import os
import re
from typing import Optional

import duckdb
import pandas as pd
import streamlit as st

from sqlp.parser import parse_script
from sqlp.executor import Executor


def get_conn() -> duckdb.DuckDBPyConnection:
    if "duckdb_conn" not in st.session_state:
        st.session_state["duckdb_conn"] = duckdb.connect(database=":memory:")
    return st.session_state["duckdb_conn"]


def sanitize_table_name(filename: str) -> str:
    base = os.path.splitext(os.path.basename(filename))[0]
    name = re.sub(r"\W+", "_", base)
    if not name:
        name = "table"
    if name[0].isdigit():
        name = f"t_{name}"
    return name.lower()


def load_file_to_df(file) -> tuple[pd.DataFrame, str]:
    name = sanitize_table_name(file.name)
    suffix = os.path.splitext(file.name)[1].lower()
    data = file.read()
    bio = io.BytesIO(data)
    if suffix in {".csv"}:
        df = pd.read_csv(bio)
    elif suffix in {".parquet", ".pq"}:
        df = pd.read_parquet(bio)
    elif suffix in {".json"}:
        df = pd.read_json(bio, lines=False)
    else:
        # Try CSV as fallback
        try:
            bio.seek(0)
            df = pd.read_csv(bio)
        except Exception as e:
            raise ValueError(f"Unsupported file type: {suffix}") from e
    return df, name


def register_df_as_table(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame, table_name: str):
    conn.register(table_name, df)


def main():
    st.set_page_config(page_title="SQL+ Local Runner", layout="wide")
    st.title("SQL+ Local Runner")
    st.caption("Upload data, run SQL or SQL+ against DuckDB in-memory.")

    conn = get_conn()

    with st.sidebar:
        st.header("Upload Dataset")
        file = st.file_uploader("Upload CSV / Parquet / JSON", type=["csv", "parquet", "pq", "json"])
        if file is not None:
            try:
                df, tname = load_file_to_df(file)
                register_df_as_table(conn, df, tname)
                st.session_state["last_table_name"] = tname
                st.success(f"Registered table '{tname}' with {len(df)} rows")
            except Exception as e:
                st.error(f"Failed to load file: {e}")

        st.divider()
        st.header("Engine")
        engine_mode = st.radio(
            "Choose engine",
            options=["DuckDB SQL", "SQL+ runtime (DuckDB)"]
        )

    # Main area: preview + editor
    tab_preview, tab_query = st.tabs(["Preview", "Query"])

    with tab_preview:
        if "last_table_name" in st.session_state:
            tname = st.session_state["last_table_name"]
            st.subheader(f"Preview: {tname}")
            try:
                preview_df = conn.execute(f"SELECT * FROM {tname} LIMIT 50").fetchdf()
                st.dataframe(preview_df, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not preview table: {e}")
        else:
            st.info("Upload a dataset to preview.")

    with tab_query:
        default_sql = ""
        if "last_table_name" in st.session_state:
            default_sql = f"SELECT * FROM {st.session_state['last_table_name']} LIMIT 10;"
        sql_text = st.text_area("SQL / SQL+", value=default_sql, height=200, placeholder="Write your SQL or SQL+ here...")
        run = st.button("Run", type="primary")

        if run:
            if not sql_text.strip():
                st.warning("Please enter a query.")
            else:
                try:
                    if engine_mode.startswith("DuckDB"):
                        res_df = conn.execute(sql_text).fetchdf()
                        st.success("Query executed.")
                        st.dataframe(res_df, use_container_width=True)
                        st.download_button(
                            "Download CSV",
                            data=res_df.to_csv(index=False),
                            file_name="result.csv",
                            mime="text/csv",
                        )
                    else:
                        # SQL+ runtime path using shared DuckDB connection
                        script = parse_script(sql_text)
                        ex = Executor(engine="duckdb")
                        conn, res_df = ex.execute_with_result(script, conn=conn)
                        st.success("Script executed via SQL+ runtime.")
                        if res_df is not None:
                            st.dataframe(res_df, use_container_width=True)
                            st.download_button(
                                "Download CSV",
                                data=res_df.to_csv(index=False),
                                file_name="result.csv",
                                mime="text/csv",
                            )
                        else:
                            st.info("No tabular result to display (non-SELECT statements).")
                except Exception as e:
                    st.error(f"Execution error: {e}")


if __name__ == "__main__":
    main()

