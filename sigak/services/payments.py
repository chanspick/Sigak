"""Toss Payments server-side client (MVP v1.1).

Brief section 8: we confirm each payment on two paths — frontend success redirect
and Toss webhook — and dedupe via idempotency keys on token credits. This module
just wraps the raw Toss REST API; the endpoint layer decides when to call.

Docs: https://docs.tosspayments.com/reference

Auth format is Basic base64("{secret_key}:") — the trailing colon is required
because Toss expects secret_key as the user and empty string as the password.
"""
import base64
from typing import Optional

import httpx

from config import get_settings


CONFIRM_PATH = "/v1/payments/confirm"
LOOKUP_PATH = "/v1/payments/{payment_key}"
CANCEL_PATH = "/v1/payments/{payment_key}/cancel"

HTTP_TIMEOUT_SECONDS = 10.0


class TossError(Exception):
    """Toss returned a non-2xx response with {code, message} body.

    Callers should match on ``code`` for business-logic branching — specifically
    ``ALREADY_PROCESSED_PAYMENT`` must be treated as success when the stored
    order matches the charged amount (see brief section 8.2 idempotency rule).
    """

    def __init__(self, code: str, message: str, http_status: int):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"Toss {code} ({http_status}): {message}")


def _auth_header() -> dict:
    settings = get_settings()
    if not settings.toss_secret_key:
        raise RuntimeError("TOSS_SECRET_KEY not configured")
    token = base64.b64encode(f"{settings.toss_secret_key}:".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _raise_for_toss(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    try:
        err = resp.json()
        raise TossError(
            code=err.get("code", "UNKNOWN"),
            message=err.get("message", ""),
            http_status=resp.status_code,
        )
    except ValueError:
        raise TossError(
            code="UNKNOWN",
            message=resp.text[:200],
            http_status=resp.status_code,
        )


async def confirm_payment(payment_key: str, order_id: str, amount: int) -> dict:
    """Approve a payment after the frontend SDK redirects with success.

    Returns the Toss Payment object on success. The caller is expected to verify
    that ``orderId`` and ``amount`` match our stored ``payment_orders`` row before
    crediting tokens — Toss trusts whatever we send here, so skipping that check
    opens the door to tampered amount values on the client.
    """
    settings = get_settings()
    url = settings.toss_base_url + CONFIRM_PATH
    headers = {**_auth_header(), "Content-Type": "application/json"}
    body = {
        "paymentKey": payment_key,
        "orderId": order_id,
        "amount": amount,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, headers=headers, json=body)
    _raise_for_toss(resp)
    return resp.json()


async def get_payment(payment_key: str) -> dict:
    """Lookup the authoritative state of a payment from Toss.

    This is the webhook handler's primary authentication mechanism. Toss v2
    does NOT sign webhook payloads, so we must treat incoming POST bodies as
    untrusted input — anyone who learns the webhook URL could forge a
    PAYMENT_STATUS_CHANGED or CANCEL_STATUS_CHANGED event. Pattern:

        1. Accept webhook, extract paymentKey from the payload
        2. Call get_payment(paymentKey) — this requires our secret key
        3. Use the Toss API response (not the webhook body) as source of truth
        4. Update DB from the API response only

    This also provides natural replay protection: even if a real webhook is
    replayed, we just re-run the same idempotent update from the same Toss
    state.
    """
    settings = get_settings()
    url = settings.toss_base_url + LOOKUP_PATH.format(payment_key=payment_key)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.get(url, headers=_auth_header())
    _raise_for_toss(resp)
    return resp.json()


async def cancel_payment(
    payment_key: str,
    reason: str,
    amount: Optional[int] = None,
) -> dict:
    """Cancel (refund) a completed payment. Full cancel if amount is None."""
    settings = get_settings()
    url = settings.toss_base_url + CANCEL_PATH.format(payment_key=payment_key)
    headers = {**_auth_header(), "Content-Type": "application/json"}
    body: dict = {"cancelReason": reason}
    if amount is not None:
        body["cancelAmount"] = amount
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, headers=headers, json=body)
    _raise_for_toss(resp)
    return resp.json()
