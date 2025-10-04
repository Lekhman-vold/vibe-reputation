import requests
import json
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class ReviewScraper:
    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        
    def scrape_app_store_reviews(self, app_url: str, max_reviews: int = 50) -> List[Dict]:
        """
        Scrape reviews from App Store
        
        Args:
            app_url: URL of the app on App Store
            max_reviews: Maximum number of reviews to scrape
            
        Returns:
            List of dictionaries containing review data
        """
        reviews = []
        
        try:
            # Extract app ID from URL
            app_id_match = re.search(r'/id(\d+)', app_url)
            if not app_id_match:
                return reviews
                
            app_id = app_id_match.group(1)
            
            # Use iTunes API to get reviews
            review_url = f"https://itunes.apple.com/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json"
            
            response = requests.get(review_url)
            response.raise_for_status()
            
            data = response.json()
            entries = data.get('feed', {}).get('entry', [])
            
            for entry in entries[1:]:  # Skip first entry (app info)
                if len(reviews) >= max_reviews:
                    break
                    
                review = {
                    "platform": "app_store",
                    "title": entry.get('title', {}).get('label', ''),
                    "content": entry.get('content', {}).get('label', ''),
                    "rating": int(entry.get('im:rating', {}).get('label', 0)),
                    "author": entry.get('author', {}).get('name', {}).get('label', ''),
                    "date": entry.get('updated', {}).get('label', ''),
                    "version": entry.get('im:version', {}).get('label', '')
                }
                reviews.append(review)
                
        except Exception as e:
            print(f"Error scraping App Store reviews: {e}")
            
        return reviews
    
    def scrape_google_play_reviews(self, app_url: str, max_reviews: int = 50) -> List[Dict]:
        """
        Scrape reviews from Google Play Store
        
        Args:
            app_url: URL of the app on Google Play Store
            max_reviews: Maximum number of reviews to scrape
            
        Returns:
            List of dictionaries containing review data
        """
        reviews = []
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(app_url)
            
            # Wait for reviews to load
            wait = WebDriverWait(driver, 10)
            
            # Scroll to reviews section
            try:
                reviews_section = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-g-id='reviews']"))
                )
                driver.execute_script("arguments[0].scrollIntoView();", reviews_section)
                time.sleep(2)
            except:
                pass
            
            # Find review elements
            review_elements = driver.find_elements(By.CSS_SELECTOR, "[data-review-id]")
            
            for element in review_elements[:max_reviews]:
                try:
                    # Extract review data
                    author_elem = element.find_element(By.CSS_SELECTOR, "[data-review-id] div:first-child span")
                    content_elem = element.find_element(By.CSS_SELECTOR, "[data-review-id] span[jscontroller] span")
                    rating_elem = element.find_element(By.CSS_SELECTOR, "[data-review-id] div[role='img']")
                    date_elem = element.find_element(By.CSS_SELECTOR, "[data-review-id] span.bp9Aid")
                    
                    # Parse rating from aria-label
                    rating_text = rating_elem.get_attribute("aria-label")
                    rating_match = re.search(r'(\d+)', rating_text)
                    rating = int(rating_match.group(1)) if rating_match else 0
                    
                    review = {
                        "platform": "google_play",
                        "author": author_elem.text if author_elem else "",
                        "content": content_elem.text if content_elem else "",
                        "rating": rating,
                        "date": date_elem.text if date_elem else "",
                        "helpful_count": 0  # Could be extracted if needed
                    }
                    
                    reviews.append(review)
                    
                except Exception as e:
                    print(f"Error extracting individual review: {e}")
                    continue
                    
            driver.quit()
            
        except Exception as e:
            print(f"Error scraping Google Play reviews: {e}")
            
        return reviews
    
    def scrape_all_reviews(self, app_store_url: str = None, google_play_url: str = None, max_reviews: int = 50) -> Dict:
        """
        Scrape reviews from both App Store and Google Play
        
        Args:
            app_store_url: URL of the app on App Store
            google_play_url: URL of the app on Google Play Store
            max_reviews: Maximum number of reviews to scrape from each platform
            
        Returns:
            Dictionary containing reviews from both platforms
        """
        all_reviews = {
            "app_store": [],
            "google_play": []
        }
        
        if app_store_url:
            all_reviews["app_store"] = self.scrape_app_store_reviews(app_store_url, max_reviews)
            
        if google_play_url:
            all_reviews["google_play"] = self.scrape_google_play_reviews(google_play_url, max_reviews)
            
        return all_reviews