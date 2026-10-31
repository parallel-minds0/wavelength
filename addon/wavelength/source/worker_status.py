"""Single-writer progress journal; readers never block a file replacement."""
import json


def publish(path,value):
    # Windows permits shared reads/appends but may deny renaming a file while a
    # reader has it open. Append a complete record instead of replacing status.
    with path.open('ab') as stream:
        stream.write((json.dumps(value,ensure_ascii=False)+'\n').encode('utf-8'))


def latest(path):
    try:records=path.read_bytes().splitlines(keepends=True)
    except OSError:return None
    for record in reversed(records):
        # A reader may observe an in-flight write. Only consume completed lines;
        # preserve the preceding state until the new record is fully available.
        if not record.endswith(b'\n'):continue
        try:return json.loads(record)
        except (ValueError,UnicodeError):continue
    return None
