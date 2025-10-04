from typing import Dict, List
import re

class ResponseGenerator:
    def __init__(self):
        self.response_templates = {
            'official': {
                'complaint': {
                    'opening': "Thank you for bringing this to our attention.",
                    'acknowledgment': "We understand your frustration regarding {issue}.",
                    'action': "Our team is actively working to resolve this matter.",
                    'closing': "We appreciate your patience and continued support.",
                    'tone': "professional and formal"
                },
                'question': {
                    'opening': "Thank you for your inquiry.",
                    'acknowledgment': "We're happy to help clarify {issue}.",
                    'action': "Please find the information you requested below:",
                    'closing': "If you have any additional questions, please don't hesitate to reach out.",
                    'tone': "helpful and informative"
                },
                'recommendation': {
                    'opening': "We appreciate your feedback and suggestions.",
                    'acknowledgment': "Your input regarding {issue} is valuable to us.",
                    'action': "We will share your recommendations with our product team for consideration.",
                    'closing': "Thank you for helping us improve our services.",
                    'tone': "grateful and considerate"
                }
            },
            'friendly': {
                'complaint': {
                    'opening': "Hi there! Thanks for reaching out to us.",
                    'acknowledgment': "We're really sorry to hear about the trouble with {issue}.",
                    'action': "Our team is on it and working hard to fix this for you!",
                    'closing': "Hang in there - we've got your back! 💪",
                    'tone': "warm and empathetic"
                },
                'question': {
                    'opening': "Hey! Great question!",
                    'acknowledgment': "We'd love to help you with {issue}.",
                    'action': "Here's what you need to know:",
                    'closing': "Hope this helps! Feel free to ask if you need anything else! 😊",
                    'tone': "casual and enthusiastic"
                },
                'recommendation': {
                    'opening': "Awesome feedback! We love hearing from you!",
                    'acknowledgment': "Your idea about {issue} is really interesting.",
                    'action': "We're definitely going to discuss this with our team.",
                    'closing': "Keep the great ideas coming! 🚀",
                    'tone': "enthusiastic and encouraging"
                }
            },
            'tech_support': {
                'complaint': {
                    'opening': "I understand you're experiencing technical difficulties.",
                    'acknowledgment': "Let's get {issue} sorted out for you right away.",
                    'action': "Here are the troubleshooting steps to resolve this:",
                    'closing': "If these steps don't resolve the issue, please provide your error logs for further investigation.",
                    'tone': "technical and solution-focused"
                },
                'question': {
                    'opening': "I can help you with that technical question.",
                    'acknowledgment': "For {issue}, here's the technical information:",
                    'action': "Follow these step-by-step instructions:",
                    'closing': "Let me know if you need clarification on any of these steps.",
                    'tone': "clear and instructional"
                },
                'recommendation': {
                    'opening': "Thank you for the technical suggestion.",
                    'acknowledgment': "Your recommendation about {issue} shows good technical insight.",
                    'action': "I'll escalate this to our engineering team for technical evaluation.",
                    'closing': "We appreciate users who help us identify potential improvements.",
                    'tone': "professional and technical"
                }
            }
        }
        
        self.action_checklists = {
            'technical_issue': [
                "Verify the issue reproduction steps",
                "Check system requirements and compatibility",
                "Clear cache and restart the application",
                "Update to the latest version",
                "Contact support if issue persists"
            ],
            'billing_issue': [
                "Verify payment method and billing information",
                "Check for any pending transactions",
                "Review subscription status and billing cycle",
                "Contact billing support for account-specific issues",
                "Keep transaction receipts for reference"
            ],
            'account_issue': [
                "Verify login credentials",
                "Check account status and permissions",
                "Reset password if necessary",
                "Contact account support for assistance",
                "Keep account information secure"
            ],
            'general_complaint': [
                "Document the specific issue details",
                "Gather relevant screenshots or evidence",
                "Check FAQ for common solutions",
                "Contact customer support",
                "Follow up if needed"
            ]
        }
        
        self.knowledge_base_links = {
            'technical': "https://help.company.com/technical-support",
            'billing': "https://help.company.com/billing-and-payments",
            'account': "https://help.company.com/account-management",
            'getting_started': "https://help.company.com/getting-started",
            'troubleshooting': "https://help.company.com/troubleshooting",
            'faq': "https://help.company.com/frequently-asked-questions"
        }
    
    def generate_response(self, issue_data: Dict, style: str = 'official') -> Dict:
        """
        Generate personalized response drafts
        
        Args:
            issue_data: Dictionary containing issue details, intent, etc.
            style: Response style ('official', 'friendly', 'tech_support')
            
        Returns:
            Dictionary with response components and metadata
        """
        intent = issue_data.get('intent', 'complaint')
        issue_description = issue_data.get('issue', 'your concern')
        severity = issue_data.get('priority', 'medium')
        
        # Get appropriate template
        template = self.response_templates.get(style, {}).get(intent, {})
        if not template:
            template = self.response_templates['official']['complaint']
        
        # Generate response components
        response_parts = {
            'opening': template.get('opening', ''),
            'acknowledgment': template.get('acknowledgment', '').format(issue=issue_description),
            'action': template.get('action', ''),
            'closing': template.get('closing', ''),
            'tone': template.get('tone', 'professional')
        }
        
        # Combine into full response
        full_response = f"{response_parts['opening']} {response_parts['acknowledgment']} {response_parts['action']} {response_parts['closing']}"
        
        # Generate action checklist
        checklist_type = self._determine_checklist_type(issue_data)
        action_checklist = self.action_checklists.get(checklist_type, self.action_checklists['general_complaint'])
        
        # Determine relevant knowledge base links
        relevant_links = self._get_relevant_links(issue_data)
        
        # Add escalation info based on severity
        escalation_info = self._get_escalation_info(severity)
        
        return {
            'response_draft': full_response,
            'response_components': response_parts,
            'action_checklist': action_checklist,
            'knowledge_base_links': relevant_links,
            'escalation_info': escalation_info,
            'metadata': {
                'style': style,
                'intent': intent,
                'severity': severity,
                'estimated_resolution_time': self._estimate_resolution_time(issue_data),
                'follow_up_required': self._requires_follow_up(issue_data)
            }
        }
    
    def generate_multiple_styles(self, issue_data: Dict) -> Dict:
        """Generate responses in all available styles"""
        styles = ['official', 'friendly', 'tech_support']
        responses = {}
        
        for style in styles:
            responses[style] = self.generate_response(issue_data, style)
        
        return {
            'responses': responses,
            'recommendation': self._recommend_best_style(issue_data),
            'common_elements': {
                'action_checklist': self.generate_response(issue_data)['action_checklist'],
                'knowledge_base_links': self.generate_response(issue_data)['knowledge_base_links']
            }
        }
    
    def _determine_checklist_type(self, issue_data: Dict) -> str:
        """Determine the most appropriate checklist type"""
        issue = issue_data.get('issue', '').lower()
        keywords = issue_data.get('keywords_matched', [])
        
        # Check for technical keywords
        tech_keywords = ['crash', 'error', 'bug', 'not working', 'broken', 'loading']
        if any(keyword in issue or keyword in ' '.join(keywords) for keyword in tech_keywords):
            return 'technical_issue'
        
        # Check for billing keywords
        billing_keywords = ['payment', 'billing', 'charge', 'refund', 'subscription']
        if any(keyword in issue or keyword in ' '.join(keywords) for keyword in billing_keywords):
            return 'billing_issue'
        
        # Check for account keywords
        account_keywords = ['login', 'password', 'account', 'profile', 'sign in']
        if any(keyword in issue or keyword in ' '.join(keywords) for keyword in account_keywords):
            return 'account_issue'
        
        return 'general_complaint'
    
    def _get_relevant_links(self, issue_data: Dict) -> List[Dict]:
        """Get relevant knowledge base links"""
        issue = issue_data.get('issue', '').lower()
        checklist_type = self._determine_checklist_type(issue_data)
        
        links = []
        
        # Always include FAQ
        links.append({
            'title': 'Frequently Asked Questions',
            'url': self.knowledge_base_links['faq'],
            'description': 'Common questions and answers'
        })
        
        # Add specific links based on issue type
        if checklist_type == 'technical_issue':
            links.extend([
                {
                    'title': 'Technical Support Guide',
                    'url': self.knowledge_base_links['technical'],
                    'description': 'Step-by-step technical troubleshooting'
                },
                {
                    'title': 'Troubleshooting Guide',
                    'url': self.knowledge_base_links['troubleshooting'],
                    'description': 'Common technical issues and solutions'
                }
            ])
        elif checklist_type == 'billing_issue':
            links.append({
                'title': 'Billing & Payments Help',
                'url': self.knowledge_base_links['billing'],
                'description': 'Payment processing and billing information'
            })
        elif checklist_type == 'account_issue':
            links.append({
                'title': 'Account Management',
                'url': self.knowledge_base_links['account'],
                'description': 'Account settings and login assistance'
            })
        
        return links
    
    def _get_escalation_info(self, severity: str) -> Dict:
        """Get escalation information based on severity"""
        escalation_map = {
            'high': {
                'timeline': '2-4 hours',
                'escalation_level': 'Senior Support Manager',
                'priority': 'High Priority',
                'additional_actions': ['Immediate manager notification', 'Customer retention team alert']
            },
            'medium': {
                'timeline': '1-2 business days',
                'escalation_level': 'Support Team Lead',
                'priority': 'Standard Priority',
                'additional_actions': ['Standard escalation process']
            },
            'low': {
                'timeline': '3-5 business days',
                'escalation_level': 'Support Agent',
                'priority': 'Standard Priority',
                'additional_actions': ['Follow standard resolution process']
            }
        }
        
        return escalation_map.get(severity, escalation_map['medium'])
    
    def _estimate_resolution_time(self, issue_data: Dict) -> str:
        """Estimate resolution time based on issue complexity"""
        checklist_type = self._determine_checklist_type(issue_data)
        severity = issue_data.get('priority', 'medium')
        
        time_estimates = {
            'technical_issue': {
                'high': '2-6 hours',
                'medium': '1-2 business days',
                'low': '2-3 business days'
            },
            'billing_issue': {
                'high': '1-3 hours',
                'medium': '4-8 hours',
                'low': '1-2 business days'
            },
            'account_issue': {
                'high': '1-2 hours',
                'medium': '2-4 hours',
                'low': '1 business day'
            },
            'general_complaint': {
                'high': '2-4 hours',
                'medium': '1-2 business days',
                'low': '2-3 business days'
            }
        }
        
        return time_estimates.get(checklist_type, {}).get(severity, '1-2 business days')
    
    def _requires_follow_up(self, issue_data: Dict) -> bool:
        """Determine if follow-up is required"""
        severity = issue_data.get('priority', 'medium')
        intent = issue_data.get('intent', 'complaint')
        
        # High priority issues always require follow-up
        if severity == 'high':
            return True
        
        # Complaints typically require follow-up
        if intent == 'complaint':
            return True
        
        # Technical issues often require follow-up
        if self._determine_checklist_type(issue_data) == 'technical_issue':
            return True
        
        return False
    
    def _recommend_best_style(self, issue_data: Dict) -> Dict:
        """Recommend the best response style for the given issue"""
        intent = issue_data.get('intent', 'complaint')
        severity = issue_data.get('priority', 'medium')
        checklist_type = self._determine_checklist_type(issue_data)
        
        # Technical issues -> tech support style
        if checklist_type == 'technical_issue':
            return {
                'recommended_style': 'tech_support',
                'reason': 'Technical issue detected - structured troubleshooting approach recommended'
            }
        
        # High severity complaints -> official style
        if intent == 'complaint' and severity == 'high':
            return {
                'recommended_style': 'official',
                'reason': 'High severity complaint - professional formal response recommended'
            }
        
        # Questions -> friendly style
        if intent == 'question':
            return {
                'recommended_style': 'friendly',
                'reason': 'User inquiry - helpful and approachable tone recommended'
            }
        
        # Default to official for most cases
        return {
            'recommended_style': 'official',
            'reason': 'Standard professional response appropriate for this issue type'
        }