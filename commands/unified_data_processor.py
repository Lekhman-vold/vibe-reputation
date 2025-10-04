#!/usr/bin/env python3
"""
Unified Data Processor - Single console command for data collection and sentiment classification

This script replaces multiple redundant scripts:
- update_sentiment.py
- update_all_sentiment.py
- update_misclassified_sentiment.py  
- update_sentiment_openai.py
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
from app.core.reputation_service import ReputationService


class UnifiedDataProcessor:
    def __init__(self):
        self.analysis_service = AnalysisService()
        self.reputation_service = ReputationService()
    
    def collect_and_analyze_data(self, product_name: str, app_store_url: str = None, google_play_url: str = None):
        """
        Complete data collection and analysis workflow
        """
        print(f"🚀 Starting unified data collection and analysis for '{product_name}'")
        print("=" * 60)
        
        try:
            # Run full reputation analysis which includes data collection
            result = self.reputation_service.analyze_product_reputation(
                product_name=product_name,
                app_store_url=app_store_url,
                google_play_url=google_play_url
            )
            
            if result.get("success"):
                print("✅ Data collection and analysis completed successfully!")
                print(f"📊 Analysis ID: {result['analysis_id']}")
                print(f"📈 Overall Score: {result['reputation_metrics']['overall_score']:.1f}/100")
                print(f"💭 Sentiment Score: {result['reputation_metrics']['sentiment_score']:.2f}")
                
                # Show data sources summary
                data_sources = result.get('data_sources', {})
                print(f"📚 Total Sources: {data_sources.get('total_sources', 0)}")
                platform_coverage = data_sources.get('platform_coverage', [])
                print(f"🌐 Platforms: {', '.join(platform_coverage)}")
                
                return result
            else:
                print(f"❌ Analysis failed: {result.get('error')}")
                return None
                
        except Exception as e:
            print(f"❌ Error during data collection and analysis: {e}")
            return None
    
    def update_sentiment_classifications(self, filter_type: str = "all", use_openai: bool = True, max_items: int = None):
        """
        Update sentiment classifications for existing mentions
        
        Args:
            filter_type: "all", "neutral", "positive", "misclassified"
            use_openai: Whether to use OpenAI for analysis (recommended)
            max_items: Maximum number of items to process (None for all)
        """
        db = next(get_db())
        
        try:
            print(f"🔄 Updating sentiment classifications (filter: {filter_type})")
            print("=" * 50)
            
            # Build query based on filter type
            query = db.query(UserMention)
            
            if filter_type == "neutral":
                query = query.filter(UserMention.sentiment == "neutral")
            elif filter_type == "positive":
                query = query.filter(UserMention.sentiment == "positive")
            elif filter_type == "misclassified":
                # Focus on potentially misclassified positive mentions
                query = query.filter(UserMention.sentiment == "positive")
                
            mentions = query.all()
            
            if max_items:
                mentions = mentions[:max_items]
            
            print(f"📝 Found {len(mentions)} mentions to process")
            
            if not mentions:
                print("ℹ️  No mentions found matching criteria")
                return
            
            updated = 0
            batch_size = 50
            
            for i, mention in enumerate(mentions):
                if mention.content and len(mention.content.strip()) > 5:
                    old_sentiment = mention.sentiment
                    
                    # Use OpenAI-powered analysis for better accuracy
                    if use_openai:
                        result = self.analysis_service.analyze_sentiment(mention.content)
                        new_sentiment = result.get('sentiment_label', 'neutral')
                        confidence = abs(result.get('polarity', 0))
                        method = result.get('method', 'openai')
                    else:
                        # Fallback to basic analysis
                        result = self.analysis_service.analyze_sentiment(mention.content)
                        new_sentiment = result.get('sentiment_label', 'neutral')
                        confidence = abs(result.get('polarity', 0))
                        method = result.get('method', 'basic')
                    
                    # Update if sentiment changed
                    if old_sentiment != new_sentiment:
                        mention.sentiment = new_sentiment
                        mention.confidence_score = confidence
                        updated += 1
                        
                        if updated <= 10:  # Show first 10 updates
                            print(f"✅ Updated mention {mention.id}: {old_sentiment} → {new_sentiment}")
                            print(f"   Content: {mention.content[:80]}...")
                            print(f"   Method: {method}, Confidence: {confidence:.3f}")
                
                # Commit in batches for performance
                if (i + 1) % batch_size == 0:
                    db.commit()
                    print(f"🔄 Processed {i + 1}/{len(mentions)} mentions...")
            
            # Final commit
            db.commit()
            
            print(f"\n🎉 Sentiment update completed!")
            print(f"📊 Total processed: {len(mentions)}")
            print(f"🔄 Updated: {updated}")
            
            # Show updated sentiment distribution
            self._show_sentiment_distribution(db)
            
        except Exception as e:
            print(f"❌ Error updating sentiment: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _show_sentiment_distribution(self, db):
        """Show current sentiment distribution"""
        sentiment_dist = db.query(
            UserMention.sentiment, 
            func.count(UserMention.id)
        ).group_by(UserMention.sentiment).all()
        
        print("\n📈 Current sentiment distribution:")
        total = sum(count for _, count in sentiment_dist)
        
        for sentiment, count in sentiment_dist:
            percentage = (count / total) * 100 if total > 0 else 0
            emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}.get(sentiment, "❓")
            print(f"   {emoji} {sentiment}: {count} ({percentage:.1f}%)")
    
    def show_system_status(self):
        """Show system status and data overview"""
        db = next(get_db())
        
        try:
            print("🔍 SYSTEM STATUS")
            print("=" * 40)
            
            # Product count
            product_count = db.query(Product).count()
            print(f"📦 Products: {product_count}")
            
            # Analysis count
            analysis_count = db.query(ReputationAnalysis).count()
            print(f"📊 Analyses: {analysis_count}")
            
            # Mention count and distribution
            mention_count = db.query(UserMention).count()
            print(f"💬 Total Mentions: {mention_count}")
            
            if mention_count > 0:
                self._show_sentiment_distribution(db)
            
            # Latest analysis
            latest_analysis = db.query(ReputationAnalysis).order_by(
                ReputationAnalysis.analysis_date.desc()
            ).first()
            
            if latest_analysis:
                print(f"\n📅 Latest Analysis: {latest_analysis.analysis_date}")
                print(f"📈 Score: {latest_analysis.overall_score:.1f}/100")
            
        finally:
            db.close()


def main():
    """Main entry point with argument parsing"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Unified Data Processor for Brand Reputation Analysis')
    parser.add_argument('--mode', '-m', 
                       choices=['collect', 'sentiment', 'status'], 
                       default='collect',
                       help='Operation mode: collect data, update sentiment, or show status')
    
    # Data collection arguments
    parser.add_argument('--product', '-p', help='Uber for data collection')
    parser.add_argument('--app-store', help='App Store URL')
    parser.add_argument('--google-play', help='Google Play URL')
    
    # Sentiment update arguments
    parser.add_argument('--filter', '-f',
                       choices=['all', 'neutral', 'positive', 'misclassified'],
                       default='all',
                       help='Filter type for sentiment updates')
    parser.add_argument('--max-items', type=int, help='Maximum items to process')
    parser.add_argument('--no-openai', action='store_true', help='Disable OpenAI analysis')
    
    args = parser.parse_args()
    
    # Check for required environment variables
    required_vars = ['OPENAI_API_KEY', 'SERPER_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars and args.mode in ['collect', 'sentiment']:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease check your .env file and ensure all API keys are set.")
        sys.exit(1)
    
    # Initialize database
    print("🔧 Initializing database...")
    init_db()
    
    processor = UnifiedDataProcessor()
    
    if args.mode == 'collect':
        if not args.product:
            print("❌ Product name is required for data collection mode")
            print("Usage: python unified_data_processor.py --mode collect --product 'Product Name'")
            sys.exit(1)
        
        processor.collect_and_analyze_data(
            product_name=args.product,
            app_store_url=args.app_store,
            google_play_url=args.google_play
        )
    
    elif args.mode == 'sentiment':
        processor.update_sentiment_classifications(
            filter_type=args.filter,
            use_openai=not args.no_openai,
            max_items=args.max_items
        )
    
    elif args.mode == 'status':
        processor.show_system_status()


if __name__ == "__main__":
    main()