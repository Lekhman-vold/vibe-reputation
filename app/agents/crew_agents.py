import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, List, Any
from ..parsers.serp_service import SerpService
from ..parsers.review_scraper import ReviewScraper
from ..core.analysis_service import AnalysisService
from ..parsers.reddit_scraper import RedditScraper, get_uber_relevant_subreddits
from ..parsers.trustpilot_scraper import TrustpilotScraper

def get_llm():
    return LLM(
        model="o1-mini",
        temperature=0.3
    )

class SerpSearchTool(BaseTool):
    name: str = "SERP Search Tool"
    description: str = "Search Google for brand reputation information using SERP API"
    
    def _run(self, brand_name: str) -> str:
        serp_service = SerpService()
        results = serp_service.search_brand_reputation(brand_name)
        key_info = serp_service.extract_key_information(results)
        return str(key_info)

class ReviewScrapingTool(BaseTool):
    name: str = "Review Scraping Tool"
    description: str = "Scrape reviews from App Store and Google Play Store"
    
    def _run(self, app_store_url: str = None, google_play_url: str = None) -> str:
        scraper = ReviewScraper()
        reviews = scraper.scrape_all_reviews(app_store_url, google_play_url, max_reviews=30)
        return str(reviews)

class RedditScrapingTool(BaseTool):
    name: str = "Reddit Scraping Tool"
    description: str = "Scrape mentions and discussions from Reddit"
    
    def _run(self, brand_name: str) -> str:
        scraper = RedditScraper()
        
        # Get general Reddit mentions
        mentions = scraper.search_mentions(brand_name, max_posts=50, time_filter="month")
        
        # Also search specific relevant subreddits for Uber
        if brand_name.lower() in ['uber', 'uber technologies']:
            relevant_subreddits = get_uber_relevant_subreddits()
            subreddit_mentions = scraper.search_specific_subreddits(
                brand_name, relevant_subreddits, max_posts_per_sub=10
            )
            mentions.extend(subreddit_mentions)
        
        return str(mentions)

class TrustpilotScrapingTool(BaseTool):
    name: str = "Trustpilot Scraping Tool"
    description: str = "Scrape reviews from Trustpilot"
    
    def _run(self, brand_name: str) -> str:
        scraper = TrustpilotScraper()
        
        # For Uber specifically, use optimized method
        if brand_name.lower() in ['uber', 'uber technologies']:
            reviews = scraper.get_uber_trustpilot_reviews(max_reviews=50)
        else:
            reviews = scraper.search_company_reviews(brand_name, max_reviews=50)
        
        return str(reviews)

class SentimentAnalysisTool(BaseTool):
    name: str = "Sentiment Analysis Tool"
    description: str = "Analyze sentiment and extract topics from text data"
    
    def _run(self, reviews_data: str, serp_data: str, reddit_data: str = "", trustpilot_data: str = "") -> str:
        analysis_service = AnalysisService()
        
        # Parse the string data back to objects (simplified for this example)
        try:
            reviews = eval(reviews_data) if reviews_data else []
            serp = eval(serp_data) if serp_data else []
            reddit = eval(reddit_data) if reddit_data else []
            trustpilot = eval(trustpilot_data) if trustpilot_data else []
        except:
            reviews = []
            serp = []
            reddit = []
            trustpilot = []
        
        # Combine all review content
        all_reviews = []
        if isinstance(reviews, dict):
            all_reviews.extend(reviews.get('app_store', []))
            all_reviews.extend(reviews.get('google_play', []))
        
        # Add Reddit mentions
        if isinstance(reddit, list):
            all_reviews.extend(reddit)
        
        # Add Trustpilot reviews
        if isinstance(trustpilot, list):
            all_reviews.extend(trustpilot)
        
        # Analyze sentiment
        sentiment_analysis = analysis_service.analyze_reviews_sentiment(all_reviews)
        
        # Extract topics
        review_texts = [r.get('content', '') for r in all_reviews if r.get('content')]
        topics = analysis_service.extract_topics_and_themes(review_texts)
        
        # Identify issues
        issues = analysis_service.identify_key_issues(all_reviews, serp)
        
        return str({
            "sentiment_analysis": sentiment_analysis,
            "topics": topics,
            "issues": issues
        })

class ReputationAnalyst(Agent):
    def __init__(self):
        super().__init__(
            role='Brand Reputation Analyst',
            goal='Analyze brand reputation across multiple digital channels',
            backstory="""You are an experienced brand reputation analyst with expertise in 
            digital sentiment analysis, social listening, and reputation management. You excel at 
            identifying reputation risks and opportunities from various online sources.""",
            verbose=True,
            allow_delegation=False,
            llm=get_llm(),
            tools=[SerpSearchTool(), ReviewScrapingTool(), RedditScrapingTool(), TrustpilotScrapingTool(), SentimentAnalysisTool()]
        )

class DataCollector(Agent):
    def __init__(self):
        super().__init__(
            role='Data Collection Specialist',
            goal='Gather comprehensive data about brand mentions and reviews',
            backstory="""You are a data collection expert who specializes in gathering 
            information from various online sources including search engines, app stores, 
            and social platforms. You ensure data quality and completeness.""",
            verbose=True,
            allow_delegation=False,
            llm=get_llm(),
            tools=[SerpSearchTool(), ReviewScrapingTool(), RedditScrapingTool(), TrustpilotScrapingTool()]
        )

class InsightGenerator(Agent):
    def __init__(self):
        super().__init__(
            role='Business Insight Generator',
            goal='Generate actionable business insights from reputation data',
            backstory="""You are a strategic business analyst who transforms raw reputation 
            data into actionable insights. You excel at prioritizing issues and recommending 
            specific actions for product, support, and PR teams.""",
            verbose=True,
            allow_delegation=False,
            llm=get_llm(),
            tools=[SentimentAnalysisTool()]
        )

class ReputationCrew:
    def __init__(self):
        self.data_collector = DataCollector()
        self.reputation_analyst = ReputationAnalyst()
        self.insight_generator = InsightGenerator()
        
    def create_data_collection_task(self, brand_name: str, app_store_url: str = None, google_play_url: str = None) -> Task:
        return Task(
            description=f"""Collect comprehensive reputation data for {brand_name}:
            1. Search for brand mentions, reviews, and reputation-related content using SERP
            2. Scrape reviews from app stores if URLs provided: {app_store_url}, {google_play_url}
            3. Collect mentions from Reddit across relevant subreddits
            4. Gather reviews from Trustpilot
            5. Ensure data quality and completeness across all platforms
            6. Return structured data for analysis""",
            agent=self.data_collector,
            expected_output="Structured data containing SERP results, app store reviews, Reddit mentions, and Trustpilot reviews"
        )
    
    def create_analysis_task(self) -> Task:
        return Task(
            description="""Analyze the collected reputation data:
            1. Perform sentiment analysis on all collected text data
            2. Extract key topics and themes from reviews and mentions
            3. Identify recurring issues and complaints
            4. Calculate sentiment scores and trends
            5. Prepare data for insight generation""",
            agent=self.reputation_analyst,
            expected_output="Comprehensive analysis including sentiment scores, topics, and identified issues"
        )
    
    def create_insight_generation_task(self) -> Task:
        return Task(
            description="""Generate actionable business insights:
            1. Calculate an overall reputation score (0-100)
            2. Prioritize issues by impact and urgency
            3. Categorize issues by responsible team (Product, Support, PR)
            4. Provide specific recommendations for each issue
            5. Highlight positive aspects that should be leveraged
            6. Create executive summary with key findings""",
            agent=self.insight_generator,
            expected_output="Business report with reputation score, prioritized issues, and actionable recommendations"
        )
    
    def analyze_brand_reputation(self, brand_name: str, app_store_url: str = None, google_play_url: str = None, reddit_mentions: List[Dict] = None, trustpilot_reviews: List[Dict] = None) -> Dict:
        """
        Run the complete reputation analysis workflow
        
        Args:
            brand_name: Name of the brand to analyze
            app_store_url: Optional App Store URL
            google_play_url: Optional Google Play URL
            
        Returns:
            Dictionary containing the complete analysis results
        """
        # Create tasks
        data_task = self.create_data_collection_task(brand_name, app_store_url, google_play_url)
        analysis_task = self.create_analysis_task()
        insight_task = self.create_insight_generation_task()
        
        # Create crew
        crew = Crew(
            agents=[self.data_collector, self.reputation_analyst, self.insight_generator],
            tasks=[data_task, analysis_task, insight_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Execute the workflow
        try:
            result = crew.kickoff()
            return {
                "success": True,
                "brand_name": brand_name,
                "analysis_result": result,
                "timestamp": "2024-01-01T00:00:00Z"  # This would be current timestamp
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "brand_name": brand_name
            }