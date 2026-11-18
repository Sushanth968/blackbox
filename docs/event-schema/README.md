# Common Event Model

Every piece of ingested evidence is normalized into a **common event** so that a
git commit, a Jira update and an application error can all be reasoned about
uniformly. The original source is always preserved alongside the normalized form.

## Fields

| Field | Description |
|---|---|
| `event_id` | Unique identifier for the event. |
| `event_type` | Workspace-defined type (e.g. `deployment`, `commit`, `error`). |
| `original_timestamp` | Timestamp exactly as recorded by the source (with offset if present). |
| `normalized_timestamp` | UTC-normalized timestamp used for ordering. |
| `source_timezone` | Timezone/offset information inferred or declared for the source. |
| `source` | Identifier of the evidence source the event came from. |
| `actor` | Who/what performed the event (e.g. a user, service). |
| `entity` | The primary entity involved (e.g. a service, repository). |
| `description` | Human-readable description. |
| `evidence_id` | Reference to the originating evidence record. |
| `confidence` | Extraction confidence in `[0, 1]`. |

## Example

```json
{
  "event_id": "EVT-1001",
  "event_type": "deployment",
  "original_timestamp": "2026-11-18T10:30:00+05:30",
  "normalized_timestamp": "2026-11-18T05:00:00Z",
  "source_timezone": "+05:30",
  "source": "deployment-log",
  "actor": "developer-01",
  "entity": "service-A",
  "description": "Deployment of service-A initiated",
  "evidence_id": "EVD-1001",
  "confidence": 0.98
}
```

## Notes

- `original_timestamp` is never overwritten. The temporal engine works from
  `normalized_timestamp` for ordering but always keeps the original for display
  and conflict analysis.
- Flexible, workspace-specific attributes beyond these core fields are stored in
  a JSON (JSONB) column rather than fixed schema columns, so new event types do
  not require migrations.
