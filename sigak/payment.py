"""
SIGAK Payment API - Manual verification flow (WoZ pilot)

User clicks Transfer Complete -> pending status created
Staff confirms deposit -> status changes to confirmed -> access_level updated
Pending > 24 hours -> auto-cancelled
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


PAYMENT_ACCOUNT = {
    "bank": "카카오뱅크",
    "number": "3333-00-0000000",
    "holder": "홍한진(시각)",
    "kakao_link": "kakaotalk://send?amount={amount}&bank=kakaobank&account=3333000000000",
}

PRICE_MAP = {
    "standard": 2900,
    "full": 26100,
}

AUTO_CANCEL_HOURS = 24


PAYMENT_REQUESTS: dict[str, dict] = {}


class PaymentRequestCreate(BaseModel):
    requested_level: Literal["standard", "full"]
    amount: int


class PaymentRequestResponse(BaseModel):
    status: str
    request_id: str


class PaymentConfirm(BaseModel):
    confirmed: bool
    confirmed_by: Optional[str] = None


class PaymentConfirmResponse(BaseModel):
    status: str
    access_level: str


class DashboardPaymentItem(BaseModel):
    request_id: str
    user_id: str
    user_name: str
    tier: str
    requested_level: str
    amount: int
    elapsed_time: str
    status: str


class DashboardPaymentsResponse(BaseModel):
    pending: list[DashboardPaymentItem]
    today_completed: list[DashboardPaymentItem]


router = APIRouter(prefix="/api/v1", tags=["payment"])


def _get_stores():
    import main as main_module
    return {"users": main_module.USERS, "reports": main_module.REPORTS}


def _cancel_expired_requests():
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=AUTO_CANCEL_HOURS)
    stores = _get_stores()
    for req_id, req in PAYMENT_REQUESTS.items():
        if req["status"] != "pending":
            continue
        requested_at = req["requested_at"]
        if isinstance(requested_at, str):
            requested_at = datetime.fromisoformat(requested_at)
        if requested_at < cutoff:
            req["status"] = "cancelled"
            user_id = req["user_id"]
            if user_id in stores["reports"]:
                report = stores["reports"][user_id]
                if report.get("pending_level") == req["requested_level"]:
                    report["pending_level"] = None


def _format_elapsed_time(dt) -> str:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    delta = datetime.utcnow() - dt
    total_minutes = int(delta.total_seconds() / 60)
    if total_minutes < 1:
        return "방금 전"
    elif total_minutes < 60:
        return f"{total_minutes}분 전"
    else:
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"{hours}시간 전"
        return f"{hours}시간 {minutes}분 전"


@router.post("/payment-request/{user_id}", response_model=PaymentRequestResponse)
async def create_payment_request(user_id: str, data: PaymentRequestCreate):
    _cancel_expired_requests()
    stores = _get_stores()
    if user_id not in stores["users"]:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")
    if user_id not in stores["reports"]:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다")
    report = stores["reports"][user_id]
    expected_amount = PRICE_MAP.get(data.requested_level)
    if expected_amount is None:
        raise HTTPException(status_code=400, detail="잘못된 결제 레벨입니다")
    if data.amount != expected_amount:
        raise HTTPException(status_code=400, detail=f"금액이 올바르지 않습니다. {data.requested_level} 레벨: {expected_amount}원")
    current_access = report.get("access_level", "free")
    level_order = {"free": 0, "standard": 1, "full": 2}
    if level_order.get(current_access, 0) >= level_order.get(data.requested_level, 0):
        raise HTTPException(status_code=400, detail=f"이미 {current_access} 레벨 이상으로 접근 가능합니다")
    for req in PAYMENT_REQUESTS.values():
        if req["user_id"] == user_id and req["requested_level"] == data.requested_level and req["status"] == "pending":
            raise HTTPException(status_code=400, detail="이미 동일 레벨에 대한 대기 중인 요청이 있습니다")
    request_id = str(uuid.uuid4())
    payment_request = {
        "id": request_id, "user_id": user_id, "report_id": report["id"],
        "requested_level": data.requested_level, "amount": data.amount,
        "status": "pending", "requested_at": datetime.utcnow().isoformat(),
        "confirmed_at": None, "confirmed_by": None,
    }
    PAYMENT_REQUESTS[request_id] = payment_request
    report["pending_level"] = data.requested_level
    return PaymentRequestResponse(status="pending", request_id=request_id)


@router.post("/confirm-payment/{user_id}", response_model=PaymentConfirmResponse)
async def confirm_payment(user_id: str, data: PaymentConfirm):
    _cancel_expired_requests()
    stores = _get_stores()
    if user_id not in stores["users"]:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")
    if user_id not in stores["reports"]:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다")
    pending_request = None
    for req in PAYMENT_REQUESTS.values():
        if req["user_id"] == user_id and req["status"] == "pending":
            if pending_request is None:
                pending_request = req
            else:
                req_time = req["requested_at"]
                pending_time = pending_request["requested_at"]
                if isinstance(req_time, str):
                    req_time = datetime.fromisoformat(req_time)
                if isinstance(pending_time, str):
                    pending_time = datetime.fromisoformat(pending_time)
                if req_time > pending_time:
                    pending_request = req
    if pending_request is None:
        raise HTTPException(status_code=404, detail="대기 중인 결제 요청이 없습니다")
    report = stores["reports"][user_id]
    now = datetime.utcnow()
    if data.confirmed:
        pending_request["status"] = "confirmed"
        pending_request["confirmed_at"] = now.isoformat()
        pending_request["confirmed_by"] = data.confirmed_by or "admin"
        requested_level = pending_request["requested_level"]
        report["access_level"] = requested_level
        report["pending_level"] = None
        if requested_level == "standard":
            report["payment_1_at"] = now.isoformat()
        elif requested_level == "full":
            report["payment_2_at"] = now.isoformat()
        return PaymentConfirmResponse(status="confirmed", access_level=requested_level)
    else:
        pending_request["status"] = "unconfirmed"
        pending_request["confirmed_at"] = now.isoformat()
        pending_request["confirmed_by"] = data.confirmed_by
        report["pending_level"] = None
        return PaymentConfirmResponse(status="unconfirmed", access_level=report.get("access_level", "free"))


@router.get("/dashboard/payments", response_model=DashboardPaymentsResponse)
async def get_dashboard_payments():
    _cancel_expired_requests()
    stores = _get_stores()
    today = datetime.utcnow().date()
    pending_items: list[DashboardPaymentItem] = []
    today_completed: list[DashboardPaymentItem] = []
    for req_id, req in PAYMENT_REQUESTS.items():
        user_id = req["user_id"]
        user = stores["users"].get(user_id, {})
        user_name = user.get("name", "알 수 없음")
        tier = user.get("tier", "basic")
        requested_at = req["requested_at"]
        if isinstance(requested_at, str):
            requested_at = datetime.fromisoformat(requested_at)
        item = DashboardPaymentItem(
            request_id=req_id, user_id=user_id, user_name=user_name,
            tier=tier, requested_level=req["requested_level"],
            amount=req["amount"], elapsed_time=_format_elapsed_time(requested_at),
            status=req["status"],
        )
        if req["status"] == "pending":
            pending_items.append(item)
        elif req["status"] == "confirmed":
            confirmed_at = req.get("confirmed_at")
            if confirmed_at:
                if isinstance(confirmed_at, str):
                    confirmed_at = datetime.fromisoformat(confirmed_at)
                if confirmed_at.date() == today:
                    today_completed.append(item)
    pending_items.sort(key=lambda x: PAYMENT_REQUESTS[x.request_id]["requested_at"])
    today_completed.sort(key=lambda x: PAYMENT_REQUESTS[x.request_id].get("confirmed_at", ""), reverse=True)
    return DashboardPaymentsResponse(pending=pending_items, today_completed=today_completed)
