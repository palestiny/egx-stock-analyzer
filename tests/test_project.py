# Tests that the test environment can discover and execute a minimal test successfully.
# This exists as a basic project smoke test while the domain test suite is being established.
# Its function is to detect a completely broken pytest/project setup independently of domain behavior.
def test_project_is_alive():
    assert True