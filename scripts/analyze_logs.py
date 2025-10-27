#!/usr/bin/env python3
"""
Log analysis script for Imagineer
Analyzes structured JSON logs for insights and monitoring
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def load_logs(log_file):
    """Load and parse JSON logs"""
    logs = []
    try:
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        # Handle both single-line JSON and multi-line JSON
                        if line.startswith("{") and line.endswith("}"):
                            log_entry = json.loads(line)
                            logs.append(log_entry)
                        else:
                            # Try to parse as regular log line
                            continue
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
        return []

    return logs


def analyze_request_logs(logs):
    """Analyze request patterns and performance"""
    print("=== Request Analysis ===")

    # Filter request completion logs
    request_logs = [log for log in logs if log.get("operation") == "request_completed"]

    if not request_logs:
        print("No request logs found")
        return

    # Request counts by endpoint
    endpoint_counts = Counter()
    response_times = []
    status_codes = Counter()

    for log in request_logs:
        path = log.get("request", {}).get("path", "unknown")
        endpoint_counts[path] += 1

        if "duration_ms" in log:
            response_times.append(log["duration_ms"])

        if "status_code" in log:
            status_codes[log["status_code"]] += 1

    print(f"Total requests: {len(request_logs)}")
    print(f"Unique endpoints: {len(endpoint_counts)}")
    print()

    print("Top endpoints:")
    for endpoint, count in endpoint_counts.most_common(10):
        print(f"  {endpoint}: {count} requests")
    print()

    if response_times:
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        print(f"Response times (ms):")
        print(f"  Average: {avg_time:.1f}")
        print(f"  Min: {min_time}")
        print(f"  Max: {max_time}")
        print()

    print("Status codes:")
    for status, count in status_codes.most_common():
        print(f"  {status}: {count}")
    print()


def analyze_errors(logs):
    """Analyze error patterns"""
    print("=== Error Analysis ===")

    error_logs = [log for log in logs if log.get("level") in ["ERROR", "WARNING"]]

    if not error_logs:
        print("No errors found")
        return

    print(f"Total errors/warnings: {len(error_logs)}")
    print()

    # Error types
    error_types = Counter()
    operations = Counter()

    for log in error_logs:
        if "error_type" in log:
            error_types[log["error_type"]] += 1
        if "operation" in log:
            operations[log["operation"]] += 1

    if error_types:
        print("Error types:")
        for error_type, count in error_types.most_common():
            print(f"  {error_type}: {count}")
        print()

    if operations:
        print("Operations with errors:")
        for operation, count in operations.most_common():
            print(f"  {operation}: {count}")
        print()


def analyze_security_logs(logs):
    """Analyze security-related logs"""
    print("=== Security Analysis ===")

    security_logs = [log for log in logs if "security" in log.get("logger", "")]

    if not security_logs:
        print("No security logs found")
        return

    print(f"Security events: {len(security_logs)}")
    print()

    # Authentication events
    auth_events = [log for log in security_logs if "authentication" in log.get("message", "")]
    print(f"Authentication events: {len(auth_events)}")

    # Failed logins
    failed_logins = [log for log in security_logs if "Failed login" in log.get("message", "")]
    print(f"Failed login attempts: {len(failed_logins)}")

    if failed_logins:
        print("Recent failed logins:")
        for log in failed_logins[-5:]:  # Last 5
            timestamp = log.get("timestamp", "unknown")
            print(f"  {timestamp}: {log.get('message', '')}")
    print()


def analyze_performance(logs):
    """Analyze performance metrics"""
    print("=== Performance Analysis ===")

    # Database operations
    db_ops = [log for log in logs if "operation" in log and "get_" in log["operation"]]

    if db_ops:
        print(f"Database operations: {len(db_ops)}")

        # Group by operation type
        op_types = Counter()
        for log in db_ops:
            op_types[log["operation"]] += 1

        print("Operation breakdown:")
        for op_type, count in op_types.most_common():
            print(f"  {op_type}: {count}")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <log_file>")
        print("Example: python analyze_logs.py logs/imagineer.log")
        return

    log_file = sys.argv[1]
    logs = load_logs(log_file)

    if not logs:
        print("No logs to analyze")
        return

    print(f"Analyzing {len(logs)} log entries from {log_file}")
    print("=" * 50)
    print()

    analyze_request_logs(logs)
    analyze_errors(logs)
    analyze_security_logs(logs)
    analyze_performance(logs)


if __name__ == "__main__":
    main()
