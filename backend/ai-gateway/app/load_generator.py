
"""Load-test harness for the AI Gateway Copilot query endpoint."""

import concurrent.futures
import logging
import os
import random
import statistics
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TARGET_URL = os.getenv(
    "LOAD_TEST_URL",
    "http://127.0.0.1:8000/copilot/query",
)

SAMPLE_QUERIES = [
    "What is the policy on secure data handling?",
    "Explain the risk of service account keys.",
    "How do I configure the API gateway fallback?",
    "Test query for synthetic traffic generation",
    "What are the best practices for secure coding?",
]


def send_request(request_id: int):
    """Send one request and return its status and latency."""
    payload = {"question": random.choice(SAMPLE_QUERIES)}
    headers = {
        "X-User-ID": f"load-test-user-{request_id}",
        "X-Org-Tier": "free",
    }
    start = time.perf_counter()

    try:
        response = requests.post(
            TARGET_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
        latency = time.perf_counter() - start

        logger.info(
            "Request #%s | status=%s | latency=%.3fs",
            request_id,
            response.status_code,
            latency,
        )

        return {
            "status": response.status_code,
            "latency": latency,
        }

    except requests.RequestException as exc:
        latency = time.perf_counter() - start
        logger.error("Request #%s failed: %s", request_id, exc)

        return {"status": None, "latency": latency}


def run_load_generator(total_requests=30, max_workers=5):
    """Run a small load test and summarize its results."""
    if total_requests < 1 or max_workers < 1:
        raise ValueError("Request count and workers must be positive")

    logger.info(
        "Starting load test: requests=%s, concurrency=%s, target=%s",
        total_requests,
        max_workers,
        TARGET_URL,
    )

    start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:
        futures = [
            executor.submit(send_request, index + 1)
            for index in range(total_requests)
        ]
        results = [future.result() for future in futures]

    elapsed = time.perf_counter() - start
    latencies = sorted(result["latency"] for result in results)

    successful = sum(
        result["status"] is not None
        and 200 <= result["status"] < 300
        for result in results
    )
    rate_limited = sum(
        result["status"] == 429 for result in results
    )
    server_errors = sum(
        result["status"] is not None
        and result["status"] >= 500
        for result in results
    )
    network_errors = sum(
        result["status"] is None for result in results
    )
    failed = total_requests - successful

    average = statistics.mean(latencies)
    p95_index = max(
        0,
        int(0.95 * len(latencies) + 0.999) - 1,
    )
    p95 = latencies[p95_index]

    logger.info("----- LOAD TEST SUMMARY -----")
    logger.info("Total requests: %s", total_requests)
    logger.info("Successful 2xx responses: %s", successful)
    logger.info("Failed/non-2xx responses: %s", failed)
    logger.info("Rate-limited responses (429): %s", rate_limited)
    logger.info("Server errors (5xx): %s", server_errors)
    logger.info("Network errors: %s", network_errors)
    logger.info("Error rate: %.2f%%", failed / total_requests * 100)
    logger.info("Total duration: %.2fs", elapsed)
    logger.info("Average latency: %.3fs", average)
    logger.info("P95 latency: %.3fs", p95)
    logger.info(
        "Throughput: %.2f requests/second",
        total_requests / elapsed if elapsed else 0,
    )


if __name__ == "__main__":
    run_load_generator(total_requests=30, max_workers=5)
