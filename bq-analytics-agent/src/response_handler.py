"""
response_handler — Parse streaming CA API responses into typed objects.

The CA API ``chat`` method returns a stream of ``Message`` objects.  Each
message can contain one of several payload types:

* **text**   — ``THOUGHT`` | ``PROGRESS`` | ``FINAL_RESPONSE``
* **schema** — resolved datasource schema
* **data**   — tabular query results + generated SQL
* **chart**  — Vega-Lite chart specification

This module provides :func:`parse_stream_message` which converts raw
protobuf messages into a simple :class:`AgentResponse` dataclass,
and display helpers that render each type in Streamlit or the console.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import pandas as pd
import proto

from src.utils import get_logger

logger = get_logger(__name__)


# ── Enums & Dataclasses ──────────────────────────────────


class ResponseType(str, Enum):
    TEXT = "text"
    SCHEMA = "schema"
    DATA = "data"
    CHART = "chart"
    UNKNOWN = "unknown"


class TextType(str, Enum):
    THOUGHT = "THOUGHT"
    PROGRESS = "PROGRESS"
    FINAL_RESPONSE = "FINAL_RESPONSE"
    UNKNOWN = "UNKNOWN"


@dataclass
class AgentResponse:
    """Normalized representation of a single streamed message chunk."""

    response_type: ResponseType = ResponseType.UNKNOWN

    # ── Text payload ──
    text: str = ""
    text_type: TextType = TextType.UNKNOWN
    text_parts: list[str] = field(default_factory=list)

    # ── Schema payload ──
    datasources: list[dict[str, Any]] = field(default_factory=list)

    # ── Data payload ──
    generated_sql: str = ""
    dataframe: Optional[pd.DataFrame] = None
    query_question: str = ""

    # ── Chart payload ──
    vega_config: Optional[dict[str, Any]] = None
    chart_instructions: str = ""

    # ── Raw for debugging ──
    raw: Any = None


# ── Parsing ───────────────────────────────────────────────


def parse_stream_message(msg: Any) -> AgentResponse:
    """
    Parse a single streamed ``Message`` from the CA API into a
    typed :class:`AgentResponse`.
    """
    resp = AgentResponse(raw=msg)

    try:
        system_message = msg.system_message
    except AttributeError:
        return resp

    # ── Text ──────────────────────────────────────────────
    if _has_field(system_message, "text"):
        resp.response_type = ResponseType.TEXT
        text_obj = system_message.text
        parts = list(getattr(text_obj, "parts", []))
        resp.text_parts = parts
        resp.text = "".join(parts)

        # Detect text type from proto enum
        raw_type = getattr(text_obj, "text_type", None)
        if raw_type is not None:
            type_name = str(raw_type).split(".")[-1] if "." in str(raw_type) else str(raw_type)
            try:
                resp.text_type = TextType(type_name)
            except ValueError:
                resp.text_type = TextType.UNKNOWN
        return resp

    # ── Schema ────────────────────────────────────────────
    if _has_field(system_message, "schema"):
        resp.response_type = ResponseType.SCHEMA
        schema_obj = system_message.schema

        if _has_field(schema_obj, "result"):
            ds_list = []
            for ds in getattr(schema_obj.result, "datasources", []):
                ds_list.append(_parse_datasource(ds))
            resp.datasources = ds_list
        return resp

    # ── Data ──────────────────────────────────────────────
    if _has_field(system_message, "data"):
        resp.response_type = ResponseType.DATA
        data_obj = system_message.data

        if _has_field(data_obj, "query"):
            resp.query_question = getattr(data_obj.query, "question", "")

        if _has_field(data_obj, "generated_sql"):
            resp.generated_sql = data_obj.generated_sql

        if _has_field(data_obj, "result"):
            resp.dataframe = _result_to_dataframe(data_obj.result)
        return resp

    # ── Chart ─────────────────────────────────────────────
    if _has_field(system_message, "chart"):
        resp.response_type = ResponseType.CHART
        chart_obj = system_message.chart

        if _has_field(chart_obj, "query"):
            resp.chart_instructions = getattr(
                chart_obj.query, "instructions", ""
            )

        if _has_field(chart_obj, "result"):
            vega = getattr(chart_obj.result, "vega_config", None)
            if vega is not None:
                resp.vega_config = _map_to_dict(vega)
        return resp

    return resp


# ── Internal helpers ─────────────────────────────────────


def _has_field(obj: Any, field_name: str) -> bool:
    """Check whether a proto message has a given field populated."""
    try:
        return field_name in obj
    except TypeError:
        return hasattr(obj, field_name) and getattr(obj, field_name) is not None


def _parse_datasource(ds: Any) -> dict[str, Any]:
    """Extract a dictionary description of a resolved datasource."""
    info: dict[str, Any] = {}
    if _has_field(ds, "bigquery_table_reference"):
        ref = ds.bigquery_table_reference
        info["type"] = "bigquery"
        info["ref"] = (
            f"{ref.project_id}.{ref.dataset_id}.{ref.table_id}"
        )
    elif _has_field(ds, "looker_explore_reference"):
        ref = ds.looker_explore_reference
        info["type"] = "looker"
        info["ref"] = f"{ref.lookml_model}/{ref.explore}"
    elif _has_field(ds, "studio_datasource_id"):
        info["type"] = "studio"
        info["ref"] = ds.studio_datasource_id

    # Schema fields
    if _has_field(ds, "schema"):
        fields_list = []
        for f in getattr(ds.schema, "fields", []):
            fields_list.append(
                {
                    "name": getattr(f, "name", ""),
                    "type": getattr(f, "type", ""),
                    "description": getattr(f, "description", ""),
                }
            )
        info["fields"] = fields_list
    return info


def _result_to_dataframe(result: Any) -> pd.DataFrame:
    """Convert a CA API data result into a Pandas DataFrame."""
    try:
        field_names = [f.name for f in result.schema.fields]
        data_dict: dict[str, list] = {name: [] for name in field_names}
        for row in result.data:
            for name in field_names:
                data_dict[name].append(row.get(name, None))
        return pd.DataFrame(data_dict)
    except Exception as exc:
        logger.warning("Could not convert result to DataFrame: %s", exc)
        return pd.DataFrame()


def _value_to_dict(v: Any) -> Any:
    """Recursively convert proto map values to Python dicts."""
    if isinstance(v, proto.marshal.collections.maps.MapComposite):
        return _map_to_dict(v)
    elif isinstance(v, proto.marshal.collections.RepeatedComposite):
        return [_value_to_dict(el) for el in v]
    elif isinstance(v, (int, float, str, bool)):
        return v
    else:
        try:
            from google.protobuf.json_format import MessageToDict
            return MessageToDict(v)
        except Exception:
            return str(v)


def _map_to_dict(d: Any) -> dict[str, Any]:
    """Convert a proto MapComposite to a plain Python dict."""
    out: dict[str, Any] = {}
    for k in d:
        val = d[k]
        if isinstance(val, proto.marshal.collections.maps.MapComposite):
            out[k] = _map_to_dict(val)
        else:
            out[k] = _value_to_dict(val)
    return out
