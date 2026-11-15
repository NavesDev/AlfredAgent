from models.update import newest, notes_for, parse_version

CHANGELOG = """# Changelog

## [0.2.0](https://github.com/o/r/compare/v0.1.0...v0.2.0) (2026-12-01)


### Features

* **desktop:** floating pill


## [0.1.0](https://github.com/o/r/releases/tag/v0.1.0) (2026-11-15)

First release.
"""


def test_parse_version_reads_v_tags_only() -> None:
    assert parse_version("v0.10.2") == (0, 10, 2)
    assert parse_version("0.1.0") is None
    assert parse_version("v1.0.0-rc.1") is None
    assert parse_version("latest") is None


def test_newest_compares_numbers_not_text() -> None:
    assert newest(["v0.9.0", "v0.10.0", "v0.2.1", "nightly"]) == "v0.10.0"
    assert newest(["nightly"]) is None
    assert newest([]) is None


def test_notes_for_takes_the_version_section_without_the_heading() -> None:
    assert notes_for(CHANGELOG, "v0.2.0") == "### Features\n\n* **desktop:** floating pill"
    assert notes_for(CHANGELOG, "v0.1.0") == "First release."
    assert notes_for(CHANGELOG, "v9.9.9") == ""
