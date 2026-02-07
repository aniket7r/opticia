"""WebSocket endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_websocket_connection():
    """Test WebSocket connects and receives session ID."""
    with client.websocket_connect("/ws/session") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connection.established"
        assert "sessionId" in data["payload"]
        assert len(data["payload"]["sessionId"]) == 36  # UUID length


def test_websocket_session_start():
    """Test session.start message flow."""
    with client.websocket_connect("/ws/session") as websocket:
        # Receive connection established
        data = websocket.receive_json()
        session_id = data["payload"]["sessionId"]

        # Send session.start
        websocket.send_json({
            "type": "session.start",
            "sessionId": session_id,
            "payload": {"mode": "text"},
        })

        # Receive session.ready
        data = websocket.receive_json()
        assert data["type"] == "session.ready"
        assert data["payload"]["mode"] == "text"
        assert "voice" in data["payload"]["capabilities"]
