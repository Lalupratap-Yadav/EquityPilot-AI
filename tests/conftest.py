"""Test configuration: isolated temporary database, offline mode (no network), sample data loaded."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_TMP = tempfile.mkdtemp(prefix="equitypilot_test_")
os.environ["EQUITYPILOT_DATA_DIR"] = _TMP
os.environ["EQUITYPILOT_DB"] = str(Path(_TMP) / "test.db")
os.environ["EQUITYPILOT_OFFLINE"] = "1"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import pytest  # noqa: E402

from equitypilot.data import sample  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def sample_data():
    sample.load_sample_data(force=True)
    yield
