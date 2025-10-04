#!/usr/bin/env python3
"""
Unified Parser Runner - Single console command to run all parsers and analyze data

This command:
1. Launches all available parsers to collect data
2. Saves parsed data into the database
3. Processes each record individually with OpenAI for analysis
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import func

# Add the parent directory to the Python path to access app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import get_db, init_db
from app.database.models import UserMention, Product, ReputationAnalysis
from app.core.analysis_service import AnalysisService
from app.parsers.reddit_scraper import RedditScraper, get_uber_relevant_subreddits
from app.parsers.trustpilot_scraper import TrustpilotScraper
from app.parsers.review_scraper import ReviewScraper
from app.parsers.serp_service import SerpService


class UnifiedParserRunner:
    def __init__(self):
        self.analysis_service = AnalysisService()
        self.reddit_scraper = RedditScraper()
        self.trustpilot_scraper = TrustpilotScraper()
        self.review_scraper = ReviewScraper()
        self.serp_service = SerpService()
    
    def run_all_parsers(self, product_name: str, max_items_per_parser: int = 50):
        """
        Run all available parsers to collect data for a product
        
        Args:
            product_name: Name of the product to analyze
            max_items_per_parser: Maximum items to collect per parser
        """
        db = next(get_db())
        
        try:
            # Get or create product
            product = db.query(Product).filter(Product.name.ilike(f"%{product_name}%")).first()
            if not product:
                product = Product(name=product_name)
                db.add(product)
                db.commit()
                db.refresh(product)

            print(f"🚀 Running all parsers for product: {product_name}")
            print("=" * 60)

            all_collected_data = []

            # 1. Reddit Parser (temporarily disabled for Trustpilot debugging)
            print("📱 Running Reddit parser... (skipped for debugging)")
            reddit_mentions = []
            
            # 2. Trustpilot Parser
            print("⭐ Running Trustpilot parser...")
            try:
                if product_name.lower() in ['uber', 'uber technologies']:
                    trustpilot_reviews = self.trustpilot_scraper.get_uber_trustpilot_reviews(
                        max_reviews=max_items_per_parser
                    )
                else:
                    trustpilot_reviews = self.trustpilot_scraper.search_company_reviews(
                        product_name, max_reviews=max_items_per_parser
                    )
                
                all_collected_data.extend(trustpilot_reviews)
                print(f"   ✅ Collected {len(trustpilot_reviews)} Trustpilot reviews")
                
            except Exception as e:
                print(f"   ❌ Trustpilot parser failed: {e}")
                trustpilot_reviews = []
            
            # 3. App Store Parser
            print("🍎 Running App Store parser...")
            try:
                if product_name.lower() in ['uber', 'uber technologies']:
                    app_store_url = "https://apps.apple.com/us/app/uber-request-a-ride/id368677368"
                    app_store_reviews = self.review_scraper.scrape_app_store_reviews(
                        app_store_url, max_reviews=max_items_per_parser
                    )
                    
                    if app_store_reviews:
                        all_collected_data.extend(app_store_reviews)
                        print(f"   ✅ Collected {len(app_store_reviews)} App Store reviews")
                    else:
                        print("   ⚠️  No App Store reviews collected")
                else:
                    print("   ⚠️  App Store parser requires specific URL (skipped)")
                
            except Exception as e:
                print(f"   ❌ App Store parser failed: {e}")
            
            # 4. Google Play Parser
            print("🤖 Running Google Play parser...")
            try:
                if product_name.lower() in ['uber', 'uber technologies']:
                    google_play_url = "https://play.google.com/store/apps/details?id=com.ubercab"
                    google_play_reviews = self.review_scraper.scrape_google_play_reviews(
                        google_play_url, max_reviews=max_items_per_parser
                    )
                    
                    if google_play_reviews:
                        all_collected_data.extend(google_play_reviews)
                        print(f"   ✅ Collected {len(google_play_reviews)} Google Play reviews")
                    else:
                        print("   ⚠️  No Google Play reviews collected")
                else:
                    print("   ⚠️  Google Play parser requires specific URL (skipped)")
                
            except Exception as e:
                print(f"   ❌ Google Play parser failed: {e}")
            
            # 5. SERP Parser
            print("🔍 Running SERP parser...")
            try:
                # Get SERP search results
                serp_raw_results = self.serp_service.search_brand_reputation(product_name)
                
                # Extract key information and convert to mention format
                serp_info = self.serp_service.extract_key_information(serp_raw_results)
                
                serp_mentions = []
                for serp_item in serp_info:
                    serp_mentions.append({
                        "id": f"serp_{serp_item.get('query', 'unknown')}_{serp_item.get('position', 'unknown')}",
                        "platform": "Google Search",
                        "content": serp_item.get("snippet", ""),
                        "title": serp_item.get("title", ""),
                        "author": serp_item.get("source", "Unknown"),
                        "source_url": serp_item.get("link", ""),
                        "date": datetime.now().isoformat()
                    })
                
                all_collected_data.extend(serp_mentions)
                print(f"   ✅ Collected {len(serp_mentions)} SERP results")
                
            except Exception as e:
                print(f"   ❌ SERP parser failed: {e}")
            
            print("\n📊 Parser Summary:")
            print(f"   Total data points collected: {len(all_collected_data)}")
            
            if not all_collected_data:
                print("❌ No data was collected by any parser")
                return
            
            # Save all collected data to database
            print("\n💾 Saving collected data to database...")
            self._save_collected_data(db, all_collected_data, product.id)
            
            # Process each record individually with OpenAI
            print("\n🤖 Processing records individually with OpenAI...")
            self._process_records_with_openai(db, product.id)
            
            print("\n✅ All parsers completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during parser execution: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _save_collected_data(self, db, collected_data: list, product_id: int):
        """Save collected data to database"""
        saved_count = 0
        
        for item in collected_data:
            try:
                # Check if this mention already exists
                existing = db.query(UserMention).filter(
                    UserMention.external_id == item.get('id'),
                    UserMention.platform == item.get('platform', 'Unknown')
                ).first()
                
                if existing:
                    continue  # Skip duplicates
                
                # Create new mention
                mention = UserMention(
                    product_id=product_id,
                    platform=item.get('platform', 'Unknown'),
                    external_id=item.get('id', ''),
                    author_name=item.get('author', 'Unknown'),
                    content=item.get('content', ''),
                    title=item.get('title', ''),
                    rating=item.get('rating'),
                    source_url=item.get('source_url', ''),
                    original_date=datetime.now(),
                    processed_date=datetime.now(),
                    is_processed=False,  # Will be processed individually
                    sentiment='neutral',  # Default, will be updated by OpenAI
                    confidence_score=0.0
                )
                
                db.add(mention)
                saved_count += 1
                
            except Exception as e:
                print(f"   ⚠️  Error saving item {item.get('id', 'unknown')}: {e}")
        
        db.commit()
        print(f"   💾 Saved {saved_count} new data points to database")
    
    def _process_records_with_openai(self, db, product_id: int):
        """Process each unprocessed record individually with OpenAI"""
        # Get unprocessed mentions
        unprocessed_mentions = db.query(UserMention).filter(
            UserMention.product_id == product_id,
            UserMention.is_processed == False,
            UserMention.content.isnot(None),
            UserMention.content != ''
        ).all()
        
        print(f"   🤖 Found {len(unprocessed_mentions)} records to process")
        
        processed_count = 0
        batch_size = 10
        
        for i, mention in enumerate(unprocessed_mentions):
            try:
                print(f"   Processing {i+1}/{len(unprocessed_mentions)}: {mention.platform} - ID {mention.id}")
                
                # Analyze sentiment with OpenAI
                sentiment_result = self.analysis_service.analyze_sentiment(mention.content)
                
                if sentiment_result:
                    mention.sentiment = sentiment_result.get('sentiment_label', 'neutral')
                    mention.confidence_score = abs(sentiment_result.get('polarity', 0))
                    mention.is_processed = True
                    processed_count += 1
                    
                    print(f"      ✅ Sentiment: {mention.sentiment} (confidence: {mention.confidence_score:.3f})")
                else:
                    print(f"      ⚠️  Failed to analyze sentiment")
                
                # Commit in batches
                if (i + 1) % batch_size == 0:
                    db.commit()
                    print(f"   💾 Batch saved ({i + 1}/{len(unprocessed_mentions)})")
                
            except Exception as e:
                print(f"      ❌ Error processing mention {mention.id}: {e}")
        
        # Final commit
        db.commit()
        print(f"   ✅ Successfully processed {processed_count} records with OpenAI")
        
        # Show final sentiment distribution
        self._show_sentiment_distribution(db, product_id)
    
    def _show_sentiment_distribution(self, db, product_id: int):
        """Show sentiment distribution for the product"""
        sentiment_dist = db.query(
            UserMention.sentiment, 
            func.count(UserMention.id)
        ).filter(
            UserMention.product_id == product_id
        ).group_by(UserMention.sentiment).all()
        
        print("\n📈 Final sentiment distribution:")
        total = sum(count for _, count in sentiment_dist)
        
        for sentiment, count in sentiment_dist:
            percentage = (count / total) * 100 if total > 0 else 0
            emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}.get(sentiment, "❓")
            print(f"   {emoji} {sentiment}: {count} ({percentage:.1f}%)")


def main():
    """Main entry point"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Unified Parser Runner - Collect and analyze data from all sources')
    parser.add_argument('--product', '-p', required=True, help='Product name to analyze')
    parser.add_argument('--max-items', '-m', type=int, default=50, 
                       help='Maximum items to collect per parser (default: 50)')
    
    args = parser.parse_args()
    
    # Check for required environment variables
    required_vars = ['OPENAI_API_KEY', 'SERPER_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease check your .env file and ensure all API keys are set.")
        sys.exit(1)
    
    # Initialize database
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialized")
    print()
    
    # Run all parsers
    runner = UnifiedParserRunner()
    runner.run_all_parsers(args.product, args.max_items)


if __name__ == "__main__":
    main()