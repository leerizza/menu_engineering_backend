from datetime import datetime
import pytz

JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

def get_jakarta_now():
    """Get current time in Jakarta timezone"""
    return datetime.now(JAKARTA_TZ)

def to_jakarta_tz(dt):
    """Convert datetime to Jakarta timezone"""
    if dt.tzinfo is None:
        # Naive datetime, assume UTC
        dt = pytz.utc.localize(dt)
    return dt.astimezone(JAKARTA_TZ)

def format_jakarta_datetime(dt, format='%Y-%m-%d %H:%M:%S'):
    """Format datetime in Jakarta timezone"""
    jakarta_dt = to_jakarta_tz(dt)
    return jakarta_dt.strftime(format)