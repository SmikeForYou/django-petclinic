"""Configuration access for the metering integration.

These helpers read Django settings at request time so there is no
build-time coupling. The production gate is a dedicated configurable
flag (``METERING_PRODUCTION``); the database backend/profile is NOT a
proxy for the production environment.
"""
from django.conf import settings


def is_production_enabled() -> bool:
    """Return True when the service is configured as the production
    environment for metering purposes.

    Reads ``settings.METERING_PRODUCTION`` (default ``False``). Missing or
    unrecognized values leave collection disabled.
    """
    try:
        value = getattr(settings, 'METERING_PRODUCTION', False)
    except Exception:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


def get_reporting_timezone() -> str:
    """Time zone name used to determine calendar-month boundaries."""
    return str(getattr(settings, 'METERING_REPORTING_TZ', 'UTC') or 'UTC')


def get_measure_id() -> str:
    """Technical measure key, used verbatim in submissions."""
    return 'HS_MCP_MONTLY_USER_COUNT'


def get_consumer_config() -> dict:
    """Return the non-personal consumer identifier for the SAP Unified
    Metering payload. Shape follows the BTP datastream contract::

        {
          'region': '<region>',
          'btp': {
            'environment': '<cf|k8s|...>',
            'subAccount': '<guid>'  # or 'globalAccount': '<guid>'
          }
        }
    """
    cfg = getattr(settings, 'METERING_CONSUMER', None) or {}
    try:
        return dict(cfg)
    except Exception:
        return {}


def get_product_config() -> dict:
    """Return the product identifier for the SAP Unified Metering
    payload, e.g. ``{'service': {'id': 'susage'}}``.
    """
    cfg = getattr(settings, 'METERING_PRODUCT', None) or {}
    try:
        return dict(cfg)
    except Exception:
        return {}
