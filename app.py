
from __future__ import annotations
from datetime import date
import inspect
import pandas as pd
import plotly.express as px
import streamlit as st
import database

# Import important libraries. Datetime used to track the date data was imported, pandas and plotly to make graphs, streamlit to host the site, database to keep the information


# Keep the app wide so the dashboard charts and tables have
# enough room to display useful information.
st.set_page_config(
    page_title="BushSignal | Environmental Intelligence",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# These columns must exist before a CSV can be imported.
# Keeping the list in one place makes validation consistent.
REQUIRED_COLUMNS = [
    "site",
    "species",
    "latitude",
    "longitude",
    "severity",
    "area_hectares",
    "confidence",
    "date",
]

# Notes are optional, so they are checked separately from
# the fields needed for a valid observation.
ALL_COLUMNS = REQUIRED_COLUMNS + ["notes"]



# CSS is shown down below.
# Streamlit still handles the actual layout and interactions.
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f6f8f3;
        color: #20342a;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .hero {
        background: linear-gradient(120deg, #153d32, #347151);
        color: white;
        padding: 2rem;
        border-radius: 18px;
        margin-bottom: 1.5rem;
    }

    .hero h1 {
        color: white;
        margin: 0;
        font-size: 2.4rem;
    }

    .hero p {
        color: #e0eee4;
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e1e8df;
        border-radius: 14px;
        padding: 15px;
    }

    .note {
        color: #627267;
        font-size: 0.9rem;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 12px;
    }

    .stButton > button {
        border-radius: 9px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Hero section to be shown at the top of the website to make it more clearer
st.markdown(
    """
    <div class="hero">
        <h1>🌿 BushSignal</h1>
        <p>
            Bush Signal:
            Helping people keep track of enviornmental observations in an easy system.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)




def load_records() -> pd.DataFrame:
    """Load saved observations from SQLite into a dataframe."""

    try:
        # The database module is responsible for querying SQLite.
        # Pandas makes the returned records easier to filter and chart.
        records = database.get_observations()
        frame = pd.DataFrame(records)

    except Exception as exc:
        # Show the error in the app rather than letting the
        # entire dashboard crash without an explanation.
        st.error(f"Could not load the database: {exc}")
        return pd.DataFrame(columns=["id"] + ALL_COLUMNS)

    # An empty database still needs predictable column names.
    # This prevents later pages from failing on missing columns.
    if frame.empty:
        return pd.DataFrame(columns=["id"] + ALL_COLUMNS)

    # Convert measurements to numbers so comparisons, charts
    # and calculations work even if SQLite returns strings.
    numeric_columns = [
        "latitude",
        "longitude",
        "severity",
        "area_hectares",
        "confidence",
    ]

    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

    # Dates are converted to pandas datetime values for sorting
    # and filtering. Invalid dates become NaT instead of crashing.
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(
            frame["date"],
            errors="coerce",
        )

    # Older records may not have every optional text field.
    # Fill missing text with empty strings for consistent display.
    for column in ["site", "species", "notes"]:
        if column not in frame.columns:
            frame[column] = ""

        frame[column] = (
            frame[column]
            .fillna("")
            .astype(str)
        )

    return frame


def show_table(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
) -> None:
    """Display a dataframe, optionally showing selected columns."""

    # Empty tables are confusing, so explain why there is
    # nothing to show instead of rendering a blank component.
    if frame.empty:
        st.info("There are no records to display.")
        return

    # Some pages use the same table helper with different columns.
    # Only select columns that actually exist in this dataframe.
    if columns:
        available = [
            column
            for column in columns
            if column in frame.columns
        ]
        frame = frame[available]

    # Hiding the index keeps tables focused on the actual data.
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
    )

def validate_records(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return valid records and rejected records.

    Rejected records include a validation_issue column.
    """

    # Work on a copy so checking data never changes the original
    # dataframe used elsewhere in the dashboard.
    data = frame.copy()

    # Check the headers first. Without required fields, the
    # remaining checks cannot be performed reliably.
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # CSV values can arrive as text, even when they represent
    # numbers. Convert them before checking their valid ranges.
    numeric_columns = [
        "latitude",
        "longitude",
        "severity",
        "area_hectares",
        "confidence",
    ]

    # Loop over list and convert each value into a pandas data

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    # Invalid dates become NaT, which is checked below.
    data["date"] = pd.to_datetime(
        data["date"],
        errors="coerce",
    )

    # Notes are optional. Add the column if the source file
    # doesn't contain it, so the rest of the app stays consistent.
    if "notes" not in data.columns:
        data["notes"] = ""

    # Strip whitespace so values such as "   " count as empty.
    for column in ["site", "species", "notes"]:
        data[column] = (
            data[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    issues = []

    # Check each observation separately. A row can have multiple
    # problems, and the user should be able to see all of them.
    for _, row in data.iterrows():
        problems = []

        if not row["site"]:
            problems.append("Missing site")

        if not row["species"]:
            problems.append("Missing species")

        latitude = row["latitude"]
        longitude = row["longitude"]
        severity = row["severity"]
        area = row["area_hectares"]
        confidence = row["confidence"]
        observation_date = row["date"]

        # Geographic coordinates have fixed global limits.
        if (
            pd.isna(latitude)
            or not -90 <= latitude <= 90
        ):
            problems.append("Invalid latitude")

        if (
            pd.isna(longitude)
            or not -180 <= longitude <= 180
        ):
            problems.append("Invalid longitude")

        # Severity uses a five-point scale, so only whole-number
        # levels from 1 to 5 should pass validation.
        if (
            pd.isna(severity)
            or severity not in [1, 2, 3, 4, 5]
        ):
            problems.append(
                "Severity must be an integer from 1 to 5"
            )

        # A measured affected area cannot be negative.
        if (
            pd.isna(area)
            or area < 0
        ):
            problems.append(
                "Area must be zero or greater"
            )

        # Confidence is represented as a value from 0 to 1.
        if (
            pd.isna(confidence)
            or not 0 <= confidence <= 1
        ):
            problems.append(
                "Confidence must be between 0 and 1"
            )

        # Future observations are rejected because this app
        # records field observations that have already occurred.
        if pd.isna(observation_date):
            problems.append("Invalid date")
        elif observation_date.date() > date.today():
            problems.append("Date cannot be in the future")

        # An empty string means the row passed every check.
        issues.append("; ".join(problems))

    data["validation_issue"] = issues

    # Split the dataframe without changing the original row data.
    # Valid rows are ready for import; rejected rows retain reasons.
    valid = (
        data[data["validation_issue"] == ""]
        .drop(columns=["validation_issue"])
        .copy()
    )

    rejected = (
        data[data["validation_issue"] != ""]
        .copy()
    )

    return valid, rejected


def calculate_priority(
    frame: pd.DataFrame,
) -> pd.DataFrame:

    # Add calculated fields to a copy, leaving saved observations
    # untouched in the database.
    data = frame.copy()

    # An empty dataframe still gets the expected output columns.
    if data.empty:
        data["priority_score"] = pd.Series(dtype=float)
        data["priority"] = pd.Series(dtype=str)
        data["priority_reason"] = pd.Series(dtype=str)
        return data

    # These fallbacks stop missing values from breaking the score.
    # Field validation should still be used to identify bad records.
    severity = pd.to_numeric(
        data["severity"],
        errors="coerce",
    ).fillna(1)

    area = pd.to_numeric(
        data["area_hectares"],
        errors="coerce",
    ).fillna(0)

    confidence = pd.to_numeric(
        data["confidence"],
        errors="coerce",
    ).fillna(0)

    # The area contribution has diminishing returns: increasing
    # an area from 1 to 6 ha matters more than 101 to 106 ha.
    # This keeps the area component between 0 and 100.
    area_component = (
        area / (area + 5)
    ).fillna(0) * 100

    # Combine the three components using the stated weights.
    # Clip the result to keep every score within 0–100.
    data["priority_score"] = (
        (severity / 5 * 55)
        + (area_component * 0.25)
        + (confidence * 20)
    ).round(1).clip(0, 100)

    # Convert numeric scores into simple categories for triage.
    # These thresholds are product choices, not scientific cutoffs.
    data["priority"] = pd.cut(
        data["priority_score"],
        bins=[-0.01, 39.99, 69.99, 100.01],
        labels=[
            "Monitor",
            "Follow up",
            "High priority",
        ],
    ).astype(str)

    def explain(row):
        # Keep the explanation connected to the recorded evidence.
        # This is more useful than showing a score without context.
        reasons = []

        if row["severity"] >= 4:
            reasons.append("high reported severity")

        if row["area_hectares"] >= 5:
            reasons.append("large affected area")

        if row["confidence"] < 0.5:
            reasons.append("low confidence; verify")

        # Give lower-scoring records a readable default explanation.
        if not reasons:
            reasons.append("routine monitoring")

        return ", ".join(reasons)

    data["priority_reason"] = data.apply(
        explain,
        axis=1,
    )

    return data


# The sidebar acts as the main navigation instead of making
# users scroll through every section on one long page.
with st.sidebar:
    st.header("🌿 BushSignal")
    st.caption("Helping people keep track of enviornmental observations in an easy system")

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Add observation",
            "Import CSV",
            "Record quality",
            "Manage records",
            "AI image suggestions",
            "Export",
        ],
    )

    st.divider()

    # Be clear about the limitations of the scoring system.
    st.caption(
        "Priority scores are Educational triage aids. "
        "Verify important findings using field evidence."
    )


# Reload saved data whenever Streamlit reruns the app.
# SQLite is the source of truth for observations, not session state.
records = load_records()



if page == "Overview":

    st.subheader("Overview")

    st.write(
        "Review field observations, identify patterns "
        "and organise follow-up."
    )

    # Avoid drawing charts from an empty dataset.
    if records.empty:
        st.info(
            "Your database is empty. Add an observation "
            "or import a CSV to begin."
        )

    else:
        # Check existing records before using them for analysis.
        # This also exposes legacy records that may be malformed.
        valid_records, rejected_records = validate_records(records)

        data = calculate_priority(valid_records)

        # These metrics provide a quick snapshot of the database.
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Observations",
            len(records),
        )

        col2.metric(
            "Sites",
            records["site"].nunique(),
        )

        col3.metric(
            "Species recorded",
            records["species"].nunique(),
        )

        # Count only valid records when presenting calculated
        # priorities, since malformed values shouldn't rank.
        high_count = (
            int(
                (
                    data["priority"] == "High priority"
                ).sum()
            )
            if not data.empty
            else 0
        )

        col4.metric(
            "High-priority records",
            high_count,
        )

        st.markdown("### Filter observations")

        # Put the filters on one row so they are easy to compare.
        filter1, filter2, filter3 = st.columns(3)

        species_options = sorted(
            records["species"].unique()
        )

        site_options = sorted(
            records["site"].unique()
        )

        # Invalid or missing severity values are excluded from
        # the filter options rather than being cast to integers.
        severity_options = sorted(
            records["severity"]
            .dropna()
            .astype(int)
            .unique()
        )

        chosen_species = filter1.multiselect(
            "Species",
            species_options,
            default=species_options,
        )

        chosen_sites = filter2.multiselect(
            "Sites",
            site_options,
            default=site_options,
        )

        chosen_severity = filter3.multiselect(
            "Severity",
            severity_options,
            default=severity_options,
        )

        # Apply all filters together. An observation must match
        # the selected species, site and severity to be included.
        filtered = data[
            data["species"].isin(chosen_species)
            & data["site"].isin(chosen_sites)
            & data["severity"].isin(chosen_severity)
        ].copy()

        st.markdown("### Observation map")

        # A map needs usable coordinates, so records without them
        # are left out of the map but remain in the database.
        map_data = filtered.dropna(
            subset=["latitude", "longitude"]
        )

        if map_data.empty:
            st.info(
                "No records with valid coordinates "
                "match the selected filters."
            )
        else:
            # Streamlit expects latitude/longitude under these names.
            st.map(
                map_data.rename(
                    columns={
                        "latitude": "lat",
                        "longitude": "lon",
                    }
                )[["lat", "lon"]],
                size=30,
            )

        chart1, chart2 = st.columns(2)

        with chart1:
            st.markdown("### Records by species")

            if filtered.empty:
                st.info("No matching records.")
            else:
                # Count observations per species for the bar chart.
                counts = (
                    filtered["species"]
                    .value_counts()
                    .rename_axis("species")
                    .reset_index(name="observations")
                )

                fig = px.bar(
                    counts,
                    x="species",
                    y="observations",
                    title="Observation count",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

        with chart2:
            st.markdown("### Severity distribution")

            if filtered.empty:
                st.info("No matching records.")
            else:
                # Sorting severity gives the chart a natural 1–5 order.
                counts = (
                    filtered["severity"]
                    .value_counts()
                    .sort_index()
                    .rename_axis("severity")
                    .reset_index(name="observations")
                )

                fig = px.bar(
                    counts,
                    x="severity",
                    y="observations",
                    title="Reported severity (1–5)",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

        st.markdown("### Priority queue")

        # Put the highest  scores first so users can
        # review the records that may need attention sooner.
        ordered = filtered.sort_values(
            "priority_score",
            ascending=False,
        )

        show_table(
            ordered,
            [
                "site",
                "species",
                "date",
                "severity",
                "area_hectares",
                "confidence",
                "priority_score",
                "priority",
                "priority_reason",
            ],
        )

        st.caption(
            "This score is a Educational, not a scientific "
            "risk assessment."
        )


elif page == "Add observation":

    st.subheader("Add an observation")

    st.write(
        "Record a field observation in the local database."
    )

    # A form groups the inputs and only submits them together
    # when the user presses the save button.
    with st.form(
        "add_observation_form",
        clear_on_submit=True,
    ):

        site = st.text_input("Site name")
        species = st.text_input("Species")

        col1, col2 = st.columns(2)

        # These defaults are example coordinates for Adelaide.
        # Replace them with the actual observation location.
        latitude = col1.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=-34.9285,
            format="%.6f",
        )

        longitude = col2.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=138.6007,
            format="%.6f",
        )

        col3, col4, col5 = st.columns(3)

        severity = col3.select_slider(
            "Severity (1–5)",
            options=[1, 2, 3, 4, 5],
            value=3,
        )

        area = col4.number_input(
            "Affected area (hectares)",
            min_value=0.0,
            value=0.0,
            step=0.1,
        )

        confidence = col5.slider(
            "Confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.05,
        )

        # Prevent future dates at the input stage as well as
        # during CSV validation.
        observation_date = st.date_input(
            "Observation date",
            value=date.today(),
            max_value=date.today(),
        )

        notes = st.text_area(
            "Notes (optional)",
            placeholder=(
                "Evidence, context or follow-up needed..."
            ),
        )

        submitted = st.form_submit_button(
            "Save observation",
            type="primary",
        )

    if submitted:

        # A whitespace-only name should count as missing.
        if not site.strip() or not species.strip():
            st.error(
                "Please enter both a site name and species."
            )

        else:
            try:
                # The database function handles the actual insert.
                # Keeping SQL operations in database.py separates
                # storage logic from the user interface.
                database.add_observation(
                    site=site,
                    species=species,
                    latitude=latitude,
                    longitude=longitude,
                    severity=severity,
                    area_hectares=area,
                    confidence=confidence,
                    observation_date=observation_date,
                    notes=notes,
                )

                st.success(
                    "Observation saved successfully."
                )

                # Reload the page so the new record appears
                # immediately in the dashboard.
                st.rerun()

            except Exception as exc:
                st.error(
                    f"Could not save the observation: {exc}"
                )




elif page == "Import CSV":

    st.subheader("Import observations")

    st.write(
        "Upload a CSV file. Invalid rows will be shown "
        "before anything is imported."
    )

    st.markdown(
        "**Required headers:** "
        "`site, species, latitude, longitude, severity, "
        "area_hectares, confidence, date`"
    )

    st.caption("Optional header: `notes`")

    uploaded = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
    )

    if uploaded is not None:

        try:
            # Read the uploaded file into a dataframe. Normalising
            # headers makes " Species " and "species" equivalent.
            raw = pd.read_csv(uploaded)

            raw.columns = [
                str(column).strip().lower()
                for column in raw.columns
            ]

            missing = [
                column
                for column in REQUIRED_COLUMNS
                if column not in raw.columns
            ]

            if missing:
                st.error(
                    "Missing required columns: "
                    + ", ".join(missing)
                )

            else:
                st.markdown("### Preview")

                # Show a small preview before processing the file.
                show_table(raw.head(20))

                valid, rejected = validate_records(raw)

                # These counts help the user understand what
                # will be imported and what needs fixing.
                col1, col2, col3 = st.columns(3)

                col1.metric("Rows in file", len(raw))
                col2.metric("Valid rows", len(valid))
                col3.metric("Rejected rows", len(rejected))

                if not rejected.empty:

                    st.markdown(
                        "### Rows requiring correction"
                    )

                    rejected_display = rejected.copy()

                    # CSV rows start with the header on line 1,
                    # so add 2 to the zero-based dataframe index.
                    rejected_display.insert(
                        0,
                        "csv_row",
                        rejected_display.index + 2,
                    )

                    show_table(
                        rejected_display,
                        ["csv_row"]
                        + REQUIRED_COLUMNS
                        + ["notes", "validation_issue"],
                    )

                    # Let the user fix rejected rows in a spreadsheet
                    # instead of having to copy errors manually.
                    st.download_button(
                        "Download rejected rows",
                        data=rejected.to_csv(
                            index=False
                        ).encode("utf-8"),
                        file_name="bushsignal_rejected_rows.csv",
                        mime="text/csv",
                    )

                # Only valid rows can be submitted for import.
                # The database also skips likely duplicates.
                if st.button(
                    "Import valid rows",
                    type="primary",
                    disabled=valid.empty,
                ):

                    to_import = valid.copy()

                    # Use one consistent date format in SQLite.
                    to_import["date"] = (
                        to_import["date"]
                        .dt.strftime("%Y-%m-%d")
                    )

                    result = database.import_observations(
                        to_import.to_dict(orient="records")
                    )

                    st.success(
                        f"Import finished: "
                        f"{result['inserted']} inserted; "
                        f"{result['skipped']} skipped."
                    )

                    st.rerun()

        except Exception as exc:
            st.error(
                f"Could not read or import the CSV: {exc}"
            )


elif page == "Record quality":

    st.subheader("Record quality review")

    if records.empty:
        st.info("No saved observations to review.")

    else:
        # This page checks records already saved in the database,
        # not just the rows in a newly uploaded CSV.
        valid, rejected = validate_records(records)

        st.metric(
            "Records failing field validation",
            len(rejected),
        )

        if not rejected.empty:
            show_table(
                rejected,
                [
                    "id",
                    "site",
                    "species",
                    "latitude",
                    "longitude",
                    "severity",
                    "area_hectares",
                    "confidence",
                    "date",
                    "validation_issue",
                ],
            )
        else:
            st.success(
                "All saved records pass the basic checks."
            )

        st.markdown("### Possible duplicates")

        # These fields together are used as a practical duplicate
        # check. It is only a warning, not proof of duplication.
        duplicate_columns = [
            "site",
            "species",
            "latitude",
            "longitude",
            "date",
        ]

        duplicates = records[
            records.duplicated(
                subset=duplicate_columns,
                keep=False,
            )
        ]

        if duplicates.empty:
            st.success("No possible duplicates found.")
        else:
            show_table(
                duplicates.sort_values(duplicate_columns),
                ["id"] + duplicate_columns,
            )

        st.markdown("### Missing values")

        missing_rows = []

        for column in records.columns:
            values = records[column]

            # Count null values once, then count blank strings only
            # among values that aren't already null. This avoids
            # double-counting a missing cell.
            missing_mask = values.isna()

            if values.dtype == object:
                blank_mask = (
                    values.notna()
                    & values.astype(str).str.strip().eq("")
                )
                missing_mask = missing_mask | blank_mask

            missing_rows.append(
                {
                    "field": column,
                    "missing_count": int(missing_mask.sum()),
                }
            )

        show_table(pd.DataFrame(missing_rows))



elif page == "Manage records":

    st.subheader("Manage saved observations")

    # Make it clear that this page changes the persistent database.
    st.warning(
        "Changes here affect your local SQLite database."
    )

    if records.empty:
        st.info("No saved observations to manage.")

    else:
        # The database ID is the stable identifier for each record.
        ids = records["id"].tolist()

        selected_id = st.selectbox(
            "Choose an observation",
            ids,
            format_func=lambda record_id: (
                f"#{record_id} — "
                f"{records.loc[records['id'] == record_id, 'site'].iloc[0]} / "
                f"{records.loc[records['id'] == record_id, 'species'].iloc[0]}"
            ),
        )

        selected = records.loc[
            records["id"] == selected_id
        ].iloc[0]

        # The form is prefilled with the selected record so the user
        # can change only the fields that need correction.
        with st.form("edit_observation_form"):

            species = st.text_input(
                "Species",
                value=str(selected["species"]),
            )

            col1, col2 = st.columns(2)

            # Number inputs need finite defaults. Fall back to a
            # sensible coordinate if an older record is malformed.
            latitude_value = (
                float(selected["latitude"])
                if pd.notna(selected["latitude"])
                else -34.9285
            )

            longitude_value = (
                float(selected["longitude"])
                if pd.notna(selected["longitude"])
                else 138.6007
            )

            latitude = col1.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=latitude_value,
            )

            longitude = col2.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=longitude_value,
            )

            col3, col4, col5 = st.columns(3)

            # Use safe fallbacks for legacy records with missing values.
            selected_severity = (
                int(selected["severity"])
                if pd.notna(selected["severity"])
                and selected["severity"] in [1, 2, 3, 4, 5]
                else 3
            )

            severity = col3.select_slider(
                "Severity",
                options=[1, 2, 3, 4, 5],
                value=selected_severity,
            )

            selected_area = (
                float(selected["area_hectares"])
                if pd.notna(selected["area_hectares"])
                else 0.0
            )

            area = col4.number_input(
                "Area (hectares)",
                min_value=0.0,
                value=max(0.0, selected_area),
                step=0.1,
            )

            selected_confidence = (
                float(selected["confidence"])
                if pd.notna(selected["confidence"])
                and 0 <= selected["confidence"] <= 1
                else 0.7
            )

            confidence = col5.slider(
                "Confidence",
                min_value=0.0,
                max_value=1.0,
                value=selected_confidence,
                step=0.05,
            )

            saved_date = (
                selected["date"].date()
                if pd.notna(selected["date"])
                else date.today()
            )

            # Never let an old or invalid record prefill a future date.
            observation_date = st.date_input(
                "Observation date",
                value=min(saved_date, date.today()),
                max_value=date.today(),
            )

            notes = st.text_area(
                "Notes",
                value=str(selected.get("notes", "")),
            )

            save_changes = st.form_submit_button(
                "Save changes",
                type="primary",
            )

        if save_changes:

            if not species.strip():
                st.error("Species cannot be empty.")

            else:
                try:
                    # The current database schema doesn't include
                    # editing the site name, so this updates the
                    # other editable fields for the selected ID.
                    database.update_observation(
                        observation_id=selected_id,
                        species=species,
                        latitude=latitude,
                        longitude=longitude,
                        severity=severity,
                        area_hectares=area,
                        confidence=confidence,
                        observation_date=observation_date,
                        notes=notes,
                    )

                    st.success("Observation updated.")
                    st.rerun()

                except Exception as exc:
                    st.error(
                        f"Could not update the record: {exc}"
                    )

        st.divider()

        # Require explicit confirmation to reduce accidental deletions.
        confirm_delete = st.checkbox(
            f"I understand deleting observation #{selected_id} is permanent."
        )

        if st.button(
            "Delete selected observation",
            disabled=not confirm_delete,
        ):
            try:
                database.delete_observation(selected_id)

                st.success("Observation deleted.")
                st.rerun()

            except Exception as exc:
                st.error(
                    f"Could not delete the record: {exc}"
                )

elif page == "AI image suggestions":

    st.subheader("AI-assisted image suggestions")

    st.write(
        "Use image analysis to generate suggestions for "
        "further investigation. Results are not confirmed "
        "species identifications."
    )

    uploaded_image = st.file_uploader(
        "Upload a field image",
        type=["jpg", "jpeg", "png", "webp"],
    )

    if uploaded_image is not None:

        # Display the image before running inference so the user
        # can confirm they selected the intended file.
        st.image(
            uploaded_image,
            caption="Uploaded field image",
            use_container_width=True,
        )

        st.info(
            "First-time model use may download weights "
            "and require additional memory."
        )

        if st.button(
            "Analyse image",
            type="primary",
        ):

            try:
                # Import only when needed so users can still use
                # the rest of BushSignal without the AI dependencies.
                import image_analysis

                analyse = getattr(
                    image_analysis,
                    "analyze_image",
                    None,
                )

                if analyse is None:
                    st.error(
                        "image_analysis.py must define "
                        "analyze_image(...)."
                    )

                else:
                    # Some versions of the analysis function may
                    # accept a filename, while others accept only
                    # the uploaded file. Inspect the signature first.
                    parameters = inspect.signature(
                        analyse
                    ).parameters

                    # Reset the file pointer before passing the
                    # upload to the image-analysis function.
                    uploaded_image.seek(0)

                    if len(parameters) >= 2:
                        result = analyse(
                            uploaded_image,
                            uploaded_image.name,
                        )
                    else:
                        result = analyse(uploaded_image)

                    st.markdown("### Analysis results")

                    # Display structured results in a readable form.
                    if isinstance(result, pd.DataFrame):
                        show_table(result)

                    elif isinstance(result, (dict, list, tuple)):
                        st.json(result)

                    else:
                        st.write(result)

            except Exception as exc:
                st.error(
                    f"Image analysis failed: {exc}"
                )

                st.caption(
                    "The rest of BushSignal can still "
                    "be used without image analysis."
                )



elif page == "Export":

    st.subheader("Export observations")

    if records.empty:
        st.info(
            "There are no saved observations to export."
        )

    else:
        # Keep the raw export separate from the calculated priority
        # export so users can choose between source data and analysis.
        export_data = records.copy()

        # Use a consistent, spreadsheet-friendly date format.
        export_data["date"] = (
            export_data["date"]
            .dt.strftime("%Y-%m-%d")
        )

        st.download_button(
            "Download observations CSV",
            data=export_data.to_csv(
                index=False
            ).encode("utf-8"),
            file_name="bushsignal_observations.csv",
            mime="text/csv",
            type="primary",
        )

        # The priority export includes the calculated score,
        # category and explanation alongside the observation fields.
        priority_data = calculate_priority(records)

        priority_data["date"] = (
            priority_data["date"]
            .dt.strftime("%Y-%m-%d")
        )

        st.download_button(
            "Download priority review CSV",
            data=priority_data.to_csv(
                index=False
            ).encode("utf-8"),
            file_name="bushsignal_priority_review.csv",
            mime="text/csv",
        )

# Keep the limitation visible regardless of the selected page.
st.divider()

st.caption(
    "BushSignal - v1 • Note - storage will occur on your local laptop • "
    "Verify Evidence Before Making Decisions - This is not fully accurate."
)
