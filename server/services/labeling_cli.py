"""
AI-powered image labeling using Claude CLI in Docker containers
"""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ClaudeCliLabeler:
    """
    Runs Claude CLI in ephemeral Docker containers for image labeling
    """

    DOCKER_IMAGE = "imagineer-claude-cli:latest"
    CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize labeler

        Args:
            credentials_path: Path to Claude credentials file
                             (defaults to ~/.claude/.credentials.json)
        """
        self.credentials_path = (
            Path(credentials_path) if credentials_path else self.CREDENTIALS_PATH
        )

        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Claude credentials not found at {self.credentials_path}. "
                "Please run 'claude setup-token' first."
            )

    def label_image(
        self, image_path: str, prompt_type: str = "default", timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Label image using Claude CLI in Docker container

        Args:
            image_path: Absolute path to image file
            prompt_type: Type of labeling prompt to use
            timeout: Max seconds for Docker execution

        Returns:
            Dict with labeling results or error
        """
        image_path = Path(image_path).resolve()

        if not image_path.exists():
            return {"status": "error", "message": f"Image not found: {image_path}"}

        # Get prompt template
        prompt = self._get_prompt(prompt_type, image_path)

        # Build Docker command
        docker_cmd = [
            "docker",
            "run",
            "--rm",  # Remove container after exit
            "-v",
            f"{image_path.parent}:/images:ro",  # Mount image dir read-only
            "--tmpfs",
            "/home/node/.claude:uid=1000,gid=1000",  # Writable temp for CLI
            "-v",
            f"{self.credentials_path}:/tmp/host-creds.json:ro",  # Mount credentials
            self.DOCKER_IMAGE,
            "sh",
            "-c",
            f"cp /tmp/host-creds.json /home/node/.claude/.credentials.json && "
            f"claude --print --dangerously-skip-permissions --output-format json '{prompt}'",
        ]

        try:
            logger.info(f"Labeling {image_path.name} with Claude CLI in Docker")

            result = subprocess.run(
                docker_cmd, capture_output=True, text=True, timeout=timeout, check=True
            )

            # Parse CLI output
            return self._parse_response(result.stdout, result.stderr)

        except subprocess.TimeoutExpired:
            logger.error(f"Docker timeout after {timeout}s for {image_path.name}")
            return {"status": "error", "message": "Timeout"}

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker failed for {image_path.name}: {e.stderr}")
            return {"status": "error", "message": f"Docker error: {e.stderr}"}

        except Exception as e:
            logger.error(f"Unexpected error labeling {image_path.name}: {e}")
            return {"status": "error", "message": str(e)}

    def _get_prompt(self, prompt_type: str, image_path: Path) -> str:
        """Get labeling prompt template"""
        # Use absolute path in container
        container_path = f"/images/{image_path.name}"

        prompts = {
            "default": f"""Analyze {container_path}

Provide your response in this EXACT format:
DESCRIPTION: [2-3 sentence description suitable for AI training]
NSFW: [SAFE, SUGGESTIVE, ADULT, or EXPLICIT]
TAGS: [tag1, tag2, tag3, tag4, tag5]""",
            "sd_training": f"""Analyze {container_path}

You are creating training captions for Stable Diffusion 1.5.
Write a detailed, factual description suitable for AI training.

Provide your response in this EXACT format:
CAPTION: [one detailed paragraph describing visual elements, composition, style, and subject]
NSFW: [SAFE, SUGGESTIVE, ADULT, or EXPLICIT]
TAGS: [descriptive tags]""",
        }
        return prompts.get(prompt_type, prompts["default"])

    def _parse_response(self, stdout: str, stderr: str) -> Dict[str, Any]:  # noqa: C901
        """
        Parse Claude CLI JSON output

        The CLI returns JSON with structure:
        {
            "type": "result",
            "result": "... formatted text ...",
            ...
        }
        """
        if stderr:
            logger.warning(f"Claude CLI stderr: {stderr}")

        try:
            # Parse JSON response
            response_json = json.loads(stdout)
            raw_text = response_json.get("result", "")

            # Parse structured output from result text
            description = None
            nsfw_rating = "SAFE"
            tags = []

            for line in raw_text.split("\n"):
                line = line.strip()
                # Match DESCRIPTION: or CAPTION:
                if match := re.match(r"^(?:DESCRIPTION|CAPTION):\s*(.+)$", line):
                    description = match.group(1).strip()
                # Match NSFW:
                elif match := re.match(r"^NSFW:\s*(.+)$", line):
                    rating_text = match.group(1).strip().upper()
                    # Normalize rating to our standard values
                    if "SAFE" in rating_text or "SFW" in rating_text:
                        nsfw_rating = "SAFE"
                    elif "SUGGESTIVE" in rating_text:
                        nsfw_rating = "SUGGESTIVE"
                    elif "EXPLICIT" in rating_text:
                        nsfw_rating = "EXPLICIT"
                    elif "ADULT" in rating_text:
                        nsfw_rating = "ADULT"
                # Match TAGS:
                elif match := re.match(r"^TAGS:\s*(.+)$", line):
                    tags_str = match.group(1).strip()
                    # Split by comma or whitespace
                    tags = [tag.strip() for tag in re.split(r"[,\s]+", tags_str) if tag.strip()]

            return {
                "status": "success",
                "description": description,
                "nsfw_rating": nsfw_rating,
                "tags": tags,
                "raw_response": raw_text,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {
                "status": "error",
                "message": f"JSON parse error: {e}",
                "raw_output": stdout,
            }
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return {"status": "error", "message": f"Parse error: {e}", "raw_output": stdout}


def label_image_with_claude(image_path: str, prompt_type: str = "default") -> Dict[str, Any]:
    """
    Backward-compatible wrapper for existing code

    Args:
        image_path: Path to image file
        prompt_type: Type of prompt to use ('default', 'sd_training')

    Returns:
        Dict with labeling results or error
    """
    try:
        labeler = ClaudeCliLabeler()
        return labeler.label_image(image_path, prompt_type)
    except Exception as e:
        logger.error(f"Failed to initialize labeler: {e}")
        return {"status": "error", "message": str(e)}


def batch_label_images(image_paths, prompt_type="default", progress_callback=None):
    """
    Label multiple images in batch using Docker containers

    Args:
        image_paths: List of image file paths
        prompt_type: Type of prompt to use
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with batch results
    """
    try:
        labeler = ClaudeCliLabeler()
    except Exception as e:
        logger.error(f"Failed to initialize labeler: {e}")
        return {
            "total": len(image_paths),
            "success": 0,
            "failed": len(image_paths),
            "results": [{"status": "error", "message": str(e)} for _ in image_paths],
        }

    results = {"total": len(image_paths), "success": 0, "failed": 0, "results": []}

    for i, image_path in enumerate(image_paths):
        if progress_callback:
            progress_callback(i + 1, len(image_paths))

        result = labeler.label_image(image_path, prompt_type)
        result["image_path"] = image_path

        if result["status"] == "success":
            results["success"] += 1
        else:
            results["failed"] += 1

        results["results"].append(result)

    return results
