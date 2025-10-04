import requests
import json
import re
from typing import Dict, List, Optional
from datetime import datetime
import time
from urllib.parse import quote


class RedditScraper:
    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.search_url = "https://www.reddit.com/search.json"
        self.headers = {
            'User-Agent': 'Brand Reputation Analysis Bot 1.0'
        }
    
    def search_mentions(self, brand_name: str, max_posts: int = 100, time_filter: str = "month") -> List[Dict]:
        """
        Search for brand mentions on Reddit
        
        Args:
            brand_name: Name of the brand to search for
            max_posts: Maximum number of posts to retrieve
            time_filter: Time filter (hour, day, week, month, year, all)
            
        Returns:
            List of dictionaries containing post and comment data
        """
        mentions = []
        
        # Search queries for the brand
        search_queries = [
            brand_name,
            f"{brand_name} review",
            f"{brand_name} experience",
            f"{brand_name} problem",
            f"{brand_name} complaint",
            f"{brand_name} good",
            f"{brand_name} bad"
        ]
        
        for query in search_queries:
            try:
                posts = self._search_posts(query, max_posts // len(search_queries), time_filter)
                mentions.extend(posts)
                
                # Add delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error searching Reddit for '{query}': {e}")
                continue
        
        # Remove duplicates based on post ID
        seen_ids = set()
        unique_mentions = []
        for mention in mentions:
            if mention.get('external_id') not in seen_ids:
                seen_ids.add(mention.get('external_id'))
                unique_mentions.append(mention)
        
        return unique_mentions[:max_posts]
    
    def _search_posts(self, query: str, limit: int, time_filter: str) -> List[Dict]:
        """
        Search for posts using Reddit's JSON API
        
        Args:
            query: Search query
            limit: Number of posts to retrieve
            time_filter: Time filter for search
            
        Returns:
            List of post data
        """
        posts = []
        
        params = {
            'q': query,
            'sort': 'relevance',
            't': time_filter,
            'limit': min(limit, 25),  # Reddit API limit
            'type': 'link'
        }
        
        try:
            response = requests.get(self.search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and 'children' in data['data']:
                for post_data in data['data']['children']:
                    post = post_data.get('data', {})
                    
                    # Convert Reddit post to mention format
                    mention = self._convert_post_to_mention(post)
                    if mention:
                        posts.append(mention)
                        
                        # Also get comments for this post if it has few comments
                        if post.get('num_comments', 0) <= 20:
                            comments = self._get_post_comments(post.get('subreddit'), post.get('id'))
                            posts.extend(comments)
            
        except Exception as e:
            print(f"Error fetching Reddit posts for query '{query}': {e}")
        
        return posts
    
    def _convert_post_to_mention(self, post: Dict) -> Optional[Dict]:
        """
        Convert Reddit post data to mention format
        
        Args:
            post: Reddit post data
            
        Returns:
            Dictionary in mention format or None if invalid
        """
        if not post:
            return None
        
        # Combine title and selftext for content
        title = post.get('title', '')
        selftext = post.get('selftext', '')
        content = f"{title}. {selftext}".strip() if selftext else title
        
        # Skip if content is too short
        if len(content.strip()) < 10:
            return None
        
        # Convert Reddit timestamp to datetime
        created_utc = post.get('created_utc', 0)
        date = datetime.fromtimestamp(created_utc) if created_utc else datetime.now()
        
        return {
            'platform': 'Reddit',
            'external_id': f"reddit_post_{post.get('id', '')}",
            'source_url': f"https://www.reddit.com{post.get('permalink', '')}",
            'author': post.get('author', 'Anonymous'),
            'content': content,
            'title': title,
            'date': date.isoformat(),
            'rating': None,  # Reddit doesn't have ratings
            'upvotes': post.get('ups', 0),
            'downvotes': post.get('downs', 0),
            'score': post.get('score', 0),
            'subreddit': post.get('subreddit', ''),
            'num_comments': post.get('num_comments', 0)
        }
    
    def _get_post_comments(self, subreddit: str, post_id: str, max_comments: int = 10) -> List[Dict]:
        """
        Get comments for a specific post
        
        Args:
            subreddit: Subreddit name
            post_id: Post ID
            max_comments: Maximum number of comments to retrieve
            
        Returns:
            List of comment data in mention format
        """
        comments = []
        
        if not subreddit or not post_id:
            return comments
        
        try:
            # Get post comments
            comments_url = f"{self.base_url}/r/{subreddit}/comments/{post_id}.json"
            response = requests.get(comments_url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Reddit returns [post_data, comments_data]
            if len(data) >= 2 and 'data' in data[1] and 'children' in data[1]['data']:
                comment_children = data[1]['data']['children']
                
                for comment_data in comment_children[:max_comments]:
                    comment = comment_data.get('data', {})
                    
                    # Skip deleted/removed comments
                    if comment.get('body') in ['[deleted]', '[removed]', '']:
                        continue
                    
                    mention = self._convert_comment_to_mention(comment, subreddit)
                    if mention:
                        comments.append(mention)
            
        except Exception as e:
            print(f"Error fetching comments for post {post_id}: {e}")
        
        return comments
    
    def _convert_comment_to_mention(self, comment: Dict, subreddit: str) -> Optional[Dict]:
        """
        Convert Reddit comment data to mention format
        
        Args:
            comment: Reddit comment data
            subreddit: Subreddit name
            
        Returns:
            Dictionary in mention format or None if invalid
        """
        if not comment or not comment.get('body'):
            return None
        
        content = comment.get('body', '').strip()
        
        # Skip if content is too short or is a bot comment
        if len(content) < 10 or comment.get('author', '').lower().endswith('bot'):
            return None
        
        # Convert Reddit timestamp to datetime
        created_utc = comment.get('created_utc', 0)
        date = datetime.fromtimestamp(created_utc) if created_utc else datetime.now()
        
        return {
            'platform': 'Reddit',
            'external_id': f"reddit_comment_{comment.get('id', '')}",
            'source_url': f"https://www.reddit.com/r/{subreddit}/comments/{comment.get('link_id', '').replace('t3_', '')}/comment/{comment.get('id', '')}",
            'author': comment.get('author', 'Anonymous'),
            'content': content,
            'title': None,
            'date': date.isoformat(),
            'rating': None,
            'upvotes': comment.get('ups', 0),
            'score': comment.get('score', 0),
            'subreddit': subreddit,
            'is_comment': True
        }
    
    def search_specific_subreddits(self, brand_name: str, subreddits: List[str], max_posts_per_sub: int = 20) -> List[Dict]:
        """
        Search for brand mentions in specific subreddits
        
        Args:
            brand_name: Name of the brand to search for
            subreddits: List of subreddit names to search in
            max_posts_per_sub: Maximum posts per subreddit
            
        Returns:
            List of mentions from specified subreddits
        """
        all_mentions = []
        
        for subreddit in subreddits:
            try:
                # Search within specific subreddit
                subreddit_url = f"{self.base_url}/r/{subreddit}/search.json"
                params = {
                    'q': brand_name,
                    'restrict_sr': 'on',  # Restrict to this subreddit
                    'sort': 'relevance',
                    't': 'month',
                    'limit': max_posts_per_sub
                }
                
                response = requests.get(subreddit_url, headers=self.headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if 'data' in data and 'children' in data['data']:
                    for post_data in data['data']['children']:
                        post = post_data.get('data', {})
                        mention = self._convert_post_to_mention(post)
                        if mention:
                            all_mentions.append(mention)
                
                # Add delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error searching subreddit r/{subreddit}: {e}")
                continue
        
        return all_mentions


def get_uber_relevant_subreddits() -> List[str]:
    """
    Get list of subreddits relevant for Uber mentions
    
    Returns:
        List of subreddit names
    """
    return [
        'uber',
        'uberdrivers',
        'rideshare',
        'lyft',  # For comparisons
        'personalfinance',
        'mildlyinfuriating',
        'tipofmytongue',
        'askanamerican',
        'travel',
        'askreddit',
        'transportation',
        'city-specific subreddits would go here'
    ]