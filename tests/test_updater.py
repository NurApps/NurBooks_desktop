from src.core.updater import _parse_version, is_newer


def test_parse_version_clean():
    assert _parse_version("v1.3.5") == (1, 3, 5)


def test_parse_version_without_v():
    assert _parse_version("1.2.0") == (1, 2, 0)


def test_parse_version_non_numeric():
    assert _parse_version("v1.3.beta") == (1, 3, 0)


def test_parse_version_short():
    assert _parse_version("v2") == (2, 0, 0)


def test_is_newer_major():
    assert is_newer("1.9.9", "2.0.0")


def test_is_newer_minor():
    assert is_newer("1.2.9", "1.3.0")


def test_is_newer_patch():
    assert is_newer("1.3.4", "1.3.5")


def test_is_newer_equal():
    assert not is_newer("1.3.5", "1.3.5")


def test_is_newer_older():
    assert not is_newer("1.3.6", "1.3.5")
