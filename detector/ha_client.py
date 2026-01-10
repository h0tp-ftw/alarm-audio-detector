"""Home Assistant REST API client for direct communication without MQTT"""

import json
import os
import logging
import http.client
from urllib import request

logger = logging.getLogger(__name__)


class HAClient:
    """Talks directly to Home Assistant API via Supervisor"""

    def __init__(self, token: str | None = None):
        manual = (token or "").strip()
        if manual:
            self.token = manual
            self.base_url = "http://homeassistant:8123/api/"
            self.token_source = "MANUAL"
        else:
            sup = os.getenv("SUPERVISOR_TOKEN")
            has = os.getenv("HASSIO_TOKEN")
            self.token = sup or has
            self.base_url = "http://supervisor/core/api/"
            self.token_source = (
                "SUPERVISOR_TOKEN" if sup else ("HASSIO_TOKEN" if has else "NONE")
            )

        logger.info(
            f"HAClient init: base_url={self.base_url} token_source={self.token_source} token_present={bool(self.token)}"
        )

        if self.token:
            t = self.token.strip()
            logger.info(
                f"HAClient token fingerprint: len={len(t)} head={t[:6]} tail={t[-6:]}"
            )

        if not self.token:
            logger.error(
                "HAClient: No API token found. Direct HA integration will fail."
            )

    def _request_raw(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict | None = None,
    ):
        conn = http.client.HTTPConnection("supervisor", 80, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", errors="replace")
        conn.close()
        return resp.status, data

    def get_config_raw_httpclient(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        logger.info(
            f"raw auth header prefix ok = {headers['Authorization'].startswith('Bearer ')}"
        )
        status, body = self._request_raw("GET", "/core/api/config", headers=headers)
        logger.info(f"get_config_raw_httpclient: status={status}")
        if status != 200:
            logger.error(f"Raw config failed: {body[:200]}")
        return status, body

    def post_state_raw_httpclient(
        self, entity_id: str, state: str, attributes: dict | None = None
    ):
        path = f"/core/api/states/{entity_id}"
        payload = {"state": state, "attributes": attributes or {}}
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        }
        logger.info(
            f"raw auth header prefix ok = {headers['Authorization'].startswith('Bearer ')}"
        )
        status, body_resp = self._request_raw("POST", path, body=body, headers=headers)
        logger.info(f"post_state_raw_httpclient: POST {path} status={status}")
        if status not in (200, 201):
            logger.error(f"Raw state update failed: {body_resp[:500]}")
        return status, body_resp

    def test_connection(self):
        """Test if the current token works against the API"""
        if not self.token:
            logger.warning("test_connection: no token available")
            return False

        status, body = self.get_config_raw_httpclient()
        if status == 200:
            logger.info("✅ HA API Connection Test: SUCCESS")
            return True
        else:
            logger.error(f"❌ HA API test failed: HTTP {status}")
            logger.error(f"Response body: {body[:200]}")
            return False

    def sync_notification(self, detected: bool, device_name: str, alarm_type: str):
        """High-level method to ensure HA knows the current state"""
        state_str = "on" if detected else "off"
        entity_id = f"binary_sensor.{device_name}_{alarm_type}"

        attributes = {
            "device_class": "smoke" if alarm_type == "smoke" else "gas",
            "friendly_name": f"Acoustic {alarm_type.capitalize()} Alarm",
            "icon": "mdi:alert-decagram" if detected else "mdi:shield-check",
            "integration": "acoustic_alarm_detector",
        }

        # 1. Update State (This creates/updates the 'Binary Sensor')
        success = self.update_state(entity_id, state_str, attributes)

        if success:
            logger.info(f"✅ Binary Sensor Updated: {entity_id} = {state_str.upper()}")
        else:
            logger.error(f"❌ Binary Sensor Update FAILED: {entity_id}")

        # 2. Fire Event (Good for automations)
        self.fire_event(
            "acoustic_alarm_event",
            {"entity_id": entity_id, "state": state_str, "type": alarm_type},
        )

        return success

    def fire_event(self, event_type: str, data: dict) -> bool:
        """Fire a native Home Assistant Event"""
        if not self.token:
            return False
        try:
            req = request.Request(
                f"{self.base_url}events/{event_type}",
                data=json.dumps(data).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with request.urlopen(req) as response:
                return response.status == 200
        except Exception:
            return False

    def update_state(
        self, entity_id: str, state: str, attributes: dict | None = None
    ) -> bool:
        """Directly update the state of an entity. This bypasses MQTT."""
        if not self.token:
            logger.error("update_state: no token available")
            return False

        url = f"{self.base_url}states/{entity_id}"
        payload = {"state": state, "attributes": attributes or {}}

        logger.info(f"update_state: POST {url}")
        logger.debug(f"update_state: payload = {payload}")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        logger.info(
            f"update_state: POST {url} auth_header_present={'Authorization' in headers} token_source={self.token_source}"
        )

        try:
            req = request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with request.urlopen(req, timeout=5) as response:
                status = response.status
                logger.info(f"✅ update_state: HTTP {status}")
                return status in (200, 201)
        except request.HTTPError as e:
            logger.error(f"❌ update_state failed: HTTP {e.code} {e.reason}")
            try:
                body = e.read().decode("utf-8")
                logger.error(f"Response body: {body[:500]}")
            except Exception:
                pass
            if e.code == 401:
                logger.warning("urllib returned 401, trying raw http.client")
                status, body = self.post_state_raw_httpclient(
                    entity_id, state, attributes
                )
                return status in (200, 201)
            return False
        except Exception as e:
            logger.error(f"❌ update_state failed: {e}")
            return False
