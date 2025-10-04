from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
import uuid

from ..database.models import UserMention, Product
from .analysis_service import AnalysisService


class MentionService:
    def __init__(self):
        self.analysis_service = AnalysisService()
    
    def parse_and_store_mentions(self, db: Session, raw_reviews: List[Dict], product_id: int, analysis_id: Optional[int] = None) -> List[UserMention]:
        """
        Parse raw reviews and store them as classified UserMention records
        
        Args:
            db: Database session
            raw_reviews: List of raw review/mention data
            product_id: ID of the product these mentions belong to
            analysis_id: Optional ID of the reputation analysis
            
        Returns:
            List of created UserMention objects
        """
        created_mentions = []
        
        for review_data in raw_reviews:
            mention = self._create_mention_from_review(review_data, product_id, analysis_id)
            
            # Check if mention already exists (avoid duplicates)
            existing = db.query(UserMention).filter(
                UserMention.external_id == mention["external_id"],
                UserMention.platform == mention["platform"]
            ).first()
            
            if not existing:
                db_mention = UserMention(**mention)
                db.add(db_mention)
                created_mentions.append(db_mention)
        
        db.commit()
        
        # Refresh all created mentions to get their IDs
        for mention in created_mentions:
            db.refresh(mention)
            
        return created_mentions
    
    def _create_mention_from_review(self, review_data: Dict, product_id: int, analysis_id: Optional[int] = None) -> Dict:
        """
        Convert a raw review into a structured mention with classification
        
        Args:
            review_data: Raw review data
            product_id: Product ID
            analysis_id: Optional analysis ID
            
        Returns:
            Dictionary with UserMention fields
        """
        content = review_data.get("content", "")
        platform = review_data.get("platform", "unknown")
        
        # Classify the mention
        sentiment = self.analysis_service.analyze_sentiment(content)
        intent = self.analysis_service.classify_intent(content)
        priority = self._determine_priority(sentiment, intent, content)
        keywords = self._extract_keywords(content)
        topics = self._extract_topics(content)
        
        # Generate unique external ID if not provided
        external_id = review_data.get("id") or review_data.get("external_id") or str(uuid.uuid4())
        
        # Parse original date
        original_date = None
        if review_data.get("date"):
            try:
                if isinstance(review_data["date"], str):
                    original_date = datetime.fromisoformat(review_data["date"].replace('Z', '+00:00'))
                elif isinstance(review_data["date"], datetime):
                    original_date = review_data["date"]
            except:
                original_date = datetime.now()
        else:
            original_date = datetime.now()
        
        return {
            "product_id": product_id,
            "analysis_id": analysis_id,
            
            # Platform and source
            "platform": platform,
            "source_url": review_data.get("source_url"),
            "external_id": external_id,
            
            # Author information
            "author_name": review_data.get("author", "Anonymous"),
            "author_avatar_url": review_data.get("author_avatar"),
            "author_profile_url": review_data.get("author_profile"),
            
            # Content
            "content": content,
            "title": review_data.get("title"),
            "rating": review_data.get("rating"),
            
            # Classification results
            "sentiment": sentiment.get("sentiment_label", "neutral"),
            "intent": intent.get("intent", "neutral"),
            "priority": priority,
            "confidence_score": min(sentiment.get("confidence", 0.5), intent.get("confidence", 0.5)),
            
            # Metadata
            "original_date": original_date,
            "is_processed": "processed",
            
            # Analysis data
            "keywords_matched": keywords,
            "topics": topics,
            "response_suggested": self._generate_response_suggestion(intent, sentiment, priority)
        }
    
    def _determine_priority(self, sentiment: Dict, intent: Dict, content: str) -> str:
        """
        Determine the priority level of a mention based on sentiment, intent, and content
        
        Args:
            sentiment: Sentiment analysis result
            intent: Intent classification result
            content: The actual content text
            
        Returns:
            Priority level (critical, high, medium, low)
        """
        # Critical keywords that indicate urgent issues
        critical_keywords = [
            "terrible", "worst", "awful", "broken", "crash", "bug", "error", 
            "scam", "fraud", "stealing", "illegal", "lawsuit", "refund", 
            "money back", "cancel subscription", "hate", "disgusting"
        ]
        
        # High priority keywords
        high_keywords = [
            "problem", "issue", "complaint", "disappointed", "frustrated",
            "not working", "doesn't work", "failed", "slow", "lag"
        ]
        
        content_lower = content.lower()
        
        # Critical priority conditions
        if (sentiment.get("sentiment_label") == "negative" and sentiment.get("confidence", 0) > 0.8) or \
           (intent.get("intent") == "complaint" and intent.get("confidence", 0) > 0.8) or \
           any(keyword in content_lower for keyword in critical_keywords):
            return "critical"
        
        # High priority conditions
        if (sentiment.get("sentiment_label") == "negative" and sentiment.get("confidence", 0) > 0.6) or \
           (intent.get("intent") == "complaint") or \
           any(keyword in content_lower for keyword in high_keywords):
            return "high"
        
        # Medium priority for questions and neutral content
        if intent.get("intent") == "question" or sentiment.get("sentiment_label") == "neutral":
            return "medium"
        
        # Low priority for positive content and recommendations
        return "low"
    
    def _extract_keywords(self, content: str) -> List[str]:
        """
        Extract relevant keywords from the content
        
        Args:
            content: Text content to analyze
            
        Returns:
            List of extracted keywords
        """
        # Simple keyword extraction based on common product-related terms
        product_keywords = [
            "app", "service", "price", "cost", "payment", "billing", "subscription",
            "feature", "update", "interface", "design", "bug", "crash", "slow",
            "fast", "easy", "difficult", "customer service", "support", "help"
        ]
        
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in product_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:10]  # Limit to top 10 keywords
    
    def _extract_topics(self, content: str) -> List[str]:
        """
        Extract topics/themes from the content
        
        Args:
            content: Text content to analyze
            
        Returns:
            List of identified topics
        """
        # Topic mapping based on keywords
        topic_keywords = {
            "performance": ["slow", "fast", "lag", "speed", "performance", "quick"],
            "usability": ["easy", "difficult", "confusing", "simple", "user-friendly", "interface"],
            "pricing": ["expensive", "cheap", "cost", "price", "money", "billing", "subscription"],
            "features": ["feature", "function", "capability", "option", "tool"],
            "bugs": ["bug", "error", "crash", "broken", "glitch", "issue"],
            "customer_service": ["support", "help", "service", "staff", "team", "representative"],
            "design": ["design", "look", "appearance", "ui", "layout", "visual"]
        }
        
        content_lower = content.lower()
        identified_topics = []
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                identified_topics.append(topic)
        
        return identified_topics
    
    def _generate_response_suggestion(self, intent: Dict, sentiment: Dict, priority: str) -> Dict:
        """
        Generate response suggestions based on classification
        
        Args:
            intent: Intent classification result
            sentiment: Sentiment analysis result
            priority: Determined priority level
            
        Returns:
            Response suggestion data
        """
        intent_type = intent.get("intent", "neutral")
        sentiment_type = sentiment.get("sentiment_label", "neutral")
        
        suggestions = {
            "should_respond": priority in ["critical", "high"],
            "urgency": priority,
            "recommended_style": "official" if priority == "critical" else "friendly",
            "response_type": self._get_response_type(intent_type, sentiment_type),
            "key_points": self._get_key_response_points(intent_type, sentiment_type, priority)
        }
        
        return suggestions
    
    def _get_response_type(self, intent: str, sentiment: str) -> str:
        """Get the type of response needed"""
        if intent == "complaint":
            return "apology_and_resolution"
        elif intent == "question":
            return "informational_assistance"
        elif intent == "recommendation" and sentiment == "positive":
            return "gratitude_and_engagement"
        else:
            return "acknowledgment"
    
    def _get_key_response_points(self, intent: str, sentiment: str, priority: str) -> List[str]:
        """Get key points to address in the response"""
        points = []
        
        if intent == "complaint":
            points.extend([
                "Acknowledge the issue",
                "Apologize for the inconvenience",
                "Offer a solution or next steps"
            ])
        elif intent == "question":
            points.extend([
                "Provide helpful information",
                "Offer additional resources",
                "Invite further questions"
            ])
        elif intent == "recommendation":
            points.extend([
                "Thank the user for feedback",
                "Consider implementing suggestion",
                "Keep user updated on progress"
            ])
        
        if priority == "critical":
            points.append("Escalate to senior support team")
            
        return points