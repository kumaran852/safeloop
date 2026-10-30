import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="safeloop_test_")
os.environ["SAFELOOP_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "test.db").replace("\\", "/")
os.environ["SAFELOOP_AUTO_SEED"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_reference  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference(db)
        db.commit()
    with TestClient(app) as c:
        yield c
