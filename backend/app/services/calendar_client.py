"""
Cal.com v2 API client.
- get_available_slots(): fetch open time slots for a date range
- book_meeting(): create a booking
"""

from datetime import datetime, timedelta

import httpx

from app.config import settings

BASE_URL = "https://api.cal.com/v2"


def _headers(api_version: str = "2024-06-14") -> dict:
    return {
        "Authorization": f"Bearer {settings.calcom_api_key}",
        "cal-api-version": api_version,
        "Content-Type": "application/json",
    }


def get_available_slots(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """
    Fetch available slots from Cal.com.
    start_date/end_date: "YYYY-MM-DD" format. Defaults to next 7 days.
    Returns: [{"time": "2024-01-15T10:00:00Z"}, ...]
    """
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    resp = httpx.get(
        f"{BASE_URL}/slots/available",
        params={
            "startTime": f"{start_date}T00:00:00Z",
            "endTime": f"{end_date}T23:59:59Z",
            "eventTypeId": settings.calcom_event_type_id,
            "eventTypeSlug": "30min",
            "username": settings.calcom_username,
        },
        headers=_headers("2024-06-14"),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    # Flatten the slots from the response
    slots = []
    slot_data = data.get("data", {}).get("slots", {})
    for date_key, day_slots in slot_data.items():
        for slot in day_slots:
            slots.append({"time": slot.get("time", slot)})

    return slots


def book_meeting(
    name: str,
    email: str,
    start_time: str,
    notes: str = "",
) -> dict:
    """
    Book a meeting on Cal.com.
    start_time: ISO format, e.g. "2024-01-15T10:00:00Z"
    Returns: booking confirmation dict or error.
    """
    payload = {
        "start": start_time,
        "eventTypeId": settings.calcom_event_type_id,
        "attendee": {
            "name": name,
            "email": email,
            "timeZone": "Asia/Kolkata",
        },
        "metadata": {},
    }
    if notes:
        payload["metadata"]["notes"] = notes

    resp = httpx.post(
        f"{BASE_URL}/bookings",
        json=payload,
        headers=_headers("2024-08-13"),
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()

    booking = result.get("data", {})
    return {
        "status": "confirmed",
        "id": booking.get("id"),
        "title": booking.get("title"),
        "start": booking.get("start"),
        "end": booking.get("end"),
        "attendee_email": email,
        "meeting_url": booking.get("meetingUrl", ""),
    }
