# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Database Management
- **Initialize database**: `python -c "from app.database import init_db; init_db()"`
- **Run migrations**: `alembic upgrade head`
- **Create migration**: `alembic revision --autogenerate -m "description"`
- **Check migration status**: `alembic current`

### Running the Application
- **FastAPI server**: `uvicorn app.main:app --reload` (development)
- **Console analysis (interactive)**: `python console_runner.py --interactive`
- **Console analysis (CLI)**: `python console_runner.py --product "Product Name"`
- **Demo analysis**: `python demo_analysis.py`

### Data Processing (REFACTORED - Unified Commands)
- **Run all parsers and analyze**: `python commands/run_all_parsers.py --product "Product Name" --max-items 50`
- **Legacy data collection**: `python commands/unified_data_processor.py --mode collect --product "Product Name"`
- **Update sentiment classifications**: `python commands/unified_data_processor.py --mode sentiment --filter all`
- **Update only neutral sentiments**: `python commands/unified_data_processor.py --mode sentiment --filter neutral`
- **Fix misclassified sentiments**: `python commands/unified_data_processor.py --mode sentiment --filter misclassified`
- **System status**: `python commands/unified_data_processor.py --mode status`

### AI-Powered Classification (Gemini API)
- **Classify user mentions with Gemini**: `python commands/classify_mentions.py` (classifies unprocessed mentions)
- **Classify all mentions**: `python commands/classify_mentions.py --all`
- **Classify specific product**: `python commands/classify_mentions.py --product-id 1`
- **Test classification**: `python commands/classify_mentions.py --test`
- **Custom batch size**: `python commands/classify_mentions.py --batch-size 20`

### Background Task Scheduler
- **Enable scheduler**: Set environment variable `ENV_RUN_SCHEDULER=true`
- **Daily data parsing**: Runs automatically at 09:00 (Europe/Kiev timezone)
- **Daily AI analysis**: Runs automatically at 10:00 (Europe/Kiev timezone)
- **Check scheduler status**: GET `/scheduler/status`
- **Manual data parsing**: POST `/scheduler/manual/parse`
- **Manual AI analysis**: POST `/scheduler/manual/analyze`

### Dependencies
- **Install requirements**: `pip install -r requirements.txt`
- **Activate virtual environment**: `source venv/bin/activate` (if using venv)

### Testing & Development
- **Health check**: GET `/health` endpoint or check if required environment variables are set
- **Sample data**: POST `/mentions/sample/{product_id}` to create test mentions

## Architecture Overview

This is a **Brand Reputation Analysis System** built with:
- **FastAPI** for REST API endpoints
- **CrewAI** for multi-agent AI analysis
- **SQLAlchemy** with SQLite for data persistence
- **Alembic** for database migrations

## Refactored Code Structure

The codebase has been reorganized for better maintainability:

```
app/
├── parsers/           # Data collection and scraping services
│   ├── reddit_scraper.py
│   ├── trustpilot_scraper.py
│   ├── review_scraper.py
│   └── serp_service.py
├── core/              # Core business logic services
│   ├── analysis_service.py
│   ├── reputation_service.py
│   ├── mention_service.py
│   └── response_generator.py
├── api/               # FastAPI endpoints and handlers
│   └── main.py
├── database/          # Models and database configuration
│   ├── models.py
│   └── database.py
├── agents/            # AI agents (CrewAI)
│   └── crew_agents.py
└── utils/             # Utility functions (future use)

commands/              # Console commands
├── run_all_parsers.py          # NEW: Unified parser execution
├── unified_data_processor.py   # Legacy: Data processing
└── console_runner.py           # Interactive analysis
```

### Core Components

1. **Multi-Agent System** (`app/agents/crew_agents.py`):
   - `DataCollector`: Gathers data from SERP API and app stores
   - `ReputationAnalyst`: Performs sentiment and topic analysis
   - `InsightGenerator`: Generates business insights and recommendations

2. **Service Layer** (`app/services/`):
   - `ReputationService`: Main orchestration service
   - `AnalysisService`: Sentiment analysis and topic extraction
   - `ResponseGenerator`: Generates response templates in multiple styles
   - `MentionService`: Manages user mentions and sample data
   - `SerpService`: Google SERP API integration
   - `ReviewScraper`: App store review collection

3. **Data Models** (`app/models.py`):
   - `Product`: Stores product information and app store URLs
   - `ReputationAnalysis`: Comprehensive analysis results with enhanced fields
   - `UserMention`: Individual user mentions from various platforms

4. **API Structure** (`app/main.py`):
   - `/analyze` - Complete brand reputation analysis
   - `/products` - Product management
   - `/analysis/{product_id}` - Unified analysis results
   - `/mentions` - Paginated user mentions with filtering
   - `/health` - System health check

### Key Analysis Features

- **Unified Response Architecture**: Single API call returns complete analysis
- **Intent Classification**: Complaint, question, recommendation, neutral
- **Crisis Detection**: Early warning system with escalation protocols
- **Multi-Style Responses**: Official, friendly, tech support templates
- **Evidence-Based Insights**: Data source citations and supporting evidence
- **Team-Specific Actions**: Prioritized recommendations by responsibility

### Data Flow

1. **Data Collection**: Agents gather from SERP API and app stores using external APIs
2. **Analysis**: Sentiment analysis, intent classification, topic extraction
3. **Scoring**: Weighted reputation score calculation (0-100)
4. **Response Generation**: Multi-style response templates for different scenarios
5. **Crisis Monitoring**: Early warning system with escalation timelines
6. **Storage**: Comprehensive results stored with enhanced metadata

## Required Environment Variables

Create `.env` file with:
```
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here
DATABASE_URL=sqlite:///./main.db
```

## Model Configuration

The system uses **GPT-3.5-turbo** for all CrewAI agents to avoid rate limits. This provides:
- Higher rate limits compared to GPT-4o-mini
- Good performance for sentiment analysis and reputation tasks
- Cost-effective processing for large data volumes

## Working with the Codebase

### Adding New Data Sources
1. Create service class in `app/services/`
2. Implement data collection logic
3. Add to relevant CrewAI agents
4. Update analysis workflow in `ReputationService`

### Extending Analysis Features
1. Modify analysis models in `app/models.py` (add migrations)
2. Update service logic in `app/services/analysis_service.py`
3. Enhance unified response structure in `app/main.py`
4. Test with console runner or API endpoints

### Database Changes
Always use Alembic for schema changes:
1. Modify models in `app/models.py`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Apply migration: `alembic upgrade head`

## Important Notes

- **Database**: SQLite file `main.db` is created automatically
- **Dependencies**: Chrome/Chromium required for Selenium web scraping
- **API Integration**: Requires OpenAI and Serper API keys
- **CrewAI**: Multi-agent system handles complex analysis workflows
- **Response Management**: System generates multiple response styles for different scenarios
- **Crisis Detection**: Built-in early warning system for reputation issues