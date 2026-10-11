
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "bushsignal.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                latitude REAL,
                longitude REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                species TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
                area_hectares REAL NOT NULL CHECK (area_hectares >= 0),
                confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
                observation_date TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        """)


def get_observations():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                observations.id,
                sites.name AS site,
                observations.species,
                observations.latitude,
                observations.longitude,
                observations.severity,
                observations.area_hectares,
                observations.confidence,
                observations.observation_date AS date,
                observations.notes
            FROM observations
            JOIN sites ON observations.site_id = sites.id
            ORDER BY observations.observation_date DESC, observations.id DESC
        """).fetchall()

    return [dict(row) for row in rows]


initialise_database()



def add_observation(
    site,
    species,
    latitude,
    longitude,
    severity,
    area_hectares,
    confidence,
    observation_date,
    notes="",
):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sites (name, latitude, longitude)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO NOTHING
            """,
            (site.strip(), latitude, longitude),
        )

        site_row = connection.execute(
            "SELECT id FROM sites WHERE name = ?",
            (site.strip(),),
        ).fetchone()

        connection.execute(
            """
            INSERT INTO observations (
                site_id, species, latitude, longitude,
                severity, area_hectares, confidence,
                observation_date, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site_row["id"], species.strip(), latitude, longitude,
                severity, area_hectares, confidence,
                str(observation_date), notes.strip(),
            ),
        )


def delete_observation(observation_id):
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM observations WHERE id = ?",
            (observation_id,),
        )


def update_observation(
    observation_id,
    species,
    latitude,
    longitude,
    severity,
    area_hectares,
    confidence,
    observation_date,
    notes="",
):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE observations
            SET species = ?,
                latitude = ?,
                longitude = ?,
                severity = ?,
                area_hectares = ?,
                confidence = ?,
                observation_date = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                species.strip(), latitude, longitude,
                severity, area_hectares, confidence,
                str(observation_date), notes.strip(),
                observation_id,
            ),
        )



def import_observations(records):
    """Import validated observation dictionaries into SQLite.

    Expected keys: site, species, latitude, longitude, severity,
    area_hectares, confidence, date. Optional key: notes.

    Returns counts of inserted and skipped records.
    """
    inserted = 0
    skipped = 0

    with get_connection() as connection:
        for record in records:
            site_name = str(record["site"]).strip()
            species = str(record["species"]).strip()
            observation_date = str(record["date"])[:10]

            if not site_name or not species:
                skipped += 1
                continue

            latitude = float(record["latitude"])
            longitude = float(record["longitude"])
            severity = int(record["severity"])
            area = float(record["area_hectares"])
            confidence = float(record["confidence"])

            # Avoid importing the same observation twice.
            existing = connection.execute(
                """
                SELECT observations.id
                FROM observations
                JOIN sites ON sites.id = observations.site_id
                WHERE sites.name = ?
                  AND observations.species = ?
                  AND observations.latitude = ?
                  AND observations.longitude = ?
                  AND observations.observation_date = ?
                LIMIT 1
                """,
                (
                    site_name, species, latitude, longitude,
                    observation_date,
                ),
            ).fetchone()

            if existing:
                skipped += 1
                continue

            connection.execute(
                """
                INSERT INTO sites (name, latitude, longitude)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO NOTHING
                """,
                (site_name, latitude, longitude),
            )

            site_row = connection.execute(
                "SELECT id FROM sites WHERE name = ?",
                (site_name,),
            ).fetchone()

            connection.execute(
                """
                INSERT INTO observations (
                    site_id, species, latitude, longitude,
                    severity, area_hectares, confidence,
                    observation_date, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    site_row["id"], species, latitude, longitude,
                    severity, area, confidence, observation_date,
                    str(record.get("notes", "")),
                ),
            )

            inserted += 1

    return {"inserted": inserted, "skipped": skipped}
