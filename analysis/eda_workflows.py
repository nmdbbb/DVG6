"""Read-only EDA workflows called by the analysis notebooks."""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist

from analysis.notebook_utils import (
    FIGURES_DIR,
    query_df,
    require_core_relations,
    require_nonempty_core,
    save_csv,
)


def _save_plot(fig, filename: str, *, rect=None, tight: bool = True) -> None:
    if tight:
        fig.tight_layout(rect=rect)
    fig.savefig(
        FIGURES_DIR / filename,
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    import matplotlib.pyplot as plt

    plt.close(fig)


def run_overview() -> dict[str, pl.DataFrame]:
    """Profile available core relations and the cleaned report fact."""
    import matplotlib.pyplot as plt

    relations = query_df(
        """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'core'
        ORDER BY table_name
        """
    )
    if relations.is_empty():
        print("Schema core chưa có relation. Chạy dbt transform trước.")
        return {"core_relations": relations}

    counts = []
    for table in relations["table_name"].to_list():
        # table comes from information_schema, quoted as an identifier.
        from psycopg import sql
        from analysis.notebook_utils import connect

        with connect() as conn:
            statement = sql.SQL("SELECT COUNT(*) FROM core.{}").format(
                sql.Identifier(table)
            )
            counts.append({"table_name": table, "rows": conn.execute(statement).fetchone()[0]})
    table_counts = pl.DataFrame(counts)
    save_csv(table_counts, "00_core_table_counts.csv")
    output = {"core_relations": relations, "core_table_counts": table_counts}

    if "fct_report" not in relations["table_name"].to_list():
        print("Chưa có core.fct_report.")
        return output
    report_count = query_df("SELECT COUNT(*) AS n FROM core.fct_report")["n"][0]
    if report_count == 0:
        print(
            "core.fct_report existe, tetapi đang rỗng. "
            "Kiểm tra ingest, dbt transform và quality trước các notebook A1–A8."
        )
        return output

    if {"fct_report_raw", "report_duplicate_map"} <= set(relations["table_name"].to_list()):
        report_reconciliation = query_df(
            """
            SELECT 'before_dedup' AS dataset, COUNT(*) AS reports
            FROM core.fct_report_raw
            UNION ALL
            SELECT 'after_dedup', COUNT(*) FROM core.fct_report
            UNION ALL
            SELECT 'duplicates_removed', COUNT(*) FROM core.report_duplicate_map
            """
        )
        save_csv(report_reconciliation, "00_report_reconciliation.csv")
        output["report_reconciliation"] = report_reconciliation

    completeness = query_df(
        """
        SELECT COUNT(*) AS total_reports,
               COUNT(*) FILTER (WHERE age_group_key = -1) AS unknown_age_group,
               COUNT(*) FILTER (WHERE sex_key = -1) AS unknown_sex,
               COUNT(*) FILTER (WHERE state_key = -1) AS unknown_state,
               COUNT(*) FILTER (WHERE received_date_key = -1) AS unknown_received_date,
               COUNT(*) FILTER (WHERE age_yrs IS NULL) AS null_age_years,
               COUNT(*) FILTER (WHERE vax_date IS NULL) AS null_vax_date,
               COUNT(*) FILTER (WHERE onset_date IS NULL) AS null_onset_date,
               MIN(recvdate) AS first_received_date,
               MAX(recvdate) AS last_received_date
        FROM core.fct_report
        """
    )
    demographics = query_df(
        """
        SELECT ag.age_group_label, ag.sort_order, sx.sex_code, COUNT(*) AS reports
        FROM core.fct_report r
        JOIN core.dim_age_group ag ON ag.age_group_key = r.age_group_key
        JOIN core.dim_sex sx ON sx.sex_key = r.sex_key
        GROUP BY ag.age_group_label, ag.sort_order, sx.sex_code
        ORDER BY ag.sort_order, sx.sex_code
        """
    )
    monthly = query_df(
        """
        SELECT date_trunc('month', recvdate)::date AS month, COUNT(*) AS reports
        FROM core.fct_report
        WHERE recvdate IS NOT NULL
        GROUP BY 1 ORDER BY 1
        """
    )
    for name, frame in (
        ("00_report_completeness.csv", completeness),
        ("00_demographic_counts.csv", demographics),
        ("00_monthly_reports.csv", monthly),
    ):
        save_csv(frame, name)
    output.update(
        completeness=completeness,
        demographics=demographics,
        monthly_reports=monthly,
    )
    if not monthly.is_empty():
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(monthly["month"].to_list(), monthly["reports"].to_list(), marker="o")
        ax.set(title="VAERS reports by received month", xlabel="Month", ylabel="Reports")
        ax.grid(alpha=0.25)
        fig.autofmt_xdate()
        _save_plot(fig, "00_reports_by_month.png")
    return output


def _top_symptoms(limit: int = 10) -> pl.DataFrame:
    return query_df(
        f"""
        SELECT fs.symptom_key, ds.symptom_name,
               COUNT(DISTINCT fs.report_key) AS reports
        FROM core.fct_report_symptom fs
        JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
        WHERE fs.symptom_key <> -1
        GROUP BY fs.symptom_key, ds.symptom_name
        ORDER BY reports DESC, fs.symptom_key
        LIMIT {int(limit)}
        """
    )


def run_a1() -> dict[str, pl.DataFrame]:
    import matplotlib.pyplot as plt

    require_core_relations(
        "fct_report", "fct_report_symptom", "fct_report_vaccine",
        "dim_symptom", "dim_vaccine",
    )
    require_nonempty_core("fct_report")
    result = query_df(
        """
        WITH report_manufacturer AS (
            SELECT DISTINCT rv.report_key, dv.vax_manu
            FROM core.fct_report_vaccine rv
            JOIN core.dim_vaccine dv ON dv.vaccine_key = rv.vaccine_key
            WHERE dv.vax_manu IN ('PFIZER-BIONTECH', 'MODERNA', 'JANSSEN')
        ),
        manufacturer_totals AS (
            SELECT vax_manu, COUNT(DISTINCT report_key) AS total_reports
            FROM report_manufacturer GROUP BY vax_manu
        ),
        top_10 AS (
            SELECT fs.symptom_key FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key
            ORDER BY COUNT(DISTINCT fs.report_key) DESC, fs.symptom_key LIMIT 10
        )
        SELECT ds.symptom_name, rm.vax_manu,
               COUNT(DISTINCT fs.report_key) AS report_count,
               mt.total_reports,
               ROUND(100.0 * COUNT(DISTINCT fs.report_key)
                     / NULLIF(mt.total_reports, 0), 3) AS pct_manufacturer_reports
        FROM core.fct_report_symptom fs
        JOIN top_10 t ON t.symptom_key = fs.symptom_key
        JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
        JOIN report_manufacturer rm ON rm.report_key = fs.report_key
        JOIN manufacturer_totals mt ON mt.vax_manu = rm.vax_manu
        GROUP BY ds.symptom_name, rm.vax_manu, mt.total_reports
        ORDER BY ds.symptom_name, rm.vax_manu
        """
    )
    save_csv(result, "01_frequency_by_vaccine.csv")
    if not result.is_empty():
        pdf = result.to_pandas()
        symptoms = pdf.groupby("symptom_name")["report_count"].sum().sort_values().index
        manufacturers = [
            maker for maker in ("PFIZER-BIONTECH", "MODERNA", "JANSSEN")
            if maker in set(pdf["vax_manu"])
        ]
        x = np.arange(len(symptoms))
        width = 0.8 / max(len(manufacturers), 1)
        fig, ax = plt.subplots(figsize=(15, 7))
        for i, maker in enumerate(manufacturers):
            group = pdf[pdf["vax_manu"] == maker].set_index("symptom_name")
            values = group["pct_manufacturer_reports"].reindex(symptoms).fillna(0)
            offset = (i - (len(manufacturers) - 1) / 2) * width
            ax.bar(x + offset, values, width=width, label=maker)
        ax.set(
            xlabel="Symptom",
            ylabel="Percent of manufacturer reports (%)",
            xticks=x,
            xticklabels=symptoms,
        )
        ax.set_title("Top 10 symptoms by manufacturer", fontsize=14, pad=12)
        ax.tick_params(axis="x", labelrotation=45, labelsize=9)
        for label in ax.get_xticklabels():
            label.set_ha("right")
        ax.tick_params(axis="y", labelsize=10)
        ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(title="Manufacturer", frameon=False, ncols=1)
        _save_plot(fig, "01_frequency_by_vaccine.png")
    return {"frequency_by_vaccine": result}


def run_a2() -> dict[str, pl.DataFrame]:
    import matplotlib.pyplot as plt

    require_core_relations(
        "fct_report", "fct_report_symptom", "dim_symptom", "dim_age_group", "dim_sex"
    )
    require_nonempty_core("fct_report")
    result = query_df(
        """
        WITH top_10 AS (
            SELECT fs.symptom_key FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key
            ORDER BY COUNT(DISTINCT fs.report_key) DESC, fs.symptom_key LIMIT 10
        ),
        groups AS (
            SELECT age_group_key, sex_key, COUNT(*) AS n
            FROM core.fct_report
            WHERE age_group_key <> -1 AND sex_key <> -1
            GROUP BY age_group_key, sex_key
        ),
        counts AS (
            SELECT r.age_group_key, r.sex_key, fs.symptom_key,
                   COUNT(DISTINCT r.report_key) AS n
            FROM core.fct_report r
            JOIN core.fct_report_symptom fs ON fs.report_key = r.report_key
            JOIN top_10 t ON t.symptom_key = fs.symptom_key
            WHERE r.age_group_key <> -1 AND r.sex_key <> -1
            GROUP BY r.age_group_key, r.sex_key, fs.symptom_key
        )
        SELECT ag.age_group_label, ag.sort_order, sx.sex_code, ds.symptom_name,
               g.n AS group_reports, COALESCE(c.n, 0) AS reports,
               ROUND(100.0 * COALESCE(c.n, 0) / NULLIF(g.n, 0), 3) AS pct_group_reports
        FROM groups g
        JOIN core.dim_age_group ag ON ag.age_group_key = g.age_group_key
        JOIN core.dim_sex sx ON sx.sex_key = g.sex_key
        CROSS JOIN top_10 t
        JOIN core.dim_symptom ds ON ds.symptom_key = t.symptom_key
        LEFT JOIN counts c ON c.age_group_key = g.age_group_key
                          AND c.sex_key = g.sex_key AND c.symptom_key = t.symptom_key
        ORDER BY ag.sort_order, sx.sex_code, pct_group_reports DESC
        """
    )
    save_csv(result, "02_age_sex_symptom_frequency.csv")
    if not result.is_empty():
        wide = result.pivot(
            on="symptom_name", index=["age_group_label", "sort_order", "sex_code"],
            values="pct_group_reports", aggregate_function="first",
        ).sort(["sort_order", "sex_code"]).fill_null(0)
        features = [c for c in wide.columns
                    if c not in {"age_group_label", "sort_order", "sex_code"}]
        sex_tables = {}
        sex_matrices = {}
        for sex_code, sex_label in (("M", "male"), ("F", "female")):
            sex_wide = wide.filter(pl.col("sex_code") == sex_code)
            sex_tables[sex_label] = sex_wide.select(
                ["age_group_label", *features]
            ).rename({"age_group_label": "age_group"})
            save_csv(sex_tables[sex_label], f"02_{sex_label}_symptom_frequency.csv")
            sex_matrices[sex_code] = sex_wide.select(
                [pl.col(column).cast(pl.Float64) for column in features]
            ).to_numpy()

        vmax = max(
            float(np.nanmax(matrix))
            for matrix in sex_matrices.values()
            if matrix.size
        )
        vmax = vmax if vmax > 0 else 1.0
        fig = plt.figure(figsize=(17, 7))
        grid = fig.add_gridspec(
            1, 3, width_ratios=(1, 1, 0.035), wspace=0.26
        )
        axes = [
            fig.add_subplot(grid[0, 0]),
            fig.add_subplot(grid[0, 1]),
        ]
        colorbar_ax = fig.add_subplot(grid[0, 2])
        for ax, (sex_code, sex_label) in zip(
            axes, (("M", "Male"), ("F", "Female")), strict=True
        ):
            table = sex_tables[sex_label.lower()]
            labels = table["age_group"].to_list()
            im = ax.imshow(
                sex_matrices[sex_code], aspect="auto", cmap="YlOrRd", vmin=0, vmax=vmax
            )
            ax.set_xlim(-0.5, len(features) - 0.5)
            ax.set_yticks(range(len(labels)), labels)
            ax.set_xticks(range(len(features)), features, rotation=60, ha="right")
            ax.tick_params(axis="x", labelsize=9)
            ax.tick_params(axis="y", labelsize=9)
            ax.set_title(f"{sex_label}: symptom reports by age group", fontsize=13, pad=10)
        fig.colorbar(im, cax=colorbar_ax, label="Reports within age-sex group (%)")
        _save_plot(fig, "02_age_sex_heatmap.png")
        return {"male_symptom_frequency": sex_tables["male"],
                "female_symptom_frequency": sex_tables["female"]}
    return {"age_sex_frequency": result}


def run_a3() -> dict[str, pl.DataFrame]:
    """Test independence of manufacturer/year and top-10 symptom profiles."""
    require_core_relations(
        "fct_report", "fct_report_symptom", "dim_symptom",
        "fct_report_vaccine", "dim_vaccine", "dim_age_group", "dim_sex",
    )
    require_nonempty_core("fct_report")
    reports = query_df(
        """
        WITH top_10_symptoms AS (
            SELECT fs.symptom_key, ds.symptom_name
            FROM core.fct_report_symptom fs
            JOIN core.fct_report r ON r.report_key = fs.report_key
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key, ds.symptom_name
            ORDER BY COUNT(DISTINCT r.report_key) DESC, fs.symptom_key
            LIMIT 10
        ),
        symptom_profiles AS (
            SELECT r.report_key,
                   COALESCE(
                       STRING_AGG(DISTINCT t.symptom_name, ' + ' ORDER BY t.symptom_name),
                       'NO TOP-10 SYMPTOM'
                   ) AS symptom_profile
            FROM core.fct_report r
            LEFT JOIN core.fct_report_symptom fs ON fs.report_key = r.report_key
            LEFT JOIN top_10_symptoms t ON t.symptom_key = fs.symptom_key
            GROUP BY r.report_key
        ),
        report_manufacturer AS (
            SELECT r.report_key,
                   CASE
                       WHEN COUNT(DISTINCT dv.vax_manu) = 0 THEN 'UNKNOWN'
                       WHEN COUNT(DISTINCT dv.vax_manu) = 1 THEN MIN(dv.vax_manu)
                       ELSE 'MULTIPLE'
                   END AS manufacturer
            FROM core.fct_report r
            LEFT JOIN core.fct_report_vaccine rv ON rv.report_key = r.report_key
            LEFT JOIN core.dim_vaccine dv ON dv.vaccine_key = rv.vaccine_key
            GROUP BY r.report_key
        )
        SELECT r.report_key,
               COALESCE(EXTRACT(YEAR FROM r.recvdate)::integer::text, 'UNKNOWN') AS report_year,
               rm.manufacturer,
               sp.symptom_profile,
               CASE
                   WHEN r.age_group_key = -1 OR ag.age_group_label IS NULL THEN 'UNKNOWN'
                   ELSE ag.age_group_label
               END AS age_group,
               CASE
                   WHEN r.sex_key = -1 OR sx.sex_code IS NULL THEN 'UNKNOWN'
                   ELSE sx.sex_code
               END AS gender
        FROM core.fct_report r
        JOIN report_manufacturer rm ON rm.report_key = r.report_key
        JOIN symptom_profiles sp ON sp.report_key = r.report_key
        LEFT JOIN core.dim_age_group ag ON ag.age_group_key = r.age_group_key
        LEFT JOIN core.dim_sex sx ON sx.sex_key = r.sex_key
        """
    )

    # Each report contributes exactly once to each table. Rare symptom profiles
    # are pooled so the contingency tables are not dominated by one-off patterns.
    profile_counts = reports.group_by("symptom_profile").len()
    rare_profiles = profile_counts.filter(pl.col("len") < 5)["symptom_profile"].to_list()
    reports = reports.with_columns(
        pl.when(pl.col("symptom_profile").is_in(list(rare_profiles)))
        .then(pl.lit("OTHER / RARE PROFILES"))
        .otherwise(pl.col("symptom_profile"))
        .alias("symptom_profile")
    )
    report_pdf = reports.to_pandas()
    maker_table = pd.crosstab(report_pdf["manufacturer"], report_pdf["symptom_profile"])
    year_table = pd.crosstab(report_pdf["report_year"], report_pdf["symptom_profile"])
    age_reports = report_pdf[report_pdf["age_group"] != "UNKNOWN"]
    age_table = pd.crosstab(age_reports["age_group"], age_reports["symptom_profile"])
    gender_reports = report_pdf[report_pdf["gender"] != "UNKNOWN"]
    gender_table = pd.crosstab(gender_reports["gender"], gender_reports["symptom_profile"])

    from scipy.stats import chi2_contingency

    test_rows = []
    comparison_tables = (
        ("manufacturer × symptom profile", maker_table),
        ("report year × symptom profile", year_table),
        ("age group × symptom profile", age_table),
        ("gender × symptom profile", gender_table),
    )
    n_comparisons = len(comparison_tables)
    for pair_name, table in comparison_tables:
        observed = table.to_numpy(dtype=np.int64)
        if observed.shape[0] < 2 or observed.shape[1] < 2:
            raise RuntimeError(f"A3 không đủ nhóm để kiểm định {pair_name}.")
        chi2, p_value, degrees_freedom, expected = chi2_contingency(
            observed, correction=False
        )
        n = int(observed.sum())
        denominator = n * min(observed.shape[0] - 1, observed.shape[1] - 1)
        test_rows.append({
            "variable_pair": pair_name,
            "chi_square": float(chi2),
            "degrees_freedom": int(degrees_freedom),
            "p_value": float(p_value),
            "p_adjusted_bonferroni": min(float(p_value) * n_comparisons, 1.0),
            "cramers_v": float(np.sqrt(chi2 / denominator)) if denominator else np.nan,
            "reports": n,
            "min_expected_count": float(expected.min()),
            "expected_cells_below_5": int((expected < 5).sum()),
            "symptom_profiles_after_pooling": int(table.shape[1]),
        })

    maker_output = pl.from_pandas(maker_table.rename_axis("manufacturer").reset_index())
    year_output = pl.from_pandas(year_table.rename_axis("report_year").reset_index())
    age_output = pl.from_pandas(age_table.rename_axis("age_group").reset_index())
    gender_output = pl.from_pandas(gender_table.rename_axis("gender").reset_index())
    tests = pl.DataFrame(test_rows)
    save_csv(maker_output, "03_manufacturer_symptom_profile_contingency.csv")
    save_csv(year_output, "03_year_symptom_profile_contingency.csv")
    save_csv(age_output, "03_age_symptom_profile_contingency.csv")
    save_csv(gender_output, "03_gender_symptom_profile_contingency.csv")
    save_csv(tests, "03_categorical_independence_tests.csv")
    return {
        "manufacturer_symptom_profile_contingency": maker_output,
        "year_symptom_profile_contingency": year_output,
        "age_symptom_profile_contingency": age_output,
        "gender_symptom_profile_contingency": gender_output,
        "independence_tests": tests,
    }


def run_a4() -> dict[str, pl.DataFrame]:
    import matplotlib.pyplot as plt

    require_core_relations(
        "fct_report", "fct_report_symptom", "dim_symptom", "dim_age_group"
    )
    require_nonempty_core("fct_report")
    data = query_df(
        """
        WITH top_10 AS (
            SELECT fs.symptom_key, ds.symptom_name
            FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key, ds.symptom_name
            ORDER BY COUNT(DISTINCT fs.report_key) DESC, fs.symptom_key LIMIT 10
        ),
        counts AS (
            SELECT fs.symptom_key, r.age_group_key,
                   COUNT(DISTINCT r.report_key) AS n
            FROM core.fct_report r
            JOIN core.fct_report_symptom fs ON fs.report_key = r.report_key
            JOIN top_10 t ON t.symptom_key = fs.symptom_key
            WHERE r.age_group_key <> -1
            GROUP BY fs.symptom_key, r.age_group_key
        )
        SELECT t.symptom_name, ag.age_group_label, ag.sort_order,
               COALESCE(c.n, 0) AS reports
        FROM top_10 t CROSS JOIN core.dim_age_group ag
        LEFT JOIN counts c ON c.symptom_key = t.symptom_key
                          AND c.age_group_key = ag.age_group_key
        WHERE ag.age_group_key <> -1
        ORDER BY t.symptom_name, ag.sort_order
        """
    )
    save_csv(data, "04_symptom_age_profile.csv")
    if data.height < 2:
        raise RuntimeError("Cần dữ liệu của ít nhất hai triệu chứng để phân cụm.")
    wide = data.pivot(
        on="age_group_label", index="symptom_name", values="reports",
        aggregate_function="sum",
    ).fill_null(0)
    names = wide["symptom_name"].to_list()
    values = wide.select([c for c in wide.columns if c != "symptom_name"]).to_numpy().astype(float)
    sums = values.sum(axis=1, keepdims=True)
    profiles = np.divide(values, sums, out=np.zeros_like(values), where=sums != 0)
    distances = np.nan_to_num(pdist(profiles, metric="cosine"), nan=0.0, posinf=0.0)
    tree = linkage(distances, method="average")
    fig, ax = plt.subplots(figsize=(10, max(5.5, len(names) * 0.38)))
    dendrogram(tree, labels=names, orientation="right", leaf_font_size=7, ax=ax)
    ax.set_title("Hierarchical clustering of symptom age profiles", fontsize=14, pad=12)
    ax.set_xlabel("Cosine distance", fontsize=11)
    ax.set_ylabel("Symptom", fontsize=11)
    ax.tick_params(axis="both", labelsize=9)
    ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    _save_plot(fig, "04_symptom_age_dendrogram.png")
    return {"symptom_age_profile": data}


def run_a5() -> dict[str, pl.DataFrame]:
    require_core_relations("fct_report", "fct_report_symptom", "dim_symptom")
    top = _top_symptoms(10)
    names = top["symptom_name"].to_list()
    n_reports = query_df("SELECT COUNT(*) AS n FROM core.fct_report")["n"][0]
    if n_reports == 0 or not names:
        raise RuntimeError("Không có báo cáo hoặc triệu chứng để mining.")
    pairs = query_df(
        """
        WITH chosen AS (
            SELECT fs.symptom_key FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key
            ORDER BY COUNT(DISTINCT fs.report_key) DESC, fs.symptom_key LIMIT 10
        )
        SELECT DISTINCT fs.report_key, ds.symptom_name
        FROM core.fct_report_symptom fs
        JOIN chosen c ON c.symptom_key = fs.symptom_key
        JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
        """
    ).to_pandas()
    all_ids = query_df("SELECT report_key FROM core.fct_report")["report_key"].to_list()
    matrix = pd.crosstab(pairs["report_key"], pairs["symptom_name"]).astype(bool)
    matrix = matrix.reindex(index=all_ids, columns=names, fill_value=False)
    from mlxtend.frequent_patterns import apriori, association_rules

    frequent = apriori(
        matrix, min_support=0.01, use_colnames=True, max_len=3, low_memory=True
    )
    if frequent.empty or not frequent["itemsets"].map(len).gt(1).any():
        output = pl.DataFrame()
    else:
        rules = association_rules(frequent, metric="confidence", min_threshold=0.5)
        rules = rules[rules["lift"] > 1].copy()
        rules["antecedents"] = rules["antecedents"].map(lambda x: ", ".join(sorted(x)))
        rules["consequents"] = rules["consequents"].map(lambda x: ", ".join(sorted(x)))
        rules = rules.sort_values(["lift", "confidence"], ascending=False)
        output = pl.from_pandas(rules)
    save_csv(output, "05_association_rules.csv")
    print("Parameters fixed before analysis: support=0.01, confidence=0.50, lift>1, max_len=3.")
    return {"association_rules": output}


def run_a11(top_n: int = 10, min_pair_reports: int = 1) -> dict[str, pl.DataFrame]:
    """Summarize report-level symptom co-occurrence and association measures."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    if top_n < 2:
        raise ValueError("top_n must be at least 2 to form symptom pairs")
    if min_pair_reports < 1:
        raise ValueError("min_pair_reports must be at least 1")

    require_core_relations("fct_report", "fct_report_symptom", "dim_symptom")
    require_nonempty_core("fct_report")

    reports = query_df("SELECT report_key FROM core.fct_report").to_pandas()
    n_reports = reports["report_key"].nunique()
    selected = query_df(
        """
        WITH top_symptoms AS (
            SELECT fs.symptom_key, ds.symptom_name,
                   COUNT(DISTINCT fs.report_key) AS reports
            FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key, ds.symptom_name
            ORDER BY reports DESC, fs.symptom_key
            LIMIT %s
        )
        SELECT DISTINCT fs.report_key, ts.symptom_key, ts.symptom_name, ts.reports
        FROM core.fct_report_symptom fs
        JOIN top_symptoms ts ON ts.symptom_key = fs.symptom_key
        ORDER BY ts.reports DESC, ts.symptom_key, fs.report_key
        """,
        [top_n],
    ).to_pandas()
    if n_reports == 0 or selected.empty:
        raise RuntimeError("No reports or selected symptoms are available for co-occurrence analysis.")

    names = (
        selected[["symptom_key", "symptom_name"]]
        .drop_duplicates()
        ["symptom_name"]
        .tolist()
    )
    binary = pd.crosstab(selected["report_key"], selected["symptom_name"])
    binary = binary.reindex(columns=names, fill_value=0).astype(bool)
    symptom_reports = binary.sum(axis=0).to_numpy(dtype=np.int64)
    co_counts = binary.astype(np.int64).to_numpy().T @ binary.astype(np.int64).to_numpy()
    support = co_counts / n_reports
    marginal_support = symptom_reports / n_reports
    denominator = np.outer(marginal_support, marginal_support)
    lift = np.divide(support, denominator, out=np.zeros_like(support), where=denominator > 0)
    np.fill_diagonal(lift, np.nan)

    pair_rows = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pair_count = int(co_counts[i, j])
            if pair_count < min_pair_reports:
                continue
            pair_rows.append(
                {
                    "symptom_a": names[i],
                    "symptom_b": names[j],
                    "co_reports": pair_count,
                    "reports_with_a": int(symptom_reports[i]),
                    "reports_with_b": int(symptom_reports[j]),
                    "total_reports": int(n_reports),
                    "support": float(support[i, j]),
                    "p_b_given_a": float(pair_count / symptom_reports[i]),
                    "p_a_given_b": float(pair_count / symptom_reports[j]),
                    "lift": float(lift[i, j]),
                }
            )
    pair_stats = pl.DataFrame(
        pair_rows,
        schema={
            "symptom_a": pl.String,
            "symptom_b": pl.String,
            "co_reports": pl.Int64,
            "reports_with_a": pl.Int64,
            "reports_with_b": pl.Int64,
            "total_reports": pl.Int64,
            "support": pl.Float64,
            "p_b_given_a": pl.Float64,
            "p_a_given_b": pl.Float64,
            "lift": pl.Float64,
        },
    )
    if not pair_stats.is_empty():
        pair_stats = pair_stats.sort("co_reports", descending=True)
    save_csv(pair_stats, "11_symptom_cooccurrence_pairs.csv")

    fig, (ax_counts, ax_lift) = plt.subplots(1, 2, figsize=(16, max(7, len(names) * 0.65)))
    count_image = ax_counts.imshow(co_counts, cmap="YlOrRd", aspect="auto")
    lift_values = lift[np.isfinite(lift)]
    vmax = max(2.0, float(np.percentile(lift_values, 95))) if lift_values.size else 2.0
    lift_image = ax_lift.imshow(
        np.ma.masked_invalid(lift),
        cmap="coolwarm",
        norm=TwoSlopeNorm(vmin=0, vcenter=1, vmax=vmax),
        aspect="auto",
    )
    for ax in (ax_counts, ax_lift):
        ax.set_xticks(range(len(names)), names, rotation=55, ha="right")
        ax.set_yticks(range(len(names)), names)
        ax.tick_params(axis="both", labelsize=8)
    ax_counts.set_title("Reports containing both symptoms")
    ax_lift.set_title("Lift (diagonal omitted)")
    for i in range(len(names)):
        for j in range(len(names)):
            ax_counts.text(j, i, f"{co_counts[i, j]:,}", ha="center", va="center", fontsize=7)
            if i != j:
                color = "white" if lift[i, j] < 0.65 or lift[i, j] > vmax * 0.75 else "#222222"
                ax_lift.text(j, i, f"{lift[i, j]:.2f}", ha="center", va="center", fontsize=7, color=color)
    fig.colorbar(count_image, ax=ax_counts, label="Distinct reports")
    fig.colorbar(lift_image, ax=ax_lift, label=f"Lift (color scale capped at {vmax:.2f})")
    fig.suptitle(
        f"Symptom co-occurrence among {n_reports:,} distinct reports (top {len(names)} symptoms)",
        fontsize=14,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save_plot(fig, "11_symptom_cooccurrence_heatmaps.png")

    print(
        "Support = co-reports / all distinct reports; P(B|A) and P(A|B) use the corresponding "
        "symptom report count as denominator. Lift > 1 means the pair co-occurs more often than "
        "expected under independence in this report set. This is co-mention, not causality."
    )
    return {"symptom_cooccurrence_pairs": pair_stats}


def run_a12(
    group_by_x: str = "age_group",
    group_by_y: str = "sex",
    selected_symptom: str | None = None,
    top_n: int = 10,
) -> dict[str, pl.DataFrame]:
    """Compare report-level symptom percentages across two selected dimensions."""
    import matplotlib.pyplot as plt
    from textwrap import fill

    dimensions = {
        "product": "COALESCE(NULLIF(BTRIM(dv.vax_name), ''), 'UNKNOWN')",
        "manufacturer": "COALESCE(NULLIF(BTRIM(dv.vax_manu), ''), 'UNKNOWN')",
        "dose_series": "COALESCE(NULLIF(BTRIM(rv.dose_series), ''), 'UNKNOWN')",
        "age_group": (
            "CASE WHEN r.age_group_key = -1 OR ag.age_group_label IS NULL "
            "THEN 'UNKNOWN' ELSE ag.age_group_label END"
        ),
        "sex": (
            "CASE WHEN r.sex_key = -1 OR sx.sex_code IS NULL OR UPPER(sx.sex_code) IN ('U', 'UNKNOWN') "
            "THEN 'UNKNOWN / UNSPECIFIED' ELSE sx.sex_code END"
        ),
        "report_year": "COALESCE(EXTRACT(YEAR FROM r.recvdate)::integer::text, 'UNKNOWN')",
    }
    if group_by_x not in dimensions or group_by_y not in dimensions:
        raise ValueError(f"Dimensions must be selected from: {', '.join(dimensions)}")
    if group_by_x == group_by_y:
        raise ValueError("Choose two different grouping dimensions")
    if top_n < 1:
        raise ValueError("top_n must be a positive integer")

    require_core_relations(
        "fct_report", "fct_report_symptom", "fct_report_vaccine",
        "dim_symptom", "dim_vaccine", "dim_age_group", "dim_sex",
    )
    require_nonempty_core("fct_report")

    x_expr = dimensions[group_by_x]
    y_expr = dimensions[group_by_y]
    selected_filter = "(%s::text IS NULL OR LOWER(BTRIM(ds.symptom_name)) = LOWER(BTRIM(%s::text)))"
    stats = query_df(
        f"""
        WITH selected_symptoms AS (
            SELECT ds.symptom_key, ds.symptom_name,
                   COUNT(DISTINCT fs.report_key) AS symptom_total
            FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
              AND {selected_filter}
            GROUP BY ds.symptom_key, ds.symptom_name
            ORDER BY symptom_total DESC, ds.symptom_name
            LIMIT CASE WHEN %s::text IS NULL THEN %s ELSE 1 END
        ),
        report_groups AS (
            SELECT DISTINCT r.report_key,
                   {x_expr} AS group_x,
                   {y_expr} AS group_y
            FROM core.fct_report r
            LEFT JOIN core.dim_age_group ag ON ag.age_group_key = r.age_group_key
            LEFT JOIN core.dim_sex sx ON sx.sex_key = r.sex_key
            LEFT JOIN core.fct_report_vaccine rv ON rv.report_key = r.report_key
            LEFT JOIN core.dim_vaccine dv ON dv.vaccine_key = rv.vaccine_key
        ),
        group_counts AS (
            SELECT group_x, group_y, COUNT(DISTINCT report_key)::bigint AS group_reports
            FROM report_groups
            GROUP BY group_x, group_y
        )
        SELECT gc.group_x,
               gc.group_y,
               ss.symptom_key,
               ss.symptom_name,
               gc.group_reports,
               COUNT(DISTINCT fs.report_key)::bigint AS symptom_reports,
               100.0 * COUNT(DISTINCT fs.report_key)
                   / NULLIF(gc.group_reports, 0) AS symptom_pct
        FROM group_counts gc
        JOIN report_groups rg ON rg.group_x = gc.group_x AND rg.group_y = gc.group_y
        CROSS JOIN selected_symptoms ss
        LEFT JOIN core.fct_report_symptom fs
          ON fs.report_key = rg.report_key AND fs.symptom_key = ss.symptom_key
        GROUP BY gc.group_x, gc.group_y, gc.group_reports,
                 ss.symptom_key, ss.symptom_name
        ORDER BY gc.group_x, gc.group_y, ss.symptom_name
        """,
        [selected_symptom, selected_symptom, selected_symptom, top_n],
    )
    if stats.is_empty():
        if selected_symptom and selected_symptom.strip():
            raise RuntimeError(f"No reports found for symptom '{selected_symptom}'. Check its exact name.")
        raise RuntimeError("No report-symptom combinations are available for this comparison.")

    save_csv(stats, "12_symptom_percentage_by_group.csv")
    frame = stats.to_pandas()
    if selected_symptom and selected_symptom.strip():
        plot_symptoms = [selected_symptom.strip()]
    else:
        plot_symptoms = (
            frame.groupby("symptom_name", as_index=False)["symptom_reports"]
            .sum()
            .sort_values(["symptom_reports", "symptom_name"], ascending=[False, True])
            .head(5)["symptom_name"]
            .tolist()
        )

    def visible_groups(data: pd.DataFrame, column: str) -> list[str]:
        totals = (
            data.groupby(column, as_index=False)["group_reports"]
            .max()
            .sort_values(["group_reports", column], ascending=[False, True])
        )
        labels = totals[column].astype(str).head(10).tolist()
        all_labels = totals[column].astype(str).tolist()
        unknown = [label for label in all_labels if label.upper().startswith("UNKNOWN")]
        labels = [label for label in labels if not label.upper().startswith("UNKNOWN")]
        dimension = group_by_x if column == "group_x" else group_by_y

        if dimension == "age_group":
            age_order = ["5-11", "12-15", "16-18", "19-30", "31-50", "51-65", "66+"]
            labels = sorted(labels, key=lambda value: age_order.index(value) if value in age_order else len(age_order))
        elif dimension == "sex":
            sex_order = {"F": 0, "M": 1}
            labels = sorted(labels, key=lambda value: (sex_order.get(value, 2), value))
        elif dimension == "report_year":
            labels = sorted(labels, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value))
        elif dimension == "dose_series":
            labels = sorted(labels, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value))

        return labels + unknown[:1]

    ncols = 1 if len(plot_symptoms) == 1 else 2
    nrows = (len(plot_symptoms) + ncols - 1) // ncols
    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(10.5 if ncols == 1 else 14.5, (6.0 if ncols == 1 else 4.4) * nrows),
        squeeze=False,
    )
    visible_max = float(frame["symptom_pct"].max())
    color_max = min(100.0, max(10.0, float(np.ceil(visible_max / 10.0) * 10.0)))
    images = []
    for ax, symptom in zip(axes.flat, plot_symptoms):
        data = frame[frame["symptom_name"] == symptom]
        x_labels = visible_groups(data, "group_x")
        y_labels = visible_groups(data, "group_y")
        panel = data.pivot(index="group_y", columns="group_x", values="symptom_pct")
        panel = panel.reindex(index=y_labels, columns=x_labels)
        image = ax.imshow(
            np.ma.masked_invalid(panel.to_numpy(dtype=float)),
            cmap="YlOrRd",
            vmin=0,
            vmax=color_max,
            aspect="auto",
            interpolation="none",
        )
        images.append(image)
        ax.set_title(symptom, fontsize=11, pad=9, loc="left", fontweight="semibold")
        ax.set_xticks(
            range(len(x_labels)),
            [fill(label, width=20, break_long_words=False) for label in x_labels],
            rotation=60,
            ha="right",
            rotation_mode="anchor",
        )
        ax.set_yticks(
            range(len(y_labels)),
            [fill(label, width=22, break_long_words=False) for label in y_labels],
        )
        ax.tick_params(axis="x", labelsize=8, pad=5)
        ax.tick_params(axis="y", labelsize=8, pad=4)
        ax.set_xlabel(group_by_x.replace("_", " ").title(), fontsize=9, labelpad=8)
        ax.set_ylabel(group_by_y.replace("_", " ").title(), fontsize=9, labelpad=8)
        ax.set_xticks(np.arange(-0.5, len(x_labels), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(y_labels), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.0)
        ax.tick_params(which="minor", bottom=False, left=False)
        ax.set_xlim(-0.5, len(x_labels) - 0.5)
        ax.set_ylim(len(y_labels) - 0.5, -0.5)
        annotation_size = 6 if len(x_labels) * len(y_labels) > 70 else 7
        for row_idx, y_value in enumerate(y_labels):
            for col_idx, x_value in enumerate(x_labels):
                cell = data[(data["group_x"] == x_value) & (data["group_y"] == y_value)]
                if cell.empty:
                    continue
                record = cell.iloc[0]
                pct = float(record["symptom_pct"] or 0)
                count = int(record["symptom_reports"])
                denom = int(record["group_reports"])
                ax.text(
                    col_idx, row_idx, f"{pct:.1f}%\n{count:,}/{denom:,}",
                    ha="center", va="center", fontsize=annotation_size,
                    color="white" if pct >= color_max * 0.58 else "#222222",
                )
    for ax in axes.flat[len(plot_symptoms):]:
        ax.set_visible(False)
    fig.suptitle(
        f"Symptom reporting by {group_by_x.replace('_', ' ').title()} × "
        f"{group_by_y.replace('_', ' ').title()}\n"
        "Cell labels show percentage and symptom reports / subgroup reports",
        fontsize=13,
        fontweight="semibold",
        y=0.985,
    )
    fig.subplots_adjust(left=0.09, right=0.89, bottom=0.18, top=0.92, wspace=0.35, hspace=0.55)
    colorbar_ax = fig.add_axes([0.925, 0.2, 0.018, 0.68])
    fig.colorbar(
        images[0],
        cax=colorbar_ax,
        label=f"Reports with symptom (%)\nColor scale: 0–{color_max:.0f}%",
    )
    _save_plot(fig, "12_symptom_percentage_by_group.png", tight=False)
    print(
        "Each cell shows symptom reports / all distinct reports in that group. UNKNOWN categories are retained. "
        "For product or dose-series comparisons, one report can belong to multiple groups if multiple vaccines were recorded. "
        "These are report percentages, not incidence among vaccinated people."
    )
    return {"symptom_percentage_by_group": stats}


def run_a6() -> dict[str, pl.DataFrame]:
    """Train a hexagonal SOM on a reproducible report-by-symptom sample."""
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib.patches import RegularPolygon
    from minisom import MiniSom

    require_core_relations("fct_report", "fct_report_symptom", "dim_symptom")
    top = _top_symptoms(10)
    names = top["symptom_name"].to_list()
    pairs = query_df(
        """
        WITH chosen AS (
            SELECT fs.symptom_key FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key
            ORDER BY COUNT(DISTINCT fs.report_key) DESC, fs.symptom_key LIMIT 10
        ),
        sample_reports AS (
            SELECT report_key FROM core.fct_report
            ORDER BY md5(report_key::text) LIMIT 10000
        )
        SELECT DISTINCT sr.report_key, ds.symptom_name
        FROM sample_reports sr
        JOIN core.fct_report_symptom fs ON fs.report_key = sr.report_key
        JOIN chosen c ON c.symptom_key = fs.symptom_key
        JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
        """
    ).to_pandas()
    if not names or pairs.empty:
        raise RuntimeError("Không có mẫu báo cáo/triệu chứng để chạy SOM.")
    binary = pd.crosstab(pairs["report_key"], pairs["symptom_name"])
    binary = binary.reindex(columns=names, fill_value=0).astype(float)
    data = binary.to_numpy(dtype=float)
    if data.shape[0] < 2 or data.shape[1] < 2:
        raise RuntimeError("SOM cần ít nhất 2 báo cáo và 2 triệu chứng.")

    # Fixed seed and fixed sample make notebook runs reproducible. Hex topology
    # preserves neighborhood structure; weights remain on the binary 0..1 scale.
    grid_x = grid_y = 15
    som = MiniSom(
        grid_x, grid_y, data.shape[1], sigma=2.0, learning_rate=0.5,
        topology="hexagonal", neighborhood_function="gaussian", random_seed=42,
    )
    som.random_weights_init(data)
    som.train_random(data, num_iteration=min(20_000, max(2_000, len(data) * 2)),
                     verbose=False)

    weights = som.get_weights()
    hits = np.zeros((grid_x, grid_y), dtype=int)
    neuron_x, neuron_y, distances = [], [], []
    for row in data:
        x, y = som.winner(row)
        hits[x, y] += 1
        neuron_x.append(x)
        neuron_y.append(y)
        distances.append(float(np.linalg.norm(row - weights[x, y])))

    assignments = pl.DataFrame({
        "report_key": binary.index.to_list(),
        "neuron_x": neuron_x,
        "neuron_y": neuron_y,
        "distance_to_prototype": distances,
    })
    occupancy = pl.DataFrame([
        {"neuron_x": x, "neuron_y": y, "report_count": int(hits[x, y])}
        for x in range(grid_x) for y in range(grid_y)
    ])
    codebook = pl.DataFrame([
        {"neuron_x": x, "neuron_y": y, "symptom_name": name,
         "prototype_weight": float(weights[x, y, j]),
         "report_count": int(hits[x, y])}
        for x in range(grid_x) for y in range(grid_y)
        for j, name in enumerate(names)
    ])
    summary = pl.DataFrame({
        "metric": ["sample_reports", "symptoms", "grid_x", "grid_y",
                   "occupied_neurons", "mean_quantization_error"],
        "value": [float(len(data)), float(len(names)), float(grid_x), float(grid_y),
                  float(np.count_nonzero(hits)), float(np.mean(distances))],
    })
    save_csv(assignments, "06_som_report_assignments.csv")
    save_csv(occupancy, "06_som_neuron_occupancy.csv")
    save_csv(codebook, "06_som_codebook.csv")

    # Component planes: each subplot is one symptom on the same learned map.
    # Shared 0..1 color scale means warmer cells have higher prototype weights.
    cols = 5
    rows = int(np.ceil(len(names) / cols))
    fig = plt.figure(figsize=(16, rows * 3.2))
    grid = fig.add_gridspec(
        rows, cols + 1, width_ratios=[1] * cols + [0.16],
        wspace=0.12, hspace=0.22,
    )
    axes = np.array([
        [fig.add_subplot(grid[row, col]) for col in range(cols)]
        for row in range(rows)
    ], dtype=object)
    colorbar_ax = fig.add_subplot(grid[:, cols])
    cmap = plt.get_cmap("YlOrRd")
    for j, name in enumerate(names):
        ax = axes.flat[j]
        values = weights[:, :, j]
        for x in range(grid_x):
            for y in range(grid_y):
                center = (x + 0.5 * (y % 2), y * np.sqrt(3) / 2)
                patch = RegularPolygon(
                    center, numVertices=6, radius=0.49, orientation=np.pi / 6,
                    facecolor=cmap(float(np.clip(values[x, y], 0, 1))),
                    edgecolor="white", linewidth=0.25,
                )
                ax.add_patch(patch)
        ax.set_title(name, fontsize=10, pad=6)
        ax.set_aspect("equal")
        ax.set_xlim(-0.7, grid_x + 0.7)
        ax.set_ylim(-0.6, grid_y * np.sqrt(3) / 2 + 0.6)
        ax.axis("off")
    for ax in axes.flat[len(names):]:
        ax.axis("off")
    norm = plt.Normalize(0, 1)
    fig.colorbar(
        cm.ScalarMappable(norm=norm, cmap=cmap), cax=colorbar_ax,
        label="Prototype weight (0–1)",
    )
    fig.suptitle("A6 — SOM component planes", fontsize=15)
    _save_plot(fig, "06_som_component_planes.png")

    # U-Matrix: larger values mark boundaries between unlike neighboring neurons.
    distance_map = som.distance_map()
    u_cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(figsize=(8, 7))
    for x in range(grid_x):
        for y in range(grid_y):
            center = (x + 0.5 * (y % 2), y * np.sqrt(3) / 2)
            ax.add_patch(RegularPolygon(
                center, numVertices=6, radius=0.49, orientation=np.pi / 6,
                facecolor=u_cmap(float(distance_map[x, y])),
                edgecolor="white", linewidth=0.35,
            ))
    ax.set_aspect("equal")
    ax.set_xlim(-0.7, grid_x + 0.7)
    ax.set_ylim(-0.6, grid_y * np.sqrt(3) / 2 + 0.6)
    ax.axis("off")
    fig.colorbar(cm.ScalarMappable(norm=plt.Normalize(0, 1), cmap=u_cmap),
                 ax=ax, label="Normalized distance to neighboring prototypes")
    ax.set_title("A6 — SOM U-Matrix", fontsize=14, pad=12)
    _save_plot(fig, "06_som_umatrix.png")

    return {
        "som_summary": summary,
        "neuron_occupancy_sample": occupancy.filter(pl.col("report_count") > 0).head(20),
        "report_assignments_sample": assignments.head(20),
    }


def run_a7() -> dict[str, pl.DataFrame]:
    import matplotlib.pyplot as plt

    require_core_relations(
        "fct_report", "fct_report_symptom", "fct_report_allergen",
        "fct_report_vaccine", "dim_symptom", "dim_allergen", "dim_vaccine",
    )
    require_nonempty_core("fct_report")
    allergen = query_df(
        """
        WITH top_10_symptoms AS (
            SELECT fs.symptom_key FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key
            ORDER BY COUNT(DISTINCT fs.report_key) DESC, fs.symptom_key
            LIMIT 10
        )
        SELECT da.canonical_name AS allergen_name, ds.symptom_name,
               COUNT(DISTINCT fa.report_key) AS co_occurrence_reports
        FROM core.fct_report_allergen fa
        JOIN core.dim_allergen da ON da.allergen_key = fa.allergen_key
        JOIN core.fct_report_symptom fs ON fs.report_key = fa.report_key
        JOIN top_10_symptoms t ON t.symptom_key = fs.symptom_key
        JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
        WHERE fa.match_type IN ('exact', 'fuzzy')
          AND da.canonical_name <> 'UNMAPPED'
          AND fa.allergen_key <> -1 AND fs.symptom_key <> -1
        GROUP BY da.canonical_name, ds.symptom_name
        HAVING COUNT(DISTINCT fa.report_key) >= 50
        ORDER BY co_occurrence_reports DESC
        """
    )
    manufacturers = query_df(
        """
        WITH report_maker AS (
            SELECT DISTINCT rv.report_key, dv.vax_manu
            FROM core.fct_report_vaccine rv
            JOIN core.dim_vaccine dv ON dv.vaccine_key = rv.vaccine_key
            WHERE dv.vax_manu IN ('PFIZER-BIONTECH', 'MODERNA', 'JANSSEN')
        ),
        top_10_symptoms AS (
            SELECT fs.symptom_key FROM core.fct_report_symptom fs
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
            GROUP BY fs.symptom_key
            ORDER BY COUNT(DISTINCT fs.report_key) DESC, fs.symptom_key
            LIMIT 10
        )
        SELECT rm.vax_manu AS manufacturer, ds.symptom_name,
               COUNT(DISTINCT fs.report_key) AS co_occurrence_reports
        FROM report_maker rm
        JOIN core.fct_report_symptom fs ON fs.report_key = rm.report_key
        JOIN top_10_symptoms t ON t.symptom_key = fs.symptom_key
        JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
        WHERE fs.symptom_key <> -1
        GROUP BY rm.vax_manu, ds.symptom_name
        HAVING COUNT(DISTINCT fs.report_key) >= 50
        ORDER BY co_occurrence_reports DESC
        """
    )
    save_csv(allergen, "07_allergen_symptom_edges.csv")
    save_csv(manufacturers, "07_manufacturer_symptom_edges.csv")
    if not allergen.is_empty():
        p = allergen.head(20).to_pandas()
        p["edge"] = p["allergen_name"] + " — " + p["symptom_name"]
        p = p.sort_values("co_occurrence_reports")
        fig, ax = plt.subplots(figsize=(12, max(6, len(p) * 0.38)))
        ax.barh(p["edge"], p["co_occurrence_reports"])
        ax.set_title("Top allergen–symptom links", fontsize=14, pad=12)
        ax.set_xlabel("Distinct reports", fontsize=11)
        ax.set_ylabel("Allergen — symptom", fontsize=11)
        ax.tick_params(axis="both", labelsize=9)
        ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.35)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        _save_plot(fig, "07_allergen_symptom_edges.png")
    return {"allergen_symptom_edges": allergen, "manufacturer_symptom_edges": manufacturers}


def run_a8() -> dict[str, pl.DataFrame]:
    import matplotlib.pyplot as plt

    require_core_relations(
        "fct_report", "fct_report_symptom", "dim_symptom",
    )
    require_nonempty_core("fct_report")
    stats = query_df(
        """
        WITH report_symptom_ages AS (
            SELECT DISTINCT r.report_key, fs.symptom_key, ds.symptom_name,
                   r.age_yrs::double precision AS age_yrs
            FROM core.fct_report r
            JOIN core.fct_report_symptom fs ON fs.report_key = r.report_key
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE r.age_yrs BETWEEN 0 AND 120
              AND fs.symptom_key <> -1
        ),
        top_symptoms AS (
            SELECT symptom_key, symptom_name, COUNT(*) AS report_count
            FROM report_symptom_ages
            GROUP BY symptom_key, symptom_name
            ORDER BY report_count DESC, symptom_name
            LIMIT 10
        ),
        quartiles AS (
            SELECT t.symptom_key, t.symptom_name, t.report_count,
                   percentile_cont(0.25) WITHIN GROUP (ORDER BY a.age_yrs) AS q1,
                   percentile_cont(0.50) WITHIN GROUP (ORDER BY a.age_yrs) AS median,
                   percentile_cont(0.75) WITHIN GROUP (ORDER BY a.age_yrs) AS q3,
                   MIN(a.age_yrs) AS min_age,
                   MAX(a.age_yrs) AS max_age
            FROM top_symptoms t
            JOIN report_symptom_ages a ON a.symptom_key = t.symptom_key
            GROUP BY t.symptom_key, t.symptom_name, t.report_count
        )
        SELECT q.symptom_name, q.report_count, q.min_age, q.q1, q.median, q.q3,
               q.max_age,
               MIN(a.age_yrs) FILTER (
                   WHERE a.age_yrs >= q.q1 - 1.5 * (q.q3 - q.q1)
               ) AS lower_whisker,
               MAX(a.age_yrs) FILTER (
                   WHERE a.age_yrs <= q.q3 + 1.5 * (q.q3 - q.q1)
               ) AS upper_whisker
        FROM quartiles q
        JOIN report_symptom_ages a
          ON a.symptom_key = q.symptom_key
        GROUP BY q.symptom_name, q.report_count, q.min_age, q.q1,
                 q.median, q.q3, q.max_age
        ORDER BY q.report_count DESC, q.symptom_name
        """
    )
    save_csv(stats, "08_age_by_symptom_boxplot_stats.csv")
    if not stats.is_empty():
        box_data = [
            {
                "label": f"{row['symptom_name']} (n={row['report_count']:,})",
                "whislo": row["lower_whisker"],
                "q1": row["q1"],
                "med": row["median"],
                "q3": row["q3"],
                "whishi": row["upper_whisker"],
                "fliers": [],
            }
            for row in stats.iter_rows(named=True)
        ]
        fig, ax = plt.subplots(figsize=(12, max(6, stats.height * 0.55)))
        ax.bxp(box_data, vert=False, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "#8ecae6", "edgecolor": "#2563eb"},
               medianprops={"color": "#b91c1c", "linewidth": 1.8},
               whiskerprops={"color": "#475569"},
               capprops={"color": "#475569"})
        ax.set_xlabel("Age (years)")
        ax.set_ylabel("Symptom")
        ax.set_title("Age distribution by symptom (top 10)", fontsize=14, pad=12)
        ax.set_xlim(left=0)
        ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.4)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="y", labelsize=9)
        _save_plot(fig, "08_age_by_symptom_boxplot.png")
    return {"age_by_symptom_boxplot_stats": stats}


def run_a9(selected_symptom: str | None = None) -> dict[str, pl.DataFrame]:
    """Summarize report-level onset delay for the top five symptoms.

    If selected_symptom is provided, also plot a histogram for that symptom.
    Onset delay is measured at report level because VAERS has no onset date per symptom.
    """
    import matplotlib.pyplot as plt

    require_core_relations("fct_report", "fct_report_symptom", "dim_symptom")
    require_nonempty_core("fct_report")

    valid = """
        SELECT DISTINCT r.report_key, fs.symptom_key, ds.symptom_name,
               (r.onset_date - r.vax_date)::integer AS onset_days
        FROM core.fct_report r
        JOIN core.fct_report_symptom fs ON fs.report_key = r.report_key
        JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
        WHERE fs.symptom_key <> -1
          AND r.vax_date IS NOT NULL
          AND r.onset_date IS NOT NULL
          AND r.onset_date >= r.vax_date
    """
    top5_stats = query_df(
        f"""
        WITH valid_observations AS ({valid}),
        top5 AS (
            SELECT symptom_key, symptom_name, COUNT(*)::bigint AS report_count
            FROM valid_observations
            GROUP BY symptom_key, symptom_name
            ORDER BY report_count DESC, symptom_name
            LIMIT 5
        ),
        quartiles AS (
            SELECT t.symptom_key, t.symptom_name, t.report_count,
                   MIN(v.onset_days) AS min_days,
                   percentile_cont(0.25) WITHIN GROUP (ORDER BY v.onset_days) AS q1_days,
                   percentile_cont(0.50) WITHIN GROUP (ORDER BY v.onset_days) AS median_days,
                   percentile_cont(0.75) WITHIN GROUP (ORDER BY v.onset_days) AS q3_days,
                   MAX(v.onset_days) AS max_days,
                   COUNT(*) FILTER (WHERE v.onset_days BETWEEN 0 AND 1)::bigint AS reports_0_1_day,
                   COUNT(*) FILTER (WHERE v.onset_days BETWEEN 2 AND 7)::bigint AS reports_2_7_days,
                   COUNT(*) FILTER (WHERE v.onset_days BETWEEN 8 AND 30)::bigint AS reports_8_30_days,
                   COUNT(*) FILTER (WHERE v.onset_days > 30)::bigint AS reports_over_30_days
            FROM top5 t
            JOIN valid_observations v ON v.symptom_key = t.symptom_key
            GROUP BY t.symptom_key, t.symptom_name, t.report_count
        )
        SELECT q.symptom_name, q.report_count, q.min_days, q.q1_days,
               q.median_days, q.q3_days, q.max_days,
               MIN(v.onset_days) FILTER (
                   WHERE v.onset_days >= q.q1_days - 1.5 * (q.q3_days - q.q1_days)
               ) AS lower_whisker,
               MAX(v.onset_days) FILTER (
                   WHERE v.onset_days <= q.q3_days + 1.5 * (q.q3_days - q.q1_days)
               ) AS upper_whisker,
               q.reports_0_1_day, q.reports_2_7_days,
               q.reports_8_30_days, q.reports_over_30_days
        FROM quartiles q
        JOIN valid_observations v ON v.symptom_key = q.symptom_key
        GROUP BY q.symptom_name, q.report_count, q.min_days, q.q1_days,
                 q.median_days, q.q3_days, q.max_days,
                 q.reports_0_1_day, q.reports_2_7_days,
                 q.reports_8_30_days, q.reports_over_30_days
        ORDER BY q.report_count DESC, q.symptom_name
        """
    )
    if top5_stats.is_empty():
        raise RuntimeError("Không có báo cáo nào có ngày tiêm, ngày khởi phát hợp lệ và triệu chứng.")

    save_csv(top5_stats, "09_onset_delay_top5_stats.csv")
    box_data = [
        {
            "label": f"{row['symptom_name']} (n={row['report_count']:,})",
            "whislo": row["lower_whisker"],
            "q1": row["q1_days"],
            "med": row["median_days"],
            "q3": row["q3_days"],
            "whishi": row["upper_whisker"],
            "fliers": [],
        }
        for row in top5_stats.iter_rows(named=True)
    ]
    fig, ax = plt.subplots(figsize=(11, max(5.5, top5_stats.height * 0.8)))
    ax.bxp(
        box_data,
        vert=False,
        showfliers=False,
        patch_artist=True,
        boxprops={"facecolor": "#8ecae6", "edgecolor": "#2563eb"},
        medianprops={"color": "#b91c1c", "linewidth": 1.8},
        whiskerprops={"color": "#475569"},
        capprops={"color": "#475569"},
    )
    ax.set_xlabel("Days from vaccination to report-level onset")
    ax.set_ylabel("Symptom")
    ax.set_title("Onset delay distribution for top 5 symptoms", fontsize=14, pad=12)
    ax.set_xlim(left=0)
    ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.4)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    _save_plot(fig, "09_onset_delay_top5_boxplot.png")

    results = {"top5_onset_delay_stats": top5_stats}
    if selected_symptom is None or not selected_symptom.strip():
        print("No symptom selected: showing only the top-5 box plot.")
        return results

    selected = query_df(
        """
        SELECT symptom_name
        FROM core.dim_symptom
        WHERE lower(trim(symptom_name)) = lower(trim(%s))
        ORDER BY symptom_name
        LIMIT 1
        """,
        [selected_symptom.strip()],
    )
    if selected.is_empty():
        raise ValueError(
            f"Không tìm thấy symptom '{selected_symptom}' trong dim_symptom "
            "(hoặc symptom thuộc danh sách loại trừ). Hãy dùng tên chuẩn trong dim_symptom."
        )
    canonical_symptom = selected["symptom_name"][0]
    selected_days = query_df(
        f"""
        WITH valid_observations AS ({valid})
        SELECT onset_days
        FROM valid_observations
        WHERE lower(trim(symptom_name)) = lower(trim(%s))
        ORDER BY onset_days
        """,
        [canonical_symptom],
    )
    if selected_days.is_empty():
        raise ValueError(
            f"Symptom '{canonical_symptom}' có trong dimension nhưng không có báo cáo "
            "nào với ngày tiêm và ngày khởi phát hợp lệ."
        )

    values = selected_days["onset_days"].to_numpy()
    selected_summary = query_df(
        f"""
        WITH valid_observations AS ({valid})
        SELECT symptom_name,
               COUNT(*)::bigint AS report_count,
               MIN(onset_days) AS min_days,
               percentile_cont(0.25) WITHIN GROUP (ORDER BY onset_days) AS q1_days,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY onset_days) AS median_days,
               percentile_cont(0.75) WITHIN GROUP (ORDER BY onset_days) AS q3_days,
               MAX(onset_days) AS max_days
        FROM valid_observations
        WHERE lower(trim(symptom_name)) = lower(trim(%s))
        GROUP BY symptom_name
        """,
        [canonical_symptom],
    )
    save_csv(selected_summary, "09_onset_delay_selected_symptom_stats.csv")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.hist(values, bins="auto", color="#219ebc", edgecolor="white", alpha=0.9)
    ax.set_xlabel("Days from vaccination to report-level onset")
    ax.set_ylabel("VAERS reports")
    ax.set_title(f"Onset delay histogram: {canonical_symptom} (n={len(values):,})")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    _save_plot(fig, "09_onset_delay_selected_symptom_histogram.png")
    results["selected_symptom_onset_stats"] = selected_summary
    return results


def run_a10(
    vaccine_name: str | None = None,
    age_group: str | None = None,
    onset_min_days: int | None = None,
    onset_max_days: int | None = None,
    selected_symptom: str | None = None,
    top_n: int = 10,
) -> dict[str, pl.DataFrame]:
    """Compare report-level outcome flags across symptoms in the selected cohort."""
    import matplotlib.pyplot as plt

    require_core_relations(
        "fct_report", "fct_report_symptom", "fct_report_vaccine",
        "dim_symptom", "dim_vaccine", "dim_age_group",
    )
    require_nonempty_core("fct_report")
    if top_n <= 0:
        raise ValueError("top_n must be a positive integer")
    if onset_min_days is not None and onset_min_days < 0:
        raise ValueError("onset_min_days must be non-negative")
    if onset_max_days is not None and onset_max_days < 0:
        raise ValueError("onset_max_days must be non-negative")
    if (onset_min_days is not None and onset_max_days is not None
            and onset_min_days > onset_max_days):
        raise ValueError("onset_min_days must be <= onset_max_days")

    filters = []
    params: list[object] = []
    if vaccine_name and vaccine_name.strip():
        filters.append(
            """EXISTS (
                SELECT 1
                FROM core.fct_report_vaccine rv
                JOIN core.dim_vaccine dv ON dv.vaccine_key = rv.vaccine_key
                WHERE rv.report_key = r.report_key
                  AND lower(trim(dv.vax_name)) LIKE lower(trim(%s))
            )"""
        )
        params.append(f"%{vaccine_name.strip()}%")
    if selected_symptom and selected_symptom.strip():
        filters.append("lower(trim(ds.symptom_name)) = lower(trim(%s))")
        params.append(selected_symptom.strip())
    if age_group and age_group.strip():
        filters.append(
            """EXISTS (
                SELECT 1 FROM core.dim_age_group ag
                WHERE ag.age_group_key = r.age_group_key
                  AND lower(trim(ag.age_group_label)) = lower(trim(%s))
            )"""
        )
        params.append(age_group.strip())
    if onset_min_days is not None:
        filters.append("r.numdays >= %s")
        params.append(onset_min_days)
    if onset_max_days is not None:
        filters.append("r.numdays <= %s")
        params.append(onset_max_days)
    cohort_filter = "\n          AND ".join(filters)
    if cohort_filter:
        cohort_filter = "AND " + cohort_filter

    stats = query_df(
        f"""
        WITH report_symptoms AS (
            SELECT DISTINCT
                r.report_key,
                fs.symptom_key,
                ds.symptom_name,
                r.hospital,
                r.er_visit,
                r.life_threatening,
                r.disabled,
                r.died
            FROM core.fct_report r
            JOIN core.fct_report_symptom fs ON fs.report_key = r.report_key
            JOIN core.dim_symptom ds ON ds.symptom_key = fs.symptom_key
            WHERE fs.symptom_key <> -1
              {cohort_filter}
        ),
        top_symptoms AS (
            SELECT symptom_key, symptom_name, COUNT(DISTINCT report_key)::bigint AS reports
            FROM report_symptoms
            GROUP BY symptom_key, symptom_name
            ORDER BY reports DESC, symptom_name
            LIMIT %s
        )
        SELECT
            t.symptom_name,
            COUNT(DISTINCT rs.report_key)::bigint AS report_denominator,
            COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.hospital)::bigint AS hospital_reports,
            100.0 * COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.hospital)
                / NULLIF(COUNT(DISTINCT rs.report_key), 0) AS hospital_pct,
            COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.er_visit)::bigint AS er_reports,
            100.0 * COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.er_visit)
                / NULLIF(COUNT(DISTINCT rs.report_key), 0) AS er_pct,
            COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.life_threatening)::bigint AS life_threatening_reports,
            100.0 * COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.life_threatening)
                / NULLIF(COUNT(DISTINCT rs.report_key), 0) AS life_threatening_pct,
            COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.disabled)::bigint AS disability_reports,
            100.0 * COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.disabled)
                / NULLIF(COUNT(DISTINCT rs.report_key), 0) AS disability_pct,
            COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.died)::bigint AS death_reports,
            100.0 * COUNT(DISTINCT rs.report_key) FILTER (WHERE rs.died)
                / NULLIF(COUNT(DISTINCT rs.report_key), 0) AS death_pct
        FROM top_symptoms t
        JOIN report_symptoms rs ON rs.symptom_key = t.symptom_key
        GROUP BY t.symptom_name, t.reports
        ORDER BY t.reports DESC, t.symptom_name
        """,
        [*params, top_n],
    )
    if stats.is_empty():
        if selected_symptom and selected_symptom.strip():
            raise RuntimeError(
                f"Không có báo cáo phù hợp cho symptom '{selected_symptom}' và các bộ lọc đã chọn."
            )
        raise RuntimeError("Không có báo cáo phù hợp với bộ lọc để tính outcome theo symptom.")

    save_csv(stats, "10_outcomes_by_symptom.csv")
    outcome_fields = [
        ("hospital_pct", "hospital_reports", "Hospitalization"),
        ("er_pct", "er_reports", "ER visit"),
        ("life_threatening_pct", "life_threatening_reports", "Life-threatening"),
        ("disability_pct", "disability_reports", "Disability"),
        ("death_pct", "death_reports", "Death"),
    ]
    matrix = np.array(
        [
            [float(row[pct_col] or 0) for pct_col, _, _ in outcome_fields]
            for row in stats.iter_rows(named=True)
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(11, max(5.5, stats.height * 0.65)))
    image = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(outcome_fields)), [label for _, _, label in outcome_fields])
    ax.set_yticks(
        range(stats.height),
        [f"{row['symptom_name']} (n={row['report_denominator']:,})"
         for row in stats.iter_rows(named=True)],
    )
    for row_idx, row in enumerate(stats.iter_rows(named=True)):
        denominator = row["report_denominator"]
        for col_idx, (pct_col, count_col, _) in enumerate(outcome_fields):
            pct = float(row[pct_col] or 0)
            count = int(row[count_col] or 0)
            text_color = "white" if pct >= 50 else "#222222"
            ax.text(
                col_idx, row_idx, f"{pct:.1f}%\n{count}/{denominator}",
                ha="center", va="center", color=text_color, fontsize=8,
            )
    vaccine_scope = (
        f"vaccine keyword: {vaccine_name.strip()} (partial match)"
        if vaccine_name and vaccine_name.strip()
        else "all vaccines (no vaccine filter)"
    )
    ax.set_title(
        f"Outcome flags by symptom — {vaccine_scope}",
        fontsize=14,
        pad=12,
    )
    ax.set_xlabel("Outcome flag recorded in VAERS report")
    ax.set_ylabel("Symptom; n is the number of distinct reports")
    ax.tick_params(axis="x", labelrotation=18)
    fig.colorbar(image, ax=ax, label="Percent of reports with symptom (%)")
    ax.spines[["top", "right"]].set_visible(False)
    _save_plot(fig, "10_outcomes_by_symptom_heatmap.png")

    print(
        "Percentages use distinct reports containing each symptom as denominator. "
        "Outcome flags may overlap; they are not mutually exclusive."
    )
    return {"outcomes_by_symptom": stats}
