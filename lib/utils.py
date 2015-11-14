from datetime import datetime

import yaml


def to_py_date(timestamp_string):
    if timestamp_string:
        return datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ').date()
    else:
        return None

def permissive_yaml_load(txt):
    txt = txt.replace('\t', ' ')
    txt = txt.strip(' -\n')
    return yaml.load(txt)
