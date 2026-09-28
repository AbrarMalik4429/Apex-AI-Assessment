"""Small interactive client; requires the running API and DEMO_ENABLED=true."""

import json
from uuid import uuid4

import httpx


def main():
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=45) as client:
        response = client.post("/demo/session")
        response.raise_for_status()
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        confirmation = None
        pending = None
        print(
            "Booking demo. Type 'confirm' for the displayed proposal, 'reset' to start over, or 'quit'."
        )
        print("If a request fails, type 'retry' to resend the identical request safely.")
        while True:
            message = input("You: ").strip()
            if message == "quit":
                break
            if not message:
                continue
            if message == "retry":
                if pending is None:
                    print("There is no failed request to retry.")
                    continue
                payload = pending
            else:
                if pending is not None:
                    print(
                        "Resolve the previous failed request with 'retry' before starting another action."
                    )
                    continue
                payload = {"request_id": str(uuid4()), "message": message}
                if message.casefold() == "confirm" and confirmation:
                    payload["confirmation_token"] = confirmation
            try:
                response = client.post("/assistant/message", json=payload)
                data = response.json()
            except (httpx.RequestError, ValueError):
                pending = payload
                print("No verified response. Type 'retry' to reuse the same request_id.")
                continue
            pending = payload if response.status_code >= 500 else None
            if response.status_code < 500:
                confirmation = data.get("confirmation_token")
            print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
