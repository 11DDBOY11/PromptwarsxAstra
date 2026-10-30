import os
import tempfile

# Must run before app.config is imported: isolated DB/uploads and the deterministic rule-based AI path.
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()
os.environ["FALLBACK_ONLY"] = "1"
