"""Vision/video frame handlers."""

import logging
from typing import Any

from app.services.gemini_service import gemini_service
from app.ws.connection import ConnectionState
from app.ws.handlers.gemini import _ensure_receive_loop, _get_or_create_session

logger = logging.getLogger(__name__)


async def handle_video_frame(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle video.frame message - stream camera/screen frame to Gemini.

    Video is processed at 1 FPS by Gemini Live API.
    Frames are sent via send_realtime_input() for low-latency streaming.
    """
    frame_data = payload.get("data", "")  # base64 encoded image
    mime_type = payload.get("mimeType", "image/jpeg")

    if not frame_data:
        await state.send_error("empty_frame", "Frame data is required")
        return

    try:
        session = await _get_or_create_session(state)
        if not session:
            return

        # Send frame - fire-and-forget for video streaming
        # Responses come through the background receive loop
        logger.info(f"Sending video frame to Gemini: {len(frame_data)} chars, mime: {mime_type}")
        await session.send_video_frame(frame_data, mime_type)
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown vision error"
        logger.error(f"Vision error for {state.session_id}: {error_msg}", exc_info=True)
        await state.send_error("vision_error", error_msg[:500])


async def handle_photo_capture(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle photo.capture message - analyze a single photo.

    Sends image + text prompt. Responses come via the background receive loop.
    """
    photo_data = payload.get("data", "")  # base64 encoded image
    mime_type = payload.get("mimeType", "image/jpeg")
    context = payload.get("context", "")  # Optional user context

    if not photo_data:
        await state.send_error("empty_photo", "Photo data is required")
        return

    try:
        session = await _get_or_create_session(state)
        if not session:
            return

        # Create prompt based on context
        prompt = context if context else "Analyze this image and describe what you see."

        # Fire-and-forget: send image + prompt, responses come via receive loop
        await session.send_image(photo_data, mime_type, prompt)
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
