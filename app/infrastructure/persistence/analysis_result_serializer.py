import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from app.application.analysis.stock_analysis import StockAnalysisResult


SERIALIZATION_VERSION = 1


class AnalysisResultSerializationError(ValueError):
    """Raised when a persisted analysis result cannot be serialized or restored."""


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return {
            "__type__": "enum",
            "class": f"{value.__class__.__module__}.{value.__class__.__qualname__}",
            "value": value.value,
        }

    if isinstance(value, UUID):
        return {"__type__": "uuid", "value": str(value)}

    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}

    if isinstance(value, date):
        return {"__type__": "date", "value": value.isoformat()}

    if isinstance(value, Decimal):
        return {"__type__": "decimal", "value": str(value)}

    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__type__": "dataclass",
            "class": f"{value.__class__.__module__}.{value.__class__.__qualname__}",
            "fields": {
                field.name: _encode(getattr(value, field.name))
                for field in fields(value)
            },
        }

    if isinstance(value, tuple):
        return {"__type__": "tuple", "items": [_encode(item) for item in value]}

    if isinstance(value, list):
        return {"__type__": "list", "items": [_encode(item) for item in value]}

    if isinstance(value, dict):
        return {
            "__type__": "dict",
            "items": [[_encode(key), _encode(item)] for key, item in value.items()],
        }

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    raise AnalysisResultSerializationError(
        f"Unsupported value type: {type(value)!r}"
    )


def _resolve_class(path: str) -> type:
    module_name, _, qualname = path.rpartition(".")
    if not module_name or not qualname:
        raise AnalysisResultSerializationError(f"Invalid type path: {path}")

    module = __import__(module_name, fromlist=[qualname.split(".")[0]])
    value: Any = module
    for part in qualname.split("."):
        value = getattr(value, part)
    if not isinstance(value, type):
        raise AnalysisResultSerializationError(f"Resolved value is not a type: {path}")
    return value


def _decode(value: Any, expected_type: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if origin in (Union, UnionType):
        non_none = [item for item in args if item is not type(None)]
        if len(non_none) == 1:
            return _decode(value, non_none[0])

    if origin is list:
        item_type = args[0] if args else Any
        return [_decode(item, item_type) for item in value["items"]]

    if origin is tuple:
        item_type = args[0] if args else Any
        return tuple(_decode(item, item_type) for item in value["items"])

    if origin is dict:
        key_type, value_type = args if len(args) == 2 else (Any, Any)
        return {
            _decode(key, key_type): _decode(item, value_type)
            for key, item in value["items"]
        }

    if expected_type is Any:
        return _decode_untyped(value)

    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        return expected_type(value["value"])

    if expected_type is UUID:
        return UUID(value["value"])

    if expected_type is datetime:
        return datetime.fromisoformat(value["value"])

    if expected_type is date:
        return date.fromisoformat(value["value"])

    if expected_type is Decimal:
        return Decimal(value["value"])

    if isinstance(expected_type, type) and is_dataclass(expected_type):
        fields_by_name = get_type_hints(expected_type)
        payload = value["fields"]
        return expected_type(
            **{
                name: _decode(payload[name], field_type)
                for name, field_type in fields_by_name.items()
            }
        )

    return value


def _decode_untyped(value: Any) -> Any:
    if not isinstance(value, dict) or "__type__" not in value:
        return value

    marker = value["__type__"]

    if marker == "uuid":
        return UUID(value["value"])
    if marker == "datetime":
        return datetime.fromisoformat(value["value"])
    if marker == "date":
        return date.fromisoformat(value["value"])
    if marker == "decimal":
        return Decimal(value["value"])
    if marker == "tuple":
        return tuple(_decode_untyped(item) for item in value["items"])
    if marker == "list":
        return [_decode_untyped(item) for item in value["items"]]
    if marker == "dict":
        return {
            _decode_untyped(key): _decode_untyped(item)
            for key, item in value["items"]
        }

    if marker == "enum":
        enum_type = _resolve_class(value["class"])
        return enum_type(value["value"])

    if marker == "dataclass":
        dataclass_type = _resolve_class(value["class"])
        hints = get_type_hints(dataclass_type)
        return dataclass_type(
            **{
                name: _decode(payload, hints[name])
                for name, payload in value["fields"].items()
            }
        )

    raise AnalysisResultSerializationError(f"Unknown serialized type: {marker}")


def serialize_analysis_result(result: StockAnalysisResult) -> str:
    try:
        return json.dumps(
            {
                "version": SERIALIZATION_VERSION,
                "result": _encode(result),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError, AnalysisResultSerializationError) as error:
        if isinstance(error, AnalysisResultSerializationError):
            raise
        raise AnalysisResultSerializationError(
            "Failed to serialize analysis result"
        ) from error


def deserialize_analysis_result(payload: str) -> StockAnalysisResult:
    try:
        document = json.loads(payload)
        if document.get("version") != SERIALIZATION_VERSION:
            raise AnalysisResultSerializationError(
                f"Unsupported analysis result serialization version: "
                f"{document.get('version')}"
            )

        result = _decode(document["result"], StockAnalysisResult)
        if not isinstance(result, StockAnalysisResult):
            raise AnalysisResultSerializationError(
                "Persisted payload did not contain a StockAnalysisResult"
            )
        return result
    except AnalysisResultSerializationError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise AnalysisResultSerializationError(
            "Failed to deserialize analysis result"
        ) from error
