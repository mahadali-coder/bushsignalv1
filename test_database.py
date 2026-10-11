import sqlite3
import tempfile
from pathlib import Path

import database

# Use a temporary database so real project data stays untouched.
with tempfile.TemporaryDirectory() as folder:
    database.DB_PATH = Path(folder) / "test.db"
    database.initialise_database()

    database.add_observation(
        site="Test Reserve",
        species="Test species",
        latitude=-34.9,
        longitude=138.6,
        severity=3,
        area_hectares=1.5,
        confidence=0.8,
        observation_date="2026-10-10",
        notes="Temporary test record",
    )

    rows = database.get_observations()
    assert len(rows) == 1, f"Expected 1 record, got {len(rows)}"
    assert rows[0]["site"] == "Test Reserve"
    assert rows[0]["species"] == "Test species"

    observation_id = rows[0]["id"]

    database.update_observation(
        observation_id=observation_id,
        species="Updated species",
        latitude=-34.9,
        longitude=138.6,
        severity=4,
        area_hectares=2.0,
        confidence=0.9,
        observation_date="2026-10-10",
        notes="Updated test record",
    )

    rows = database.get_observations()
    assert rows[0]["species"] == "Updated species"
    assert rows[0]["severity"] == 4

    # Verify the record is still there after reopening the connection.
    assert len(database.get_observations()) == 1

    database.delete_observation(observation_id)
    assert database.get_observations() == []

print("PASS: create, read, update, delete, and persistence")
