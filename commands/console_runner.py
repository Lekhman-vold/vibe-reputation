#!/usr/bin/env python3
"""
Console interface for running brand reputation analysis
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to the Python path to access app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.reputation_service import ReputationService
from app.database.database import init_db

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("  BRAND REPUTATION ANALYSIS SYSTEM")
    print("  Powered by CrewAI")
    print("=" * 60)
    print()

def print_analysis_result(result: dict):
    """Print formatted unified analysis results"""
    if not result.get("success"):
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        return
    
    print("✅ Analysis completed successfully!")
    print()
    
    # Basic info
    print(f"📊 UNIFIED REPUTATION ANALYSIS REPORT")
    print(f"Product: {result['product_name']}")
    print(f"Analysis Date: {result['analysis_date']}")
    print(f"Analysis ID: {result['analysis_id']}")
    print()
    
    # Reputation Metrics (consolidated view)
    metrics = result.get('reputation_metrics', {})
    print("📈 REPUTATION METRICS")
    print(f"Overall Score: {metrics.get('overall_score', 0):.1f}/100")
    print(f"Sentiment Score: {metrics.get('sentiment_score', 0):.2f} (-1 to 1)")
    
    interpretation = metrics.get('score_interpretation', {})
    status_emoji = {"excellent": "🟢", "good": "🟡", "concerning": "🟠", "critical": "🔴"}.get(interpretation.get('status'), "⚪")
    print(f"{status_emoji} Status: {interpretation.get('description', 'Unknown')}")
    print(f"Recommended Action: {interpretation.get('action', 'No action specified')}")
    print()
    
    # Crisis Monitoring
    early_warning = result.get('early_warning_system', {})
    crisis_level = early_warning.get('crisis_level', 'none')
    print("🚨 EARLY WARNING SYSTEM")
    crisis_emoji = {"critical": "🚨", "high": "⚠️", "medium": "🟡", "low": "🔵", "none": "🟢"}.get(crisis_level, "⚪")
    print(f"{crisis_emoji} Crisis Level: {crisis_level.upper()}")
    
    alerts = early_warning.get('active_alerts', [])
    if alerts:
        print("Active Alerts:")
        for alert in alerts:
            print(f"  ⚠️  {alert.get('category', 'Unknown')}: {alert.get('message', 'No details')}")
    else:
        print("✅ No active crisis signals detected")
    
    escalation = early_warning.get('escalation_timeline', 'No escalation needed')
    print(f"Escalation Timeline: {escalation}")
    print()
    
    # User Intent Analysis
    intent_analysis = result.get('user_intent_analysis', {})
    intent_breakdown = intent_analysis.get('intent_breakdown', {})
    print("🎯 USER INTENT ANALYSIS")
    total_feedback = intent_analysis.get('total_feedback_items', 0)
    complaint_ratio = intent_analysis.get('complaint_ratio', 0)
    dominant_intent = intent_analysis.get('dominant_intent', 'unknown')
    
    if total_feedback > 0:
        print(f"Total Feedback Items: {total_feedback}")
        print(f"Complaint Ratio: {complaint_ratio:.1%}")
        print(f"Dominant Intent: {dominant_intent.title()}")
        print("Intent Breakdown:")
        for intent, count in intent_breakdown.items():
            percentage = (count / total_feedback * 100) if total_feedback > 0 else 0
            print(f"  {intent.title()}: {count} ({percentage:.1f}%)")
    print()
    
    # Priority Issues with Evidence
    priority_issues = result.get('priority_issues', {})
    issues = priority_issues.get('issues_with_evidence', [])
    print("🔍 PRIORITY ISSUES WITH EVIDENCE")
    print(f"Total Issues: {priority_issues.get('total_issues', 0)}")
    print(f"High Priority: {priority_issues.get('high_priority_count', 0)}")
    
    evidence_summary = priority_issues.get('evidence_summary', {})
    print(f"Total Evidence: {evidence_summary.get('total_evidence_pieces', 0)} pieces")
    
    for i, issue in enumerate(issues[:3], 1):  # Show top 3 issues
        priority_emoji = "🔴" if issue.get('priority') == 'high' else "🟡"
        print(f"{i}. {priority_emoji} {issue.get('issue', 'N/A')} "
              f"(mentioned {issue.get('frequency', 0)} times)")
        print(f"   Evidence: {issue.get('evidence_count', 0)} supporting sources")
        print(f"   Insight: {issue.get('actionable_insight', 'No insight available')}")
    print()
    
    # Response Management
    response_mgmt = result.get('response_management', {})
    print("💬 RESPONSE MANAGEMENT")
    templates_count = response_mgmt.get('total_response_templates', 0)
    print(f"Generated Response Templates: {templates_count}")
    
    urgent_responses = response_mgmt.get('immediate_response_needed', [])
    if urgent_responses:
        print("🚨 Immediate Response Needed:")
        for issue in urgent_responses:
            print(f"  • {issue}")
    
    style_recs = response_mgmt.get('style_recommendations', [])
    if style_recs:
        print("Style Recommendations:")
        for rec in style_recs[:3]:
            print(f"  • {rec['issue']}: Use {rec['recommended_style']} style")
    print()
    
    # Data Sources
    data_sources = result.get('data_sources', {})
    print("📚 DATA SOURCES & EVIDENCE")
    print(f"Total Sources: {data_sources.get('total_sources', 0)}")
    platform_coverage = data_sources.get('platform_coverage', [])
    print(f"Platform Coverage: {', '.join(platform_coverage)}")
    print(f"Data Freshness: {data_sources.get('data_freshness', 'Unknown')}")
    print()
    
    # Actionable Insights
    actionable = result.get('actionable_insights', {})
    insights = actionable.get('insights', [])
    print("💡 ACTIONABLE INSIGHTS")
    print(f"Total Insights: {actionable.get('total_insights', 0)}")
    
    immediate_actions = actionable.get('immediate_actions', [])
    if immediate_actions:
        print("🚨 Immediate Actions Required:")
        for action in immediate_actions:
            priority_emoji = "🔴" if action.get('priority') == 'critical' else "🟡"
            print(f"  {priority_emoji} {action.get('action', 'Unknown action')}")
            print(f"     Team: {action.get('responsible_team', 'Unassigned')} | Timeline: {action.get('timeline', 'TBD')}")
    
    by_team = actionable.get('by_team', {})
    if by_team:
        print("By Team Assignment:")
        for team, team_insights in list(by_team.items())[:3]:  # Show top 3 teams
            print(f"  🎯 {team}: {len(team_insights)} action(s)")
    print()
    
    # Executive Summary
    exec_summary = result.get('executive_summary', {})
    print("📋 EXECUTIVE SUMMARY")
    print(f"Overall Health: {exec_summary.get('overall_health', 'Unknown')}")
    print(f"Critical Actions Required: {exec_summary.get('critical_actions_required', 0)}")
    print(f"Response Readiness: {'✅ Ready' if exec_summary.get('response_readiness') else '❌ Not Ready'}")
    print(f"Monitoring Status: {exec_summary.get('monitoring_status', 'Unknown')}")
    print(f"Next Review: {exec_summary.get('next_review_recommended', 'Not specified')}")
    print()
    
    print("🎯 UNIFIED NEXT STEPS:")
    print("1. Address immediate crisis alerts and high-priority issues")
    print("2. Deploy appropriate response templates based on style recommendations")
    print("3. Execute team-specific actionable insights within timelines")
    print("4. Monitor early warning system for escalation triggers")
    print("5. Review comprehensive evidence and update strategies accordingly")
    print()

def run_analysis():
    """Interactive mode for running analysis"""
    print_banner()
    
    # Initialize database
    print("Initializing database...")
    init_db()
    print("✅ Database initialized")
    print()
    
    # Get product information
    print("🔍 PRODUCT INFORMATION")
    product_name = input("Enter product/brand name (e.g., Uber): ").strip()
    
    if not product_name:
        print("❌ Product name is required!")
        return
    
    print("\n📱 APP STORE URLS (Optional)")
    app_store_url = input("App Store URL (press Enter to skip): ").strip() or None
    google_play_url = input("Google Play URL (press Enter to skip): ").strip() or None
    
    print(f"\n🚀 Starting analysis for '{product_name}'...")
    print("This may take several minutes...")
    print()
    
    # Run analysis
    reputation_service = ReputationService()
    
    try:
        result = reputation_service.analyze_product_reputation(
            product_name=product_name,
            app_store_url=app_store_url,
            google_play_url=google_play_url
        )
        
        print_analysis_result(result)
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return

def main():
    """Main entry point"""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Brand Reputation Analysis System')
    parser.add_argument('--product', '-p', help='Product name to analyze')
    parser.add_argument('--app-store', help='App Store URL')
    parser.add_argument('--google-play', help='Google Play URL')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='Run in interactive mode')
    
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
    
    if args.interactive or not args.product:
        run_analysis()
    else:
        # Command line mode
        print_banner()
        print("Initializing database...")
        init_db()
        print("✅ Database initialized")
        print()
        
        print(f"🚀 Starting analysis for '{args.product}'...")
        
        reputation_service = ReputationService()
        result = reputation_service.analyze_product_reputation(
            product_name=args.product,
            app_store_url=args.app_store,
            google_play_url=args.google_play
        )
        
        print_analysis_result(result)

if __name__ == "__main__":
    main()