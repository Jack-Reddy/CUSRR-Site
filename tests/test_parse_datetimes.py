from datetime import datetime
from website.routes.block_schedule import parse_local_datetime

def test_parse_local_datetime_string_and_nonstring():
    """Test parse_local_datetime for string and non-string inputs."""

    # --- Case 1: val is a valid datetime string ---
    val_str = "2025-12-09T15:30"
    parsed = parse_local_datetime(val_str)
    assert isinstance(parsed, datetime)
    assert parsed.year == 2025
    assert parsed.month == 12
    assert parsed.day == 9
    assert parsed.hour == 15
    assert parsed.minute == 30

    # --- Case 2: val is a valid datetime object ---
    dt_obj = datetime(2025, 12, 9, 15, 30)
    parsed_obj = parse_local_datetime(dt_obj)
    assert parsed_obj == dt_obj

    # --- Case 3: val is neither string nor datetime (e.g., int) ---
    invalid_val = 12345
    parsed_invalid = parse_local_datetime(invalid_val)
    assert parsed_invalid is None

    # --- Case 4: val is None ---
    parsed_none = parse_local_datetime(None)
    assert parsed_none is None

    # --- Case 5: val is a string but invalid format ---
    invalid_str = "not-a-datetime"
    parsed_invalid_str = parse_local_datetime(invalid_str)
    assert parsed_invalid_str is None
