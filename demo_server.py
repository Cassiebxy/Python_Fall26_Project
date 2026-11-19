import json
import select
import socket
import sys

import server


# Xinyi: TCP server checks, adapted with Codex assistance.
def _check(name, passed):
    """Print one check result"""
    print(f"  [{'OK' if passed else 'FAIL'}] {name}")
    assert passed, name


def encode(obj):
    return (json.dumps(obj) + "\n").encode("utf-8")


def read_reply(reader):
    line = reader.readline()
    assert line.endswith(b"\n"), "Missing complete reply"
    return json.loads(line)


def echo_request(line, state):
    return {"echo": json.loads(line)}


def send_reply(conn, reply):
    conn.sendall(encode(reply))


def framing_demo():
    print("== Xinyi: TCP message framing ==")

    with socket.create_connection(server.ADDR, timeout=2) as conn, conn.makefile("rb") as reader:
        conn.sendall(b'{"id":1}')
        readable, _, _ = select.select([conn], [], [], 0.2)
        _check("server waits for the newline", not readable)
        conn.sendall(b"\n")
        _check("split request produces one reply", read_reply(reader) == {"echo": {"id": 1}})

        conn.sendall(encode({"id": 2}) + encode({"id": 3}))
        for number in (2, 3):
            _check(f"received reply for request {number}",
                   read_reply(reader) == {"echo": {"id": number}})

        conn.sendall(b'{"id":')
    with socket.create_connection(server.ADDR, timeout=2) as conn, conn.makefile("rb") as reader:
        conn.sendall(encode({"id": 4}))
        _check("new client can connect after an incomplete request",
               read_reply(reader) == {"echo": {"id": 4}})



def query_demo():
    print("== Xinyi: availability over TCP ==")
    query = {"op": "availability", "pet_type": "dog",
             "check_in": "2026-12-01", "check_out": "2026-12-03"}
    with socket.create_connection(server.ADDR, timeout=2) as conn, conn.makefile("rb") as reader:
        conn.sendall(encode(query))
        first = read_reply(reader)
        _check("availability query succeeds", first.get("ok") is True)
        remaining = first["remaining"]
        _check("only the two occupied nights are returned",
               set(remaining) == {"2026-12-01", "2026-12-02"})
        _check("each night has a non-negative number of spaces",
               all(type(n) is int and n >= 0 for n in remaining.values()))

        conn.sendall(b'not JSON\n')
        error = read_reply(reader)
        _check("invalid JSON gets an error reply",
               error.get("ok") is False and error.get("error") == "bad request")
        conn.sendall(encode(query))
        _check("same connection still returns the original availability",
               read_reply(reader) == first)



def main():
    usage = "Usage: python3 demo_server.py {echo-server|framing|query}"
    if len(sys.argv) != 2:
        sys.exit(usage)

    mode = sys.argv[1]
    if mode == "echo-server":
        server.serve(None, echo_request, send_reply)
    elif mode == "framing":
        framing_demo()
    elif mode == "query":
        query_demo()
    else:
        sys.exit(usage)


if __name__ == "__main__":
    main()
