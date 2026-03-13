from app.services.parser.dispatcher import parse_dump
from app.services.audit.engine import run_audit


def process_dump_background(dump_id: int):
    """Called as a FastAPI BackgroundTask: parse then audit."""
    parse_dump(dump_id)
    run_audit(dump_id)
