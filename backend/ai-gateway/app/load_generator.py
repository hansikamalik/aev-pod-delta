# How to run this load generator:
# 1. Ensure the FastAPI server is running: python -m uvicorn app.main:app --reload
# 2. Run the load test script: python app/load_generator.py

import asyncio
import time
import httpx

# Configuration settings for total requests and target endpoint
TOTAL_REQUESTS = 100
URL = "http://127.0.0.1:8000/copilot/query"

# Generate a pool of distinct user identifiers to simulate multi-tenant traffic
USERS = [f"user_org_{i}" for i in range(1, 11)]


async def send_request(client, index):
  # Assign a distinct user ID based on the request index
  user_id = USERS[index % len(USERS)]

  # Transmit the user identifier via HTTP headers for rate-limiting evaluation
  headers = {"X-User-ID": user_id}

  # Construct the request payload using the expected schema while omitting redundant body parameters
  payload = {"question": f"Test query {index}"}

  try:
    response = await client.post(
        URL, json=payload, headers=headers, timeout=15.0
    )
    return response.status_code
  except httpx.RequestError:
    return "connection_error"


async def main():
  print(
      f"Starting load test with {TOTAL_REQUESTS} requests across {len(USERS)}"
      " distinct users..."
  )
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
      rate_limited_count += 1  # Expected throttling response (rate-limited)
    elif status in [500, 502, 503, 504]:
      server_error_count += 1  # Actual server errors and unexpected failures
    else:
      connection_errors += 1

  total_time = time.time() - start_time

  print("\n--- Load Test Summary ---")
  print(f"Total Time Taken:       {total_time:.2f} seconds")
  print(f"Successful (200 OK):    {success_count}")
  print(f"Rate-Limited (429):     {rate_limited_count} (Expected throttling)")
  print(
      f"Server Errors/Fail:     {server_error_count} (Actual failures/bugs"
      " - 500s)"
  )
  print(f"Connection Errors:      {connection_errors}")


if __name__ == "__main__":
  asyncio.run(main())