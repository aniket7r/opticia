"""Test context preservation across session reconnects.

Tests that conversation history AND active task state are properly
captured and handed off when a Gemini session times out and reconnects.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from unittest.mock import AsyncMock, MagicMock, patch
from app.services.gemini_service import GeminiSession, GeminiService


def test_context_history_capture():
    """Verify context_history stores both user and AI messages."""
    session = GeminiSession("test-123", "voice")
    session.context_history.append({"role": "user", "content": "How do I fix my sink?"})
    session.context_history.append({"role": "ai", "content": "I can see the leak. First, turn off the water supply."})
    session.context_history.append({"role": "user", "content": "OK I turned it off"})
    session.context_history.append({"role": "ai", "content": "Great, now loosen the compression nut with a wrench."})

    assert len(session.context_history) == 4
    assert session.context_history[0]["role"] == "user"
    assert session.context_history[1]["role"] == "ai"
    print("PASS: context_history stores both user and AI messages")


def test_context_history_trimming():
    """Verify context_history is trimmed to MAX_CONTEXT_HISTORY."""
    session = GeminiSession("test-123", "voice")
    for i in range(40):
        session.context_history.append({"role": "user", "content": f"Message {i}"})
    session._trim_context_history()

    assert len(session.context_history) == GeminiSession.MAX_CONTEXT_HISTORY
    assert session.context_history[0]["content"] == "Message 10"
    assert session.context_history[-1]["content"] == "Message 39"
    print("PASS: context_history trimmed to MAX_CONTEXT_HISTORY")


def test_active_task_lifecycle():
    """Verify active_task set/update/clear lifecycle."""
    session = GeminiSession("test-123", "voice")

    # Set task
    steps = [
        {"id": "step-0", "title": "Fold paper in half", "status": "current"},
        {"id": "step-1", "title": "Fold corners to center", "status": "upcoming"},
        {"id": "step-2", "title": "Fold edges to center", "status": "upcoming"},
        {"id": "step-3", "title": "Fold in half", "status": "upcoming"},
        {"id": "step-4", "title": "Create wings", "status": "upcoming"},
    ]
    session.set_active_task("Make Paper Airplane", steps)

    assert session.active_task is not None
    assert session.active_task["title"] == "Make Paper Airplane"
    assert session.active_task["current_step"] == 0
    assert "Guiding: Make Paper Airplane (step 1/5: Fold paper in half)" == session.running_summary
    print("  Task set correctly")

    # Update steps
    session.update_task_step(0, "completed")
    assert session.active_task["current_step"] == 1
    assert "step 2/5: Fold corners to center" in session.running_summary
    print("  Step 0 completed, moved to step 1")

    session.update_task_step(1, "completed")
    assert session.active_task["current_step"] == 2
    assert "step 3/5: Fold edges to center" in session.running_summary
    print("  Step 1 completed, moved to step 2")

    # Clear task
    session.clear_active_task()
    assert session.active_task is None
    print("  Task cleared")

    print("PASS: active_task lifecycle works correctly")


def test_context_handoff_with_active_task():
    """Verify context handoff includes active task state prominently."""
    service = GeminiService()
    session = GeminiSession("test-123", "voice")

    # Set up conversation + active task (simulating paper airplane scenario)
    session.context_history = [
        {"role": "user", "content": "Can you guide me step by step to create a paper airplane?"},
        {"role": "ai", "content": "Sure! Let me walk you through it."},
        {"role": "user", "content": "Here is the paper, I folded it in half."},
        {"role": "ai", "content": "Great, step one done! Now fold the top corners to the center."},
        {"role": "user", "content": "OK I did it."},
        {"role": "ai", "content": "Perfect! Now fold the top edges to the center again."},
    ]

    steps = [
        {"id": "step-0", "title": "Fold paper in half", "status": "completed"},
        {"id": "step-1", "title": "Fold corners to center", "status": "completed"},
        {"id": "step-2", "title": "Fold edges to center", "status": "current"},
        {"id": "step-3", "title": "Fold in half", "status": "upcoming"},
        {"id": "step-4", "title": "Create wings", "status": "upcoming"},
    ]
    session.set_active_task("Make Paper Airplane", steps)
    session.update_task_step(0, "completed")
    session.update_task_step(1, "completed")

    msg = service._build_context_handoff(session)

    print(f"\n  Handoff message ({len(msg)} chars):")
    print("  " + msg.replace("\n", "\n  "))

    # Task section must be present
    assert "[ACTIVE TASK]" in msg
    assert "Make Paper Airplane" in msg
    assert "IN PROGRESS" in msg

    # Steps with status
    assert "Fold paper in half" in msg
    assert "DONE" in msg
    assert "CURRENT STEP" in msg
    assert "Fold edges to center" in msg

    # Strong continuation instructions
    assert "Continue guiding from step 3" in msg
    assert "Do NOT restart" in msg

    # Conversation context also present
    assert "paper airplane" in msg
    assert "fold" in msg.lower()

    print("\nPASS: Context handoff includes active task with step progress")


def test_context_handoff_without_task():
    """Verify handoff still works normally without active task."""
    service = GeminiService()
    session = GeminiSession("test-123", "voice")

    session.context_history = [
        {"role": "user", "content": "What color is the sky?"},
        {"role": "ai", "content": "The sky is blue during the day."},
    ]
    session.running_summary = "What color is the sky?"

    msg = service._build_context_handoff(session)

    assert "[CONTEXT HANDOFF]" in msg
    assert "[ACTIVE TASK]" not in msg
    assert "sky is blue" in msg
    print("PASS: Context handoff works without active task")


def test_context_handoff_strips_control_patterns():
    """Verify AI control patterns are stripped from context handoff."""
    service = GeminiService()
    session = GeminiSession("test-123", "voice")

    session.context_history = [
        {"role": "user", "content": "Help me fix my sink"},
        {"role": "ai", "content": '[TASK: {"title": "Fix Sink", "steps": [{"title": "Turn off water"}]}] Let me guide you step by step.'},
        {"role": "user", "content": "Done with step 1"},
        {"role": "ai", "content": '[TASK_UPDATE: {"step": 0, "status": "completed"}] Great job!'},
    ]

    msg = service._build_context_handoff(session)

    assert "[TASK:" not in msg
    assert "[TASK_UPDATE:" not in msg
    assert "guide you step by step" in msg
    assert "Great job!" in msg
    print("PASS: Control patterns stripped from context handoff")


def test_serialize_restore_with_active_task():
    """Verify active_task is preserved through serialization."""
    session = GeminiSession("test-123", "voice")
    session.has_video = True
    session.context_history = [
        {"role": "user", "content": "Guide me"},
        {"role": "ai", "content": "Sure, let's start."},
    ]

    steps = [
        {"id": "step-0", "title": "Step A", "status": "completed"},
        {"id": "step-1", "title": "Step B", "status": "current"},
        {"id": "step-2", "title": "Step C", "status": "upcoming"},
    ]
    session.set_active_task("My Task", steps)
    session.update_task_step(0, "completed")

    data = session.serialize_context()
    restored = GeminiSession.restore_context(data)

    assert restored.active_task is not None
    assert restored.active_task["title"] == "My Task"
    assert restored.active_task["current_step"] == 1
    assert restored.active_task["steps"][0]["status"] == "completed"
    assert restored.active_task["steps"][1]["status"] == "current"
    assert restored.has_video is True
    print("PASS: active_task preserved through serialization/restore")


def test_running_summary_task_aware():
    """Verify running_summary reflects task state when task is active."""
    session = GeminiSession("test-123", "voice")

    # Before task: normal user message
    session.running_summary = "How do I make a paper airplane?"

    # Set task: should override running_summary
    steps = [
        {"id": "step-0", "title": "Fold in half", "status": "current"},
        {"id": "step-1", "title": "Fold corners", "status": "upcoming"},
    ]
    session.set_active_task("Paper Airplane", steps)
    assert "Guiding: Paper Airplane" in session.running_summary
    assert "step 1/2" in session.running_summary

    # Update step: should update running_summary
    session.update_task_step(0, "completed")
    assert "step 2/2: Fold corners" in session.running_summary

    # Complete all: should reflect completion
    session.update_task_step(1, "completed")
    assert "all 2 steps completed" in session.running_summary

    print("PASS: running_summary reflects task progress")


def test_empty_context_handoff():
    """Verify empty context with no task produces minimal handoff."""
    service = GeminiService()
    session = GeminiSession("test-123", "voice")
    session.context_history = []

    msg = service._build_context_handoff(session)
    # With no history and no task, should still have base message
    assert "[CONTEXT HANDOFF]" in msg or msg == ""
    print("PASS: Empty context handled gracefully")


async def test_reconnect_with_active_task():
    """Test full reconnect flow preserves active task state."""
    service = GeminiService()

    session = GeminiSession("test-reconnect", "voice")
    session.has_video = True
    session._is_active = True
    session._session = AsyncMock()

    # Set up conversation with task in progress
    session.context_history = [
        {"role": "user", "content": "Guide me to make a paper airplane"},
        {"role": "ai", "content": "Let me walk you through it step by step."},
        {"role": "user", "content": "I folded it in half"},
        {"role": "ai", "content": "Great! Now fold the corners to the center."},
        {"role": "user", "content": "Done, what's next?"},
        {"role": "ai", "content": "Fold the edges to the center one more time."},
    ]

    steps = [
        {"id": "step-0", "title": "Fold paper in half", "status": "completed"},
        {"id": "step-1", "title": "Fold corners to center", "status": "completed"},
        {"id": "step-2", "title": "Fold edges to center", "status": "current"},
        {"id": "step-3", "title": "Fold in half", "status": "upcoming"},
        {"id": "step-4", "title": "Create wings", "status": "upcoming"},
    ]
    session.set_active_task("Make Paper Airplane", steps)
    session.update_task_step(0, "completed")
    session.update_task_step(1, "completed")

    service.sessions["test-reconnect"] = session

    mock_new_session = AsyncMock()

    async def fake_start(self):
        self._session = mock_new_session
        self._is_active = True
        from datetime import datetime, timezone
        self.started_at = datetime.now(timezone.utc)

    with patch.object(GeminiSession, 'start', fake_start):
        new_session = await service.reconnect_session("test-reconnect")

    assert new_session is not None

    # Task preserved
    assert new_session.active_task is not None
    assert new_session.active_task["title"] == "Make Paper Airplane"
    assert new_session.active_task["current_step"] == 2

    # Handoff sent
    mock_new_session.send_client_content.assert_called_once()
    call_args = mock_new_session.send_client_content.call_args
    turns = call_args.kwargs.get("turns", [])
    handoff_text = turns[0].parts[0].text

    print(f"\n  Handoff sent to new session ({len(handoff_text)} chars):")
    print("  " + handoff_text[:600].replace("\n", "\n  ") + "...")

    assert "[ACTIVE TASK]" in handoff_text
    assert "Make Paper Airplane" in handoff_text
    assert "CURRENT STEP" in handoff_text
    assert "Continue guiding from step 3" in handoff_text
    assert "paper airplane" in handoff_text.lower()

    print("\nPASS: Reconnect preserves active task and sends correct handoff")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Context Preservation (Task-Aware)")
    print("=" * 60)

    test_context_history_capture()
    test_context_history_trimming()
    test_active_task_lifecycle()
    test_context_handoff_with_active_task()
    test_context_handoff_without_task()
    test_context_handoff_strips_control_patterns()
    test_serialize_restore_with_active_task()
    test_running_summary_task_aware()
    test_empty_context_handoff()
    asyncio.run(test_reconnect_with_active_task())

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
