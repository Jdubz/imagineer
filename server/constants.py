"""
Shared constants for the Imagineer application
"""

# AI labeling service returns these rating values
# We use them to determine the boolean is_nsfw flag (blur or not)
NSFW_BLUR_RATINGS = {"ADULT", "EXPLICIT"}
