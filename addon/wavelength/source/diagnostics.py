"""Persistent, bounded add-on diagnostics and CLI/error log; imports without Blender."""
from collections import deque
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import sys
import traceback as _tb
import uuid

logger = logging.getLogger('wavelength')
logger.addHandler(logging.NullHandler())
logger.propagate = False
log_path = None
last_error = ''
_handler = None
entries = deque(maxlen=500)


class _CLIRingHandler(logging.Handler):
    def emit(self, record):
        try:
            ts = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            tb_text = ''
            if record.exc_info and record.exc_info[0] is not None:
                tb_text = ''.join(_tb.format_exception(*record.exc_info)).rstrip()
            entry = {
                'time': ts,
                'level': record.levelname,
                'message': record.getMessage(),
                'traceback': tb_text,
            }
            entries.append(entry)
            stream = sys.stderr if record.levelno >= logging.WARNING else sys.stdout
            print(f'[Wavelength {ts} {record.levelname}] {entry["message"]}', file=stream, flush=True)
            if tb_text and record.levelno >= logging.ERROR:
                print(tb_text, file=sys.stderr, flush=True)
        except Exception:
            pass


_cli_handler = _CLIRingHandler()
_cli_handler.setLevel(logging.INFO)
logger.addHandler(_cli_handler)
logger.setLevel(logging.INFO)


def start(directory, version='unknown'):
    global _handler, log_path
    stop()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / 'wavelength.log'
    _handler = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024,
                                  backupCount=3, encoding='utf-8')
    _handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.info('Session %s | Blender %s | %s', uuid.uuid4().hex[:12], version, platform.platform())


def stop():
    global _handler
    if _handler is not None:
        logger.info('Logging stopped')
        logger.removeHandler(_handler)
        _handler.close()
        _handler = None


def error(action, exception):
    global last_error
    reference = uuid.uuid4().hex[:8]
    last_error = f'{action}: {exception} [Error {reference}]'
    logger.error('%s', last_error,
                 exc_info=(type(exception), exception, exception.__traceback__))
    return f'{exception} [Error {reference}; see Diagnostics > View Log]'


def warning(action, message):
    logger.warning('%s: %s', action, message)


def info(action, message):
    logger.info('%s: %s', action, message)


def recent(limit=20, min_level='ALL'):
    lvl = str(min_level or 'ALL').upper()
    allowed = {'ERROR'} if lvl == 'ERROR' else ({'WARNING', 'ERROR', 'CRITICAL'} if lvl in {'WARN', 'WARNING'} else None)
    items = [e for e in entries if allowed is None or e['level'] in allowed]
    return items[-limit:]


def counts():
    err = sum(1 for e in entries if e['level'] in {'ERROR', 'CRITICAL'})
    warn = sum(1 for e in entries if e['level'] == 'WARNING')
    return err, warn, len(entries)


def clear():
    global last_error
    entries.clear()
    last_error = ''
    if _handler is not None and log_path and log_path.exists():
        try:
            _handler.flush()
            log_path.write_text('', encoding='utf-8')
        except OSError:
            pass


def read():
    if _handler is not None:
        _handler.flush()
    if log_path is not None and log_path.exists():
        text = log_path.read_text(encoding='utf-8', errors='replace')
        if text.strip():
            return text
    if entries:
        lines = []
        for e in entries:
            lines.append(f'{e["time"]} {e["level"]} {e["message"]}')
            if e.get('traceback'):
                lines.append(e['traceback'])
        return '\n'.join(lines) + '\n'
    return 'No persistent log available for this session.'

