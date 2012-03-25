from datetime import datetime
import re
try:
    import pytz
    HAS_PYTZ = True
    UTC = pytz.utc
except ImportError:
    HAS_PYTZ = False
    UTC = None

# "+00:00", "-01:05"
_TIMEZONE_REGEX = re.compile(ur"^([+-][0-9]{2}):([0-9]{2})$")

def datetime_set_utc(dt):
    return dt.replace(tzinfo=UTC)

def datetime_utcnow():
    return datetime_set_utc(datetime.utcnow())

def parseTimezone(text):
    if HAS_PYTZ:
        match = _TIMEZONE_REGEX.match(text)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return pytz.FixedOffset(hours * 60 + minutes)
        else:
            return pytz.timezone(text)
    else:
        return None

