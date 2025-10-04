import re
from typing import Dict, List, Tuple
from textblob import TextBlob
from collections import Counter, defaultdict
import numpy as np
from datetime import datetime, timedelta
from crewai import Agent, Task, Crew
import os

class AnalysisService:
    def __init__(self):
        self.negative_keywords = [
            'terrible', 'awful', 'horrible', 'bad', 'worst', 'hate', 'disgusting',
            'useless', 'broken', 'failed', 'disappointed', 'frustrated', 'annoying',
            'slow', 'crash', 'bug', 'issue', 'problem', 'complaint', 'refund'
        ]
        
        self.positive_keywords = [
            'excellent', 'amazing', 'great', 'awesome', 'fantastic', 'perfect',
            'love', 'wonderful', 'outstanding', 'brilliant', 'impressive',
            'helpful', 'easy', 'fast', 'reliable', 'smooth', 'convenient'
        ]
        
        # Intent classification patterns
        self.intent_patterns = {
            'complaint': [
                'not working', 'doesnt work', 'broken', 'terrible', 'awful', 'worst',
                'hate', 'disappointed', 'frustrated', 'annoying', 'useless', 'horrible',
                'crash', 'bug', 'issue', 'problem', 'error', 'fail', 'refund'
            ],
            'question': [
                'how to', 'how do', 'can i', 'is it possible', 'help', 'support',
                'what is', 'where is', 'when will', 'why does', 'tutorial', 'guide'
            ],
            'recommendation': [
                'recommend', 'suggest', 'try', 'should use', 'better', 'alternative',
                'prefer', 'switch to', 'instead of', 'upgrade'
            ],
            'neutral_mention': [
                'using', 'experience with', 'tried', 'found', 'noticed', 'seems',
                'appears', 'looks like', 'basically', 'generally'
            ]
        }
        
        # Crisis keywords for early warning
        self.crisis_keywords = {
            'technical': ['crash', 'not working', 'broken', 'down', 'offline', 'error'],
            'payment': ['charged', 'billing', 'payment', 'money', 'refund', 'overcharge'],
            'security': ['hacked', 'security', 'privacy', 'data breach', 'stolen'],
            'service': ['rude', 'unprofessional', 'terrible service', 'bad support']
        }
        
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of text using OpenAI via CrewAI for enhanced accuracy
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        # Try OpenAI-powered analysis first (if API key available)
        if os.getenv("OPENAI_API_KEY"):
            try:
                openai_result = self._analyze_sentiment_with_openai(text)
                if openai_result:
                    return openai_result
            except Exception as e:
                print(f"OpenAI sentiment analysis failed, falling back to TextBlob: {e}")
        
        # Fallback to enhanced TextBlob analysis
        blob = TextBlob(text)
        base_polarity = blob.sentiment.polarity
        
        # Apply context-aware adjustments
        adjusted_polarity = self._apply_context_adjustments(text, base_polarity)
        
        return {
            "polarity": adjusted_polarity,  # -1 to 1
            "subjectivity": blob.sentiment.subjectivity,  # 0 to 1
            "sentiment_label": self._get_sentiment_label(adjusted_polarity),
            "base_polarity": base_polarity,  # Original TextBlob score for debugging
            "method": "textblob_enhanced"
        }
    
    def _apply_context_adjustments(self, text: str, base_polarity: float) -> float:
        """
        Apply context-aware adjustments to sentiment polarity
        
        Args:
            text: Original text
            base_polarity: Base polarity from TextBlob
            
        Returns:
            Adjusted polarity score
        """
        text_lower = text.lower()
        adjusted_polarity = base_polarity
        
        # Patterns that indicate dissatisfaction despite positive words
        dissatisfaction_patterns = [
            # Seeking alternatives (strong indicator of dissatisfaction)
            (r'\b(alternative|alternatives)\s+to\b', -0.4),
            (r'\bother\s+(apps?|options?|services?)\s+(than|instead of|better than)\b', -0.4),
            (r'\breplace(ment)?\s+(for|to)\b', -0.3),
            (r'\bswitch\s+(from|away from)\b', -0.3),
            
            # Comparison seeking (moderate dissatisfaction)
            (r'\bbetter\s+(than|alternatives?|options?)\b', -0.2),
            (r'\bcheaper\s+(than|alternatives?|options?)\b', -0.2),
            (r'\bwhat.*better\b', -0.2),
            (r'\banything\s+(better|cheaper)\b', -0.2),
            
            # Implicit complaints
            (r'\bstop\s+using\b', -0.4),
            (r'\buninstall\b', -0.4),
            (r'\bdelete\b.*\bapp\b', -0.4),
            (r'\bworse\s+than\b', -0.3),
            (r'\bnot\s+worth\b', -0.3),
            (r'\bwaste\s+of\b', -0.4),
            
            # Conditional dissatisfaction
            (r'\bokay\s+but\b', -0.2),
            (r'\bfine\s+but\b', -0.2),
            (r'\bdecent\s+but\b', -0.2),
            (r'\bused\s+to\s+be\s+(good|great|better)\b', -0.3),
            (r'\bwant\s+(better|cheaper|different)\b', -0.2),
            (r'\bneed\s+(something|anything)\s+(better|cheaper|else)\b', -0.3),
        ]
        
        # Patterns that reinforce positive sentiment
        positive_reinforcement_patterns = [
            (r'\blove\s+(this|it|uber|lyft)\b', 0.2),
            (r'\bamazing\b', 0.3),
            (r'\bawesome\b', 0.3),
            (r'\bperfect\b', 0.3),
            (r'\bexcellent\b', 0.3),
            (r'\bhighly\s+recommend\b', 0.4),
            (r'\bbest\s+(app|service)\b', 0.3),
        ]
        
        # Patterns that reinforce negative sentiment
        negative_reinforcement_patterns = [
            (r'\bterrible\b', -0.4),
            (r'\bawful\b', -0.4),
            (r'\bhorrible\b', -0.4),
            (r'\bnever\s+(again|use|using)\b', -0.4),
            (r'\bworst\b', -0.4),
            (r'\bhate\b', -0.4),
            (r'\bdisgusting\b', -0.4),
        ]
        
        # Apply dissatisfaction pattern adjustments
        import re
        for pattern, adjustment in dissatisfaction_patterns:
            if re.search(pattern, text_lower):
                adjusted_polarity += adjustment
                
        # Apply positive reinforcement (only if already positive)
        if base_polarity > 0:
            for pattern, adjustment in positive_reinforcement_patterns:
                if re.search(pattern, text_lower):
                    adjusted_polarity += adjustment
                    
        # Apply negative reinforcement (amplify negative sentiment)
        for pattern, adjustment in negative_reinforcement_patterns:
            if re.search(pattern, text_lower):
                adjusted_polarity += adjustment
        
        # Clamp to valid range
        return max(-1.0, min(1.0, adjusted_polarity))
    
    def _analyze_sentiment_with_openai(self, text: str) -> Dict:
        """
        Analyze sentiment using OpenAI via CrewAI for enhanced accuracy with sarcasm detection
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary containing sentiment analysis results or None if failed
        """
        try:
            # Import LLM for model configuration
            from crewai import LLM
            
            # Configure LLM to use GPT-3.5-turbo for higher rate limits
            llm = LLM(
                model="o1-mini",
                temperature=0.3
            )
            
            # Create a sentiment analysis agent
            sentiment_agent = Agent(
                role="Expert Sentiment Analyzer",
                goal="Accurately classify sentiment in text, especially detecting sarcasm, irony, and subtle negative feedback",
                backstory="""You are an expert at understanding human emotions and sentiment in text. 
                You excel at detecting sarcasm, irony, subtle complaints, and negative experiences that might be 
                disguised with positive words. You understand context, tone, and implied meaning.""",
                verbose=False,
                allow_delegation=False,
                llm=llm
            )
            
            # Create sentiment analysis task
            sentiment_task = Task(
                description=f"""
                Analyze the sentiment of this text with high accuracy:
                
                Text: "{text}"
                
                Pay special attention to:
                1. Sarcasm and irony (e.g., "great ambiance" when describing something bad)
                2. Negative experiences described with seemingly positive words
                3. Subtle complaints and dissatisfaction
                4. Context and implied meaning
                
                Respond with ONLY a JSON object in this exact format:
                {{
                    "sentiment": "positive|negative|neutral",
                    "confidence": 0.85,
                    "polarity": -0.6,
                    "reasoning": "Brief explanation of why this sentiment was chosen"
                }}
                
                Where:
                - sentiment: The detected sentiment (positive, negative, or neutral)
                - confidence: How confident you are (0.0 to 1.0)
                - polarity: Numeric score from -1.0 (very negative) to +1.0 (very positive)
                - reasoning: Brief explanation of your analysis
                """,
                agent=sentiment_agent,
                expected_output="JSON object with sentiment analysis results"
            )
            
            # Create crew and execute
            crew = Crew(
                agents=[sentiment_agent],
                tasks=[sentiment_task],
                verbose=False
            )
            
            result = crew.kickoff()
            
            # Parse the result
            import json
            try:
                # Extract JSON from the result
                result_text = str(result).strip()
                
                # Find JSON in the response
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = result_text[start_idx:end_idx]
                    parsed_result = json.loads(json_str)
                    
                    return {
                        "polarity": parsed_result.get("polarity", 0.0),
                        "subjectivity": 0.8,  # Default subjectivity for OpenAI results
                        "sentiment_label": parsed_result.get("sentiment", "neutral"),
                        "confidence": parsed_result.get("confidence", 0.8),
                        "reasoning": parsed_result.get("reasoning", ""),
                        "method": "openai_crewai"
                    }
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse OpenAI response as JSON: {e}")
                print(f"Raw response: {result}")
                
        except Exception as e:
            print(f"OpenAI sentiment analysis error: {e}")
            
        return None
    
    def _get_sentiment_label(self, polarity: float) -> str:
        """Convert polarity score to sentiment label"""
        if polarity > 0.05:
            return "positive"
        elif polarity < -0.05:
            return "negative"
        else:
            return "neutral"
    
    def extract_topics_and_themes(self, texts: List[str], min_frequency: int = 3) -> Dict:
        """
        Extract common topics and themes from a list of texts
        
        Args:
            texts: List of texts to analyze
            min_frequency: Minimum frequency for a topic to be included
            
        Returns:
            Dictionary containing topics and themes
        """
        # Combine all texts
        combined_text = " ".join(texts).lower()
        
        # Extract common phrases and keywords
        words = re.findall(r'\b\w+\b', combined_text)
        word_freq = Counter(words)
        
        # Filter out common words and short words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'a', 'an', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
        
        filtered_words = {
            word: freq for word, freq in word_freq.items()
            if len(word) > 3 and word not in stop_words and freq >= min_frequency
        }
        
        # Extract bigrams (two-word phrases)
        bigrams = []
        words_list = words
        for i in range(len(words_list) - 1):
            bigram = f"{words_list[i]} {words_list[i+1]}"
            if len(bigram) > 6:  # Filter short bigrams
                bigrams.append(bigram)
        
        bigram_freq = Counter(bigrams)
        common_bigrams = {
            phrase: freq for phrase, freq in bigram_freq.items()
            if freq >= min_frequency
        }
        
        return {
            "common_words": dict(sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:20]),
            "common_phrases": dict(sorted(common_bigrams.items(), key=lambda x: x[1], reverse=True)[:15]),
            "total_texts_analyzed": len(texts)
        }
    
    def analyze_reviews_sentiment(self, reviews: List[Dict]) -> Dict:
        """
        Analyze sentiment of multiple reviews
        
        Args:
            reviews: List of review dictionaries
            
        Returns:
            Dictionary containing aggregated sentiment analysis
        """
        if not reviews:
            return {
                "average_sentiment": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "sentiment_distribution": {},
                "total_reviews": 0
            }
        
        sentiments = []
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for review in reviews:
            content = review.get("content", "") or review.get("title", "")
            if content:
                sentiment = self.analyze_sentiment(content)
                sentiments.append(sentiment["polarity"])
                sentiment_counts[sentiment["sentiment_label"]] += 1
        
        return {
            "average_sentiment": np.mean(sentiments) if sentiments else 0,
            "positive_count": sentiment_counts["positive"],
            "negative_count": sentiment_counts["negative"],
            "neutral_count": sentiment_counts["neutral"],
            "sentiment_distribution": {
                k: v / len(reviews) for k, v in sentiment_counts.items()
            },
            "total_reviews": len(reviews)
        }
    
    def identify_key_issues(self, reviews: List[Dict], serp_data: List[Dict]) -> List[Dict]:
        """
        Identify key issues from reviews and SERP data
        
        Args:
            reviews: List of review dictionaries
            serp_data: List of SERP result dictionaries
            
        Returns:
            List of key issues with priority and details
        """
        issues = []
        
        # Analyze negative reviews
        negative_reviews = []
        for review in reviews:
            content = review.get("content", "") or review.get("title", "")
            if content:
                sentiment = self.analyze_sentiment(content)
                if sentiment["sentiment_label"] == "negative":
                    negative_reviews.append(content)
        
        # Extract issues from negative reviews
        if negative_reviews:
            topics = self.extract_topics_and_themes(negative_reviews, min_frequency=2)
            
            for word, frequency in topics["common_words"].items():
                if any(keyword in word for keyword in self.negative_keywords):
                    issues.append({
                        "issue": word,
                        "type": "product_issue",
                        "frequency": frequency,
                        "priority": "high" if frequency > 5 else "medium",
                        "source": "reviews"
                    })
        
        # Analyze SERP data for reputation issues
        negative_serp_content = []
        for item in serp_data:
            if any(term in item.get("query", "").lower() for term in ["complaint", "problem", "issue"]):
                content = f"{item.get('title', '')} {item.get('snippet', '')}"
                negative_serp_content.append(content)
        
        if negative_serp_content:
            serp_topics = self.extract_topics_and_themes(negative_serp_content, min_frequency=1)
            
            for phrase, frequency in serp_topics["common_phrases"].items():
                issues.append({
                    "issue": phrase,
                    "type": "reputation_issue",
                    "frequency": frequency,
                    "priority": "high" if frequency > 2 else "medium",
                    "source": "serp"
                })
        
        # Sort issues by priority and frequency
        priority_order = {"high": 3, "medium": 2, "low": 1}
        issues.sort(key=lambda x: (priority_order[x["priority"]], x["frequency"]), reverse=True)
        
        return issues[:10]  # Return top 10 issues
    
    def calculate_reputation_score(self, reviews_data: Dict, serp_data: List[Dict], issues: List[Dict]) -> float:
        """
        Calculate overall reputation score
        
        Args:
            reviews_data: Aggregated review sentiment data
            serp_data: SERP results data
            issues: List of identified issues
            
        Returns:
            Reputation score from 0 to 100
        """
        # Base score from review sentiment (50% weight)
        sentiment_score = 0
        if reviews_data.get("total_reviews", 0) > 0:
            avg_sentiment = reviews_data.get("average_sentiment", 0)
            # Convert sentiment (-1 to 1) to score (0 to 50)
            sentiment_score = (avg_sentiment + 1) * 25
        
        # SERP reputation factor (30% weight)
        serp_score = 30  # Default neutral score
        negative_serp_count = sum(1 for item in serp_data if any(
            term in item.get("query", "").lower() 
            for term in ["complaint", "problem", "lawsuit", "scandal"]
        ))
        
        if len(serp_data) > 0:
            negative_ratio = negative_serp_count / len(serp_data)
            serp_score = 30 * (1 - negative_ratio)
        
        # Issues penalty (20% weight)
        issues_penalty = min(len(issues) * 2, 20)  # Max 20 point penalty
        
        # Calculate final score
        final_score = sentiment_score + serp_score + (20 - issues_penalty)
        
        # Ensure score is between 0 and 100
        return max(0, min(100, final_score))
    
    def classify_intent(self, text: str) -> Dict:
        """
        Classify the intent of user feedback
        
        Args:
            text: Text to classify
            
        Returns:
            Dictionary with intent classification and confidence
        """
        text_lower = text.lower()
        intent_scores = {}
        
        for intent, keywords in self.intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return {"intent": "neutral_mention", "confidence": 0.5, "keywords_matched": []}
        
        # Get the intent with highest score
        primary_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k])
        confidence = min(1.0, intent_scores[primary_intent] / 3)  # Normalize confidence
        
        # Get matched keywords
        matched_keywords = [
            keyword for keyword in self.intent_patterns[primary_intent]
            if keyword in text_lower
        ]
        
        return {
            "intent": primary_intent,
            "confidence": confidence,
            "keywords_matched": matched_keywords,
            "all_scores": intent_scores
        }
    
    def detect_crisis_signals(self, reviews: List[Dict], time_window_hours: int = 24) -> Dict:
        """
        Detect potential crisis signals from recent reviews
        
        Args:
            reviews: List of review dictionaries with dates
            time_window_hours: Time window to analyze for spikes
            
        Returns:
            Dictionary with crisis detection results
        """
        if not reviews:
            return {"alerts": [], "crisis_level": "none", "total_signals": 0}
        
        # For demo purposes, simulate time-based analysis
        recent_reviews = reviews  # In real implementation, filter by date
        
        crisis_signals = defaultdict(int)
        affected_reviews = []
        
        for review in recent_reviews:
            content = (review.get('content', '') + ' ' + review.get('title', '')).lower()
            
            for category, keywords in self.crisis_keywords.items():
                for keyword in keywords:
                    if keyword in content:
                        crisis_signals[category] += 1
                        affected_reviews.append({
                            "review_id": review.get('id', 'unknown'),
                            "content_snippet": content[:100] + "...",
                            "category": category,
                            "keyword": keyword,
                            "platform": review.get('platform', 'unknown')
                        })
                        break
        
        # Determine crisis level
        total_signals = sum(crisis_signals.values())
        if total_signals >= 10:
            crisis_level = "critical"
        elif total_signals >= 5:
            crisis_level = "high"
        elif total_signals >= 2:
            crisis_level = "medium"
        else:
            crisis_level = "low"
        
        # Generate alerts
        alerts = []
        for category, count in crisis_signals.items():
            if count >= 2:  # Threshold for alert
                alerts.append({
                    "category": category,
                    "severity": "high" if count >= 5 else "medium",
                    "count": count,
                    "message": f"Spike detected in {category} issues: {count} mentions in recent reviews"
                })
        
        return {
            "alerts": alerts,
            "crisis_level": crisis_level,
            "total_signals": total_signals,
            "category_breakdown": dict(crisis_signals),
            "affected_reviews": affected_reviews[:5],  # Show top 5 for brevity
            "recommendation": self._get_crisis_recommendation(crisis_level, alerts)
        }
    
    def _get_crisis_recommendation(self, crisis_level: str, alerts: List[Dict]) -> str:
        """Generate crisis management recommendations"""
        if crisis_level == "critical":
            return "IMMEDIATE ACTION REQUIRED: Contact crisis management team and prepare public statement"
        elif crisis_level == "high":
            return "URGENT: Escalate to management and prepare response strategy"
        elif crisis_level == "medium":
            return "MONITOR CLOSELY: Increase response frequency and track trends"
        else:
            return "NORMAL: Continue standard monitoring and response procedures"
    
    def analyze_with_evidence(self, reviews: List[Dict], serp_data: List[Dict]) -> Dict:
        """
        Comprehensive analysis with evidence tracking
        
        Args:
            reviews: List of review dictionaries
            serp_data: List of SERP result dictionaries
            
        Returns:
            Enhanced analysis with evidence and citations
        """
        # Basic sentiment analysis
        sentiment_analysis = self.analyze_reviews_sentiment(reviews)
        
        # Intent classification for all reviews
        intent_breakdown = defaultdict(int)
        classified_reviews = []
        
        for review in reviews:
            content = review.get('content', '') or review.get('title', '')
            if content:
                intent_result = self.classify_intent(content)
                intent_breakdown[intent_result['intent']] += 1
                
                classified_reviews.append({
                    **review,
                    "intent": intent_result['intent'],
                    "intent_confidence": intent_result['confidence'],
                    "matched_keywords": intent_result['keywords_matched']
                })
        
        # Crisis detection
        crisis_analysis = self.detect_crisis_signals(reviews)
        
        # Enhanced issue identification with evidence
        issues = self.identify_key_issues_with_evidence(reviews, serp_data)
        
        # Key themes with supporting evidence
        themes = self.extract_themes_with_evidence(reviews, serp_data)
        
        return {
            "sentiment_analysis": sentiment_analysis,
            "intent_breakdown": dict(intent_breakdown),
            "classified_reviews": classified_reviews,
            "crisis_analysis": crisis_analysis,
            "prioritized_issues": issues,
            "key_themes": themes,
            "data_sources": {
                "reviews_analyzed": len(reviews),
                "serp_results_analyzed": len(serp_data),
                "platforms_covered": list(set(r.get('platform', 'unknown') for r in reviews))
            }
        }
    
    def identify_key_issues_with_evidence(self, reviews: List[Dict], serp_data: List[Dict]) -> List[Dict]:
        """Enhanced issue identification with supporting evidence"""
        issues = self.identify_key_issues(reviews, serp_data)
        
        # Add evidence and citations for each issue
        enhanced_issues = []
        for issue in issues:
            evidence = []
            
            # Find supporting reviews
            for review in reviews:
                content = (review.get('content', '') + ' ' + review.get('title', '')).lower()
                if issue['issue'].lower() in content:
                    evidence.append({
                        "type": "review",
                        "platform": review.get('platform', 'unknown'),
                        "snippet": content[:150] + "...",
                        "rating": review.get('rating'),
                        "date": review.get('date', 'unknown')
                    })
                    if len(evidence) >= 3:  # Limit evidence per issue
                        break
            
            # Find supporting SERP data
            for serp_item in serp_data:
                title_snippet = (serp_item.get('title', '') + ' ' + serp_item.get('snippet', '')).lower()
                if issue['issue'].lower() in title_snippet:
                    evidence.append({
                        "type": "serp",
                        "title": serp_item.get('title', ''),
                        "snippet": serp_item.get('snippet', ''),
                        "source": serp_item.get('source', ''),
                        "link": serp_item.get('link', '')
                    })
                    if len([e for e in evidence if e['type'] == 'serp']) >= 2:
                        break
            
            enhanced_issues.append({
                **issue,
                "evidence": evidence,
                "evidence_count": len(evidence),
                "actionable_insight": self._generate_issue_insight(issue, evidence)
            })
        
        return enhanced_issues
    
    def extract_themes_with_evidence(self, reviews: List[Dict], serp_data: List[Dict]) -> Dict:
        """Extract themes with supporting evidence"""
        review_texts = [r.get('content', '') for r in reviews if r.get('content')]
        themes = self.extract_topics_and_themes(review_texts)
        
        # Add evidence for top themes
        enhanced_themes = {}
        for theme, frequency in list(themes.get('common_words', {}).items())[:5]:
            supporting_reviews = []
            for review in reviews:
                content = review.get('content', '').lower()
                if theme in content:
                    supporting_reviews.append({
                        "platform": review.get('platform'),
                        "snippet": content[:100] + "...",
                        "rating": review.get('rating')
                    })
                    if len(supporting_reviews) >= 3:
                        break
            
            enhanced_themes[theme] = {
                "frequency": frequency,
                "supporting_evidence": supporting_reviews,
                "sentiment_context": self._analyze_theme_sentiment(theme, review_texts)
            }
        
        return enhanced_themes
    
    def _generate_issue_insight(self, issue: Dict, evidence: List[Dict]) -> str:
        """Generate actionable insight for an issue"""
        issue_type = issue.get('type', 'unknown')
        frequency = issue.get('frequency', 0)
        
        if issue_type == "product_issue":
            return f"Product team should prioritize fixing '{issue['issue']}' - affects {frequency} customers across multiple platforms"
        elif issue_type == "reputation_issue":
            return f"PR team should address '{issue['issue']}' narrative appearing in search results and online discussions"
        else:
            return f"Investigate '{issue['issue']}' mentioned {frequency} times - cross-functional response may be needed"
    
    def _analyze_theme_sentiment(self, theme: str, texts: List[str]) -> Dict:
        """Analyze sentiment specifically for a theme"""
        theme_contexts = []
        for text in texts:
            if theme.lower() in text.lower():
                # Extract context around the theme
                words = text.split()
                theme_indices = [i for i, word in enumerate(words) if theme.lower() in word.lower()]
                for idx in theme_indices:
                    start = max(0, idx - 10)
                    end = min(len(words), idx + 10)
                    context = ' '.join(words[start:end])
                    theme_contexts.append(context)
        
        if not theme_contexts:
            return {"average_sentiment": 0, "sample_contexts": []}
        
        sentiments = []
        for context in theme_contexts:
            sentiment = self.analyze_sentiment(context)
            sentiments.append(sentiment['polarity'])
        
        return {
            "average_sentiment": np.mean(sentiments),
            "sample_contexts": theme_contexts[:3]
        }