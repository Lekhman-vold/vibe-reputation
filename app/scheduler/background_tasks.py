"""
Background task scheduler for automated data parsing and AI analysis
Uses APScheduler with CronTrigger for daily execution
"""

import os
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import Product
from ..core.reputation_service import ReputationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone='Europe/Kiev')
        
        # Add event listeners for job monitoring
        scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
        scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
    
    return scheduler


def job_executed_listener(event):
    """Log successful job execution"""
    logger.info(f"Job {event.job_id} executed successfully at {datetime.now()}")


def job_error_listener(event):
    """Log job execution errors"""
    logger.error(f"Job {event.job_id} failed: {event.exception}")


async def parse_data_task():
    """
    Daily data parsing task - collects new mentions from all configured sources
    """
    logger.info("🔄 Starting daily data parsing task...")
    
    try:
        # Get all products from database
        db = next(get_db())
        products = db.query(Product).all()
        
        if not products:
            logger.warning("No products found in database. Skipping data parsing.")
            return
        
        logger.info(f"Found {len(products)} products to process")
        
        for product in products:
            try:
                logger.info(f"🔍 Parsing data for product: {product.name}")
                
                # Here you would call your existing parser commands
                # For now, we'll use a placeholder that simulates the parsing
                await simulate_data_parsing(product)
                
                logger.info(f"✅ Data parsing completed for {product.name}")
                
            except Exception as e:
                logger.error(f"❌ Error parsing data for {product.name}: {str(e)}")
                continue
        
        logger.info("🎉 Daily data parsing task completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Critical error in data parsing task: {str(e)}")
        raise
    finally:
        db.close()


async def simulate_data_parsing(product: Product):
    """
    Simulate data parsing - replace this with actual parser execution
    
    In production, this would execute something like:
    - subprocess.run(['python', 'commands/run_all_parsers.py', '--product', product.name])
    - Or call the parser functions directly
    """
    # Simulate processing time
    await asyncio.sleep(2)
    
    # Log what would be done
    logger.info(f"  📊 Collecting mentions from Reddit, App Stores, SERP...")
    logger.info(f"  🔗 App Store URL: {product.app_store_url or 'Not configured'}")
    logger.info(f"  🔗 Google Play URL: {product.google_play_url or 'Not configured'}")
    logger.info(f"  🏷️  Brand Keywords: {product.brand_keywords or 'Default keywords'}")


async def run_ai_analysis_task():
    """
    Daily AI analysis task - processes collected data and updates classifications
    """
    logger.info("🤖 Starting daily AI analysis task...")
    
    try:
        # Get all products from database
        db = next(get_db())
        products = db.query(Product).all()
        
        if not products:
            logger.warning("No products found in database. Skipping AI analysis.")
            return
        
        logger.info(f"Found {len(products)} products to analyze")
        
        for product in products:
            try:
                logger.info(f"🧠 Running AI analysis for product: {product.name}")
                
                # Run reputation analysis
                reputation_service = ReputationService()
                
                result = reputation_service.analyze_product_reputation(
                    product_name=product.name,
                    app_store_url=product.app_store_url,
                    google_play_url=product.google_play_url
                )
                
                if result.get("success"):
                    logger.info(f"✅ AI analysis completed for {product.name}")
                    logger.info(f"  📊 Overall Score: {result.get('overall_score', 'N/A')}")
                    logger.info(f"  💭 Total Issues: {len(result.get('issues_list', []))}")
                else:
                    logger.error(f"❌ AI analysis failed for {product.name}: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"❌ Error in AI analysis for {product.name}: {str(e)}")
                continue
        
        # After analysis, run classification on any unprocessed mentions
        await run_classification_task()
        
        logger.info("🎉 Daily AI analysis task completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Critical error in AI analysis task: {str(e)}")
        raise
    finally:
        db.close()


async def run_classification_task():
    """
    Run mention classification using Gemini API for any unprocessed mentions
    """
    logger.info("🏷️  Starting mention classification task...")
    
    try:
        # Import classification function
        import subprocess
        import sys
        
        # Get the path to the classification script
        script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'commands', 'classify_mentions.py')
        
        # Run classification command
        result = subprocess.run([
            sys.executable, script_path, '--batch-size', '20'
        ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
        
        if result.returncode == 0:
            logger.info("✅ Mention classification completed successfully")
            logger.info(f"  📝 Output: {result.stdout.strip()}")
        else:
            logger.error(f"❌ Mention classification failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Mention classification timed out after 30 minutes")
    except Exception as e:
        logger.error(f"❌ Error in mention classification: {str(e)}")


def start_scheduler():
    """
    Initialize and start the background task scheduler
    """
    # Check environment flag
    run_scheduler = os.getenv("ENV_RUN_SCHEDULER", "false").lower() == "true"
    
    if not run_scheduler:
        logger.info("📅 Scheduler disabled (ENV_RUN_SCHEDULER not set to true)")
        return
    
    logger.info("📅 Starting background task scheduler...")
    
    scheduler = get_scheduler()
    
    # Add daily data parsing job (runs at 9:00 AM Kiev time)
    scheduler.add_job(
        parse_data_task,
        CronTrigger(hour=9, minute=0, second=0, timezone='Europe/Kiev'),
        id='daily_data_parsing',
        name='Daily Data Parsing',
        replace_existing=True,
        max_instances=1  # Prevent overlapping executions
    )
    
    # Add daily AI analysis job (runs at 10:00 AM Kiev time, after data parsing)
    scheduler.add_job(
        run_ai_analysis_task,
        CronTrigger(hour=10, minute=0, second=0, timezone='Europe/Kiev'),
        id='daily_ai_analysis',
        name='Daily AI Analysis',
        replace_existing=True,
        max_instances=1  # Prevent overlapping executions
    )
    
    # Add a test job that runs every minute (for testing - remove in production)
    # scheduler.add_job(
    #     test_job,
    #     CronTrigger(minute='*', timezone='Europe/Kiev'),
    #     id='test_job',
    #     name='Test Job (Every Minute)',
    #     replace_existing=True
    # )
    
    # Start the scheduler
    scheduler.start()
    
    logger.info("✅ Background task scheduler started successfully")
    logger.info("📋 Scheduled jobs:")
    logger.info("  🔄 Data Parsing: Daily at 09:00 (Europe/Kiev)")
    logger.info("  🤖 AI Analysis: Daily at 10:00 (Europe/Kiev)")


async def test_job():
    """Test job for debugging scheduler functionality"""
    logger.info(f"🧪 Test job executed at {datetime.now()}")


def stop_scheduler():
    """
    Stop the background task scheduler
    """
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("📅 Background task scheduler stopped")


def get_scheduler_status():
    """
    Get current scheduler status and job information
    """
    global scheduler
    
    if not scheduler:
        return {
            "running": False,
            "jobs": [],
            "message": "Scheduler not initialized"
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run,
            "trigger": str(job.trigger),
            "max_instances": job.max_instances
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs,
        "timezone": "Europe/Kiev",
        "env_flag": os.getenv("ENV_RUN_SCHEDULER", "false")
    }


# Manual execution functions for testing
async def run_manual_parsing():
    """Manually trigger data parsing (for testing)"""
    logger.info("🔧 Manual data parsing triggered")
    await parse_data_task()


async def run_manual_analysis():
    """Manually trigger AI analysis (for testing)"""
    logger.info("🔧 Manual AI analysis triggered")
    await run_ai_analysis_task()