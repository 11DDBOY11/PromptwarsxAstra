import os
import tempfile
import pytest

# Must run before app.config is imported: isolated DB/uploads and the deterministic rule-based AI path.
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()
os.environ["FALLBACK_ONLY"] = "1"
os.environ["ALLOW_DEMO_RESET"] = "1"


@pytest.fixture(autouse=True)
def reset_report_rate_limits():
    from app.main import REPORT_SUBMISSIONS
    REPORT_SUBMISSIONS.clear()
    yield
    REPORT_SUBMISSIONS.clear()
