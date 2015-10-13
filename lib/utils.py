from datetime import datetime

def to_python_datetime(timestamp_string):
    if timestamp_string:
        return datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ')
    else:
        return None
