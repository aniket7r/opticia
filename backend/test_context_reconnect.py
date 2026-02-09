"""In-process test for context preservation during forced reconnect.

This test patches timeouts to be very short, creates a session,
sends messages, waits for the proactive reconnect timer to fire,
and verifies context is preserved.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

# Patch timeout constants before importing the module
import app.services.gemini_service as gs
ORIGINAL_VIDEO_TIMEOUT = gs.SESSION_TIMEOUT_WITH_VIDEO
ORIGINAL_RECONNECT_BUFFER = gs.RECONNECT_BUFFER_SECONDS


async def test_proactive_reconnect_timer():
    """Test that the proactive reconnect timer fires and preserves context."""
    print("=" * 60)
    print("Test: Proactive reconnect timer fires correctly")
    print("=" * 60)

    from app.services.gemini_service import GeminiSession, RECONNECT_BUFFER_SECONDS

    reconnect_fired = asyncio.Event()

    session = GeminiSession("timer-test", "voice")
    session.has_video = True
    session.started_at = datetime.now(timezone.utc)
    session._is_active = True

    async def on_reconnect():
        print("   Reconnect timer FIRED!")
        reconnect_fired.set()

    # Set a very short timer (1 second)
    session._on_reconnect_needed = on_reconnect
    session._reconnect_timer = asyncio.create_task(
        session._reconnect_timer_task(1.0),
        name="test-timer",
    )

    print("   Waiting for reconnect timer (1s)...")
    try:
        await asyncio.wait_for(reconnect_fired.wait(), timeout=3.0)
        print("   PASS: Reconnect timer fired within expected time")
    except asyncio.TimeoutError:
        print("   FAIL: Reconnect timer did not fire within 3s")
        return False

    # Cancel cleanup
    if session._reconnect_timer and not session._reconnect_timer.done():
        session._reconnect_timer.cancel()

    return True


async def test_full_reconnect_with_context():
    """Test full reconnect flow preserves context and sends handoff."""
    print("\n" + "=" * 60)
    print("Test: Full reconnect preserves context")
    print("=" * 60)

    from app.services.gemini_service import GeminiSession, GeminiService

    service = GeminiService()

    # Create a "session" with history
    session = GeminiSession("context-test", "voice")
    session.has_video = True
    session._is_active = True
    session.context_history = [
        {"role": "user", "content": "Help me fix my leaky faucet"},
        {"role": "ai", "content": "I can see the faucet. The issue is with the O-ring seal. Here's what we need to do: turn off the water, remove the handle, replace the O-ring."},
        {"role": "user", "content": "I turned off the water, what's next?"},
        {"role": "ai", "content": "Great! Now use a Phillips screwdriver to remove the handle screw. It's usually under the decorative cap."},
    ]
    session.running_summary = "I turned off the water, what's next?"

    # Mock the internal Gemini session for close
    session._session = AsyncMock()
    service.sessions["context-test"] = session

    # Mock start for the new session
    mock_new_internal = AsyncMock()

    async def fake_start(self):
        self._session = mock_new_internal
        self._is_active = True
        self.started_at = datetime.now(timezone.utc)

    with patch.object(GeminiSession, 'start', fake_start):
        new_session = await service.reconnect_session("context-test")

    assert new_session is not None, "Reconnect should return a new session"
    print(f"   New session created: {new_session.session_id}")

    # Verify context was preserved
    assert len(new_session.context_history) == 4, f"Expected 4 entries, got {len(new_session.context_history)}"
    print(f"   Context history: {len(new_session.context_history)} entries preserved")

    for entry in new_session.context_history:
        print(f"     {entry['role']}: {entry['content'][:60]}...")

    # Verify send_client_content was called with handoff
    assert mock_new_internal.send_client_content.called, "Handoff should be sent"
    call_args = mock_new_internal.send_client_content.call_args

    # Extract the text from the call
    turns = call_args.kwargs.get("turns", [])
    assert len(turns) > 0, "Should have turns"
    handoff_text = turns[0].parts[0].text
    print(f"\n   Handoff message ({len(handoff_text)} chars):")
    print(f"   {handoff_text[:300]}...")

    assert "[CONTEXT HANDOFF]" in handoff_text
    assert "leaky faucet" in handoff_text
    assert "O-ring" in handoff_text
    assert "Phillips screwdriver" in handoff_text
    assert "Do NOT mention the session restart" in handoff_text
    assert call_args.kwargs.get("turn_complete") is False, "Should not mark as turn_complete"

    print("\n   PASS: All context preserved and handoff sent correctly!")
    return True


async def test_context_capture_in_receive_loop():
    """Test that AI text and user transcriptions are captured in context_history."""
    print("\n" + "=" * 60)
    print("Test: AI text and transcriptions captured in context_history")
    print("=" * 60)

    from app.services.gemini_service import GeminiSession
    from app.ws.connection import ConnectionState

    # Create a session
    session = GeminiSession("capture-test", "voice")
    session._is_active = True

    # Mock the state
    state = MagicMock(spec=ConnectionState)
    state.session_id = "capture-test"
    state.send = AsyncMock()
    state.send_error = AsyncMock()
    state.mode = "voice"

    # Import the handler function
    from app.ws.handlers.gemini import _ensure_receive_loop

    # Set up the receive loop (which registers the callback)
    # We need to capture the callback that _ensure_receive_loop passes to start_receive_loop
    captured_callback = [None]
    original_start_receive = session.start_receive_loop

    async def capture_callback(callback):
        captured_callback[0] = callback

    session.start_receive_loop = capture_callback
    await _ensure_receive_loop(state, session)

    callback = captured_callback[0]
    assert callback is not None, "Callback should be registered"

    # Simulate user input transcription
    print("   Simulating user voice transcription...")
    await callback({"type": "input_transcription", "content": "How do I change a tire?"})

    # Simulate AI text response
    print("   Simulating AI text response...")
    await callback({"type": "text", "content": "First, you need to loosen the lug nuts. ", "complete": False})
    await callback({"type": "text", "content": "Then jack up the car.", "complete": False})

    # Simulate turn complete
    await callback({"type": "turn_complete"})

    # Wait for delayed processing (turn_complete with no patterns uses 5s delay)
    print("   Waiting for buffer processing (6s)...")
    await asyncio.sleep(6)

    # Check context_history
    print(f"   Context history: {len(session.context_history)} entries")
    for entry in session.context_history:
        print(f"     {entry['role']}: {entry['content'][:80]}")

    # Should have user transcription and AI response
    user_entries = [e for e in session.context_history if e["role"] == "user"]
    ai_entries = [e for e in session.context_history if e["role"] == "ai"]

    assert len(user_entries) >= 1, f"Expected at least 1 user entry, got {len(user_entries)}"
    assert len(ai_entries) >= 1, f"Expected at least 1 AI entry, got {len(ai_entries)}"

    assert "change a tire" in user_entries[0]["content"]
    assert "lug nuts" in ai_entries[0]["content"]

    # Check running summary updated
    assert session.running_summary == "How do I change a tire?"
    print(f"   Running summary: {session.running_summary}")

    print("   PASS: AI text and user transcriptions correctly captured!")
    return True


async def test_has_video_timeout_change():
    """Verify session timeout changes when video is sent."""
    print("\n" + "=" * 60)
    print("Test: has_video changes session timeout")
    print("=" * 60)

    from app.services.gemini_service import GeminiSession, SESSION_TIMEOUT_AUDIO_ONLY, SESSION_TIMEOUT_WITH_VIDEO

    session = GeminiSession("timeout-test", "voice")

    assert session.session_timeout == SESSION_TIMEOUT_AUDIO_ONLY  # 900s
    print(f"   Audio-only timeout: {session.session_timeout}s")

    session.has_video = True
    assert session.session_timeout == SESSION_TIMEOUT_WITH_VIDEO  # 120s
    print(f"   With-video timeout: {session.session_timeout}s")

    print("   PASS: Timeout correctly changes with video")
    return True


async def main():
    results = []
    results.append(await test_has_video_timeout_change())
    results.append(await test_proactive_reconnect_timer())
    results.append(await test_context_capture_in_receive_loop())
    results.append(await test_full_reconnect_with_context())

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    if passed == total:
        print(f"ALL {total} TESTS PASSED")
    else:
        print(f"{passed}/{total} tests passed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
