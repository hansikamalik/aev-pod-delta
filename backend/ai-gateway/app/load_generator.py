# How to run this load generator:
# 1. Ensure the FastAPI server is running: python -m uvicorn app.main:app --reload
# 2. Run the load test script: python app/load_generator.py

import asyncio
import httpx
import time

# Total requests aur concurrent users configure kar le
TOTAL_REQUESTS = 100
CONCURRENT_USERS = 10

async def send_request(client, index):
    # Har request ke liye alag user ID generate karein (e.g., user_1, user_2, ... user_10)
    user_id = f"user_{index % 10 + 1}"
    headers = {"X-User-ID": user_id}  # Agar header ke through user pass hota hai
    
    # Payload ya endpoint jahan request ja rahi hai
    url = "http://127.0.0.1:8000/copilot/query" # Ya jo bhi tera endpoint ho
    payload = {"query": "test query", "user_id": user_id} # Agar body mein hai

    try:
        response = await client.post(url, json=payload, headers=headers, timeout=10.0)
        return response.status_code
    except Exception as e:
        return "connection_error"

async def main():
    start_time = time.time()
    
    success_count = 0
    rate_limited_count = 0
    server_error_count = 0
    connection_errors = 0

    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, i) for i in range(TOTAL_REQUESTS)]
        results = await asyncio.gather(*tasks)

    for status in results:
        if status == 200:
            success_count += 1
        elif status == 429:
            rate_limited_count += 1
        elif status in [500, 502, 503, 504]:
            server_error_count += 1
        else:
            connection_errors += 1

    total_time = time.time() - start_time

    print("\n--- Load Test Summary ---")
    print(f"Total Time Taken:     {total_time:.2f} seconds")
    print(f"Successful (200 OK):  {success_count}")
    print(f"Rate-Limited (429):   {rate_limited_count} (Expected throttling)")
    print(f"Server Errors/Fail:   {server_error_count} (Actual failures/bugs)")
    print(f"Connection Errors:    {connection_errors}")

if __name__ == "__main__":
    asyncio.run(main())