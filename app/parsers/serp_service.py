import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class SerpService:
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"
        
    def search_brand_reputation(self, brand_name: str, location: str = "United States", time_period: str = "qdr:y") -> Dict:
        """
        Search for brand reputation using Google SERP API
        
        Args:
            brand_name: Name of the brand to search for
            location: Location for the search (default: United States)
            time_period: Time period filter (default: qdr:y for past year)
            
        Returns:
            Dictionary containing search results
        """
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Search queries focused on reputation
        reputation_queries = [
            f"{brand_name} reviews",
            f"{brand_name} complaints",
            f"{brand_name} problems",
            f"{brand_name} customer service",
            f"{brand_name} news",
            f"{brand_name} reputation"
        ]
        
        all_results = {}
        
        for query in reputation_queries:
            payload = {
                "q": query,
                "location": location,
                "tbs": time_period
            }
            
            try:
                response = requests.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                
                all_results[query] = response.json()
                
            except requests.exceptions.RequestException as e:
                print(f"Error searching for '{query}': {e}")
                all_results[query] = {"error": str(e)}
                
        return all_results
    
    def extract_key_information(self, search_results: Dict) -> List[Dict]:
        """
        Extract key information from search results
        
        Args:
            search_results: Raw search results from SERP API
            
        Returns:
            List of dictionaries containing key information
        """
        key_info = []
        
        for query, results in search_results.items():
            if "error" in results:
                continue
                
            organic_results = results.get("organic", [])
            
            for result in organic_results:
                info = {
                    "query": query,
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "link": result.get("link", ""),
                    "source": result.get("source", ""),
                    "position": result.get("position", 0)
                }
                key_info.append(info)
                
        return key_info