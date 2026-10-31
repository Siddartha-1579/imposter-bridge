import asyncio
import httpx
import uvicorn
from backend.main import app

async def main():
    config = uvicorn.Config(app=app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    # Wait for server to start
    await asyncio.sleep(1.0)

    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
            # 1. Test /health
            resp_health = await client.get("/health")
            print(f"[Health Check] Status: {resp_health.status_code}, Body: {resp_health.json()}")
            assert resp_health.status_code == 200
            assert resp_health.json()["status"] == "ok"

            # 2. Test homepage /
            resp_home = await client.get("/")
            print(f"[Homepage Check] Status: {resp_home.status_code}, Content-Type: {resp_home.headers.get('content-type')}")
            assert resp_home.status_code == 200
            assert "text/html" in resp_home.headers.get("content-type", "")
            assert "Imposter Word" in resp_home.text
            assert '<div id="root">' in resp_home.text

            # 3. Test static assets if referenced
            import re
            assets = re.findall(r'/assets/[a-zA-Z0-9_\-\.]+', resp_home.text)
            print(f"[Assets Found in HTML] {assets}")
            for asset in assets:
                resp_asset = await client.get(asset)
                print(f"[Asset Check] {asset} -> Status: {resp_asset.status_code}, Length: {len(resp_asset.content)} bytes")
                assert resp_asset.status_code == 200
                assert len(resp_asset.content) > 0

            print("\nALL SERVER ENDPOINTS & STATIC ASSETS VERIFIED SUCCESSFULLY!")
    finally:
        server.should_exit = True
        await server_task

if __name__ == "__main__":
    asyncio.run(main())
