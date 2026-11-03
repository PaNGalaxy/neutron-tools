"""Links into the Kibana dashboard holding the Elasticsearch logs for an environment.

Shared by the pytest suites, through `tests/conftest.py`, and by the planemo JUnit
reports, through `add_kibana_links.py`, so a failure looks the same whichever of the
two produced it.
"""

import os
from datetime import datetime, timezone

KIBANA_INDEX = "ndip-k8s"
KIBANA_COLUMNS = "kubernetes.container.name,message"

# Widen the window slightly so container start-up and post-failure messages are included
WINDOW_PADDING_SECONDS = 15

SECTION_NAME = "Elasticsearch logs"


def format_timestamp(epoch_seconds):
    """Format epoch seconds the way Kibana wants them, e.g. 2026-10-23T10:04:18.469Z."""
    moment = datetime.fromtimestamp(epoch_seconds, timezone.utc)
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%S')}.{moment.microsecond // 1000:03d}Z"


def discover_url(start, end):
    """Link to the Kibana logs between the `start` and `end` epoch timestamps.

    Returns an empty string for environments without a Kibana instance, which are
    the ones that leave KIBANA_URL unset.
    """
    kibana_url = os.getenv("KIBANA_URL")
    if not kibana_url:
        return ""

    time_from = format_timestamp(start - WINDOW_PADDING_SECONDS)
    time_to = format_timestamp(end + WINDOW_PADDING_SECONDS)
    return (
        f"{kibana_url.rstrip('/')}/app/discover#/"
        "?_g=(filters:!(),refreshInterval:(pause:!t,value:60000),"
        f"time:(from:'{time_from}',to:'{time_to}'))"
        f"&_a=(columns:!({KIBANA_COLUMNS}),filters:!(),index:{KIBANA_INDEX},"
        "interval:auto,query:(language:kuery,query:''),sort:!(!('@timestamp',desc)))"
    )


def log_section(start, end, job_ids=()):
    """The block of text a failure reports, or an empty string without a Kibana instance."""
    url = discover_url(start, end)
    if not url:
        return ""

    details = [f"{format_timestamp(start)} to {format_timestamp(end)}", url]
    if job_ids:
        details.append(f"Galaxy job ids: {', '.join(job_ids)}")
    return "\n".join(details)
