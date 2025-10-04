from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from ..database.models import Product, ReputationAnalysis
from ..database.database import get_db
from ..agents.crew_agents import ReputationCrew
from .analysis_service import AnalysisService
from .response_generator import ResponseGenerator
from .mention_service import MentionService
from ..parsers.reddit_scraper import RedditScraper, get_uber_relevant_subreddits
from ..parsers.trustpilot_scraper import TrustpilotScraper
from datetime import datetime
import json

class ReputationService:
    def __init__(self):
        self.reputation_crew = ReputationCrew()
        self.analysis_service = AnalysisService()
        self.response_generator = ResponseGenerator()
        self.mention_service = MentionService()
        self.reddit_scraper = RedditScraper()
        self.trustpilot_scraper = TrustpilotScraper()
    
    def get_product_by_name(self, db: Session, product_name: str) -> Optional[Product]:
        """Get product from database by name"""
        return db.query(Product).filter(Product.name.ilike(f"%{product_name}%")).first()
    
    def create_product(self, db: Session, product_data: Dict) -> Product:
        """Create a new product in the database"""
        product = Product(**product_data)
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    
    def save_analysis_result(self, db: Session, analysis_result: Dict, product_id: int) -> ReputationAnalysis:
        """Save enhanced analysis result to database"""
        enhanced_analysis = analysis_result.get('enhanced_analysis', {})
        
        analysis = ReputationAnalysis(
            product_id=product_id,
            overall_score=analysis_result.get('overall_score', 0),
            sentiment_score=analysis_result.get('sentiment_score', 0),
            serp_results=analysis_result.get('serp_results', {}),
            app_store_reviews=analysis_result.get('app_store_reviews', {}),
            google_play_reviews=analysis_result.get('google_play_reviews', {}),
            key_insights=enhanced_analysis.get('key_themes', {}),
            issues_list=enhanced_analysis.get('prioritized_issues', []),
            
            # Enhanced fields
            intent_breakdown=enhanced_analysis.get('intent_breakdown', {}),
            crisis_analysis=analysis_result.get('early_warning', {}),
            response_drafts=analysis_result.get('response_drafts', {}),
            data_citations=analysis_result.get('data_citations', []),
            actionable_insights=analysis_result.get('actionable_insights', []),
            evidence_data=enhanced_analysis.get('data_sources', {})
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    
    def get_latest_analysis(self, db: Session, product_id: int) -> Optional[ReputationAnalysis]:
        """Get the latest analysis for a product"""
        return db.query(ReputationAnalysis)\
                 .filter(ReputationAnalysis.product_id == product_id)\
                 .order_by(ReputationAnalysis.analysis_date.desc())\
                 .first()
    
    def analyze_product_reputation(self, product_name: str, app_store_url: str = None, google_play_url: str = None) -> Dict:
        """
        Perform complete reputation analysis for a product
        
        Args:
            product_name: Name of the product to analyze
            app_store_url: Optional App Store URL
            google_play_url: Optional Google Play URL
            
        Returns:
            Dictionary containing the complete analysis results
        """
        try:
            # Get database session
            db = next(get_db())
            
            # Get or create product
            product = self.get_product_by_name(db, product_name)
            if not product:
                product_data = {
                    "name": product_name,
                    "app_store_url": app_store_url,
                    "google_play_url": google_play_url,
                    "brand_keywords": product_name
                }
                product = self.create_product(db, product_data)
            
            print(f"Starting reputation analysis for: {product_name}")
            
            # Collect additional data from Reddit and Trustpilot
            print("Collecting Reddit mentions...")
            reddit_mentions = self._collect_reddit_mentions(product_name)
            
            print("Collecting Trustpilot reviews...")
            trustpilot_reviews = self._collect_trustpilot_reviews(product_name)
            
            # Run CrewAI analysis with all data sources
            crew_result = self.reputation_crew.analyze_brand_reputation(
                product_name, app_store_url, google_play_url, reddit_mentions, trustpilot_reviews
            )
            
            if not crew_result.get("success"):
                return {
                    "success": False,
                    "error": crew_result.get("error", "Analysis failed"),
                    "product_name": product_name
                }
            
            # Parse and structure the results with real data
            analysis_result = self._process_crew_results(crew_result, product_name, reddit_mentions, trustpilot_reviews)
            
            # Save to database
            saved_analysis = self.save_analysis_result(db, analysis_result, product.id)
            
            # Parse and store individual mentions from all sources
            all_reviews = []
            all_reviews.extend(analysis_result.get("app_store_reviews", []))
            all_reviews.extend(analysis_result.get("google_play_reviews", []))
            
            # Add Reddit mentions
            all_reviews.extend(reddit_mentions)
            
            # Add Trustpilot reviews  
            all_reviews.extend(trustpilot_reviews)
            
            # Convert SERP results to mention format
            serp_mentions = []
            for serp_item in analysis_result.get("serp_results", []):
                serp_mentions.append({
                    "id": f"serp_{serp_item.get('position', 'unknown')}",
                    "platform": "Google Serp",
                    "content": serp_item.get("snippet", ""),
                    "title": serp_item.get("title", ""),
                    "author": serp_item.get("source", "Unknown"),
                    "source_url": serp_item.get("link", ""),
                    "date": datetime.now().isoformat()
                })
            all_reviews.extend(serp_mentions)
            
            # Store individual mentions
            if all_reviews:
                self.mention_service.parse_and_store_mentions(db, all_reviews, product.id, saved_analysis.id)
            
            # Format unified final result matching API response structure
            enhanced_analysis = analysis_result.get("enhanced_analysis", {})
            crisis_analysis = analysis_result.get("early_warning", {})
            
            final_result = {
                "success": True,
                "product_name": product_name,
                "analysis_id": saved_analysis.id,
                "analysis_date": saved_analysis.analysis_date.isoformat(),
                
                # Unified response structure
                "analysis_metadata": {
                    "id": saved_analysis.id,
                    "product_id": product.id,
                    "analysis_date": saved_analysis.analysis_date.isoformat(),
                    "version": "3.0"
                },
                
                "reputation_metrics": {
                    "overall_score": analysis_result["overall_score"],
                    "sentiment_score": analysis_result["sentiment_score"],
                    "score_interpretation": self._get_score_interpretation(analysis_result["overall_score"]),
                    "trend_indicators": {
                        "crisis_level": crisis_analysis.get("crisis_level", "none"),
                        "total_crisis_signals": crisis_analysis.get("total_signals", 0),
                        "escalation_required": crisis_analysis.get("crisis_level") in ["high", "critical"]
                    }
                },
                
                "user_intent_analysis": {
                    "intent_breakdown": enhanced_analysis.get("intent_breakdown", {}),
                    "total_feedback_items": sum((enhanced_analysis.get("intent_breakdown", {})).values()),
                    "complaint_ratio": self._calculate_complaint_ratio(enhanced_analysis.get("intent_breakdown", {})),
                    "dominant_intent": self._get_dominant_intent(enhanced_analysis.get("intent_breakdown", {}))
                },
                
                "priority_issues": {
                    "issues_with_evidence": enhanced_analysis.get("prioritized_issues", []),
                    "total_issues": len(enhanced_analysis.get("prioritized_issues", [])),
                    "high_priority_count": len([i for i in enhanced_analysis.get("prioritized_issues", []) if i.get("priority") == "high"]),
                    "evidence_summary": self._summarize_evidence(enhanced_analysis.get("prioritized_issues", []))
                },
                
                "response_management": {
                    "generated_responses": analysis_result.get("response_drafts", {}),
                    "total_response_templates": len(analysis_result.get("response_drafts", {})),
                    "style_recommendations": self._get_style_recommendations(analysis_result.get("response_drafts", {})),
                    "usage_guidelines": {
                        "official": "Use for high-priority complaints and formal communications",
                        "friendly": "Use for general questions and positive interactions",
                        "tech_support": "Use for technical issues and troubleshooting"
                    },
                    "immediate_response_needed": self._identify_urgent_responses(analysis_result.get("response_drafts", {}))
                },
                
                "early_warning_system": {
                    "crisis_level": crisis_analysis.get("crisis_level", "none"),
                    "active_alerts": crisis_analysis.get("alerts", []),
                    "category_breakdown": crisis_analysis.get("category_breakdown", {}),
                    "affected_reviews": crisis_analysis.get("affected_reviews", []),
                    "monitoring_recommendation": crisis_analysis.get("recommendation", "Continue normal monitoring"),
                    "escalation_timeline": self._get_escalation_timeline(crisis_analysis.get("crisis_level", "none")),
                    "stakeholder_notifications": self._get_required_notifications(crisis_analysis.get("crisis_level", "none"))
                },
                
                "data_sources": {
                    "citations": analysis_result.get("data_citations", []),
                    "evidence_data": enhanced_analysis.get("data_sources", {}),
                    "total_sources": len(analysis_result.get("data_citations", [])),
                    "platform_coverage": self._extract_platform_coverage(analysis_result.get("data_citations", [])),
                    "data_freshness": self._assess_data_freshness(saved_analysis.analysis_date)
                },
                
                "actionable_insights": {
                    "insights": analysis_result.get("actionable_insights", []),
                    "total_insights": len(analysis_result.get("actionable_insights", [])),
                    "by_team": self._group_insights_by_team(analysis_result.get("actionable_insights", [])),
                    "by_priority": self._group_insights_by_priority(analysis_result.get("actionable_insights", [])),
                    "immediate_actions": self._filter_immediate_actions(analysis_result.get("actionable_insights", []))
                },
                
                "key_themes": enhanced_analysis.get("key_themes", {}),
                
                "executive_summary": {
                    "overall_health": self._assess_overall_health(analysis_result["overall_score"], crisis_analysis.get("crisis_level", "none")),
                    "critical_actions_required": self._count_critical_actions(analysis_result.get("actionable_insights", [])),
                    "response_readiness": len(analysis_result.get("response_drafts", {})) > 0,
                    "monitoring_status": "Active" if crisis_analysis.get("total_signals", 0) > 0 else "Normal",
                    "next_review_recommended": self._recommend_next_review(crisis_analysis.get("crisis_level", "none"))
                }
            }
            
            return final_result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "product_name": product_name
            }
        finally:
            db.close()
    
    def _process_crew_results(self, crew_result: Dict, product_name: str, reddit_mentions: List[Dict] = None, trustpilot_reviews: List[Dict] = None) -> Dict:
        """
        Process and structure the results from CrewAI analysis using REAL data only
        
        Args:
            crew_result: Raw results from CrewAI crew
            product_name: Name of the product
            reddit_mentions: Real Reddit data collected
            trustpilot_reviews: Real Trustpilot data collected
            
        Returns:
            Analysis result using only real collected data
        """
        print("🔍 Processing REAL collected data (no mocks)")
        
        # Extract real data from crew results
        analysis_result_text = str(crew_result.get("analysis_result", ""))
        
        # Get actual reviews from reviewers (real data from crew tools)
        app_store_reviews = []
        google_play_reviews = []
        serp_results = []
        
        # Parse actual data from crew result if available
        try:
            import re
            import json
            
            # Try to extract structured data from crew results
            if "app_store" in analysis_result_text.lower():
                # Extract app store reviews from crew result
                pass  # Will be implemented to parse real crew output
            
            if "google_play" in analysis_result_text.lower():
                # Extract google play reviews from crew result  
                pass  # Will be implemented to parse real crew output
                
        except Exception as e:
            print(f"Could not parse crew results: {e}")
        
        # Use REAL collected data
        all_reviews = []
        
        # Add real Reddit mentions if available
        if reddit_mentions:
            print(f"📱 Adding {len(reddit_mentions)} real Reddit mentions")
            all_reviews.extend(reddit_mentions)
        
        # Add real Trustpilot reviews if available  
        if trustpilot_reviews:
            print(f"⭐ Adding {len(trustpilot_reviews)} real Trustpilot reviews")
            all_reviews.extend(trustpilot_reviews)
        
        # For app store data, we need to collect real data
        # Currently the crew tools should be collecting this, but if not available, skip
        real_app_store = self._get_real_app_store_data(product_name)
        real_google_play = self._get_real_google_play_data(product_name)
        real_serp = self._get_real_serp_data(product_name)
        
        if real_app_store:
            print(f"🍎 Adding {len(real_app_store)} real App Store reviews")
            all_reviews.extend(real_app_store)
            
        if real_google_play:
            print(f"🤖 Adding {len(real_google_play)} real Google Play reviews")
            all_reviews.extend(real_google_play)
        
        print(f"📊 Total real data points: {len(all_reviews)}")
        
        if not all_reviews:
            print("⚠️  No real data collected, analysis may be limited")
            return {
                "error": "No real data available for analysis",
                "total_data_points": 0
            }
        
        # Analyze ONLY real data
        comprehensive_analysis = self.analysis_service.analyze_with_evidence(all_reviews, real_serp or [])
        
        # Calculate reputation score using real data
        reputation_score = self.analysis_service.calculate_reputation_score(
            comprehensive_analysis["sentiment_analysis"], real_serp or [], comprehensive_analysis["prioritized_issues"]
        )
        
        # Generate response drafts for top issues
        response_drafts = {}
        for issue in comprehensive_analysis["prioritized_issues"][:3]:  # Top 3 issues
            response_data = self.response_generator.generate_multiple_styles({
                "issue": issue["issue"],
                "intent": "complaint",  # Most issues are complaints
                "priority": issue["priority"],
                "keywords_matched": [issue["issue"]]
            })
            response_drafts[issue["issue"]] = response_data
        
        # Structure real data by platform
        real_data_by_platform = {
            "app_store": real_app_store or [],
            "google_play": real_google_play or [],
            "reddit": reddit_mentions or [],
            "trustpilot": trustpilot_reviews or [],
            "serp": real_serp or []
        }
        
        return {
            "overall_score": reputation_score,
            "sentiment_score": comprehensive_analysis["sentiment_analysis"].get("average_sentiment", 0),
            "enhanced_analysis": comprehensive_analysis,
            "serp_results": real_serp or [],
            "app_store_reviews": real_app_store or [],
            "google_play_reviews": real_google_play or [],
            "reddit_mentions": reddit_mentions or [],
            "trustpilot_reviews": trustpilot_reviews or [],
            "response_drafts": response_drafts,
            "data_citations": self._generate_data_citations(real_data_by_platform, real_serp or []),
            "actionable_insights": self._generate_actionable_insights(comprehensive_analysis),
            "early_warning": comprehensive_analysis["crisis_analysis"]
        }
    
    def _generate_data_citations(self, reviews: Dict, serp_data: List[Dict]) -> List[Dict]:
        """Generate citations for data sources used in analysis"""
        citations = []
        
        # Review sources
        for platform, platform_reviews in reviews.items():
            if platform_reviews:
                citations.append({
                    "source_type": "app_reviews",
                    "platform": platform.replace("_", " ").title(),
                    "sample_count": len(platform_reviews),
                    "date_range": "Last 30 days",
                    "methodology": "Automated sentiment analysis and topic extraction",
                    "sample_reviews": [
                        {
                            "id": review["id"],
                            "snippet": review["content"][:100] + "...",
                            "rating": review["rating"],
                            "date": review["date"]
                        }
                        for review in platform_reviews[:2]  # Show first 2 as examples
                    ]
                })
        
        # SERP sources
        if serp_data:
            citations.append({
                "source_type": "search_results",
                "search_engine": "Google",
                "results_analyzed": len(serp_data),
                "search_queries": list(set(item.get("query", "") for item in serp_data)),
                "methodology": "SERP API analysis for brand mentions and reputation tracking",
                "sample_results": [
                    {
                        "title": item["title"],
                        "source": item["source"],
                        "link": item["link"],
                        "relevance_score": item["position"]
                    }
                    for item in serp_data[:3]  # Show top 3
                ]
            })
        
        return citations
    
    def _generate_actionable_insights(self, analysis: Dict) -> List[Dict]:
        """Generate specific actionable insights from analysis"""
        insights = []
        
        # Crisis-level insights
        crisis_analysis = analysis.get("crisis_analysis", {})
        if crisis_analysis.get("crisis_level") in ["high", "critical"]:
            insights.append({
                "category": "immediate_action",
                "priority": "critical",
                "insight": f"Crisis level detected: {crisis_analysis.get('crisis_level')}",
                "action": crisis_analysis.get("recommendation", ""),
                "timeline": "Immediate",
                "responsible_team": "Crisis Management"
            })
        
        # Intent-based insights
        intent_breakdown = analysis.get("intent_breakdown", {})
        total_intents = sum(intent_breakdown.values())
        
        if total_intents > 0:
            complaint_ratio = intent_breakdown.get("complaint", 0) / total_intents
            if complaint_ratio > 0.4:  # More than 40% complaints
                insights.append({
                    "category": "customer_satisfaction",
                    "priority": "high",
                    "insight": f"{complaint_ratio:.1%} of feedback consists of complaints",
                    "action": "Implement proactive customer outreach and issue resolution process",
                    "timeline": "1-2 weeks",
                    "responsible_team": "Customer Success"
                })
        
        # Issue-specific insights
        prioritized_issues = analysis.get("prioritized_issues", [])
        for issue in prioritized_issues[:3]:  # Top 3 issues
            insights.append({
                "category": "product_improvement",
                "priority": issue.get("priority", "medium"),
                "insight": issue.get("actionable_insight", ""),
                "action": f"Address '{issue['issue']}' mentioned {issue['frequency']} times",
                "timeline": "2-4 weeks" if issue.get("priority") == "high" else "1-2 months",
                "responsible_team": "Product Team" if issue.get("type") == "product_issue" else "Support Team",
                "evidence_count": issue.get("evidence_count", 0)
            })
        
        return insights
    
    def _generate_enhanced_recommendations(self, analysis_result: Dict) -> Dict:
        """Generate enhanced recommendations with response drafts and timelines"""
        recommendations = self._generate_recommendations(analysis_result)
        
        # Add response strategy recommendations
        response_drafts = analysis_result.get("response_drafts", {})
        if response_drafts:
            recommendations["response_strategy"] = {
                "available_styles": ["official", "friendly", "tech_support"],
                "recommended_approach": "Use official style for high-priority issues, friendly for questions",
                "response_templates_generated": len(response_drafts),
                "immediate_responses_needed": [
                    issue for issue in response_drafts.keys() 
                    if any(draft.get("metadata", {}).get("severity") == "high" 
                          for draft in response_drafts[issue].get("responses", {}).values())
                ]
            }
        
        # Add crisis management recommendations
        early_warning = analysis_result.get("early_warning", {})
        if early_warning.get("crisis_level") in ["high", "critical"]:
            recommendations["crisis_management"] = {
                "escalation_required": True,
                "timeline": "Immediate action within 2 hours",
                "communication_plan": "Prepare public statement and social media response",
                "monitoring_frequency": "Every 30 minutes",
                "stakeholder_notification": ["CEO", "PR Team", "Customer Success"]
            }
        
        return recommendations
    
    # Helper functions for unified response (copied from main.py)
    def _get_score_interpretation(self, score: float) -> Dict:
        """Interpret reputation score with actionable context"""
        if score >= 80:
            return {"status": "excellent", "description": "Strong positive reputation", "action": "maintain current practices"}
        elif score >= 60:
            return {"status": "good", "description": "Generally positive with improvement opportunities", "action": "address moderate issues"}
        elif score >= 40:
            return {"status": "concerning", "description": "Mixed reputation with notable issues", "action": "immediate improvement plan needed"}
        else:
            return {"status": "critical", "description": "Significant reputation damage", "action": "urgent intervention required"}

    def _calculate_complaint_ratio(self, intent_breakdown: Dict) -> float:
        """Calculate the ratio of complaints to total feedback"""
        if not intent_breakdown:
            return 0.0
        total = sum(intent_breakdown.values())
        return (intent_breakdown.get("complaint", 0) / total) if total > 0 else 0.0

    def _get_dominant_intent(self, intent_breakdown: Dict) -> str:
        """Identify the most common user intent"""
        if not intent_breakdown:
            return "unknown"
        return max(intent_breakdown.keys(), key=lambda k: intent_breakdown[k])

    def _summarize_evidence(self, issues: List[Dict]) -> Dict:
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

    def _get_style_recommendations(self, response_drafts: Dict) -> List[Dict]:
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

    def _identify_urgent_responses(self, response_drafts: Dict) -> List[str]:
        """Identify issues requiring immediate response"""
        urgent = []
        for issue, drafts in response_drafts.items():
            for style, draft in drafts.get("responses", {}).items():
                if draft.get("metadata", {}).get("severity") == "high":
                    urgent.append(issue)
                    break
        return list(set(urgent))

    def _get_escalation_timeline(self, crisis_level: str) -> str:
        """Get escalation timeline based on crisis level"""
        timelines = {
            "critical": "Immediate (within 1 hour)",
            "high": "Urgent (within 4 hours)", 
            "medium": "Standard (within 24 hours)",
            "low": "Normal (within 3 days)",
            "none": "No escalation needed"
        }
        return timelines.get(crisis_level, "Standard process")

    def _get_required_notifications(self, crisis_level: str) -> List[str]:
        """Get required stakeholder notifications"""
        notifications = {
            "critical": ["CEO", "PR Director", "Crisis Management Team", "Legal Team"],
            "high": ["VP Customer Success", "PR Team", "Support Manager"],
            "medium": ["Customer Success Manager", "Support Team Lead"],
            "low": ["Support Team"],
            "none": []
        }
        return notifications.get(crisis_level, [])

    def _extract_platform_coverage(self, citations: List[Dict]) -> List[str]:
        """Extract platform coverage from citations"""
        platforms = []
        for citation in citations:
            if citation.get("source_type") == "app_reviews":
                platforms.append(citation.get("platform", "Unknown"))
            elif citation.get("source_type") == "search_results":
                platforms.append("Google Search")
        return list(set(platforms))

    def _assess_data_freshness(self, analysis_date) -> str:
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

    def _group_insights_by_team(self, insights: List[Dict]) -> Dict:
        """Group insights by responsible team"""
        by_team = {}
        for insight in insights:
            team = insight.get("responsible_team", "Unassigned")
            if team not in by_team:
                by_team[team] = []
            by_team[team].append(insight)
        return by_team

    def _group_insights_by_priority(self, insights: List[Dict]) -> Dict:
        """Group insights by priority level"""
        by_priority = {}
        for insight in insights:
            priority = insight.get("priority", "medium")
            if priority not in by_priority:
                by_priority[priority] = []
            by_priority[priority].append(insight)
        return by_priority

    def _filter_immediate_actions(self, insights: List[Dict]) -> List[Dict]:
        """Filter insights requiring immediate action"""
        return [insight for insight in insights if insight.get("priority") in ["critical", "high"]]

    def _assess_overall_health(self, score: float, crisis_level: str) -> str:
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

    def _count_critical_actions(self, insights: List[Dict]) -> int:
        """Count insights requiring critical/immediate action"""
        return len([i for i in insights if i.get("priority") in ["critical", "high"]])

    def _recommend_next_review(self, crisis_level: str) -> str:
        """Recommend when next review should occur"""
        recommendations = {
            "critical": "Every 30 minutes",
            "high": "Every 2 hours",
            "medium": "Daily",
            "low": "Weekly",
            "none": "Monthly"
        }
        return recommendations.get(crisis_level, "Weekly")
    
    def _generate_recommendations(self, analysis_result: Dict) -> Dict:
        """
        Generate actionable recommendations based on analysis results
        
        Args:
            analysis_result: Structured analysis result
            
        Returns:
            Dictionary containing recommendations by team
        """
        recommendations = {
            "product_team": [],
            "support_team": [],
            "pr_team": [],
            "immediate_actions": []
        }
        
        overall_score = analysis_result.get("overall_score", 0)
        issues = analysis_result.get("issues_list", [])
        
        # Product team recommendations
        product_issues = [issue for issue in issues if issue.get("type") == "product_issue"]
        if product_issues:
            recommendations["product_team"].extend([
                f"Address {issue['issue']} mentioned {issue['frequency']} times" 
                for issue in product_issues[:3]
            ])
        
        # Support team recommendations
        if overall_score < 60:
            recommendations["support_team"].append("Implement proactive customer outreach program")
            recommendations["support_team"].append("Enhance response time for customer complaints")
        
        # PR team recommendations
        reputation_issues = [issue for issue in issues if issue.get("type") == "reputation_issue"]
        if reputation_issues:
            recommendations["pr_team"].extend([
                "Develop crisis communication strategy",
                "Increase positive content creation and distribution"
            ])
        
        # Immediate actions
        if overall_score < 40:
            recommendations["immediate_actions"].append("Executive review required - critical reputation risk")
        elif overall_score < 60:
            recommendations["immediate_actions"].append("Develop reputation recovery plan within 30 days")
        
        return recommendations
    
    def _collect_reddit_mentions(self, product_name: str) -> List[Dict]:
        """
        Collect Reddit mentions for the product
        
        Args:
            product_name: Name of the product to search for
            
        Returns:
            List of Reddit mentions in mention format
        """
        try:
            print(f"Searching Reddit for {product_name}...")
            
            # Get general Reddit mentions
            mentions = self.reddit_scraper.search_mentions(product_name, max_posts=100, time_filter="month")
            
            # For Uber specifically, search relevant subreddits
            if product_name.lower() in ['uber', 'uber technologies']:
                relevant_subreddits = get_uber_relevant_subreddits()
                subreddit_mentions = self.reddit_scraper.search_specific_subreddits(
                    product_name, relevant_subreddits, max_posts_per_sub=15
                )
                mentions.extend(subreddit_mentions)
            
            print(f"Found {len(mentions)} Reddit mentions")
            return mentions
            
        except Exception as e:
            print(f"Error collecting Reddit mentions: {e}")
            return []
    
    def _collect_trustpilot_reviews(self, product_name: str) -> List[Dict]:
        """
        Collect Trustpilot reviews for the product
        
        Args:
            product_name: Name of the product to search for
            
        Returns:
            List of Trustpilot reviews in mention format
        """
        try:
            print(f"Searching Trustpilot for {product_name}...")
            
            # For Uber specifically, use optimized method
            if product_name.lower() in ['uber', 'uber technologies']:
                reviews = self.trustpilot_scraper.get_uber_trustpilot_reviews(max_reviews=100)
            else:
                reviews = self.trustpilot_scraper.search_company_reviews(product_name, max_reviews=100)
            
            print(f"Found {len(reviews)} Trustpilot reviews")
            return reviews
            
        except Exception as e:
            print(f"Error collecting Trustpilot reviews: {e}")
            return []
    
    
    def _get_real_app_store_data(self, product_name: str) -> List[Dict]:
        """Get real App Store reviews using the review scraper"""
        try:
            from ..parsers.review_scraper import ReviewScraper
            scraper = ReviewScraper()
            
            # For Uber, use known App Store URL, otherwise try to find it
            if product_name.lower() in ['uber', 'uber technologies']:
                app_store_url = "https://apps.apple.com/us/app/uber-request-a-ride/id368677368"
                result = scraper.scrape_app_store_reviews(app_store_url, max_reviews=50)
                if result and 'reviews' in result:
                    print(f"🍎 Successfully collected {len(result['reviews'])} real App Store reviews")
                    return result['reviews']
            
        except Exception as e:
            print(f"⚠️  Could not collect real App Store data: {e}")
        
        return []
    
    def _get_real_google_play_data(self, product_name: str) -> List[Dict]:
        """Get real Google Play reviews using the review scraper"""
        try:
            from ..parsers.review_scraper import ReviewScraper
            scraper = ReviewScraper()
            
            # For Uber, use known Google Play URL, otherwise try to find it
            if product_name.lower() in ['uber', 'uber technologies']:
                google_play_url = "https://play.google.com/store/apps/details?id=com.ubercab"
                result = scraper.scrape_google_play_reviews(google_play_url, max_reviews=50)
                if result and 'reviews' in result:
                    print(f"🤖 Successfully collected {len(result['reviews'])} real Google Play reviews")
                    return result['reviews']
            
        except Exception as e:
            print(f"⚠️  Could not collect real Google Play data: {e}")
        
        return []
    
    def _get_real_serp_data(self, product_name: str) -> List[Dict]:
        """Get real SERP data using the SERP service"""
        try:
            from ..parsers.serp_service import SerpService
            serp_service = SerpService()
            
            # Search for brand reputation information
            results = serp_service.search_brand_reputation(product_name)
            if results:
                key_info = serp_service.extract_key_information(results)
                print(f"🔍 Successfully collected {len(results)} real SERP results")
                return results
            
        except Exception as e:
            print(f"⚠️  Could not collect real SERP data: {e}")
        
        return []