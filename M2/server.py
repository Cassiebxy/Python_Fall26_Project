"""TCP connections and line-by-line requests for PetStay."""

import socket

# Xinyi: server connections and message framing
# AI assistance: OpenAI Codex helped implement.
ADDR = ("127.0.0.1", 5050)


def handle(conn, state, process_line, send):
    """Read one complete request at a time on this connection."""
    with conn.makefile("rb") as requests:
        for line in requests:
            if not line.endswith(b"\n"):
                # Client disconnected before finishing this request.
                return
            reply = process_line(line, state)
            send(conn, reply)


def serve(state, process_line, send):
    """Reuse the same state across successive clients."""
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(ADDR)
        listener.listen()
        print(f"PetStay listening on {ADDR}", flush=True)
        while True:
            conn, _ = listener.accept()
            with conn:
                try:
                    handle(conn, state, process_line, send)
                except ConnectionError:
                    continue


def main():
    from protocol import process_line, send
    from state import load_state

    state = load_state()   # shared by all connections
    serve(state, process_line, send)


if __name__ == "__main__":
    main()
