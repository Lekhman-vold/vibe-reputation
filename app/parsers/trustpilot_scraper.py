import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TrustpilotScraper:
    def __init__(self):
        self.base_url = "https://www.trustpilot.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Chrome options for headless browsing
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
    
    def search_company_reviews(self, company_name: str, max_reviews: int = 100) -> List[Dict]:
        """
        Search for company reviews on Trustpilot
        
        Args:
            company_name: Name of the company to search for
            max_reviews: Maximum number of reviews to retrieve
            
        Returns:
            List of dictionaries containing review data
        """
        reviews = []
        
        try:
            # First, find the company's Trustpilot URL
            company_url = self._find_company_url(company_name)
            if not company_url:
                print(f"Could not find Trustpilot page for {company_name}")
                return reviews
            
            # Scrape reviews from the company page
            reviews = self._scrape_company_reviews(company_url, max_reviews)
            
        except Exception as e:
            print(f"Error searching Trustpilot reviews for {company_name}: {e}")
        
        return reviews
    
    def _find_company_url(self, company_name: str) -> Optional[str]:
        """
        Find the Trustpilot URL for a company
        
        Args:
            company_name: Name of the company
            
        Returns:
            Trustpilot URL for the company or None if not found
        """
        try:
            # Search using Trustpilot's business search
            search_url = f"{self.base_url}/search"
            params = {'query': company_name}
            
            response = requests.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for the first business result
            business_links = soup.find_all('a', href=re.compile(r'/review/'))
            
            for link in business_links:
                href = link.get('href', '')
                if href.startswith('/review/'):
                    return f"{self.base_url}{href}"
            
            # Alternative: try direct URL construction
            company_slug = company_name.lower().replace(' ', '').replace('.', '')
            potential_urls = [
                f"{self.base_url}/review/{company_slug}",
                f"{self.base_url}/review/{company_slug}.com",
                f"{self.base_url}/review/www.{company_slug}.com"
            ]
            
            for url in potential_urls:
                response = requests.head(url, headers=self.headers)
                if response.status_code == 200:
                    return url
            
        except Exception as e:
            print(f"Error finding company URL for {company_name}: {e}")
        
        return None
    
    def _scrape_company_reviews(self, company_url: str, max_reviews: int) -> List[Dict]:
        """
        Scrape reviews from a company's Trustpilot page
        
        Args:
            company_url: Trustpilot URL for the company
            max_reviews: Maximum number of reviews to retrieve
            
        Returns:
            List of review data
        """
        reviews = []
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.get(company_url)
            
            wait = WebDriverWait(driver, 10)
            
            # Wait for reviews to load - try multiple selectors
            review_selectors = [
                "[data-service-review-card-paper]",
                "article[data-testid='review']",
                ".review-card",
                ".consumer-review"
            ]
            
            reviews_found = False
            for selector in review_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    reviews_found = True
                    break
                except TimeoutException:
                    continue
            
            if not reviews_found:
                print("Reviews did not load in time")
                driver.quit()
                return reviews
            
            # Scroll and load more reviews
            reviews_loaded = 0
            while reviews_loaded < max_reviews:
                # Scroll down to load more reviews
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Check if "Load more" button exists and click it
                try:
                    load_more_button = driver.find_element(By.CSS_SELECTOR, "[data-pagination-button-next]")
                    if load_more_button.is_enabled():
                        driver.execute_script("arguments[0].click();", load_more_button)
                        time.sleep(3)
                except NoSuchElementException:
                    break
                
                # Get current review count - try multiple selectors
                current_reviews = []
                for selector in review_selectors:
                    current_reviews = driver.find_elements(By.CSS_SELECTOR, selector)
                    if current_reviews:
                        break
                
                if len(current_reviews) <= reviews_loaded:
                    break  # No new reviews loaded
                reviews_loaded = len(current_reviews)
            
            # Extract review data - try multiple selectors
            review_elements = []
            for selector in review_selectors:
                review_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if review_elements:
                    break
            
            for element in review_elements[:max_reviews]:
                try:
                    review_data = self._extract_review_data(element, company_url)
                    if review_data:
                        reviews.append(review_data)
                except Exception as e:
                    print(f"Error extracting review data: {e}")
                    continue
            
            driver.quit()
            
        except Exception as e:
            print(f"Error scraping reviews from {company_url}: {e}")
        
        return reviews
    
    def _extract_review_data(self, element, company_url: str) -> Optional[Dict]:
        """
        Extract review data from a review element
        
        Args:
            element: Selenium WebElement containing review data
            company_url: URL of the company page
            
        Returns:
            Dictionary containing review data
        """
        try:
            # Debug: Print element structure
            element_text = element.text[:100] if element.text else "No text"
            print(f"      Extracting review from element: {element_text}...")
            
            # Extract rating - try multiple selectors
            rating = 0
            rating_selectors = [
                "[data-service-review-rating] img",
                "img[alt*='star']",
                "[data-testid='rating'] img",
                ".star-rating img"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_element = element.find_element(By.CSS_SELECTOR, selector)
                    rating_alt = rating_element.get_attribute("alt")
                    rating_match = re.search(r'(\d+)', rating_alt)
                    rating = int(rating_match.group(1)) if rating_match else 0
                    print(f"      Found rating: {rating}")
                    break
                except NoSuchElementException:
                    continue
            
            # Extract review text - try multiple selectors
            content = ""
            content_selectors = [
                "[data-service-review-text]",
                "[data-testid='review-content']",
                ".review-content",
                "p[data-testid='review-text']",
                "div[data-service-review-text-typography]",
                "div p",
                "span[data-hook='review-body']",
                "p",  # Try any paragraph
                "div[data-service-review-card-paper] p"
            ]
            
            for selector in content_selectors:
                try:
                    content_element = element.find_element(By.CSS_SELECTOR, selector)
                    content = content_element.text.strip()
                    if content:  # Make sure we actually got content
                        break
                except NoSuchElementException:
                    continue
            
            # If still no content, try a more general approach
            if not content:
                try:
                    # Get all text from the element and try to find review content
                    all_text = element.text.strip()
                    # Split by common separators and look for substantial text
                    text_parts = [part.strip() for part in all_text.split('\n') if len(part.strip()) > 20]
                    if text_parts:
                        content = text_parts[-1]  # Usually the last substantial text is the review
                        print(f"      Found content via fallback: {content[:50]}...")
                except Exception:
                    pass
            
            print(f"      Final content length: {len(content)}")
            
            # Extract author name - try multiple selectors
            author = "Anonymous"
            author_selectors = [
                "[data-consumer-name-typography]",
                "[data-testid='consumer-name']",
                ".consumer-name",
                "span[data-testid='name']"
            ]
            
            for selector in author_selectors:
                try:
                    author_element = element.find_element(By.CSS_SELECTOR, selector)
                    author = author_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract date - try multiple selectors
            date = datetime.now().isoformat()
            date_selectors = [
                "[data-service-review-date-time-ago]",
                "[data-testid='review-date']",
                "time",
                ".review-date"
            ]
            
            for selector in date_selectors:
                try:
                    date_element = element.find_element(By.CSS_SELECTOR, selector)
                    date_text = date_element.text.strip()
                    date = self._parse_trustpilot_date(date_text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract review title - try multiple selectors
            title = ""
            title_selectors = [
                "[data-service-review-title]",
                "[data-testid='review-title']",
                "h3",
                ".review-title"
            ]
            
            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract verification status
            is_verified = False
            try:
                element.find_element(By.CSS_SELECTOR, "[data-service-review-verified]")
                is_verified = True
            except NoSuchElementException:
                pass
            
            # Extract location if available
            location = ""
            try:
                location_element = element.find_element(By.CSS_SELECTOR, "[data-consumer-country-typography]")
                location = location_element.text.strip()
            except NoSuchElementException:
                pass
            
            return {
                'platform': 'Trustpilot',
                'external_id': f"trustpilot_{hash(content + author + str(rating))}",
                'source_url': company_url,
                'author': author,
                'content': f"{title}. {content}".strip() if title else content,
                'title': title,
                'date': date,
                'rating': rating,
                'is_verified': is_verified,
                'location': location
            }
            
        except Exception as e:
            print(f"Error extracting individual review: {e}")
            return None
    
    def _parse_trustpilot_date(self, date_text: str) -> str:
        """
        Parse Trustpilot date text to ISO format
        
        Args:
            date_text: Date text from Trustpilot (e.g., "2 days ago", "1 week ago")
            
        Returns:
            ISO formatted date string
        """
        try:
            from dateutil.relativedelta import relativedelta
            
            now = datetime.now()
            date_text = date_text.lower()
            
            if 'hour' in date_text:
                hours = int(re.search(r'(\d+)', date_text).group(1))
                date = now - relativedelta(hours=hours)
            elif 'day' in date_text:
                days = int(re.search(r'(\d+)', date_text).group(1))
                date = now - relativedelta(days=days)
            elif 'week' in date_text:
                weeks = int(re.search(r'(\d+)', date_text).group(1))
                date = now - relativedelta(weeks=weeks)
            elif 'month' in date_text:
                months = int(re.search(r'(\d+)', date_text).group(1))
                date = now - relativedelta(months=months)
            elif 'year' in date_text:
                years = int(re.search(r'(\d+)', date_text).group(1))
                date = now - relativedelta(years=years)
            else:
                date = now
            
            return date.isoformat()
            
        except Exception:
            return datetime.now().isoformat()
    
    def get_uber_trustpilot_reviews(self, max_reviews: int = 100) -> List[Dict]:
        """
        Get Trustpilot reviews specifically for Uber
        
        Args:
            max_reviews: Maximum number of reviews to retrieve
            
        Returns:
            List of Uber reviews from Trustpilot
        """
        # Try direct Uber URLs first
        uber_urls = [
            "https://www.trustpilot.com/review/uber.com",
            "https://www.trustpilot.com/review/www.uber.com",
            "https://uk.trustpilot.com/review/uber.com",
            "https://www.trustpilot.com/review/ubertechnologies.com"
        ]
        
        all_reviews = []
        
        # Try direct URLs first
        for url in uber_urls:
            print(f"   Trying Uber URL: {url}")
            try:
                reviews = self._scrape_company_reviews_direct(url, max_reviews)
                if reviews:
                    all_reviews.extend(reviews)
                    print(f"   ✅ Found {len(reviews)} reviews from {url}")
                    if len(all_reviews) >= max_reviews:
                        break
                else:
                    print(f"   ⚠️ No reviews found at {url}")
            except Exception as e:
                print(f"   ❌ Failed to scrape {url}: {e}")
                continue
        
        # If direct URLs don't work, try search approach
        if not all_reviews:
            print("   Fallback to search approach...")
            uber_variations = ["Uber", "Uber Technologies", "uber.com"]
            
            for uber_name in uber_variations:
                reviews = self.search_company_reviews(uber_name, max_reviews // len(uber_variations))
                all_reviews.extend(reviews)
                
                if len(all_reviews) >= max_reviews:
                    break
        
        # Remove duplicates based on content similarity
        unique_reviews = self._remove_duplicate_reviews(all_reviews)
        
        return unique_reviews[:max_reviews]
    
    def _scrape_company_reviews_direct(self, company_url: str, max_reviews: int) -> List[Dict]:
        """
        Directly scrape reviews from a known company URL with pagination support
        
        Args:
            company_url: Direct Trustpilot URL for the company
            max_reviews: Maximum number of reviews to retrieve
            
        Returns:
            List of review data
        """
        reviews = []
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Start with page 1
            page = 1
            collected_reviews = 0
            
            while collected_reviews < max_reviews and page <= 10:  # Limit to 10 pages
                try:
                    # Build URL with page parameter
                    if '?' in company_url:
                        page_url = f"{company_url}&page={page}"
                    else:
                        page_url = f"{company_url}?page={page}"
                    
                    print(f"   Scraping page {page}: {page_url}")
                    driver.get(page_url)
                    
                    wait = WebDriverWait(driver, 15)
                    
                    # Wait for reviews to load - try multiple selectors
                    review_selectors = [
                        "[data-service-review-card-paper]",
                        "article[data-testid='review']",
                        ".review-card",
                        ".consumer-review",
                        "div[data-service-review-card-paper]"
                    ]
                    
                    reviews_found = False
                    for selector in review_selectors:
                        try:
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                            reviews_found = True
                            break
                        except TimeoutException:
                            continue
                    
                    if not reviews_found:
                        print(f"   No reviews found on page {page}")
                        break
                    
                    # Get review elements
                    review_elements = []
                    for selector in review_selectors:
                        review_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if review_elements:
                            break
                    
                    if not review_elements:
                        print(f"   No review elements found on page {page}")
                        break
                    
                    print(f"   Found {len(review_elements)} review elements on page {page}")
                    
                    # Extract review data from this page
                    page_reviews = []
                    for element in review_elements:
                        if collected_reviews >= max_reviews:
                            break
                        
                        try:
                            review_data = self._extract_review_data(element, company_url)
                            if review_data and review_data.get('content'):
                                page_reviews.append(review_data)
                                collected_reviews += 1
                            elif review_data:
                                print(f"   Skipped review with no content: {review_data}")
                        except Exception as e:
                            print(f"   Error extracting review: {e}")
                            # Print element HTML for debugging
                            try:
                                element_html = element.get_attribute('outerHTML')[:200]
                                print(f"   Element HTML: {element_html}...")
                            except:
                                pass
                            continue
                    
                    reviews.extend(page_reviews)
                    print(f"   Successfully extracted {len(page_reviews)} reviews from page {page}")
                    
                    # If we got fewer reviews than expected, we might have reached the end
                    if len(page_reviews) < 10:  # Typical reviews per page
                        print(f"   Reached end of reviews (got {len(page_reviews)} reviews)")
                        break
                    
                    page += 1
                    time.sleep(2)  # Be respectful to the server
                    
                except Exception as e:
                    print(f"   Error on page {page}: {e}")
                    break
            
            driver.quit()
            print(f"   Total reviews collected: {len(reviews)}")
            
        except Exception as e:
            print(f"   Error in direct scraping: {e}")
        
        return reviews
    
    def _remove_duplicate_reviews(self, reviews: List[Dict]) -> List[Dict]:
        """
        Remove duplicate reviews based on content similarity
        
        Args:
            reviews: List of review dictionaries
            
        Returns:
            List of unique reviews
        """
        unique_reviews = []
        seen_content = set()
        
        for review in reviews:
            content = review.get('content', '').strip().lower()
            # Create a simple hash for similarity check
            content_hash = hash(content[:100])  # Use first 100 characters
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_reviews.append(review)
        
        return unique_reviews