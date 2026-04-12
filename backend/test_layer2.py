"""
Layer 2 test: verify Cal.com calendar integration.
Run: cd backend && source .venv/bin/activate && python test_layer2.py

NOTE: This only tests get_available_slots (read-only).
      Booking test is skipped by default to avoid creating junk bookings.
      Pass --book to test booking too.
"""

import sys
from app.services.calendar_client import get_available_slots, book_meeting


def test_slots():
    print("=" * 60)
    print("TEST: Get Available Slots (next 7 days)")
    print("=" * 60)

    slots = get_available_slots()
    print(f"\nFound {len(slots)} available slots")

    if not slots:
        print("ERROR: No slots found. Check your Cal.com availability settings.")
        return False

    # Show slots grouped by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for s in slots:
        date = s["time"][:10]
        time = s["time"][11:16]
        by_date[date].append(time)

    for date, times in sorted(by_date.items()):
        print(f"  {date}: {', '.join(times[:5])}{'...' if len(times) > 5 else ''} ({len(times)} slots)")

    print("\nSlots OK")
    return True


def test_booking():
    print("\n" + "=" * 60)
    print("TEST: Book Meeting (will create a real booking!)")
    print("=" * 60)

    slots = get_available_slots()
    if not slots:
        print("ERROR: No slots available to test booking.")
        return False

    # Pick a slot that's far enough in the future
    test_slot = slots[-1]["time"]
    print(f"\nBooking slot: {test_slot}")
    print("  Name: Test Booking")
    print("  Email: test-layer2@example.com")

    result = book_meeting(
        name="Test Booking",
        email="test-layer2@example.com",
        start_time=test_slot,
    )

    print(f"\nResult:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    if result.get("status") == "confirmed":
        print("\nBooking OK")
        print("NOTE: Cancel this test booking from your Cal.com dashboard.")
        return True
    else:
        print("\nERROR: Booking failed")
        return False


if __name__ == "__main__":
    test_slots()

    if "--book" in sys.argv:
        test_booking()
    else:
        print("\nSkipping booking test (pass --book to enable)")

    print("\n\nLayer 2 tests complete!")
