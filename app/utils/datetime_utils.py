# Create this file: backend/app/utils/datetime_utils.py

from datetime import datetime
from typing import Any, Dict
import json


def datetime_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO string for JSON serialization"""
    return dt.isoformat()


def iso_to_datetime(iso_string: str) -> datetime:
    """Convert ISO string back to datetime"""
    # Handle timezone suffixes
    if iso_string.endswith('Z'):
        iso_string = iso_string.replace('Z', '+00:00')
    return datetime.fromisoformat(iso_string)


def serialize_datetime_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert datetime objects in a dictionary to ISO strings
    Useful for preparing data for JSON serialization (e.g., Supabase)
    """
    serialized = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            serialized[key] = datetime_to_iso(value)
        elif isinstance(value, dict):
            serialized[key] = serialize_datetime_fields(value)
        elif isinstance(value, list):
            serialized[key] = [
                serialize_datetime_fields(item) if isinstance(item, dict)
                else datetime_to_iso(item) if isinstance(item, datetime)
                else item
                for item in value
            ]
        else:
            serialized[key] = value
    return serialized


def deserialize_datetime_fields(data: Dict[str, Any], datetime_fields: list) -> Dict[str, Any]:
    """
    Convert ISO strings back to datetime objects for specified fields
    Useful when reading data from database
    """
    deserialized = data.copy()
    for field in datetime_fields:
        if field in deserialized and isinstance(deserialized[field], str):
            try:
                deserialized[field] = iso_to_datetime(deserialized[field])
            except (ValueError, TypeError):
                # If conversion fails, leave as string
                pass
    return deserialized


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Utility function for safe JSON dumps with datetime support
def json_dumps_with_datetime(obj: Any) -> str:
    """JSON dumps that can handle datetime objects"""
    return json.dumps(obj, cls=DateTimeJSONEncoder)


# Example usage in database operations:
def prepare_for_supabase(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare data for Supabase insertion by converting datetime objects to ISO strings
    """
    return serialize_datetime_fields(data)