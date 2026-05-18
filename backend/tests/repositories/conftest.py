"""Conftest local backend/tests/repositories/ — Sprint M2-4.1.

`PROMEOS_JWT_SECRET` requis pour `create_access_token` / `decode_token` :
`test_base_v4.py::TestRealJwtPath` exerce la chaîne réelle JWT → repo. Le
fallback test-safe permet aux tests de tourner standalone (sans .env présent).
Cohérent backend/tests/api/conftest.py (M2-3.B).
"""

import os

os.environ.setdefault("PROMEOS_JWT_SECRET", "m2_4_1_test_secret_do_not_use_prod")
