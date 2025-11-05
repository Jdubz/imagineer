"""Web crawler for discovering images on websites using Playwright."""

import asyncio
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import Browser, async_playwright

from .config import CrawlerConfig

logger = logging.getLogger(__name__)


class WebCrawler:
    """Discovers image URLs from websites using Playwright for JavaScript rendering."""

    def __init__(self, config: CrawlerConfig):
        """
        Initialize the web crawler.

        Args:
            config: Crawler configuration
        """
        self.config = config
        self.visited_urls: set[str] = set()
        self.image_urls: set[str] = set()
        self.image_metadata: dict[str, dict] = {}  # Store metadata per image URL

    async def crawl(self, start_url: str, max_images: Optional[int] = None) -> list[str]:
        """
        Crawl a website to discover image URLs.

        Args:
            start_url: Starting URL to crawl
            max_images: Maximum number of images to discover

        Returns:
            List of discovered image URLs
        """
        max_imgs = max_images or self.config.max_images
        logger.info(f"Starting crawl of {start_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                await self._crawl_recursive(browser, start_url, depth=0, max_images=max_imgs)
            finally:
                await browser.close()

        logger.info(f"Discovered {len(self.image_urls)} images")
        return list(self.image_urls)

    def get_image_metadata(self, url: str) -> Optional[dict]:
        """
        Get metadata for a discovered image URL.

        Args:
            url: Image URL

        Returns:
            Metadata dict with alt_text, title, html_caption if available
        """
        return self.image_metadata.get(url)

    async def _crawl_recursive(
        self, browser: Browser, url: str, depth: int, max_images: int
    ) -> None:
        """
        Recursively crawl a URL and its linked pages.

        Args:
            browser: Playwright browser instance
            url: URL to crawl
            depth: Current depth in crawl tree
            max_images: Maximum images to collect
        """
        # Check stop conditions
        if depth > self.config.max_depth:
            return
        if len(self.image_urls) >= max_images:
            return
        if url in self.visited_urls:
            return

        # Mark as visited
        self.visited_urls.add(url)
        parsed_start = urlparse(url)

        try:
            page = await browser.new_page(
                user_agent=self.config.user_agent,
            )
            page.set_default_timeout(self.config.timeout * 1000)

            # Navigate to page
            await page.goto(url, wait_until="networkidle", timeout=self.config.timeout * 1000)

            # Wait for lazy-loaded images
            await asyncio.sleep(1)

            # Get page content
            content = await page.content()
            await page.close()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, "lxml")

            # Extract image URLs with metadata
            await self._extract_images(soup, url)

            # Extract links for recursive crawling
            if depth < self.config.max_depth and len(self.image_urls) < max_images:
                links = await self._extract_links(soup, url, parsed_start.netloc)

                # Crawl links concurrently (but limited)
                tasks = []
                for link in links[:10]:  # Limit concurrent page crawls
                    if len(self.image_urls) >= max_images:
                        break
                    task = self._crawl_recursive(browser, link, depth + 1, max_images)
                    tasks.append(task)

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.debug(f"Error crawling {url}: {e}")

    async def _extract_images(self, soup: BeautifulSoup, base_url: str) -> None:
        """
        Extract image URLs and metadata from parsed HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative URLs
        """
        # Find all img tags
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                img_url = urljoin(base_url, src)
                if not self._is_valid_image_url(img_url):
                    logger.debug(f"Filtered URL (invalid): {img_url}")
                    continue
                if not self._is_content_image(img):
                    logger.debug(f"Filtered URL (UI element): {img_url}")
                    continue

                # Store image URL
                self.image_urls.add(img_url)

                # Store metadata
                self.image_metadata[img_url] = {
                    "alt_text": img.get("alt", "").strip() or None,
                    "title": img.get("title", "").strip() or None,
                    "html_caption": self._extract_nearby_caption(img),
                }

        # Find background images in style attributes
        for elem in soup.find_all(style=True):
            style = elem["style"]
            if "url(" in style:
                # Extract URL from style
                start = style.find("url(") + 4
                end = style.find(")", start)
                if end > start:
                    url = style[start:end].strip("'\"")
                    img_url = urljoin(base_url, url)
                    if self._is_valid_image_url(img_url) and self._is_content_background(elem):
                        self.image_urls.add(img_url)
                        self.image_metadata[img_url] = {
                            "alt_text": None,
                            "title": elem.get("title", "").strip() or None,
                            "html_caption": self._extract_nearby_caption(elem),
                        }

    def _extract_nearby_caption(self, element) -> Optional[str]:
        """
        Try to find caption text near an image element.

        Args:
            element: BeautifulSoup element

        Returns:
            Caption text if found, None otherwise
        """
        # Check for figcaption in parent figure
        parent = element.parent
        if parent and parent.name == "figure":
            figcaption = parent.find("figcaption")
            if figcaption:
                return figcaption.get_text(strip=True)

        # Check for adjacent caption elements
        next_sibling = element.find_next_sibling()
        if next_sibling and next_sibling.name in ["p", "div", "span"]:
            text = next_sibling.get_text(strip=True)
            # Only use if it looks like a caption (short-ish text)
            if text and len(text) < 200:
                return text

        return None

    async def _extract_links(
        self, soup: BeautifulSoup, base_url: str, base_netloc: str
    ) -> list[str]:
        """
        Extract same-domain links for further crawling.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative URLs
            base_netloc: Base domain to stay within

        Returns:
            List of links to crawl
        """
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Only follow same-domain links
            if parsed.netloc == base_netloc and parsed.scheme in ["http", "https"]:
                if full_url not in self.visited_urls:
                    links.append(full_url)

        return links

    def _is_valid_image_url(self, url: str) -> bool:
        """
        Check if URL is a valid image URL.

        Args:
            url: URL to check

        Returns:
            True if valid image URL
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        full_url_lower = url.lower()

        # Check for image extensions
        image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".jfif"]
        if not any(path.endswith(ext) for ext in image_extensions):
            return False

        # Filter out common thumbnail patterns in path
        thumbnail_patterns = [
            "-th.",
            "_th.",
            "-thumb",
            "_thumb",
            "-small",
            "_small",
            "-preview",
            "_preview",
            "-icon",
            "_icon",
            "/thumbs/",
            "/thumbnails/",
            "-xs.",
            "-sm.",
            "_xs.",
            "_sm.",
            "-tiny",
            "_tiny",
            "-mini",
            "_mini",
        ]
        if any(pattern in path for pattern in thumbnail_patterns):
            return False

        # Filter CDN thumbnail parameters
        cdn_params = [
            "?w=",
            "&w=",
            "?width=",
            "&width=",
            "?h=",
            "&h=",
            "?height=",
            "&height=",
            "?size=",
            "&size=",
            "?resize=",
            "&resize=",
            "?scale=",
            "&scale=",
            "?thumb=",
            "&thumb=",
        ]
        # Only filter if the parameter indicates a small size
        for param in cdn_params:
            if param in full_url_lower:
                # Extract the value and check if it's small
                try:
                    idx = full_url_lower.find(param) + len(param)
                    value_str = ""
                    for char in full_url_lower[idx:]:
                        if char.isdigit():
                            value_str += char
                        else:
                            break
                    if value_str and int(value_str) < 200:  # Less than 200px likely thumbnail
                        return False
                except (ValueError, TypeError):
                    pass

        # Filter common UI image paths
        ui_patterns = [
            "/logo",
            "/icon",
            "/badge",
            "/button",
            "/banner",
            "/nav",
            "/header",
            "/footer",
            "/sidebar",
            "/menu",
            "/social",
            "/avatar",
            "/profile",
            "/user",
            "/sprite",
            "/ui/",
            "/assets/ui",
            "/images/ui",
        ]
        if any(pattern in path for pattern in ui_patterns):
            return False

        return True

    def _is_content_image(self, img_tag) -> bool:
        """
        Check if an img tag represents actual content (not UI/logo/icon).

        Args:
            img_tag: BeautifulSoup img tag

        Returns:
            True if likely content image
        """
        # Check dimensions from HTML attributes
        width = img_tag.get("width", "")
        height = img_tag.get("height", "")

        # Filter very small images (likely icons)
        try:
            if width and int(width) < 100:
                return False
            if height and int(height) < 100:
                return False
        except (ValueError, TypeError):
            pass

        # Check class and id attributes for UI indicators
        classes = " ".join(img_tag.get("class", [])).lower()
        img_id = (img_tag.get("id") or "").lower()
        alt_text = (img_tag.get("alt") or "").lower()

        # Skip images with UI-related class/id/alt
        ui_keywords = [
            "logo",
            "icon",
            "badge",
            "button",
            "banner",
            "avatar",
            "nav",
            "menu",
            "header",
            "footer",
            "sidebar",
            "social",
            "thumbnail",
            "thumb",
            "sprite",
            "ui-",
            "advertisement",
            "ad-",
            "promo",
            "share",
            "profile",
            "user-img",
        ]

        combined_text = f"{classes} {img_id} {alt_text}"
        if any(keyword in combined_text for keyword in ui_keywords):
            return False

        # Check for common icon sizes (exactly 16x16, 32x32, etc.)
        icon_sizes = ["16", "20", "24", "32", "48", "64"]
        if width in icon_sizes and height in icon_sizes and width == height:
            return False

        return True

    def _is_content_background(self, elem) -> bool:
        """
        Check if a background image element is content (not decorative UI).

        Args:
            elem: BeautifulSoup element with background image

        Returns:
            True if likely content background
        """
        # Check class and id for UI indicators
        classes = " ".join(elem.get("class", [])).lower()
        elem_id = (elem.get("id") or "").lower()

        # Skip UI/decorative backgrounds
        ui_keywords = [
            "logo",
            "icon",
            "badge",
            "button",
            "banner",
            "nav",
            "menu",
            "header",
            "footer",
            "sidebar",
            "background-pattern",
            "bg-pattern",
            "texture",
        ]

        combined = f"{classes} {elem_id}"
        if any(keyword in combined for keyword in ui_keywords):
            return False

        return True
