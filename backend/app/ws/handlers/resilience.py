"""Resilience and fallback handlers."""

import logging
from typing import Any

from app.services.admin.metrics_collector import metrics_collector
from app.services.resilience.fallback import MediaMode, fallback_manager
from app.services.resilience.network import network_monitor
from app.services.resilience.preferences import preferences_service, UserPreferences
from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)


async def handle_preferences_get(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle preferences.get message - retrieve user preferences."""
    prefs = await preferences_service.get(state.session_id)

    await state.send(
        "preferences.loaded",
        prefs.model_dump(),
    )


async def handle_preferences_update(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle preferences.update message - update user preferences."""
    # Extract valid preference fields
    valid_fields = {"mode", "proactivity_level", "auto_fallback", "show_thinking", "camera_position"}
    updates = {k: v for k, v in payload.items() if k in valid_fields}

    if not updates:
        await state.send_error("invalid_preferences", "No valid preference fields provided")
        return

    updated = await preferences_service.update(state.session_id, updates)

    # Update connection state mode if changed
    if "mode" in updates:
        state.mode = updates["mode"]

    await state.send(
        "preferences.updated",
        updated.model_dump(),
    )


async def handle_fallback_trigger(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle fallback.trigger message - manually trigger fallback."""
    fallback_type = payload.get("type", "video")  # video, photo, audio
    reason = payload.get("reason", "user_requested")

    if fallback_type == "video":
        event = fallback_manager.trigger_video_fallback(state.session_id, reason)
        # Record fallback metric
        await metrics_collector.record_fallback(state.session_id, "video", "photo")
    elif fallback_type == "photo":
        event = fallback_manager.trigger_photo_fallback(state.session_id, reason)
        await metrics_collector.record_fallback(state.session_id, "photo", "text")
    elif fallback_type == "audio":
        event = fallback_manager.trigger_audio_fallback(state.session_id, reason)
        await metrics_collector.record_fallback(state.session_id, "audio", "text")
    else:
        await state.send_error("invalid_fallback", f"Unknown fallback type: {fallback_type}")
        return

    await state.send(event["type"], event["payload"])


async def handle_fallback_recover(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle fallback.recover message - attempt to recover to better mode."""
    target_mode = payload.get("mode", "video")

    mode_map = {
        "video": MediaMode.VIDEO,
        "photo": MediaMode.PHOTO,
        "text": MediaMode.TEXT,
    }

    mode = mode_map.get(target_mode)
    if not mode:
        await state.send_error("invalid_mode", f"Unknown mode: {target_mode}")
        return

    event = fallback_manager.try_recover(state.session_id, mode)
    await state.send(event["type"], event["payload"])


async def handle_network_ping(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle network.ping message - record latency measurement."""
    latency_ms = payload.get("latencyMs", 0)
    network_monitor.record_latency(state.session_id, latency_ms)

    # Check if we should suggest fallback
    should_suggest, reason = network_monitor.should_suggest_fallback(state.session_id)

    if should_suggest:
        await state.send(
            "network.degraded",
            {
                "suggestion": reason,
                "stats": network_monitor.get_stats(state.session_id).model_dump(),
            },
        )
    else:
        # Just send pong
        await state.send("network.pong", {"timestamp": payload.get("timestamp")})


async def handle_network_stats(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle network.stats message - get current network statistics."""
    stats = network_monitor.get_stats(state.session_id)

    await state.send(
        "network.stats",
        stats.model_dump(),
    )


async def handle_conversation_new(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle conversation.new message - start new conversation."""
    from app.services.gemini_service import gemini_service

    # Close current Gemini session
    await gemini_service.close_session(state.session_id)

    # Reset fallback state
    fallback_manager.cleanup(state.session_id)

    # Reset network monitoring
    network_monitor.cleanup(state.session_id)

    # Preferences are kept (per story requirement)

    await state.send(
        "conversation.reset",
        {"message": "Started new conversation. Context cleared."},
    )
