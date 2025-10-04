#!/usr/bin/env python3
"""
Command to classify user mentions using Gemini API
Analyzes content field for sentiment, intent, priority, confidence scores, keywords, and topics
Uses Google's Gemini 1.5 Flash model for fast and accurate classification
"""

import os
import sys
import argparse
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
import google.generativeai as genai

from app.database.database import get_db, init_db
from app.database.models import UserMention

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyCxwOziss2ankMaUx5XWANu_jZfVpWy1Lw"
genai.configure(api_key=GEMINI_API_KEY)


def classify_with_gemini(content: str, platform: str, rating: Optional[float] = None) -> Dict:
    """
    Classify user mention using Gemini API
    
    Args:
        content: The mention content to classify
        platform: Platform where the mention was found
        rating: Optional rating if available
    
    Returns:
        Dictionary with classification results
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        rating_info = f"Rating: {rating}/5" if rating else "No rating provided"
        
        prompt = f"""Classify this user mention from {platform}:

Content: "{content}"
Platform: {platform}
{rating_info}

Analyze and classify this mention with the following outputs:

1. SENTIMENT: Choose exactly one of: positive, negative, neutral
   - positive: Praise, satisfaction, recommendations, good experiences
   - negative: Complaints, frustration, dissatisfaction, problems
   - neutral: Neutral observations, questions without emotional tone, factual statements

2. INTENT: Choose exactly one of: complaint, question, recommendation, neutral
   - complaint: User is reporting a problem, expressing dissatisfaction, or requesting resolution
   - question: User is asking for information, clarification, or help
   - recommendation: User is suggesting the product/service to others or praising features
   - neutral: General observations, updates, or ambiguous intent

3. PRIORITY: Choose exactly one of: critical, high, medium, low
   - critical: Severe issues affecting safety, security, or major functionality; public reputation damage
   - high: Significant problems affecting core functionality, billing issues, widespread user impact
   - medium: Moderate issues affecting user experience, feature requests, service delays
   - low: Minor issues, general feedback, positive comments

4. CONFIDENCE_SCORE: Provide a float between 0.0 and 1.0 indicating your confidence in the classification
   - 0.9-1.0: Very confident (clear sentiment, obvious intent)
   - 0.7-0.8: Confident (mostly clear with minor ambiguity)
   - 0.5-0.6: Moderate confidence (some ambiguity in tone or intent)
   - 0.3-0.4: Low confidence (unclear or mixed signals)
   - 0.0-0.2: Very low confidence (highly ambiguous or insufficient context)

5. KEYWORDS_MATCHED: Extract 3-7 key terms or phrases that are most relevant to the content
   - Focus on product features, issues, emotions, or specific topics mentioned
   - Include technical terms, service aspects, or problem indicators
   - Examples: ["app crashes", "customer service", "payment", "driver", "booking"]

6. TOPICS: Identify 2-4 main themes or categories that this mention relates to
   - Use broad categories that help organize feedback types
   - Examples: ["technical_issues", "customer_service", "pricing", "user_experience", "driver_quality", "app_features", "billing", "safety"]

Consider these factors:
- Platform context (App Store/Google Play ratings vs Reddit discussions vs Trustpilot reviews)
- Language intensity and emotional indicators
- Specific issues mentioned (crashes, payments, customer service, etc.)
- Impact on other users or business reputation
- Urgency indicators and resolution expectations

Return your analysis in this exact JSON format:
{{
    "sentiment": "positive|negative|neutral",
    "intent": "complaint|question|recommendation|neutral", 
    "priority": "critical|high|medium|low",
    "confidence_score": 0.85,
    "keywords_matched": ["keyword1", "keyword2", "keyword3"],
    "topics": ["topic1", "topic2"]
}}

IMPORTANT: Return ONLY the JSON object, no additional text or explanation."""

        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[^}]*\}', result_text, re.DOTALL)
        if json_match:
            try:
                classification = json.loads(json_match.group())
                
                # Validate the classification
                valid_sentiments = ["positive", "negative", "neutral"]
                valid_intents = ["complaint", "question", "recommendation", "neutral"]
                valid_priorities = ["critical", "high", "medium", "low"]
                
                if (classification.get("sentiment") in valid_sentiments and
                    classification.get("intent") in valid_intents and
                    classification.get("priority") in valid_priorities and
                    isinstance(classification.get("confidence_score"), (int, float))):
                    
                    # Ensure confidence score is in valid range
                    confidence = float(classification.get("confidence_score", 0.5))
                    classification["confidence_score"] = max(0.0, min(1.0, confidence))
                    
                    # Ensure keywords_matched and topics are lists
                    keywords = classification.get("keywords_matched", [])
                    if not isinstance(keywords, list):
                        keywords = []
                    classification["keywords_matched"] = keywords[:7]  # Limit to 7 keywords
                    
                    topics = classification.get("topics", [])
                    if not isinstance(topics, list):
                        topics = []
                    classification["topics"] = topics[:4]  # Limit to 4 topics
                    
                    return classification
                    
            except json.JSONDecodeError:
                print(f"Failed to parse JSON from Gemini response: {result_text}")
        
        # Fallback to simple classification if Gemini fails
        print(f"Using fallback classification for content: {content[:50]}...")
        return classify_mention_simple(content, platform, rating)
        
    except Exception as e:
        print(f"Error with Gemini classification: {str(e)}")
        return classify_mention_simple(content, platform, rating)


def classify_mention_simple(content: str, platform: str, rating: Optional[float] = None) -> Dict:
    """
    Simple rule-based classification as fallback
    """
    content_lower = content.lower()
    
    # Sentiment analysis
    positive_words = ["great", "excellent", "love", "amazing", "good", "perfect", "fantastic", "recommend", "best", "awesome", "helpful", "professional", "easy", "convenient", "satisfied", "happy"]
    negative_words = ["terrible", "awful", "hate", "worst", "bad", "horrible", "annoying", "frustrating", "disappointed", "angry", "broken", "crash", "problem", "issue", "error", "slow", "expensive", "rude"]
    
    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)
    
    if rating:
        if rating >= 4:
            positive_count += 2
        elif rating <= 2:
            negative_count += 2
    
    if positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Intent analysis
    question_indicators = ["how", "what", "why", "when", "where", "help", "?", "can you", "could you", "please help"]
    complaint_indicators = ["problem", "issue", "error", "crash", "broken", "not working", "terrible", "awful", "disappointed", "angry", "refund"]
    recommendation_indicators = ["recommend", "love", "great", "excellent", "should try", "amazing", "perfect"]
    
    if any(word in content_lower for word in question_indicators):
        intent = "question"
    elif any(word in content_lower for word in complaint_indicators):
        intent = "complaint"
    elif any(word in content_lower for word in recommendation_indicators):
        intent = "recommendation"
    else:
        intent = "neutral"
    
    # Priority analysis
    critical_keywords = ["crash", "security", "fraud", "illegal", "unsafe", "emergency", "urgent", "immediately", "critical", "charged twice", "unauthorized"]
    high_keywords = ["billing", "payment", "refund", "customer service", "support", "not working", "broken", "error"]
    
    if any(word in content_lower for word in critical_keywords):
        priority = "critical"
    elif any(word in content_lower for word in high_keywords) or sentiment == "negative":
        priority = "high"
    elif sentiment == "positive":
        priority = "low"
    else:
        priority = "medium"
    
    # Extract keywords
    keywords = []
    keyword_candidates = ["app", "driver", "service", "payment", "billing", "crash", "bug", "support", "help", "ride", "booking", "customer service", "refund", "rating", "review", "experience", "price", "cost", "fee", "car", "trip", "route", "navigation", "location", "pickup", "dropoff", "wait time", "fast", "slow", "professional", "rude", "clean", "dirty"]
    
    for keyword in keyword_candidates:
        if keyword in content_lower:
            keywords.append(keyword)
    
    # Extract topics
    topics = []
    if any(word in content_lower for word in ["crash", "bug", "error", "broken", "slow", "loading", "freeze"]):
        topics.append("technical_issues")
    if any(word in content_lower for word in ["driver", "ride", "car", "pickup", "professional", "rude", "clean", "dirty"]):
        topics.append("service_quality")
    if any(word in content_lower for word in ["payment", "billing", "charge", "money", "cost", "price", "fee", "refund"]):
        topics.append("billing")
    if any(word in content_lower for word in ["support", "help", "contact", "customer service", "response"]):
        topics.append("customer_service")
    if any(word in content_lower for word in ["app", "interface", "navigation", "easy", "difficult", "confusing"]):
        topics.append("user_experience")
    if any(word in content_lower for word in ["safety", "secure", "unsafe", "emergency"]):
        topics.append("safety")
    
    if not topics:
        topics = ["general_feedback"]
    
    # Confidence score
    confidence = 0.6
    if rating and abs(rating - 3) > 1:  # Strong rating
        confidence += 0.2
    if len([w for w in positive_words + negative_words if w in content_lower]) > 2:
        confidence += 0.1
    if len(content) > 50:  # Longer content usually more reliable
        confidence += 0.1
    
    confidence = min(0.95, confidence)
    
    return {
        "sentiment": sentiment,
        "intent": intent,
        "priority": priority,
        "confidence_score": confidence,
        "keywords_matched": keywords[:7],
        "topics": topics[:4]
    }


def classify_mention_content(content: str, platform: str, rating: Optional[float] = None) -> Dict:
    """
    Classify a single mention using Gemini API for faster processing
    
    Args:
        content: The mention content to classify
        platform: Platform where the mention was found
        rating: Optional rating if available
    
    Returns:
        Dictionary with classification results
    """
    return classify_with_gemini(content, platform, rating)


def classify_user_mentions(batch_size: int = 10, filter_unprocessed: bool = True, product_id: Optional[int] = None) -> Dict:
    """
    Main function to classify user mentions using CrewAI
    
    Args:
        batch_size: Number of mentions to process in each batch
        filter_unprocessed: Whether to only process unclassified mentions
        product_id: Optional product ID filter
    
    Returns:
        Dictionary with processing results
    """
    print("🤖 Starting user mention classification with Gemini API...")
    
    # Initialize database
    init_db()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Build query for mentions
        query = db.query(UserMention)
        
        if product_id:
            query = query.filter(UserMention.product_id == product_id)
            
        if filter_unprocessed:
            # Only process mentions that haven't been classified yet
            query = query.filter(
                (UserMention.sentiment.is_(None)) |
                (UserMention.intent.is_(None)) |
                (UserMention.priority.is_(None)) |
                (UserMention.confidence_score.is_(None))
            )
        
        # Get total count
        total_mentions = query.count()
        print(f"📊 Found {total_mentions} mentions to classify")
        
        if total_mentions == 0:
            return {
                "success": True,
                "total_mentions": 0,
                "processed": 0,
                "errors": 0,
                "message": "No mentions found to classify"
            }
        
        processed_count = 0
        error_count = 0
        
        # Process mentions in batches
        offset = 0
        while offset < total_mentions:
            batch_mentions = query.offset(offset).limit(batch_size).all()
            
            if not batch_mentions:
                break
                
            print(f"🔄 Processing batch {offset//batch_size + 1}: mentions {offset+1}-{min(offset+batch_size, total_mentions)}")
            
            for mention in batch_mentions:
                try:
                    # Skip if content is empty
                    if not mention.content or not mention.content.strip():
                        print(f"⚠️  Skipping mention {mention.id}: empty content")
                        continue
                    
                    print(f"🔍 Classifying mention {mention.id} from {mention.platform}")
                    print(f"   Content preview: {mention.content[:100]}...")
                    
                    # Classify the mention
                    classification = classify_mention_content(
                        content=mention.content,
                        platform=mention.platform or "Unknown",
                        rating=mention.rating
                    )
                    
                    # Update the mention with classification results
                    mention.sentiment = classification["sentiment"]
                    mention.intent = classification["intent"]
                    mention.priority = classification["priority"]
                    mention.confidence_score = classification["confidence_score"]
                    mention.keywords_matched = classification["keywords_matched"]
                    mention.topics = classification["topics"]
                    mention.is_processed = "processed"
                    mention.updated_at = datetime.now()
                    
                    # Commit the changes
                    db.commit()
                    
                    processed_count += 1
                    keywords_str = ", ".join(classification['keywords_matched'][:3]) if classification['keywords_matched'] else "none"
                    topics_str = ", ".join(classification['topics'][:2]) if classification['topics'] else "none"
                    print(f"✅ Classified mention {mention.id}: {classification['sentiment']}/{classification['intent']}/{classification['priority']} (confidence: {classification['confidence_score']:.2f})")
                    print(f"   Keywords: [{keywords_str}] | Topics: [{topics_str}]")
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ Error processing mention {mention.id}: {str(e)}")
                    
                    # Mark as failed
                    try:
                        mention.is_processed = "failed"
                        db.commit()
                    except:
                        pass
            
            offset += batch_size
            
            # Progress update
            progress = min(offset, total_mentions)
            print(f"📈 Progress: {progress}/{total_mentions} mentions processed ({progress/total_mentions*100:.1f}%)")
        
        print(f"\n🎉 Classification completed!")
        print(f"   Total mentions: {total_mentions}")
        print(f"   Successfully processed: {processed_count}")
        print(f"   Errors: {error_count}")
        
        return {
            "success": True,
            "total_mentions": total_mentions,
            "processed": processed_count,
            "errors": error_count,
            "message": f"Successfully classified {processed_count} mentions"
        }
        
    except Exception as e:
        print(f"❌ Critical error during classification: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "total_mentions": 0,
            "processed": 0,
            "errors": 1
        }
    finally:
        db.close()


def main():
    """Command line interface for mention classification"""
    parser = argparse.ArgumentParser(description="Classify user mentions using CrewAI")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of mentions to process in each batch")
    parser.add_argument("--product-id", type=int, help="Filter by specific product ID")
    parser.add_argument("--all", action="store_true", help="Process all mentions, not just unclassified ones")
    parser.add_argument("--test", action="store_true", help="Test with a single mention")
    
    args = parser.parse_args()
    
    if args.test:
        # Test classification with sample content
        print("🧪 Testing Gemini-based classification...")
        test_content = "The app keeps crashing when I try to book a ride. This is very frustrating and I need help!"
        result = classify_mention_content(test_content, "App Store", 1.0)
        print(f"Test result: {result}")
        print(f"✅ Gemini classification successful!")
        return
    
    # Run the classification
    result = classify_user_mentions(
        batch_size=args.batch_size,
        filter_unprocessed=not args.all,
        product_id=args.product_id
    )
    
    if result["success"]:
        print(f"\n✅ Classification successful: {result['message']}")
    else:
        print(f"\n❌ Classification failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()