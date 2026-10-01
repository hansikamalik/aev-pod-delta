# How to run this load generator:
# 1. Ensure the FastAPI server is running: python -m uvicorn app.main:app --reload
# 2. Run the load test script: python app/load_generator.py

import concurrent.futures
import logging
import random
import time
import requests

# Configure professional logging format
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

TARGET_URL = "http://127.0.0.1:8000/copilot/query"

SAMPLE_QUERIES = [
    "What is the policy on secure data handling?",
    "Explain the risk of service account keys.",
    "How do I configure the API gateway fallback?",
    "Test query for synthetic traffic generation",
    "What are the best practices for secure coding?",
]


def send_request(request_id: int):
  payload = {"question": random.choice(SAMPLE_QUERIES)}
  headers = {"Content-Type": "application/json"}

  start_time = time.time()
  try:
    response = requests.post(
        TARGET_URL, json=payload, headers=headers, timeout=10
    )
    duration = time.time() - start_time
    logger.info(
        f"Request #{request_id} completed | Status: {response.status_code} |"
        f" Latency: {duration:.3f}s"
    )
    return response.status_code
  except requests.exceptions.RequestException as e:
    logger.error(f"Request #{request_id} failed: {e}")
    return None


def run_load_generator(total_requests: int = 30, max_workers: int = 5):
  logger.info(
      f"Initiating load test: {total_requests} total requests, concurrency:"
      f" {max_workers}"
  )

  start_total = time.time()
  success_count = 0
  failure_count = 0

  with concurrent.futures.ThreadPoolExecutor(
      max_workers=max_workers
  ) as executor:
    futures = {
        executor.submit(send_request, i + 1): i + 1
        for i in range(total_requests)
    }

    for future in concurrent.futures.as_completed(futures):
      status = future.result()
      if status == 200:
        success_count += 1
      else:
        failure_count += 1

  total_duration = time.time() - start_total
  logger.info("Load test execution summary:")
  logger.info(f"Total Duration: {total_duration:.2f} seconds")
  logger.info(f"Successful Requests: {success_count}")
  logger.info(f"Failed Requests: {failure_count}")


if __name__ == "__main__":
  run_load_generator(total_requests=30, max_workers=5)