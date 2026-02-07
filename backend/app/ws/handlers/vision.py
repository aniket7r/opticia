"""Vision/video frame handlers."""

import base64
import logging
from typing import Any

from app.services.gemini_service import gemini_service
from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)


async def handle_video_frame(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle video.frame message - process camera/screen frame."""
    frame_data = payload.get("data", "")  # base64 encoded image
    source = payload.get("source", "camera")  # camera or screen
    mime_type = payload.get("mimeType", "image/jpeg")

    if not frame_data:
        await state.send_error("empty_frame", "Frame data is required")
        return

    session = gemini_service.get_session(state.session_id)
    if not session:
        session = await gemini_service.create_session(state.session_id, state.mode)

    # Check if we need to reconnect
    if session.should_reconnect:
        await state.send("session.reconnecting", {})
        session = await gemini_service.reconnect_session(state.session_id)
        if not session:
            await state.send_error("reconnect_failed", "Failed to reconnect session")
            return

    try:
        # Send frame to Gemini for analysis
        async for chunk in session.send_image(frame_data, mime_type, source):
            if chunk["type"] == "text":
                await state.send(
                    "ai.text",
                    {"content": chunk["content"], "complete": chunk.get("complete", False)},
                )
            elif chunk["type"] == "vision_request":
                # AI is requesting camera repositioning
                await state.send(
                    "vision.request",
                    {"action": chunk["action"], "description": chunk["description"]},
                )
    except Exception as e:
        logger.error(f"Vision error: {e}")
        await state.send_error("vision_error", str(e))


async def handle_photo_capture(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle photo.capture message - process single photo."""
    photo_data = payload.get("data", "")  # base64 encoded image
    mime_type = payload.get("mimeType", "image/jpeg")
    context = payload.get("context", "")  # Optional user context about the photo

    if not photo_data:
        await state.send_error("empty_photo", "Photo data is required")
        return

    session = gemini_service.get_session(state.session_id)
    if not session:
        session = await gemini_service.create_session(state.session_id, state.mode)

    try:
        # Create prompt with optional context
        prompt = "Analyze this image and describe what you see."
        if context:
            prompt = f"{context}\n\n[User provided context: {context}]"

        async for chunk in session.send_image(photo_data, mime_type, "photo", prompt):
            if chunk["type"] == "text":
                await state.send(
                    "ai.text",
                    {"content": chunk["content"], "complete": chunk.get("complete", False)},
                )
    except Exception as e:
        logger.error(f"Photo analysis error: {e}")
        await state.send_error("vision_error", str(e))


async def handle_mode_switch_video(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle video.modeSwitch message - switch between camera and screen."""
    new_mode = payload.get("mode", "camera")  # camera or screen

    logger.info(f"Video mode switch: {state.session_id} -> {new_mode}")

    # Notify session of context change
    session = gemini_service.get_session(state.session_id)
    if session:
        session.update_summary(f"User switched to {new_mode} view")

    await state.send(
        "video.modeSwitched",
        {"mode": new_mode},
    )
