from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    app_store_url = Column(String)
    google_play_url = Column(String)
    brand_keywords = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReputationAnalysis(Base):
    __tablename__ = "reputation_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    overall_score = Column(Float)
    sentiment_score = Column(Float)
    serp_results = Column(JSON)
    app_store_reviews = Column(JSON)
    google_play_reviews = Column(JSON)
    key_insights = Column(JSON)
    issues_list = Column(JSON)
    
    # Enhanced fields for improved analysis
    intent_breakdown = Column(JSON)  # Distribution of user intents
    crisis_analysis = Column(JSON)   # Early warning system results
    response_drafts = Column(JSON)   # Generated response templates
    data_citations = Column(JSON)    # Source citations and evidence
    actionable_insights = Column(JSON)  # Specific actionable recommendations
    evidence_data = Column(JSON)     # Supporting evidence for issues
    
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())


class UserMention(Base):
    __tablename__ = "user_mentions"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("reputation_analyses.id"), nullable=True, index=True)
    
    # Platform and source information
    platform = Column(String, nullable=False, index=True)  # App Store, Reddit, Instagram, etc.
    source_url = Column(String)
    external_id = Column(String, index=True)  # Original ID from the platform
    
    # Author information
    author_name = Column(String)
    author_avatar_url = Column(String)
    author_profile_url = Column(String)
    
    # Content information
    content = Column(Text, nullable=False)
    title = Column(String)
    rating = Column(Float)  # For app store reviews (1-5 stars)
    
    # Analysis results
    sentiment = Column(String, index=True)  # positive, negative, neutral
    intent = Column(String, index=True)  # complaint, question, recommendation, neutral
    priority = Column(String, index=True)  # critical, high, medium, low
    confidence_score = Column(Float)  # Confidence in classification (0-1)
    
    # Metadata
    original_date = Column(DateTime(timezone=True))  # Original post/review date
    processed_date = Column(DateTime(timezone=True), server_default=func.now())
    is_processed = Column(String, default="pending")  # pending, processed, failed
    
    # Additional analysis data
    keywords_matched = Column(JSON)  # Keywords that matched for this mention
    topics = Column(JSON)  # Extracted topics/themes
    response_suggested = Column(JSON)  # Suggested response data
    
    # Status tracking
    is_marked = Column(Boolean, default=False, nullable=True)  # Mark for follow-up or review
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertSettings(Base):
    __tablename__ = "alert_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    # Alert threshold configuration
    threshold = Column(Float, default=0.8, nullable=False)  # Confidence threshold for triggering alerts
    
    # Platform monitoring configuration
    platforms = Column(JSON, default=["Reddit", "app_store", "google_play", "Google Serp"])  # List of platforms to monitor
    
    # Notification configuration
    telegram_bot_enabled = Column(Boolean, default=False)
    email = Column(String, nullable=True)  # Optional email for notifications
    
    # Alert frequency settings
    max_alerts_per_hour = Column(Integer, default=10)
    max_alerts_per_day = Column(Integer, default=50)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

