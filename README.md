# Brand Reputation Analysis System

A comprehensive AI-powered system for analyzing brand reputation using Gemini AI, sentiment analysis, and multi-source data collection.

## Features

- **AI-Powered Classification**: Uses Google Gemini 2.5 Flash for fast and accurate mention classification
- **Multi-Agent Analysis**: Uses CrewAI with specialized agents for data collection, reputation analysis, and insight generation
- **Google SERP Integration**: Searches for brand mentions using Serper API
- **App Store Review Analysis**: Scrapes and analyzes reviews from App Store and Google Play
- **Advanced Sentiment Analysis**: Gemini-powered sentiment, intent, and priority classification
- **Background Task Scheduler**: Automated daily data collection and analysis with APScheduler
- **Reputation Scoring**: Calculates comprehensive reputation scores (0-100) with weighted algorithms
- **Real-time Analytics**: Dashboard with sentiment trends, topic analysis, and alert management
- **Actionable Insights**: Generates prioritized recommendations for Product, Support, and PR teams
- **RESTful API**: Complete FastAPI backend with comprehensive endpoints
- **Alert System**: Telegram and Email notifications for critical mentions

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Edit `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SERPER_API_KEY=your_serper_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   DATABASE_URL=sqlite:///./main.db
   ENV_RUN_SCHEDULER=true
   ```

3. **Initialize Database**:
   ```bash
   python -c "from app.database import init_db; init_db()"
   alembic upgrade head
   ```

4. **Start the Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Usage

### FastAPI Server
```bash
# Development server with auto-reload
uvicorn app.main:app --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Interactive Console Mode
```bash
python commands/console_runner.py --interactive
```

### Command Line Analysis
```bash
# Basic analysis
python commands/console_runner.py --product "Uber"

# With app store URLs
python commands/console_runner.py --product "Uber" \
  --app-store "https://apps.apple.com/us/app/uber-request-a-ride/id368677368" \
  --google-play "https://play.google.com/store/apps/details?id=com.ubercab&hl=en"
```

### Data Collection and Processing
```bash
# Run all parsers and collect data
python commands/run_all_parsers.py --product "Uber" --max-items 50

# Classify user mentions with Gemini AI
python commands/classify_mentions.py --batch-size 10

# Test Gemini classification
python commands/classify_mentions.py --test

# Legacy unified data processor
python commands/unified_data_processor.py --mode collect --product "Uber"
```

## Example Analysis Output

```
📊 REPUTATION ANALYSIS REPORT
Product: Uber
Analysis Date: 2024-01-01T00:00:00
Analysis ID: 1

📈 REPUTATION SCORES
Overall Reputation Score: 72.5/100
Sentiment Score: 0.15 (-1 to 1)
🟡 Status: Good reputation with room for improvement

🔍 KEY INSIGHTS
Sentiment Distribution:
  Positive: 45.0%
  Negative: 30.0%
  Neutral: 25.0%
Total Reviews Analyzed: 50

⚠️  PRIORITY ISSUES
1. 🔴 service (mentioned 8 times - high priority)
2. 🟡 app (mentioned 5 times - medium priority)

💡 RECOMMENDATIONS
🚨 Immediate Actions:
  • Develop reputation recovery plan within 30 days

🛠️  Product Team:
  • Address service mentioned 8 times
  • Address app mentioned 5 times

🎧 Support Team:
  • Implement proactive customer outreach program
  • Enhance response time for customer complaints
```

## API Endpoints

### Core Analysis
- `POST /analyze` - Complete brand reputation analysis
- `GET /analysis/{product_id}` - Get unified analysis results
- `GET /dashboard` - Dashboard data with reputation scores and trends
- `GET /analytics` - Analytics data with realistic trend calculations

### Data Management
- `GET /products` - List all products
- `POST /products` - Create new product
- `GET /mentions` - Get user mentions with filtering (supports multiple platforms as list)
- `POST /mentions/sample/{product_id}` - Create sample mentions for testing

### Background Tasks
- `GET /scheduler/status` - Check scheduler status
- `POST /scheduler/trigger/parsing` - Manually trigger data parsing
- `POST /scheduler/trigger/analysis` - Manually trigger AI analysis

### System
- `GET /health` - Health check endpoint

## Architecture

### Core Components

1. **Database Models** (`app/database/models.py`):
   - `Product`: Stores product information and app store URLs
   - `ReputationAnalysis`: Comprehensive analysis results with enhanced fields
   - `UserMention`: Individual user mentions with AI classification

2. **Parsers and Data Collection** (`app/parsers/`):
   - `SerpService`: Google SERP API integration via Serper
   - `ReviewScraper`: App store review scraping
   - `RedditScraper`: Reddit mentions and discussions
   - `TrustpilotScraper`: Trustpilot review collection

3. **Core Services** (`app/core/`):
   - `AnalysisService`: Sentiment analysis and topic extraction
   - `ReputationService`: Main orchestration service
   - `MentionService`: User mention management
   - `ResponseGenerator`: AI-powered response templates

4. **AI Classification**:
   - **Gemini 2.5 Flash**: Fast AI classification for mentions
   - **CrewAI Agents**: Multi-agent analysis workflow
   - **Background Scheduler**: Automated daily processing with APScheduler

5. **Database**:
   - SQLite database with Alembic migrations
   - Stores products, analysis history, and user mentions

### Analysis Workflow

1. **Data Collection**: Automated parsers gather data from SERP API, app stores, Reddit, and Trustpilot
2. **AI Classification**: Gemini 2.5 Flash classifies mentions for sentiment, intent, priority, and topics
3. **Analysis**: CrewAI agents perform comprehensive reputation analysis and insight generation
4. **Scoring**: Calculate weighted reputation scores with realistic trend calculations
5. **Insights**: Generate prioritized recommendations by team (Product, Support, PR)
6. **Storage**: Save results to database with comprehensive metadata
7. **Automation**: Background scheduler runs daily data collection and analysis tasks

### Background Task Scheduler

The system includes an automated background task scheduler powered by APScheduler:

**Daily Tasks**:
- **09:00 Europe/Kiev**: Automated data parsing from all sources
- **10:00 Europe/Kiev**: AI-powered analysis and classification

**Configuration**:
- Set `ENV_RUN_SCHEDULER=true` in environment variables to enable
- Timezone: Europe/Kiev
- Manual triggers available via API endpoints
- Comprehensive logging and error handling

**Scheduler Commands**:
```bash
# Check scheduler status
curl GET http://localhost:8000/scheduler/status

# Manually trigger parsing
curl -X POST http://localhost:8000/scheduler/trigger/parsing

# Manually trigger analysis  
curl -X POST http://localhost:8000/scheduler/trigger/analysis
```

## API Integration

### Google SERP (Serper)
- Searches for brand mentions and reputation-related content
- Configurable time periods and locations
- Extracts title, snippet, and source information

### Google Gemini 2.5 Flash
- Fast and accurate AI classification for user mentions
- Analyzes sentiment, intent, priority, confidence scores
- Extracts keywords and topics automatically
- 10x faster than CrewAI for mention classification

### App Store Reviews
- App Store: Uses iTunes RSS API for review data
- Google Play: Web scraping with Selenium for review extraction
- Configurable review limits and filtering

### Additional Data Sources
- **Reddit**: Searches for brand discussions and mentions
- **Trustpilot**: Collects customer reviews and ratings
- **Social Media**: Extensible framework for additional platforms

## Scoring Algorithm

The reputation score (0-100) is calculated using a weighted algorithm:

### Current Score Calculation
- **Priority-weighted mentions**: Critical (-10), High (-5), Medium (-2), Low (+1)
- **Intent classification**: Complaints have higher negative impact
- **Confidence weighting**: Higher confidence scores increase impact
- **Platform weighting**: Different platforms have different impact levels

### Trend Calculation  
- **Realistic caps**: Maximum 300% increase for small previous values, 500% absolute maximum
- **Period comparison**: Current vs previous period with proper edge case handling
- **Growth/decline indicators**: Clear positive/negative trend visualization

### Alert Thresholds
- **Critical**: Score below 30 or 5+ critical mentions
- **Warning**: Score below 50 or 10+ high-priority mentions
- **Good**: Score above 70 with manageable issue volume

## AI-Powered Classification

### Gemini 2.5 Flash Integration
The system uses Google's Gemini 2.5 Flash model for fast and accurate mention classification:

**Classification Categories**:
- **Sentiment**: positive, negative, neutral
- **Intent**: complaint, question, recommendation, neutral  
- **Priority**: critical, high, medium, low
- **Confidence Score**: 0.0-1.0 indicating classification confidence
- **Keywords**: 3-7 relevant terms extracted from content
- **Topics**: 2-4 main themes (technical_issues, customer_service, billing, etc.)

**Usage Examples**:
```bash
# Classify all unprocessed mentions
python commands/classify_mentions.py

# Process specific batch size
python commands/classify_mentions.py --batch-size 20

# Test classification with sample content
python commands/classify_mentions.py --test

# Process all mentions (including already classified)
python commands/classify_mentions.py --all
```

**Benefits**:
- 10x faster than CrewAI-based classification
- Consistent and accurate sentiment analysis
- Automated priority assignment for triage
- Keyword extraction for topic clustering
- Confidence scoring for quality assessment

## Extending the System

### Adding New Data Sources
1. Create a new tool class inheriting from `BaseTool`
2. Implement data collection logic
3. Add the tool to relevant agents

### Custom Analysis Models
1. Extend `AnalysisService` with new analysis methods
2. Update the scoring algorithm in `calculate_reputation_score`
3. Modify insight generation in `ReputationService`

### New Agent Types
1. Create new agent classes in `crew_agents.py`
2. Define specialized roles and goals
3. Add to the crew workflow

## Requirements

- Python 3.8+
- **API Keys Required**:
  - OpenAI API access (for CrewAI agents)
  - Google Gemini API access (for fast mention classification)  
  - Serper API access (for Google SERP data)
- Chrome/Chromium for web scraping (Selenium)
- APScheduler 3.10.4+ (for background task automation)

## License

This project is part of a hackathon implementation for educational purposes.