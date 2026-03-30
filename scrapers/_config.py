"""
Scraping behavior configuration for CHO Marketwatch System Project
- User agent, timeouts, delays
- Retry settings, headless mode
"""

SCRAPING_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "timeout": 30,
    "delay_between_requests": 5,
    "delay_between_websites": 10,
    "max_retries": 2,
    "headless": True,
}
