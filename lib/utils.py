from datetime import datetime

def to_py_date(timestamp_string):
    if timestamp_string:
        return datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ').date()
    else:
        return None
