"""Fire-and-forget SAP Unified Metering sender.

Delivery is performed over the SAP BTP datastream REST ingestion
endpoint with mutual TLS. Credentials and the ingestion URL are read
from the ``metering-service`` binding exposed through
``VCAP_SERVICES``. Any missing binding, unreachable endpoint or non-2xx
response is logged and swallowed so metering never fails or delays the
business request.

The payload carries only the technical measure key, the aggregated
value and the non-personal consumer/product identifiers; no PII leaves
the system.
"""
import atexit
import json
import logging
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

try:  # requests is a very common dependency; fall back to urllib if missing.
    import requests  # type: ignore
except Exception:  # pragma: no cover - defensive
    requests = None  # type: ignore

from petclinic.metering.config import (
    get_consumer_config,
    get_product_config,
)

logger = logging.getLogger(__name__)

_INGESTION_PATH = '/namespaces/metering/datastreams/eventBatch'
_HTTP_TIMEOUT_SECONDS = 5

_sender_lock = threading.Lock()
_sender_instance: Optional['MeteringSender'] = None


class MeteringSender:
    """Submits metering events to SAP Unified Metering.

    The sender is constructed lazily on first use. Construction never
    raises: a missing/invalid binding simply produces a disabled
    sender that logs once and drops events.
    """

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix='metering-sender'
        )
        self._cert_path: Optional[str] = None
        self._key_path: Optional[str] = None
        self._endpoint: Optional[str] = None
        self._enabled = False
        self._tempfiles: list = []
        self._load_binding()
        atexit.register(self._cleanup)

    # ------------------------------------------------------------------
    # Binding / configuration
    # ------------------------------------------------------------------
    def _load_binding(self) -> None:
        raw = os.environ.get('VCAP_SERVICES')
        if not raw:
            logger.info(
                'metering: VCAP_SERVICES not present; submissions disabled'
            )
            return
        try:
            services = json.loads(raw)
        except Exception as exc:
            logger.info(
                'metering: VCAP_SERVICES is not valid JSON (%s); '
                'submissions disabled', exc,
            )
            return

        binding = None
        for _label, instances in (services or {}).items():
            for instance in instances or []:
                name = instance.get('name') or ''
                label = instance.get('label') or ''
                if name == 'metering-service' or label == 'metering-service':
                    binding = instance
                    break
            if binding is not None:
                break
        if binding is None:
            logger.info(
                'metering: no "metering-service" binding found; '
                'submissions disabled'
            )
            return

        credentials = binding.get('credentials') or {}
        endpoints = credentials.get('endpoints') or {}
        endpoint = endpoints.get('usageIngestion')
        cert_pem = credentials.get('certificate')
        key_pem = credentials.get('key')
        if not (endpoint and cert_pem and key_pem):
            logger.info(
                'metering: binding is missing certificate/key/usageIngestion;'
                ' submissions disabled'
            )
            return

        try:
            self._cert_path = self._write_secure_tempfile(cert_pem)
            self._key_path = self._write_secure_tempfile(key_pem)
        except Exception as exc:  # pragma: no cover - defensive
            logger.info(
                'metering: unable to materialize mTLS material (%s);'
                ' submissions disabled', exc,
            )
            return

        self._endpoint = endpoint.rstrip('/')
        self._enabled = bool(requests) and self._endpoint is not None
        if not requests:
            logger.info(
                'metering: "requests" library not available;'
                ' submissions disabled'
            )

    def _write_secure_tempfile(self, content: str) -> str:
        fd, path = tempfile.mkstemp(prefix='metering-', suffix='.pem')
        try:
            with os.fdopen(fd, 'w') as fh:
                fh.write(content)
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
            self._tempfiles.append(path)
            return path
        except Exception:
            try:
                os.unlink(path)
            except Exception:
                pass
            raise

    def _cleanup(self) -> None:
        for path in self._tempfiles:
            try:
                os.unlink(path)
            except Exception:
                pass
        self._tempfiles = []
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------
    def submit_event(
        self,
        measure_id: str,
        value,
        timestamp: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> None:
        """Queue a single event for asynchronous submission.

        This method never raises and never blocks the caller for more
        than the duration of a single ``executor.submit`` call.
        """
        if not self._enabled:
            return
        try:
            self._executor.submit(
                self._deliver, measure_id, value, timestamp, event_id
            )
        except Exception as exc:  # pragma: no cover - executor shutdown
            logger.info('metering: unable to schedule submission (%s)', exc)

    def _deliver(
        self,
        measure_id: str,
        value,
        timestamp: Optional[str],
        event_id: Optional[str],
    ) -> None:
        try:
            payload = self._build_payload(
                measure_id=measure_id,
                value=value,
                timestamp=timestamp,
                event_id=event_id,
            )
            url = '{}{}'.format(self._endpoint, _INGESTION_PATH)
            response = requests.post(  # type: ignore[union-attr]
                url,
                json=payload,
                cert=(self._cert_path, self._key_path),
                timeout=_HTTP_TIMEOUT_SECONDS,
                headers={'Content-Type': 'application/json'},
            )
            if not (200 <= response.status_code < 300):
                logger.info(
                    'metering: submission rejected status=%s measure=%s',
                    response.status_code, measure_id,
                )
        except Exception as exc:
            logger.info(
                'metering: submission failed for measure=%s (%s)',
                measure_id, exc,
            )

    def _build_payload(
        self,
        measure_id: str,
        value,
        timestamp: Optional[str],
        event_id: Optional[str],
    ) -> list:
        import uuid
        ts = timestamp or datetime.now(timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%S.000Z'
        )
        eid = event_id or uuid.uuid4().hex
        event = {
            'id': eid,
            'timestamp': ts,
            'consumer': get_consumer_config(),
            'product': get_product_config(),
            'measure': {'id': measure_id, 'value': value},
        }
        return [event]


def get_sender() -> MeteringSender:
    """Return the lazily constructed module-level sender singleton."""
    global _sender_instance
    if _sender_instance is None:
        with _sender_lock:
            if _sender_instance is None:
                _sender_instance = MeteringSender()
    return _sender_instance
