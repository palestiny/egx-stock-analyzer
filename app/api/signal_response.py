from dataclasses import asdict
from app.domain.signals.model import Signal


def signal_to_dict(signal: Signal) -> dict[str, object]:
    return asdict(signal)
