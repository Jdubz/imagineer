"""
AI-powered image labeling with Claude vision
"""

import os
import base64
import logging
from io import BytesIO
from pathlib import Path
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# Try to import anthropic, but don't fail if not available
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. AI labeling will be disabled.")

def encode_image(image_path, max_size=1568):
    """
    Encode image to base64 for Claude API
    
    Args:
        image_path: Path to image file
        max_size: Maximum dimension for Claude (1568px)
    
    Returns:
        Base64 encoded image data
    """
    with PILImage.open(image_path) as img:
        # Resize if too large
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, PILImage.LANCZOS)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Encode to base64
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

def get_labeling_prompts():
    """Get different prompt templates for various labeling needs"""
    return {
        'default': """Analyze this image and provide:
1. A detailed description suitable for AI training (2-3 sentences)
2. NSFW rating: SAFE, SUGGESTIVE, ADULT, or EXPLICIT
3. 5-10 relevant tags (comma-separated)

Format:
DESCRIPTION: [description]
NSFW: [rating]
TAGS: [tags]""",

        'sd_training': """You are creating training captions for Stable Diffusion 1.5.

Analyze this image and write a detailed, factual description suitable for AI training. Focus on:
- Visual elements (colors, composition, style)
- Subject matter (what is depicted)
- Artistic style or medium
- Notable details

Also provide:
- NSFW rating: SAFE, SUGGESTIVE, ADULT, or EXPLICIT
- 5-10 descriptive tags

Format:
CAPTION: [one detailed paragraph]
NSFW: [rating]
TAGS: [tags]""",

        'detailed': """Provide an extremely detailed analysis of this image including:
- Subject and composition
- Colors, lighting, and atmosphere
- Style, technique, or medium
- Mood and emotional content
- Any text or symbols visible
- NSFW rating
- Comprehensive tags

Be thorough and precise."""
    }

def label_image_with_claude(image_path, prompt_type='default'):
    """
    Label a single image using Claude vision
    
    Args:
        image_path: Path to image file
        prompt_type: Type of prompt to use ('default', 'sd_training', 'detailed')
    
    Returns:
        Dict with labeling results or error
    """
    if not ANTHROPIC_AVAILABLE:
        return {'status': 'error', 'message': 'Anthropic library not available'}
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {'status': 'error', 'message': 'ANTHROPIC_API_KEY not set'}
    
    try:
        # Encode image
        image_data = encode_image(image_path)
        
        # Get prompt
        prompts = get_labeling_prompts()
        prompt = prompts.get(prompt_type, prompts['default'])
        
        # Initialize Claude client
        client = Anthropic(api_key=api_key)
        
        # Call Claude API
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        
        result_text = response.content[0].text
        logger.info(f"Claude response: {result_text[:200]}...")
        
        # Parse response
        description = None
        nsfw_rating = 'SAFE'
        tags = []
        
        for line in result_text.split('\n'):
            line = line.strip()
            if line.startswith('DESCRIPTION:') or line.startswith('CAPTION:'):
                description = line.split(':', 1)[1].strip()
            elif line.startswith('NSFW:'):
                nsfw_rating = line.split(':', 1)[1].strip()
            elif line.startswith('TAGS:'):
                tags_str = line.split(':', 1)[1].strip()
                tags = [tag.strip() for tag in tags_str.split(',')]
        
        return {
            'status': 'success',
            'description': description,
            'nsfw_rating': nsfw_rating,
            'tags': tags,
            'raw_response': result_text
        }
        
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return {'status': 'error', 'message': f'Claude API failed: {e}'}

def batch_label_images(image_paths, prompt_type='default', progress_callback=None):
    """
    Label multiple images in batch
    
    Args:
        image_paths: List of image file paths
        prompt_type: Type of prompt to use
        progress_callback: Optional callback for progress updates
    
    Returns:
        Dict with batch results
    """
    results = {
        'total': len(image_paths),
        'success': 0,
        'failed': 0,
        'results': []
    }
    
    for i, image_path in enumerate(image_paths):
        if progress_callback:
            progress_callback(i + 1, len(image_paths))
        
        result = label_image_with_claude(image_path, prompt_type)
        result['image_path'] = image_path
        
        if result['status'] == 'success':
            results['success'] += 1
        else:
            results['failed'] += 1
        
        results['results'].append(result)
    
    return results
