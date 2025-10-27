#!/usr/bin/env python3
"""
GitHub Webhook Listener for Auto-Deployment

Listens for push events to main branch and triggers deployment.
Validates webhook signature for security.
"""

import hashlib
import hmac
import logging
import os
import subprocess

from flask import Flask, jsonify, request

# Configuration
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "changeme")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
BRANCH = os.environ.get("BRANCH", "main")
APP_DIR = os.environ.get("APP_DIR", "/app")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def verify_signature(payload_body, signature_header):
    """Verify GitHub webhook signature"""
    if not signature_header:
        return False

    # Get signature from header
    hash_algorithm, github_signature = signature_header.split("=")
    algorithm = hashlib.__dict__.get(hash_algorithm)

    if not algorithm:
        return False

    # Calculate expected signature
    mac = hmac.new(WEBHOOK_SECRET.encode("utf-8"), msg=payload_body, digestmod=algorithm)
    expected_signature = mac.hexdigest()

    # Compare signatures
    return hmac.compare_digest(expected_signature, github_signature)


def deploy():
    """Execute deployment script"""
    try:
        logger.info("Starting deployment...")

        # Run deployment script
        result = subprocess.run(
            ["/scripts/deploy/auto-deploy.sh"], capture_output=True, text=True, timeout=300
        )

        if result.returncode == 0:
            logger.info("Deployment successful!")
            logger.info(result.stdout)
            return True
        else:
            logger.error("Deployment failed!")
            logger.error(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        logger.error("Deployment timed out!")
        return False
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        return False


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle GitHub webhook"""

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(request.data, signature):
        logger.warning("Invalid webhook signature!")
        return jsonify({"error": "Invalid signature"}), 403

    # Parse payload
    payload = request.json

    # Check event type
    event = request.headers.get("X-GitHub-Event")
    if event != "push":
        logger.info(f"Ignoring event: {event}")
        return jsonify({"message": "Event ignored"}), 200

    # Check branch
    ref = payload.get("ref", "")
    branch_name = ref.replace("refs/heads/", "")

    if branch_name != BRANCH:
        logger.info(f"Ignoring push to branch: {branch_name}")
        return jsonify({"message": f"Branch {branch_name} ignored"}), 200

    # Check repository
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    if GITHUB_REPO and repo_full_name != GITHUB_REPO:
        logger.warning(f"Ignoring push to wrong repo: {repo_full_name}")
        return jsonify({"error": "Wrong repository"}), 403

    # Get commit info
    commits = payload.get("commits", [])
    commit_messages = [c.get("message") for c in commits[:3]]

    logger.info(f"Received push to {branch_name} on {repo_full_name}")
    logger.info(f"Commits: {commit_messages}")

    # Trigger deployment
    if deploy():
        return (
            jsonify(
                {"message": "Deployment successful", "branch": branch_name, "commits": len(commits)}
            ),
            200,
        )
    else:
        return jsonify({"error": "Deployment failed", "branch": branch_name}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route("/deploy", methods=["POST"])
def manual_deploy():
    """Manual deployment trigger (no signature check)"""
    logger.info("Manual deployment triggered")

    if deploy():
        return jsonify({"message": "Deployment successful"}), 200
    else:
        return jsonify({"error": "Deployment failed"}), 500


if __name__ == "__main__":
    logger.info(f"Starting webhook listener on port 9000")
    logger.info(f"Watching repository: {GITHUB_REPO}")
    logger.info(f"Watching branch: {BRANCH}")

    app.run(host="0.0.0.0", port=9000)
