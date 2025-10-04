from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import *
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from ..database.database import get_db, init_db
from ..core.reputation_service import ReputationService
from ..database.models import Product, UserMention, AlertSettings
from ..scheduler.background_tasks import start_scheduler, get_scheduler_status, run_manual_parsing, run_manual_analysis
from datetime import datetime, timedelta
from sqlalchemy import desc

load_dotenv()

app = FastAPI(
    title="Brand Reputation Analysis API",
    description="AI-powered brand reputation analysis using CrewAI",
    version="1.0.0"
)

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Initialize database and scheduler on startup
@app.on_event("startup")
def startup_event():
    init_db()
    start_scheduler()


# Pydantic models for API
class ProductCreate(BaseModel):
    name: str
    app_store_url: Optional[str] = None
    google_play_url: Optional[str] = None
    brand_keywords: Optional[str] = None


class AnalysisRequest(BaseModel):
    product_name: str
    app_store_url: Optional[str] = None
    google_play_url: Optional[str] = None


@app.get("/")
def read_root():
    return {
        "message": "Unified Brand Reputation Analysis API",
        "version": "3.0.0",
        "description": "AI-powered reputation analysis with unified response containing all analysis components",
    }


@app.post("/analyze")
async def analyze_reputation(request: AnalysisRequest, db: Session = Depends(get_db)):
    """
    Analyze brand reputation for a given product
    """
    try:
        reputation_service = ReputationService()

        result = reputation_service.analyze_product_reputation(
            product_name=request.product_name,
            app_store_url=request.app_store_url,
            google_play_url=request.google_play_url
        )

        if result.get("success"):
            return JSONResponse(content=result, status_code=200)
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Analysis failed"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    """
    Get all products in the database
    """
    products = db.query(Product).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "app_store_url": p.app_store_url,
            "google_play_url": p.google_play_url,
            "created_at": p.created_at
        }
        for p in products
    ]


@app.post("/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product
    """
    try:
        reputation_service = ReputationService()
        new_product = reputation_service.create_product(db, product.dict())

        return {
            "id": new_product.id,
            "name": new_product.name,
            "app_store_url": new_product.app_store_url,
            "google_play_url": new_product.google_play_url,
            "created_at": new_product.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create product: {str(e)}")


@app.get("/analysis/{product_id}")
def get_latest_analysis(product_id: int, db: Session = Depends(get_db)):
    """
    Get the complete unified analysis for a specific product including all components:
    - Reputation score and sentiment analysis
    - Prioritized issues with evidence
    - Response drafts in multiple communication styles
    - Early warning system and crisis monitoring
    - Data source citations and actionable insights
    """
    reputation_service = ReputationService()
    analysis = reputation_service.get_latest_analysis(db, product_id)

    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this product")

    crisis_analysis = analysis.crisis_analysis or {}

    return {
        # Core Analysis Results
        "analysis_metadata": {
            "id": analysis.id,
            "product_id": analysis.product_id,
            "analysis_date": analysis.analysis_date,
            "version": "2.0"
        },

        # Reputation Metrics
        "reputation_metrics": {
            "overall_score": analysis.overall_score,
            "sentiment_score": analysis.sentiment_score,
            "score_interpretation": _get_score_interpretation(analysis.overall_score),
            "trend_indicators": {
                "crisis_level": crisis_analysis.get("crisis_level", "none"),
                "total_crisis_signals": crisis_analysis.get("total_signals", 0),
                "escalation_required": crisis_analysis.get("crisis_level") in ["high", "critical"]
            }
        },

        # Intent and Sentiment Breakdown
        "user_intent_analysis": {
            "intent_breakdown": analysis.intent_breakdown or {},
            "total_feedback_items": sum((analysis.intent_breakdown or {}).values()),
            "complaint_ratio": _calculate_complaint_ratio(analysis.intent_breakdown),
            "dominant_intent": _get_dominant_intent(analysis.intent_breakdown)
        },

        # Priority Issues with Evidence
        "priority_issues": {
            "issues_with_evidence": analysis.issues_list or [],
            "total_issues": len(analysis.issues_list or []),
            "high_priority_count": len([i for i in (analysis.issues_list or []) if i.get("priority") == "high"]),
            "evidence_summary": _summarize_evidence(analysis.issues_list or [])
        },

        # Response Management
        "response_management": {
            "generated_responses": analysis.response_drafts or {},
            "total_response_templates": len(analysis.response_drafts or {}),
            "style_recommendations": _get_style_recommendations(analysis.response_drafts or {}),
            "usage_guidelines": {
                "official": "Use for high-priority complaints and formal communications",
                "friendly": "Use for general questions and positive interactions",
                "tech_support": "Use for technical issues and troubleshooting"
            },
            "immediate_response_needed": _identify_urgent_responses(analysis.response_drafts or {})
        },

        # Early Warning System
        "early_warning_system": {
            "crisis_level": crisis_analysis.get("crisis_level", "none"),
            "active_alerts": crisis_analysis.get("alerts", []),
            "category_breakdown": crisis_analysis.get("category_breakdown", {}),
            "affected_reviews": crisis_analysis.get("affected_reviews", []),
            "monitoring_recommendation": crisis_analysis.get("recommendation", "Continue normal monitoring"),
            "escalation_timeline": _get_escalation_timeline(crisis_analysis.get("crisis_level", "none")),
            "stakeholder_notifications": _get_required_notifications(crisis_analysis.get("crisis_level", "none"))
        },

        # Data Sources and Evidence
        "data_sources": {
            "citations": analysis.data_citations or [],
            "evidence_data": analysis.evidence_data or {},
            "total_sources": len(analysis.data_citations or []),
            "platform_coverage": _extract_platform_coverage(analysis.data_citations or []),
            "data_freshness": _assess_data_freshness(analysis.analysis_date)
        },

        # Actionable Insights
        "actionable_insights": {
            "insights": analysis.actionable_insights or [],
            "total_insights": len(analysis.actionable_insights or []),
            "by_team": _group_insights_by_team(analysis.actionable_insights or []),
            "by_priority": _group_insights_by_priority(analysis.actionable_insights or []),
            "immediate_actions": _filter_immediate_actions(analysis.actionable_insights or [])
        },

        # Key Themes and Topics
        "key_themes": analysis.key_insights or {},

        # Executive Summary
        "executive_summary": {
            "overall_health": _assess_overall_health(analysis.overall_score,
                                                     crisis_analysis.get("crisis_level", "none")),
            "critical_actions_required": _count_critical_actions(analysis.actionable_insights or []),
            "response_readiness": len(analysis.response_drafts or {}) > 0,
            "monitoring_status": "Active" if crisis_analysis.get("total_signals", 0) > 0 else "Normal",
            "next_review_recommended": _recommend_next_review(crisis_analysis.get("crisis_level", "none"))
        }
    }


# Helper functions for unified response
def _get_score_interpretation(score: float):
    """Interpret reputation score with actionable context"""
    if score >= 80:
        return {"status": "excellent", "description": "Strong positive reputation", "action": "maintain current practices"}
    elif score >= 60:
        return {"status": "good", "description": "Generally positive with improvement opportunities", "action": "address moderate issues"}
    elif score >= 40:
        return {"status": "concerning", "description": "Mixed reputation with notable issues", "action": "immediate improvement plan needed"}
    else:
        return {"status": "critical", "description": "Significant reputation damage", "action": "urgent intervention required"}


def _calculate_complaint_ratio(intent_breakdown: Dict) -> float:
    """Calculate the ratio of complaints to total feedback"""
    if not intent_breakdown:
        return 0.0
    total = sum(intent_breakdown.values())
    return (intent_breakdown.get("complaint", 0) / total) if total > 0 else 0.0


def _get_dominant_intent(intent_breakdown: Dict) -> str:
    """Identify the most common user intent"""
    if not intent_breakdown:
        return "unknown"
    return max(intent_breakdown.keys(), key=lambda k: intent_breakdown[k])


def _summarize_evidence(issues: List[Dict]) -> Dict:
    """Summarize evidence across all issues"""
    total_evidence = sum(issue.get("evidence_count", 0) for issue in issues)
    evidence_types = {}
    for issue in issues:
        for evidence in issue.get("evidence", []):
            ev_type = evidence.get("type", "unknown")
            evidence_types[ev_type] = evidence_types.get(ev_type, 0) + 1

    return {
        "total_evidence_pieces": total_evidence,
        "evidence_by_type": evidence_types,
        "average_evidence_per_issue": total_evidence / len(issues) if issues else 0
    }


def _get_style_recommendations(response_drafts: Dict) -> List[Dict]:
    """Get style recommendations for response management"""
    recommendations = []
    for issue, drafts in response_drafts.items():
        recommended = drafts.get("recommendation", {})
        if recommended:
            recommendations.append({
                "issue": issue,
                "recommended_style": recommended.get("recommended_style", "official"),
                "reason": recommended.get("reason", "Standard recommendation")
            })
    return recommendations


def _identify_urgent_responses(response_drafts: Dict) -> List[str]:
    """Identify issues requiring immediate response"""
    urgent = []
    for issue, drafts in response_drafts.items():
        for style, draft in drafts.get("responses", {}).items():
            if draft.get("metadata", {}).get("severity") == "high":
                urgent.append(issue)
                break
    return list(set(urgent))


def _get_escalation_timeline(crisis_level: str) -> str:
    """Get escalation timeline based on crisis level"""
    timelines = {
        "critical": "Immediate (within 1 hour)",
        "high": "Urgent (within 4 hours)",
        "medium": "Standard (within 24 hours)",
        "low": "Normal (within 3 days)",
        "none": "No escalation needed"
    }
    return timelines.get(crisis_level, "Standard process")


def _get_required_notifications(crisis_level: str) -> List[str]:
    """Get required stakeholder notifications"""
    notifications = {
        "critical": ["CEO", "PR Director", "Crisis Management Team", "Legal Team"],
        "high": ["VP Customer Success", "PR Team", "Support Manager"],
        "medium": ["Customer Success Manager", "Support Team Lead"],
        "low": ["Support Team"],
        "none": []
    }
    return notifications.get(crisis_level, [])


def _extract_platform_coverage(citations: List[Dict]) -> List[str]:
    """Extract platform coverage from citations"""
    platforms = []
    for citation in citations:
        if citation.get("source_type") == "app_reviews":
            platforms.append(citation.get("platform", "Unknown"))
        elif citation.get("source_type") == "search_results":
            platforms.append("Google Search")
    return list(set(platforms))


def _assess_data_freshness(analysis_date) -> str:
    """Assess how fresh the analysis data is"""
    from datetime import datetime, timedelta
    if isinstance(analysis_date, str):
        return "Current analysis"

    now = datetime.now(analysis_date.tzinfo) if analysis_date.tzinfo else datetime.now()
    age = now - analysis_date

    if age < timedelta(hours=1):
        return "Very fresh (< 1 hour)"
    elif age < timedelta(hours=24):
        return f"Fresh ({age.seconds // 3600} hours old)"
    elif age < timedelta(days=7):
        return f"Recent ({age.days} days old)"
    else:
        return f"Aging ({age.days} days old)"


def _group_insights_by_team(insights: List[Dict]) -> Dict:
    """Group insights by responsible team"""
    by_team = {}
    for insight in insights:
        team = insight.get("responsible_team", "Unassigned")
        if team not in by_team:
            by_team[team] = []
        by_team[team].append(insight)
    return by_team


def _group_insights_by_priority(insights: List[Dict]) -> Dict:
    """Group insights by priority level"""
    by_priority = {}
    for insight in insights:
        priority = insight.get("priority", "medium")
        if priority not in by_priority:
            by_priority[priority] = []
        by_priority[priority].append(insight)
    return by_priority


def _filter_immediate_actions(insights: List[Dict]) -> List[Dict]:
    """Filter insights requiring immediate action"""
    return [insight for insight in insights if insight.get("priority") in ["critical", "high"]]


def _assess_overall_health(score: float, crisis_level: str) -> str:
    """Assess overall reputation health"""
    if crisis_level in ["high", "critical"]:
        return "Critical - Immediate attention required"
    elif score >= 80:
        return "Healthy - Reputation is strong"
    elif score >= 60:
        return "Stable - Minor improvements needed"
    elif score >= 40:
        return "At Risk - Significant issues present"
    else:
        return "Damaged - Urgent intervention required"


def _count_critical_actions(insights: List[Dict]) -> int:
    """Count insights requiring critical/immediate action"""
    return len([i for i in insights if i.get("priority") in ["critical", "high"]])


def _recommend_next_review(crisis_level: str) -> str:
    """Recommend when next review should occur"""
    recommendations = {
        "critical": "Every 30 minutes",
        "high": "Every 2 hours",
        "medium": "Daily",
        "low": "Weekly",
        "none": "Monthly"
    }
    return recommendations.get(crisis_level, "Weekly")


@app.get("/mentions")
def get_mentions(
    product_id: Optional[int] = None,
    platform: Optional[str] = None,
    sentiment: Optional[str] = None,
    intent: Optional[str] = None,
    priority: Optional[str] = None,
    is_marked: Optional[bool] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get paginated user mentions with filtering capabilities
    
    Parameters:
    - product_id: Filter by specific product
    - platform: Filter by platforms (list of strings: App Store, Reddit, Instagram, Google Serp, etc.)
    - sentiment: Filter by sentiment (positive, negative, neutral)
    - intent: Filter by intent (complaint, question, recommendation, neutral)
    - priority: Filter by priority (critical, high, medium, low)
    - is_marked: Filter by marked status (true for marked, false for unmarked, omit for all)
    - from_date: Filter mentions from this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    - to_date: Filter mentions up to this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    - page: Page number (starts from 1)
    - page_size: Number of items per page (max 100)
    """
    # Validate pagination parameters
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")

    # Parse and validate date parameters
    parsed_from_date = None
    parsed_to_date = None

    if from_date:
        try:
            # Support both date and datetime formats
            if 'T' in from_date:
                parsed_from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            else:
                parsed_from_date = datetime.fromisoformat(from_date + 'T00:00:00')
        except ValueError:
            raise HTTPException(status_code=400,
                                detail="Invalid from_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")

    if to_date:
        try:
            # Support both date and datetime formats
            if 'T' in to_date:
                parsed_to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            else:
                parsed_to_date = datetime.fromisoformat(to_date + 'T23:59:59')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")

    # Validate date range
    if parsed_from_date and parsed_to_date and parsed_from_date > parsed_to_date:
        raise HTTPException(status_code=400, detail="from_date must be before or equal to to_date")

    # Build query with filters
    query = db.query(UserMention)

    if product_id:
        query = query.filter(UserMention.product_id == product_id)
    if platform and len(platform) > 0:
        query = query.filter(UserMention.platform == platform)
    if sentiment:
        query = query.filter(UserMention.sentiment == sentiment)
    if intent:
        query = query.filter(UserMention.intent == intent)
    if priority:
        query = query.filter(UserMention.priority == priority)
    if is_marked is not None:
        query = query.filter(UserMention.is_marked == is_marked)
    if parsed_from_date:
        query = query.filter(UserMention.original_date >= parsed_from_date)
    if parsed_to_date:
        query = query.filter(UserMention.original_date <= parsed_to_date)

    # Get total count for pagination
    total_count = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    mentions = query.offset(offset).limit(page_size).all()

    # Calculate pagination metadata
    total_pages = (total_count + page_size - 1) // page_size
    has_next = page < total_pages
    has_prev = page > 1

    # Format response
    mentions_data = []
    for mention in mentions:
        mentions_data.append({
            "id": mention.id,
            "platform": mention.platform,
            "author": {
                "name": mention.author_name,
                "avatar_url": mention.author_avatar_url,
                "profile_url": mention.author_profile_url
            },
            "content": mention.content,
            "sentiment": mention.sentiment,
            "intent": mention.intent,
            "priority": mention.priority,
            "date": mention.original_date,
            "rating": mention.rating,
            "confidence_score": mention.confidence_score,
            "keywords_matched": mention.keywords_matched,
            "topics": mention.topics,
            "response_suggested": mention.response_suggested,
            "is_marked": mention.is_marked or False,
            "metadata": {
                "processed_date": mention.processed_date,
                "source_url": mention.source_url,
                "external_id": mention.external_id
            }
        })

    return {
        "mentions": mentions_data,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        "filters_applied": {
            "product_id": product_id,
            "platform": platform,
            "sentiment": sentiment,
            "intent": intent,
            "priority": priority,
            "is_marked": is_marked,
            "from_date": from_date,
            "to_date": to_date
        },
        "available_filters": {
            "platforms": ["App Store", "Reddit", "Instagram", "Google Serp", "Quora", "Google Play", "Trustpilot"],
            "sentiments": ["positive", "negative", "neutral"],
            "intents": ["complaint", "question", "recommendation", "neutral"],
            "priorities": ["critical", "high", "medium", "low"]
        }
    }


@app.get("/dashboard")
def get_dashboard(
    product_id: Optional[int] = 1,
    days_back: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard data including:
    - Top issues requiring attention
    - Sentiment distribution 
    - Sentiment trend over time
    - Reputation score with change percentage
    """
    try:
        # Build base query
        query = db.query(UserMention)
        if product_id:
            query = query.filter(UserMention.product_id == product_id)

        # Date range for trends (last 30 days by default)
        start_date = datetime.now() - timedelta(days=days_back)
        recent_mentions = query.filter(UserMention.original_date >= start_date).all()
        all_mentions = query.all()

        # 1. TOP ISSUES REQUIRING ATTENTION
        top_issues = _get_top_issues_requiring_attention(db, product_id, limit=10)

        # 2. SENTIMENT DISTRIBUTION 
        sentiment_distribution = _get_sentiment_distribution(all_mentions)

        # 3. SENTIMENT TREND (last 30 days)
        sentiment_trend = _get_sentiment_trend(recent_mentions, days_back)

        # 4. REPUTATION SCORE WITH CHANGE
        reputation_metrics = _get_reputation_score_with_change(db, product_id, days_back)

        # 5. ADDITIONAL DASHBOARD METRICS
        platform_distribution = _get_platform_distribution(all_mentions)
        priority_breakdown = _get_priority_breakdown(all_mentions)
        recent_activity = _get_recent_activity_summary(recent_mentions)

        return {
            "dashboard_data": {
                "generated_at": datetime.now().isoformat(),
                "product_id": product_id,
                "time_period_days": days_back,
                "total_mentions": len(all_mentions),
                "recent_mentions": len(recent_mentions)
            },
            "top_issues_requiring_attention": top_issues,
            "sentiment_distribution": sentiment_distribution,
            "sentiment_trend": sentiment_trend,
            "reputation_score": reputation_metrics,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


def _get_top_issues_requiring_attention(db: Session, product_id: Optional[int], limit: int = 5) -> List[Dict]:
    """Get top issues requiring immediate attention, grouped by issue type with mention counts"""
    query = db.query(UserMention)
    if product_id:
        query = query.filter(UserMention.product_id == product_id)

    # Get all mentions with priority critical, high, or medium + complaint
    priority_mentions = query.filter(
        UserMention.priority.in_(["critical", "high", "medium"])
    ).all()

    # Group mentions by topics and keywords to identify common issues
    issue_groups = {}

    for mention in priority_mentions:
        # Extract key issues from topics and keywords
        topics = mention.topics or []
        keywords = mention.keywords_matched or []

        # Determine issue category based on content analysis
        issue_category = _categorize_issue(mention.content, topics, keywords)

        if issue_category not in issue_groups:
            issue_groups[issue_category] = {
                "mentions": [],
                "priority_counts": {"critical": 0, "high": 0, "medium": 0},
                "total_mentions": 0
            }

        issue_groups[issue_category]["mentions"].append(mention)
        issue_groups[issue_category]["priority_counts"][mention.priority] += 1
        issue_groups[issue_category]["total_mentions"] += 1

    # Convert to list and sort by severity (critical count, then high count, then total)
    issues_list = []
    for issue_category, data in issue_groups.items():
        # Determine overall priority for this issue group
        if data["priority_counts"]["critical"] > 0:
            group_priority = "critical"
        elif data["priority_counts"]["high"] > 0:
            group_priority = "high"
        else:
            group_priority = "medium"

        # Get representative mention for description
        representative_mention = max(data["mentions"], key=lambda m:
        {"critical": 3, "high": 2, "medium": 1}.get(m.priority, 0))

        # Generate issue title and description
        issue_title, issue_description = _generate_issue_title_and_description(issue_category, data["mentions"])

        issues_list.append({
            "issue_category": issue_category,
            "title": issue_title,
            "description": issue_description,
            "priority": group_priority,
            "total_mentions": data["total_mentions"],
        })

    # Sort by priority and mention count
    issues_list.sort(key=lambda x: (
        {"critical": 3, "high": 2, "medium": 1}[x["priority"]],
        x["total_mentions"]
    ), reverse=True)

    return issues_list[:limit]


def _categorize_issue(content: str, topics: List[str], keywords: List[str]) -> str:
    """Categorize the issue based on content, topics, and keywords"""
    content_lower = content.lower()

    # Define issue categories with their identifying patterns
    issue_patterns = {
        "App Crashing/Technical Issues": [
            "crash", "bug", "error", "broken", "not working", "glitch", "freeze",
            "technical", "loading", "slow", "lag", "performance"
        ],
        "Payment Processing Issues": [
            "payment", "billing", "charge", "card", "money", "transaction",
            "refund", "charged twice", "payment failed", "billing issue"
        ],
        "Customer Service Problems": [
            "support", "customer service", "help", "response", "contact",
            "terrible service", "poor service", "no help", "rude"
        ],
        "Driver/Service Quality": [
            "driver", "late", "rude driver", "car dirty", "unprofessional",
            "bad experience", "service quality", "ride quality"
        ],
        "App Navigation/UI Issues": [
            "confusing", "hard to use", "interface", "navigation", "ui",
            "user experience", "design", "layout", "difficult"
        ],
        "Feature Requests/Missing Features": [
            "feature", "request", "missing", "need", "should add", "would like",
            "improvement", "suggestion", "enhance"
        ],
        "Pricing/Cost Concerns": [
            "expensive", "price", "cost", "fare", "cheap", "overcharge",
            "pricing", "surge", "fee"
        ]
    }

    # Check topics first
    topic_matches = {
        "bugs": "App Crashing/Technical Issues",
        "performance": "App Crashing/Technical Issues",
        "customer_service": "Customer Service Problems",
        "pricing": "Pricing/Cost Concerns",
        "usability": "App Navigation/UI Issues",
        "features": "Feature Requests/Missing Features"
    }

    for topic in topics:
        if topic in topic_matches:
            return topic_matches[topic]

    # Check keywords and content
    for category, patterns in issue_patterns.items():
        if any(pattern in content_lower for pattern in patterns):
            return category
        if any(keyword.lower() in patterns for keyword in keywords):
            return category

    # Default category
    return "General Issues"


def _generate_issue_title_and_description(category: str, mentions: List) -> tuple:
    """Generate a title and description for the issue category"""
    titles_descriptions = {
        "App Crashing/Technical Issues": (
            "App Crashing/Technical Problems",
            "Users reporting crashes, bugs, and technical difficulties"
        ),
        "Payment Processing Issues": (
            "Payment Processing Problems",
            "Multiple payment failures and billing issues reported"
        ),
        "Customer Service Problems": (
            "Customer Support Issues",
            "Users experiencing poor customer service response"
        ),
        "Driver/Service Quality": (
            "Service Quality Concerns",
            "Issues with driver behavior and ride experience"
        ),
        "App Navigation/UI Issues": (
            "User Interface Problems",
            "Navigation and usability difficulties reported"
        ),
        "Feature Requests/Missing Features": (
            "Missing Feature Requests",
            "Users requesting additional functionality"
        ),
        "Pricing/Cost Concerns": (
            "Pricing and Cost Issues",
            "Users concerned about pricing and fees"
        ),
        "General Issues": (
            "General Concerns",
            "Various user concerns and feedback"
        )
    }

    return titles_descriptions.get(category, (category, f"Issues related to {category.lower()}"))


def _get_sentiment_distribution(mentions: List[UserMention]) -> Dict:
    """Calculate sentiment distribution across all mentions"""
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    total_mentions = len(mentions)

    for mention in mentions:
        sentiment = mention.sentiment or "neutral"
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1

    # Calculate percentages
    sentiment_percentages = {}
    for sentiment, count in sentiment_counts.items():
        percentage = (count / total_mentions * 100) if total_mentions > 0 else 0
        sentiment_percentages[sentiment] = round(percentage, 1)

    return {
        "counts": sentiment_counts,
        "percentages": sentiment_percentages,
        "total_mentions": total_mentions,
        "dominant_sentiment": max(sentiment_counts.keys(),
                                  key=lambda k: sentiment_counts[k]) if total_mentions > 0 else "neutral"
    }


def _get_sentiment_trend(mentions: List[UserMention], days_back: int) -> List[Dict]:
    """Calculate daily sentiment trend over the specified period"""
    from collections import defaultdict

    # Initialize date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)

    # Group mentions by date
    daily_sentiments = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

    for mention in mentions:
        if mention.original_date:
            mention_date = mention.original_date.date()
            sentiment = mention.sentiment or "neutral"
            if sentiment in daily_sentiments[mention_date]:
                daily_sentiments[mention_date][sentiment] += 1

    # Create trend data for each day
    trend_data = []
    current_date = start_date
    while current_date <= end_date:
        day_data = daily_sentiments[current_date]
        total_day = sum(day_data.values())

        trend_data.append({
            "date": current_date.isoformat(),
            "positive": day_data["positive"],
            "negative": day_data["negative"],
            "neutral": day_data["neutral"],
            "total": total_day,
            "sentiment_ratio": {
                "positive": round(day_data["positive"] / total_day * 100, 1) if total_day > 0 else 0,
                "negative": round(day_data["negative"] / total_day * 100, 1) if total_day > 0 else 0,
                "neutral": round(day_data["neutral"] / total_day * 100, 1) if total_day > 0 else 0
            }
        })
        current_date += timedelta(days=1)

    return trend_data


def _get_reputation_score_with_change(db: Session, product_id: Optional[int], days_back: int) -> Dict:
    """Calculate reputation score and percentage change from previous period"""
    current_period_end = datetime.now()
    current_period_start = current_period_end - timedelta(days=days_back)
    previous_period_start = current_period_start - timedelta(days=days_back)

    # Get mentions for current and previous periods
    query = db.query(UserMention)
    if product_id:
        query = query.filter(UserMention.product_id == product_id)

    current_mentions = query.filter(
        UserMention.original_date >= current_period_start,
        UserMention.original_date <= current_period_end
    ).all()

    previous_mentions = query.filter(
        UserMention.original_date >= previous_period_start,
        UserMention.original_date < current_period_start
    ).all()

    # Calculate scores using weighted sentiment analysis
    current_score = _calculate_reputation_score(current_mentions)
    previous_score = _calculate_reputation_score(previous_mentions)

    # Calculate percentage change
    percentage_change = 0
    change_direction = "no_change"
    if previous_score > 0:
        percentage_change = ((current_score - previous_score) / previous_score) * 100
        change_direction = "increase" if percentage_change > 0 else "decrease" if percentage_change < 0 else "no_change"

    # Get score interpretation
    score_interpretation = _get_score_interpretation(current_score)

    return {
        "current_score": round(current_score, 1),
        "previous_score": round(previous_score, 1),
        "percentage_change": round(percentage_change, 1),
        "change_direction": change_direction,
        "change_description": f"{'+' if percentage_change > 0 else ''}{percentage_change:.1f}% from last period",
        "score_interpretation": score_interpretation,
        "current_period": {
            "start": current_period_start.isoformat(),
            "end": current_period_end.isoformat(),
            "mentions_count": len(current_mentions)
        },
        "previous_period": {
            "start": previous_period_start.isoformat(),
            "end": current_period_start.isoformat(),
            "mentions_count": len(previous_mentions)
        }
    }


def _calculate_reputation_score(mentions: List[UserMention]) -> float:
    """Calculate reputation score (0-100) based on sentiment, priority, and other factors"""
    if not mentions:
        return 50.0  # Neutral baseline

    total_weight = 0
    weighted_score = 0

    for mention in mentions:
        # Base sentiment score
        sentiment_score = 50  # Neutral baseline
        if mention.sentiment == "positive":
            sentiment_score = 80
        elif mention.sentiment == "negative":
            sentiment_score = 20

        # Weight based on priority (higher priority has more impact)
        priority_weight = 1.0
        if mention.priority == "critical":
            priority_weight = 3.0
        elif mention.priority == "high":
            priority_weight = 2.0
        elif mention.priority == "medium":
            priority_weight = 1.5

        # Weight based on intent
        intent_modifier = 1.0
        if mention.intent == "complaint":
            intent_modifier = 2.0  # Complaints have higher impact
        elif mention.intent == "recommendation":
            intent_modifier = 1.5  # Recommendations are valuable

        # Consider confidence score
        confidence_weight = mention.confidence_score or 0.5

        final_weight = priority_weight * intent_modifier * confidence_weight
        weighted_score += sentiment_score * final_weight
        total_weight += final_weight

    # Calculate final score
    final_score = weighted_score / total_weight if total_weight > 0 else 50.0

    # Ensure score is within 0-100 range
    return max(0, min(100, final_score))


def _get_platform_distribution(mentions: List[UserMention]) -> Dict:
    """Get distribution of mentions across platforms"""
    platform_counts = {}
    total_mentions = len(mentions)

    for mention in mentions:
        platform = mention.platform or "Unknown"
        platform_counts[platform] = platform_counts.get(platform, 0) + 1

    # Calculate percentages and sort by count
    platform_distribution = []
    for platform, count in sorted(platform_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_mentions * 100) if total_mentions > 0 else 0
        platform_distribution.append({
            "platform": platform,
            "count": count,
            "percentage": round(percentage, 1)
        })

    return {
        "platforms": platform_distribution,
        "total_platforms": len(platform_counts)
    }


def _get_priority_breakdown(mentions: List[UserMention]) -> Dict:
    """Get breakdown of mentions by priority level"""
    priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_mentions = len(mentions)

    for mention in mentions:
        priority = mention.priority or "low"
        if priority in priority_counts:
            priority_counts[priority] += 1

    # Calculate percentages
    priority_breakdown = []
    for priority, count in priority_counts.items():
        percentage = (count / total_mentions * 100) if total_mentions > 0 else 0
        priority_breakdown.append({
            "priority": priority,
            "count": count,
            "percentage": round(percentage, 1)
        })

    return {
        "priorities": priority_breakdown,
        "total_mentions": total_mentions,
        "high_priority_count": priority_counts["critical"] + priority_counts["high"]
    }


def _get_recent_activity_summary(mentions: List[UserMention]) -> Dict:
    """Get summary of recent activity"""
    if not mentions:
        return {
            "total_recent_mentions": 0,
            "avg_daily_mentions": 0,
            "most_active_platform": None,
            "most_common_intent": None,
            "critical_issues_count": 0
        }

    # Most active platform
    platform_counts = {}
    intent_counts = {}
    critical_count = 0

    for mention in mentions:
        platform = mention.platform or "Unknown"
        intent = mention.intent or "unknown"

        platform_counts[platform] = platform_counts.get(platform, 0) + 1
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

        if mention.priority in ["critical", "high"]:
            critical_count += 1

    most_active_platform = max(platform_counts.keys(), key=lambda k: platform_counts[k]) if platform_counts else None
    most_common_intent = max(intent_counts.keys(), key=lambda k: intent_counts[k]) if intent_counts else None

    # Calculate daily average
    days_span = 30  # Based on the period
    avg_daily = len(mentions) / days_span if days_span > 0 else 0

    return {
        "total_recent_mentions": len(mentions),
        "avg_daily_mentions": round(avg_daily, 1),
        "most_active_platform": most_active_platform,
        "most_common_intent": most_common_intent,
        "critical_issues_count": critical_count
    }


@app.get("/analytics")
def get_analytics(
    product_id: Optional[int] = None,
    days_back: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics data including:
    - Sentiment distribution by platform
    - Topic analysis for chart visualization (radar/spider chart)
    - Detailed topic analysis with sentiment, trend, and mention counts
    """
    try:
        # Build base query
        query = db.query(UserMention)
        if product_id:
            query = query.filter(UserMention.product_id == product_id)

        # Date range for trends
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        recent_mentions = query.filter(UserMention.original_date >= start_date).all()
        all_mentions = query.all()

        # Previous period for trend comparison
        previous_start = start_date - timedelta(days=days_back)
        previous_mentions = query.filter(
            UserMention.original_date >= previous_start,
            UserMention.original_date < start_date
        ).all()

        # 1. SENTIMENT BY PLATFORM
        sentiment_by_platform = _get_sentiment_by_platform(all_mentions)

        # 2. TOPIC ANALYSIS (for radar chart)
        topic_analysis_chart = _get_topic_analysis_chart(recent_mentions)

        # 3. DETAILED TOPIC ANALYSIS
        detailed_topic_analysis = _get_detailed_topic_analysis(recent_mentions, previous_mentions)

        return {
            "analytics_data": {
                "generated_at": datetime.now().isoformat(),
                "product_id": product_id,
                "time_period_days": days_back,
                "total_mentions": len(all_mentions),
                "recent_mentions": len(recent_mentions),
                "previous_period_mentions": len(previous_mentions)
            },
            "sentiment_by_platform": sentiment_by_platform,
            "topic_analysis": topic_analysis_chart,
            "detailed_topic_analysis": detailed_topic_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics generation failed: {str(e)}")


def _get_sentiment_by_platform(mentions: List[UserMention]) -> Dict:
    """Get sentiment distribution grouped by platform"""
    platform_sentiment = {}

    for mention in mentions:
        platform = mention.platform or "Unknown"
        sentiment = mention.sentiment or "neutral"

        if platform not in platform_sentiment:
            platform_sentiment[platform] = {
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "total": 0
            }

        platform_sentiment[platform][sentiment] += 1
        platform_sentiment[platform]["total"] += 1

    # Calculate percentages
    result = []
    for platform, sentiments in platform_sentiment.items():
        total = sentiments["total"]
        result.append({
            "platform": platform,
            "counts": {
                "positive": sentiments["positive"],
                "negative": sentiments["negative"],
                "neutral": sentiments["neutral"],
                "total": total
            },
            "percentages": {
                "positive": round(sentiments["positive"] / total * 100, 1) if total > 0 else 0,
                "negative": round(sentiments["negative"] / total * 100, 1) if total > 0 else 0,
                "neutral": round(sentiments["neutral"] / total * 100, 1) if total > 0 else 0
            }
        })

    # Sort by total mentions descending
    result.sort(key=lambda x: x["counts"]["total"], reverse=True)

    return {
        "platforms": result,
        "total_platforms": len(result),
        "overall_sentiment": _calculate_overall_sentiment(
            [m for platform in platform_sentiment.values() for m in [platform]])
    }


def _get_topic_analysis_chart(mentions: List[UserMention]) -> Dict:
    """Generate topic analysis data for radar/spider chart visualization"""

    # Define topic categories based on the chart image
    topic_categories = {
        "Performance": ["performance", "speed", "slow", "fast", "loading", "lag", "optimization"],
        "Features": ["features", "functionality", "feature", "capability", "missing", "request"],
        "Support": ["support", "customer service", "help", "assistance", "response"],
        "Pricing": ["price", "cost", "expensive", "cheap", "pricing", "fee", "billing"],
        "UI/UX": ["ui", "ux", "interface", "design", "usability", "navigation", "user experience"],
        "Bugs": ["bug", "error", "crash", "broken", "issue", "problem", "glitch"],
        "Security": ["security", "privacy", "safe", "secure", "protection", "data"]
    }

    # Count mentions for each topic category
    topic_scores = {}
    total_mentions = len(mentions)

    for category, keywords in topic_categories.items():
        count = 0
        for mention in mentions:
            content_lower = (mention.content or "").lower()
            topics = mention.topics or []
            keywords_matched = mention.keywords_matched or []

            # Check if any keywords match in content, topics, or keywords_matched
            if (any(keyword in content_lower for keyword in keywords) or
                any(keyword in topics for keyword in keywords) or
                any(keyword in keywords_matched for keyword in keywords)):
                count += 1

        # Calculate score as percentage of total mentions, then scale to 100
        score = (count / total_mentions * 100) if total_mentions > 0 else 0
        topic_scores[category] = {
            "score": round(min(score * 2, 100), 1),  # Scale up and cap at 100
            "mention_count": count,
            "percentage": round(score, 1)
        }

    # Format for radar chart
    chart_data = {
        "categories": list(topic_categories.keys()),
        "values": [topic_scores[cat]["score"] for cat in topic_categories.keys()],
        "detailed_scores": topic_scores
    }

    return {
        "chart_type": "radar",
        "chart_data": chart_data,
        "max_value": 100,
        "description": "Topic distribution analysis showing relative mention frequency across key categories"
    }


def _get_detailed_topic_analysis(current_mentions: List[UserMention], previous_mentions: List[UserMention]) -> List[
    Dict]:
    """Generate detailed topic analysis with sentiment, trend, and mention counts"""

    # Define comprehensive topic categories
    topic_categories = {
        "Performance": ["performance", "speed", "slow", "fast", "loading", "lag", "optimization"],
        "Features": ["features", "functionality", "feature", "capability", "missing", "request"],
        "Customer Support": ["support", "customer service", "help", "assistance", "response"],
        "Pricing": ["price", "cost", "expensive", "cheap", "pricing", "fee", "billing"],
        "User Interface": ["ui", "ux", "interface", "design", "usability", "navigation"],
        "Bugs & Issues": ["bug", "error", "crash", "broken", "issue", "problem", "glitch"],
        "Security": ["security", "privacy", "safe", "secure", "protection", "data"],
        "Payment System": ["payment", "billing", "charge", "card", "transaction", "refund"],
        "Driver Quality": ["driver", "service quality", "ride", "professional", "behavior"],
        "App Reliability": ["reliable", "stability", "consistent", "available", "uptime"]
    }

    detailed_analysis = []

    for topic, keywords in topic_categories.items():
        # Current period analysis
        current_topic_mentions = []
        for mention in current_mentions:
            content_lower = (mention.content or "").lower()
            topics = mention.topics or []
            keywords_matched = mention.keywords_matched or []

            if (any(keyword in content_lower for keyword in keywords) or
                any(keyword in topics for keyword in keywords) or
                any(keyword in keywords_matched for keyword in keywords)):
                current_topic_mentions.append(mention)

        # Previous period analysis
        previous_topic_mentions = []
        for mention in previous_mentions:
            content_lower = (mention.content or "").lower()
            topics = mention.topics or []
            keywords_matched = mention.keywords_matched or []

            if (any(keyword in content_lower for keyword in keywords) or
                any(keyword in topics for keyword in keywords) or
                any(keyword in keywords_matched for keyword in keywords)):
                previous_topic_mentions.append(mention)

        # Calculate sentiment distribution
        sentiment_scores = {"positive": 0, "negative": 0, "neutral": 0}
        for mention in current_topic_mentions:
            sentiment = mention.sentiment or "neutral"
            sentiment_scores[sentiment] += 1

        total_current = len(current_topic_mentions)
        total_previous = len(previous_topic_mentions)

        # Calculate sentiment percentage (negative bias for negative sentiment)
        if total_current > 0:
            positive_pct = sentiment_scores["positive"] / total_current * 100
            negative_pct = sentiment_scores["negative"] / total_current * 100
            sentiment_score = positive_pct - negative_pct  # Range: -100 to +100
        else:
            sentiment_score = 0

        # Calculate trend (change from previous period) with realistic caps
        trend_percentage = _calculate_realistic_trend(total_current, total_previous)

        # Skip topics with no mentions in current period
        if total_current == 0:
            continue

        detailed_analysis.append({
            "topic": topic,
            "mentions": total_current,
            "sentiment": f"{sentiment_score:+.1f}%",
            "sentiment_raw": sentiment_score,
            "trend": f"{trend_percentage:+.1f}%",
            "trend_raw": trend_percentage,
            "sentiment_breakdown": {
                "positive": sentiment_scores["positive"],
                "negative": sentiment_scores["negative"],
                "neutral": sentiment_scores["neutral"]
            },
            "change_from_previous": {
                "current_mentions": total_current,
                "previous_mentions": total_previous,
                "absolute_change": total_current - total_previous
            },
            "priority": _calculate_topic_priority(sentiment_score, trend_percentage, total_current)
        })

    # Sort by priority (most concerning topics first)
    detailed_analysis.sort(key=lambda x: (
        x["priority"],
        -x["mentions"]  # Then by mention count descending
    ), reverse=True)

    return detailed_analysis


def _calculate_realistic_trend(current_mentions: int, previous_mentions: int) -> float:
    """
    Calculate a realistic trend percentage with proper edge case handling
    
    Args:
        current_mentions: Current period mention count
        previous_mentions: Previous period mention count
    
    Returns:
        Trend percentage capped at realistic values
    """
    # Handle edge cases
    if previous_mentions == 0:
        if current_mentions > 0:
            return 100.0  # New topic appearing - cap at 100%
        else:
            return 0.0  # No change

    if current_mentions == 0:
        return -100.0  # Topic disappeared completely

    # Calculate basic percentage change
    raw_percentage = ((current_mentions - previous_mentions) / previous_mentions) * 100

    # Apply realistic caps to prevent extreme values
    MAX_POSITIVE_TREND = 500.0  # Cap positive trend at 500%
    MAX_NEGATIVE_TREND = -100.0  # Cap negative trend at -100%

    # Special handling for small previous values to avoid extreme percentages
    if previous_mentions <= 3:
        # For very small previous values, use a more conservative approach
        if current_mentions > previous_mentions * 3:
            # If current is more than 3x previous, cap at 300%
            trend_percentage = min(300.0, raw_percentage)
        elif current_mentions < previous_mentions / 3:
            # If current is less than 1/3 previous, cap at -75%
            trend_percentage = max(-75.0, raw_percentage)
        else:
            # Normal calculation for moderate changes
            trend_percentage = raw_percentage
    else:
        # For larger previous values, use standard caps
        trend_percentage = max(MAX_NEGATIVE_TREND, min(MAX_POSITIVE_TREND, raw_percentage))

    return round(trend_percentage, 1)


def _calculate_topic_priority(sentiment_score: float, trend_percentage: float, mention_count: int) -> int:
    """Calculate priority score for topics (higher = more concerning)"""
    priority = 0

    # Negative sentiment increases priority
    if sentiment_score < -20:
        priority += 3
    elif sentiment_score < 0:
        priority += 1

    # Negative trend increases priority
    if trend_percentage < -20:
        priority += 2
    elif trend_percentage > 50:
        priority += 1  # Rapidly growing negative topics

    # High mention count increases priority
    if mention_count > 20:
        priority += 2
    elif mention_count > 10:
        priority += 1

    return priority


def _calculate_overall_sentiment(platform_data: List[Dict]) -> Dict:
    """Calculate overall sentiment across all platforms"""
    total_positive = sum(p.get("positive", 0) for p in platform_data)
    total_negative = sum(p.get("negative", 0) for p in platform_data)
    total_neutral = sum(p.get("neutral", 0) for p in platform_data)
    total_all = total_positive + total_negative + total_neutral

    if total_all == 0:
        return {"positive": 0, "negative": 0, "neutral": 0}

    return {
        "positive": round(total_positive / total_all * 100, 1),
        "negative": round(total_negative / total_all * 100, 1),
        "neutral": round(total_neutral / total_all * 100, 1)
    }


@app.patch("/mentions/{mention_id}/mark")
def mark_mention(
    mention_id: int,
    is_marked: bool = True,
    db: Session = Depends(get_db)
):
    """
    Mark or unmark a mention for follow-up or review
    
    Parameters:
    - mention_id: ID of the mention to mark/unmark
    - is_marked: True to mark, False to unmark (default: True)
    """
    # Find the mention
    mention = db.query(UserMention).filter(UserMention.id == mention_id).first()

    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")

    # Update the is_marked field
    mention.is_marked = is_marked
    db.commit()
    db.refresh(mention)

    return {
        "success": True,
        "mention_id": mention_id,
        "is_marked": is_marked,
        "message": f"Mention {'marked' if is_marked else 'unmarked'} successfully"
    }


@app.get("/alerts")
def get_alerts(
    product_id: Optional[int] = 1,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get critical mentions categorized by alert types with pagination:
    - ActiveAlerts: Mentions that are not marked as resolved
    - Critical: Mentions classified as critical severity
    - HighPriority: Mentions with high priority
    - Resolved: Mentions that are already marked as resolved
    
    Parameters:
    - page: Page number (starts from 1)
    - page_size: Number of items per page (default: 20)
    """
    try:
        # Validate page parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        # Build base query
        query = db.query(UserMention)
        if product_id:
            query = query.filter(UserMention.product_id == product_id)

        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Get total count of all mentions
        total_mentions = query.count()
        total_pages = (total_mentions + page_size - 1) // page_size if total_mentions > 0 else 1

        # Get paginated mentions ordered by priority and date
        mentions = query.order_by(desc(UserMention.original_date)).all()

        # Convert mentions to response format
        alerts = []
        for mention in mentions:
            alert_type = "resolved" if mention.is_marked else "active"
            if mention.priority == "critical" or (
                mention.sentiment == "negative" and (mention.confidence_score or 0) > 0.8):
                alert_type = "critical"
            elif mention.priority == "high":
                alert_type = "high_priority"

            alerts.append({
                "id": mention.id,
                "platform": mention.platform,
                "author_name": mention.author_name,
                "content": mention.content[:200] + "..." if len(mention.content or "") > 200 else mention.content,
                "full_content": mention.content,
                "sentiment": mention.sentiment,
                "priority": mention.priority,
                "original_date": mention.original_date.isoformat() if mention.original_date else None,
                "is_marked": mention.is_marked,
                "rating": mention.rating,
                "source_url": mention.source_url,
                "alert_type": alert_type
            })

        return {
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_mentions,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            },
            "alerts": alerts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alerts generation failed: {str(e)}")


@app.post("/alerts/simulate")
def simulate_alert(
    product_id: Optional[int] = 1,
    db: Session = Depends(get_db)
):
    """
    Simulate sending an alert to both Telegram bot and email.
    Returns a mock response confirming successful delivery.
    """
    try:
        # Get alert settings for the product
        alert_settings = db.query(AlertSettings).filter(AlertSettings.product_id == product_id).first()

        # Create default settings if none exist
        if not alert_settings:
            alert_settings = AlertSettings(
                product_id=product_id,
                threshold=0.8,
                platforms=["Reddit", "app_store", "google_play", "Google Serp"],
                telegram_bot_enabled=bool(os.getenv("TELEGRAM_BOT_KEY")),
                email=None
            )
            db.add(alert_settings)
            db.commit()
            db.refresh(alert_settings)

        # Check if TELEGRAM_BOT_KEY is configured
        telegram_bot_key = os.getenv("TELEGRAM_BOT_KEY")
        telegram_enabled = alert_settings.telegram_bot_enabled and bool(telegram_bot_key)

        # Simulate alert content
        sample_alert = {
            "alert_id": "ALERT_2025_001",
            "timestamp": datetime.now().isoformat(),
            "product_id": product_id,
            "severity": "HIGH",
            "platform": "Reddit",
            "message": "Critical mention detected: 'App keeps crashing during ride booking'",
            "author": "u/frustrated_user",
            "sentiment": "negative",
            "confidence": 0.95,
            "source_url": "https://reddit.com/r/uber/comments/example"
        }

        # Simulate delivery results
        delivery_results = {
            "alert_details": sample_alert,
            "delivery_status": {
                "telegram": {
                    "enabled": telegram_enabled,
                    "status": "SUCCESS" if telegram_enabled else "DISABLED",
                    "message": f"Alert sent to Telegram bot (Key: {'***' + telegram_bot_key[-4:] if telegram_bot_key else 'NOT_CONFIGURED'})" if telegram_enabled else "Telegram bot not configured",
                    "timestamp": datetime.now().isoformat()
                },
                "email": {
                    "enabled": bool(alert_settings.email),
                    "status": "SUCCESS" if alert_settings.email else "DISABLED",
                    "recipient": alert_settings.email if alert_settings.email else "Not configured",
                    "message": f"Alert sent to {alert_settings.email}" if alert_settings.email else "Email notifications not configured",
                    "timestamp": datetime.now().isoformat()
                }
            },
            "alert_settings": {
                "threshold": alert_settings.threshold,
                "platforms": alert_settings.platforms,
                "max_alerts_per_hour": alert_settings.max_alerts_per_hour,
                "max_alerts_per_day": alert_settings.max_alerts_per_day
            },
            "simulation_note": "This is a simulated alert for testing purposes. No actual notifications were sent."
        }

        return delivery_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert simulation failed: {str(e)}")


@app.post("/alerts/send")
def send_real_alert(
    product_id: Optional[int] = 1,
    message: str = "Test alert notification",
    db: Session = Depends(get_db)
):
    """
    Send a REAL alert to both Telegram bot and email.
    Actually delivers notifications using configured services.
    """
    try:
        # Get alert settings
        alert_settings = db.query(AlertSettings).filter(AlertSettings.product_id == product_id).first()

        if not alert_settings:
            raise HTTPException(status_code=404, detail="Alert settings not found. Please configure settings first.")

        telegram_success = False
        email_success = False
        telegram_error = None
        email_error = None

        # Send Telegram notification to all chat IDs
        if alert_settings.telegram_bot_enabled:
            telegram_bot_key = os.getenv("TELEGRAM_BOT_KEY")

            if telegram_bot_key:
                try:
                    # Get all chat IDs that have interacted with the bot
                    updates_url = f"https://api.telegram.org/bot{telegram_bot_key}/getUpdates"
                    updates_response = requests.get(updates_url, timeout=10)

                    if updates_response.status_code == 200:
                        updates_data = updates_response.json()

                        # Extract unique chat IDs from all messages
                        chat_ids = set()
                        for update in updates_data.get("result", []):
                            if "message" in update:
                                chat_id = update["message"]["chat"]["id"]
                                chat_ids.add(chat_id)
                            elif "callback_query" in update:
                                chat_id = update["callback_query"]["message"]["chat"]["id"]
                                chat_ids.add(chat_id)

                        if chat_ids:
                            send_url = f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage"
                            alert_text = f"""🚨 <b>Critical Mention Alert</b> 🚨

📌 <b>Platform:</b> Reddit  
👤 <b>Author:</b> S_EJK  
🗓️ <b>Date:</b> October 3rd, 2025  

📝 <b>Content:</b>  
"Uber Credit – disappointing experience. I took an Uber early AM on Oct 1. The credit did not post until later in the morning, so it wasn't applied to my ride. Customer Service refused to credit me. I find the claim misleading and am disappointed they won't apply it."

🔎 <b>Sentiment:</b> Negative  
🎯 <b>Priority:</b> High  

---
⚡ <b>Recommended Action:</b>  
- Review Uber Credit posting logic and timing  
- Escalate case to Support for resolution  
- Consider PR clarification on the "monthly credit" claim  

⏰ <b>Alert generated at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

                            successful_sends = 0
                            failed_sends = 0
                            send_errors = []

                            # Send to each chat ID
                            for chat_id in chat_ids:
                                try:
                                    payload = {
                                        "chat_id": chat_id,
                                        "text": alert_text,
                                        "parse_mode": "HTML"
                                    }

                                    response = requests.post(send_url, json=payload, timeout=10)

                                    if response.status_code == 200:
                                        successful_sends += 1
                                    else:
                                        failed_sends += 1
                                        send_errors.append(f"Chat {chat_id}: {response.text}")

                                except Exception as e:
                                    failed_sends += 1
                                    send_errors.append(f"Chat {chat_id}: {str(e)}")

                            if successful_sends > 0:
                                telegram_success = True
                                if failed_sends > 0:
                                    telegram_error = f"Sent to {successful_sends}/{len(chat_ids)} chats. Failures: {'; '.join(send_errors[:3])}"
                                else:
                                    telegram_error = f"Successfully sent to all {successful_sends} chats"
                            else:
                                telegram_error = f"Failed to send to any chats: {'; '.join(send_errors[:3])}"
                        else:
                            telegram_error = "No chat IDs found. Users need to start a conversation with the bot first."
                    else:
                        telegram_error = f"Failed to get bot updates: {updates_response.text}"

                except Exception as e:
                    telegram_error = f"Telegram sending failed: {str(e)}"
            else:
                telegram_error = "TELEGRAM_BOT_KEY not configured"
        else:
            telegram_error = "Telegram notifications disabled in settings"

        # Send Email notification
        if alert_settings.email:
            try:
                # Email configuration from environment variables
                smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
                smtp_port = int(os.getenv("SMTP_PORT", "587"))
                smtp_username = os.getenv("SMTP_USERNAME")
                smtp_password = os.getenv("SMTP_PASSWORD")
                from_email = os.getenv("FROM_EMAIL", smtp_username)

                if smtp_username and smtp_password:
                    # Create email
                    msg = MIMEMultipart()
                    msg['From'] = from_email
                    msg['To'] = alert_settings.email
                    msg['Subject'] = f"Brand Alert - Product {product_id}"

                    body = f"""
Brand Reputation Alert

Message: {message}

Product ID: {product_id}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Threshold: {alert_settings.threshold}
Monitored Platforms: {', '.join(alert_settings.platforms)}

This is an automated alert from your Brand Reputation Monitoring System.
                    """

                    msg.attach(MIMEText(body, 'plain'))

                    # Send email
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    server.starttls()
                    server.login(smtp_username, smtp_password)
                    text = msg.as_string()
                    server.sendmail(from_email, alert_settings.email, text)
                    server.quit()

                    email_success = True
                else:
                    email_error = "SMTP credentials not configured (SMTP_USERNAME, SMTP_PASSWORD)"

            except Exception as e:
                email_error = f"Email sending failed: {str(e)}"
        else:
            email_error = "Email notifications not configured in settings"

        return {
            "alert_sent": True,
            "message": message,
            "product_id": product_id,
            "timestamp": datetime.now().isoformat(),
            "delivery_results": {
                "telegram": {
                    "enabled": alert_settings.telegram_bot_enabled,
                    "success": telegram_success,
                    "error": telegram_error
                },
                "email": {
                    "enabled": bool(alert_settings.email),
                    "success": email_success,
                    "recipient": alert_settings.email,
                    "error": email_error
                }
            },
            "required_env_vars": {
                "telegram": ["TELEGRAM_BOT_KEY"],
                "email": ["SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_SERVER (optional)", "SMTP_PORT (optional)"]
            },
            "note": "Telegram alerts will be sent to all users who have started a conversation with the bot"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real alert sending failed: {str(e)}")


@app.get("/alerts/telegram/chats")
def get_telegram_chat_ids():
    """
    Get all chat IDs that have interacted with the Telegram bot.
    Useful for checking who will receive alerts.
    """
    try:
        telegram_bot_key = os.getenv("TELEGRAM_BOT_KEY")

        if not telegram_bot_key:
            return {
                "error": "TELEGRAM_BOT_KEY not configured",
                "chat_ids": [],
                "total_chats": 0
            }

        # Get all updates from the bot
        updates_url = f"https://api.telegram.org/bot{telegram_bot_key}/getUpdates"
        updates_response = requests.get(updates_url, timeout=10)

        if updates_response.status_code != 200:
            return {
                "error": f"Failed to get bot updates: {updates_response.text}",
                "chat_ids": [],
                "total_chats": 0
            }

        updates_data = updates_response.json()

        # Extract chat information
        chats = {}
        for update in updates_data.get("result", []):
            chat_info = None

            if "message" in update:
                chat = update["message"]["chat"]
                chat_info = {
                    "id": chat["id"],
                    "type": chat["type"],
                    "title": chat.get("title", f"{chat.get('first_name', '')} {chat.get('last_name', '')}").strip(),
                    "username": chat.get("username"),
                    "last_message_date": update["message"]["date"]
                }
            elif "callback_query" in update:
                chat = update["callback_query"]["message"]["chat"]
                chat_info = {
                    "id": chat["id"],
                    "type": chat["type"],
                    "title": chat.get("title", f"{chat.get('first_name', '')} {chat.get('last_name', '')}").strip(),
                    "username": chat.get("username"),
                    "last_message_date": update["callback_query"]["message"]["date"]
                }

            if chat_info:
                chat_id = chat_info["id"]
                # Keep the most recent info for each chat
                if chat_id not in chats or chat_info["last_message_date"] > chats[chat_id]["last_message_date"]:
                    chats[chat_id] = chat_info

        # Convert to list and sort by last message date
        chat_list = list(chats.values())
        chat_list.sort(key=lambda x: x["last_message_date"], reverse=True)

        return {
            "chat_ids": [chat["id"] for chat in chat_list],
            "chat_details": chat_list,
            "total_chats": len(chat_list),
            "note": "These are all users/groups that have interacted with the bot and will receive alerts"
        }

    except Exception as e:
        return {
            "error": f"Failed to get chat IDs: {str(e)}",
            "chat_ids": [],
            "total_chats": 0
        }


@app.get("/alerts/settings/")
def get_alert_settings(
    product_id: int = 1,
    db: Session = Depends(get_db)
):
    """Get alert settings for a specific product"""
    try:
        settings = db.query(AlertSettings).filter(AlertSettings.product_id == product_id).first()

        if not settings:
            # Return default settings
            return {
                "product_id": product_id,
                "threshold": 0.8,
                "platforms": ["Reddit", "app_store", "google_play", "Google Serp"],
                "telegram_bot_enabled": bool(os.getenv("TELEGRAM_BOT_KEY")),
                "email": None,
                "max_alerts_per_hour": 10,
                "max_alerts_per_day": 50,
                "exists": False
            }

        return {
            "id": settings.id,
            "product_id": settings.product_id,
            "threshold": settings.threshold,
            "platforms": settings.platforms,
            "telegram_bot_enabled": settings.telegram_bot_enabled,
            "email": settings.email,
            "max_alerts_per_hour": settings.max_alerts_per_hour,
            "max_alerts_per_day": settings.max_alerts_per_day,
            "created_at": settings.created_at.isoformat(),
            "updated_at": settings.updated_at.isoformat(),
            "exists": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert settings: {str(e)}")


@app.put("/alerts/settings/")
def update_alert_settings(
    product_id: int = 1,
    threshold: float = 0.8,
    platforms: List[str] = ["Reddit", "app_store", "google_play", "Google Serp"],
    telegram_bot_enabled: bool = False,
    email: Optional[str] = None,
    max_alerts_per_hour: int = 10,
    max_alerts_per_day: int = 50,
    db: Session = Depends(get_db)
):
    """Update or create alert settings for a specific product"""
    try:
        # Validate threshold
        if not 0.0 <= threshold <= 1.0:
            raise HTTPException(status_code=400, detail="Threshold must be between 0.0 and 1.0")

        # Validate platforms
        valid_platforms = ["Reddit", "app_store", "google_play", "Google Serp", "Trustpilot"]
        for platform in platforms:
            if platform not in valid_platforms:
                raise HTTPException(status_code=400,
                                    detail=f"Invalid platform: {platform}. Valid platforms: {valid_platforms}")

        # Get existing settings or create new
        settings = db.query(AlertSettings).filter(AlertSettings.product_id == product_id).first()

        if settings:
            # Update existing settings
            settings.threshold = threshold
            settings.platforms = platforms
            settings.telegram_bot_enabled = telegram_bot_enabled
            settings.email = email
            settings.max_alerts_per_hour = max_alerts_per_hour
            settings.max_alerts_per_day = max_alerts_per_day
            settings.updated_at = datetime.now()
        else:
            # Create new settings
            settings = AlertSettings(
                product_id=product_id,
                threshold=threshold,
                platforms=platforms,
                telegram_bot_enabled=telegram_bot_enabled,
                email=email,
                max_alerts_per_hour=max_alerts_per_hour,
                max_alerts_per_day=max_alerts_per_day
            )
            db.add(settings)

        db.commit()
        db.refresh(settings)

        return {
            "message": "Alert settings updated successfully",
            "settings": {
                "id": settings.id,
                "product_id": settings.product_id,
                "threshold": settings.threshold,
                "platforms": settings.platforms,
                "telegram_bot_enabled": settings.telegram_bot_enabled,
                "email": settings.email,
                "max_alerts_per_hour": settings.max_alerts_per_hour,
                "max_alerts_per_day": settings.max_alerts_per_day,
                "updated_at": settings.updated_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update alert settings: {str(e)}")


@app.get("/scheduler/status")
def get_scheduler_info():
    """
    Get background scheduler status and job information
    """
    try:
        status = get_scheduler_status()
        return {
            "scheduler": status,
            "environment": {
                "ENV_RUN_SCHEDULER": os.getenv("ENV_RUN_SCHEDULER", "false"),
                "timezone": "Europe/Kiev"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@app.post("/scheduler/manual/parse")
async def trigger_manual_parsing():
    """
    Manually trigger data parsing task (for testing/debugging)
    """
    try:
        await run_manual_parsing()
        return {
            "success": True,
            "message": "Manual data parsing completed successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual parsing failed: {str(e)}")


@app.post("/scheduler/manual/analyze")
async def trigger_manual_analysis():
    """
    Manually trigger AI analysis task (for testing/debugging)
    """
    try:
        await run_manual_analysis()
        return {
            "success": True,
            "message": "Manual AI analysis completed successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual analysis failed: {str(e)}")


@app.get("/health")
def health_check():
    """
    Health check endpoint
    """
    # Check if required environment variables are set
    required_vars = ["OPENAI_API_KEY", "SERPER_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    return {
        "status": "healthy" if not missing_vars else "unhealthy",
        "missing_env_vars": missing_vars,
        "database": "connected"
    }
