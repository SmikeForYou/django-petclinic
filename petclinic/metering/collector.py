"""Core collection entry point for the monthly-active-users metric.

Called from the dedicated MCP event boundary view after the handler
has completed a successful MCP interaction. All failures are swallowed
and logged; collection must never fail or delay a business response.
"""
import hashlib
import logging
from datetime import datetime, timezone as dt_timezone
from typing import Optional

try:  # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover - fallback
    ZoneInfo = None  # type: ignore

from django.db import IntegrityError, transaction

from petclinic.metering.config import (
    get_measure_id,
    get_reporting_timezone,
    is_production_enabled,
)
from petclinic.metering.identity import resolve_caller_identity
from petclinic.metering.sender import get_sender

logger = logging.getLogger(__name__)


def _current_year_month(tz_name: str) -> str:
    tz = None
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = None
    if tz is None:
        tz = dt_timezone.utc
    return datetime.now(tz).strftime('%Y-%m')


def _month_representative_timestamp(year_month: str) -> str:
    # Recommended per guideline: timestamp representing the month.
    try:
        year, month = year_month.split('-', 1)
        return '{}-{}-01T00:00:00.000Z'.format(year, month)
    except Exception:
        return datetime.now(dt_timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%S.000Z'
        )


def record_mcp_access(request) -> Optional[str]:
    """Record a served MCP interaction for monthly distinct-user counting.

    Returns the pseudonymous cookie value the view should attach to the
    response (or ``None`` if no new cookie needs to be set). Never
    raises.
    """
    try:
        if not is_production_enabled():
            return None

        from petclinic.models import MeteringMonthlyUser

        year_month = _current_year_month(get_reporting_timezone())
        identity_hash, cookie_to_set = resolve_caller_identity(request)

        newly_recorded = False
        try:
            with transaction.atomic():
                MeteringMonthlyUser.objects.create(
                    year_month=year_month,
                    identity_hash=identity_hash,
                )
                newly_recorded = True
        except IntegrityError:
            # Already recorded for this (year_month, identity) -> dedup win.
            newly_recorded = False
        except Exception as exc:  # pragma: no cover - defensive
            logger.info('metering: unable to persist MCP access (%s)', exc)
            return cookie_to_set

        if newly_recorded:
            try:
                event_id = hashlib.sha256(
                    (year_month + '|' + identity_hash).encode('utf-8')
                ).hexdigest()
                get_sender().submit_event(
                    measure_id=get_measure_id(),
                    value=1,
                    timestamp=_month_representative_timestamp(year_month),
                    event_id=event_id,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.info(
                    'metering: unable to schedule submission (%s)', exc
                )

        return cookie_to_set
    except Exception as exc:  # pragma: no cover - last-resort guard
        logger.info('metering: record_mcp_access failed (%s)', exc)
        return None
