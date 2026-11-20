import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


@dataclass
class ParserConfig:
    enabled: list = field(default_factory=lambda: [
        "json", "jsonl", "csv", "log", "git", "cicd", "syslog"
    ])
    extra_timestamp_formats: list = field(default_factory=list)


@dataclass
class TemporalConfig:
    out_of_order_threshold_seconds: float = 1.0
    clock_skew_threshold_seconds: float = 300.0
    duplicate_timestamp_min_count: int = 3
    gap_anomaly_multiplier: float = 10.0
    gap_anomaly_min_seconds: float = 3600.0


@dataclass
class EntityConfig:
    extract: list = field(default_factory=lambda: [
        "user", "ip", "email", "path", "url", "hash"
    ])
    aliases: dict = field(default_factory=dict)
    ignore: list = field(default_factory=list)


@dataclass
class ExportConfig:
    include_raw: bool = True
    report_raw_max_length: int = 200
    report_sections: list = field(default_factory=lambda: [
        "summary", "evidence_files", "temporal_conflicts",
        "flagged_events", "notes", "entities"
    ])


@dataclass
class WorkspaceConfig:
    name: str = "BlackBox"
    description: str = ""
    parsers: ParserConfig = field(default_factory=ParserConfig)
    temporal: TemporalConfig = field(default_factory=TemporalConfig)
    entities: EntityConfig = field(default_factory=EntityConfig)
    export: ExportConfig = field(default_factory=ExportConfig)


def load_workspace_config(path: Optional[str] = None) -> WorkspaceConfig:
    if not _YAML_AVAILABLE:
        return WorkspaceConfig()

    if path is None:
        path = os.environ.get("BLACKBOX_WORKSPACE", "workspace.yaml")

    if not os.path.exists(path):
        return WorkspaceConfig()

    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    cfg = WorkspaceConfig()

    ws = raw.get("workspace", {})
    if ws.get("name"):
        cfg.name = ws["name"]
    if ws.get("description"):
        cfg.description = ws["description"]

    p = raw.get("parsers", {})
    if p.get("enabled"):
        cfg.parsers.enabled = p["enabled"]
    if p.get("extra_timestamp_formats"):
        cfg.parsers.extra_timestamp_formats = p["extra_timestamp_formats"]

    t = raw.get("temporal", {})
    if t.get("out_of_order_threshold_seconds") is not None:
        cfg.temporal.out_of_order_threshold_seconds = t["out_of_order_threshold_seconds"]
    if t.get("clock_skew_threshold_seconds") is not None:
        cfg.temporal.clock_skew_threshold_seconds = t["clock_skew_threshold_seconds"]
    if t.get("duplicate_timestamp_min_count") is not None:
        cfg.temporal.duplicate_timestamp_min_count = t["duplicate_timestamp_min_count"]
    if t.get("gap_anomaly_multiplier") is not None:
        cfg.temporal.gap_anomaly_multiplier = t["gap_anomaly_multiplier"]
    if t.get("gap_anomaly_min_seconds") is not None:
        cfg.temporal.gap_anomaly_min_seconds = t["gap_anomaly_min_seconds"]

    e = raw.get("entities", {})
    if e.get("extract"):
        cfg.entities.extract = e["extract"]
    if e.get("aliases"):
        cfg.entities.aliases = e["aliases"]
    if e.get("ignore"):
        cfg.entities.ignore = e["ignore"]

    ex = raw.get("export", {})
    if ex.get("include_raw") is not None:
        cfg.export.include_raw = ex["include_raw"]
    if ex.get("report_raw_max_length") is not None:
        cfg.export.report_raw_max_length = ex["report_raw_max_length"]
    if ex.get("report_sections"):
        cfg.export.report_sections = ex["report_sections"]

    return cfg


workspace = load_workspace_config()
