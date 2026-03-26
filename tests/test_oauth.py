"""Quick OAuth test — run with: python test_oauth.py <sk-ant-oat01-...> [body.json]"""
import asyncio
import json
import sys
import httpx

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
BETAS = "claude-code-20250219,oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,interleaved-thinking-2025-05-14"


async def send(token: str, body: dict) -> int:
    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": BETAS,
        "accept": "text/event-stream",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", MESSAGES_URL, headers=headers, json=body) as resp:
            if resp.status_code != 200:
                raw = await resp.aread()
                print(f"  {resp.status_code}: {raw.decode()[:200]}")
            else:
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data and data != "[DONE]":
                            try:
                                ev = json.loads(data)
                                t = (ev.get("delta") or ev.get("content_block") or {}).get("text", "")
                                if t:
                                    print(t, end="", flush=True)
                            except Exception:
                                pass
                print()
            return resp.status_code


async def test(token: str, body_path: str | None = None):
    if body_path:
        # Test exact nanobot body
        body = json.loads(open(body_path).read())
        print(f"=== Testing FULL nanobot body ({body_path}) ===")
        status = await send(token, body)
        if status == 200:
            print("OK — full body works!")
            return

        # Binary search: remove fields one by one
        print("\n--- Binary search: removing fields ---")
        for field in ("temperature", "tool_choice", "tools"):
            if field not in body:
                continue
            trimmed = {k: v for k, v in body.items() if k != field}
            print(f"  Without {field!r}: ", end="")
            status = await send(token, trimmed)
            if status == 200:
                print(f"  ^^^ removing {field!r} FIXED it!")

        # Try minimal system
        print("  With minimal system: ", end="")
        minimal_sys = {**body, "system": "You are Claude Code, Anthropic's official CLI for Claude."}
        await send(token, minimal_sys)

        # Try single simple message
        print("  With simple message: ", end="")
        simple_msg = {**body, "messages": [{"role": "user", "content": "hi"}]}
        await send(token, simple_msg)
    else:
        # Minimal baseline
        body = {
            "model": "claude-opus-4-6",
            "max_tokens": 100,
            "stream": True,
            "system": "You are Claude Code, Anthropic's official CLI for Claude.",
            "messages": [{"role": "user", "content": "hi"}],
        }
        print(f"=== Minimal test (no tools, simple message) ===")
        await send(token, body)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_oauth.py sk-ant-oat01-... [/tmp/nanobot_oauth_body.json]")
        sys.exit(1)
    token = sys.argv[1]
    body_path = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(test(token, body_path))
