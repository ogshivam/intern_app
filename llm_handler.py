import json
import requests
from typing import Dict, List, Tuple, Optional
import random

class LLMHandler:
    def __init__(self, case_doc: Dict, metrics: Dict):
        self.case_doc = case_doc
        self.metrics = metrics
        self.conversation_history = []
        self.current_metric = None
        self.question_count = 0
        self.asked_topics = set()
        self.current_focus = None
        self.probing_count = 0
        
    def _call_ollama(self, prompt: str, system_prompt: str = "") -> str:
        """Make a call to Ollama API with optional system prompt"""
        try:
            response = requests.post('http://localhost:11434/api/generate',
                                  json={
                                      'model': 'tinyllama',
                                      'prompt': prompt,
                                      'system': system_prompt,
                                      'stream': False
                                  })
            return response.json()['response']
        except Exception as e:
            print(f"Error calling Ollama: {str(e)}")
            return ""

    def _analyze_response_quality(self, response: str) -> Dict[str, any]:
        """Analyze response quality and identify areas needing probing"""
        words = response.lower().split()
        
        analysis = {
            "length": len(words),
            "has_examples": any(word in response.lower() for word in ["example", "instance", "case", "situation"]),
            "has_metrics": any(word in response.lower() for word in ["measure", "metric", "kpi", "indicator", "target"]),
            "has_implementation": any(word in response.lower() for word in ["implement", "execute", "deploy", "roll out"]),
            "has_challenges": any(word in response.lower() for word in ["challenge", "difficulty", "problem", "issue"]),
            "vague_words": sum(1 for word in ["maybe", "probably", "might", "could", "would"] if word in words),
            "needs_probing": False,
            "probe_areas": []
        }
        
        # Identify areas needing probing
        if not analysis["has_examples"]:
            analysis["probe_areas"].append("examples")
        if not analysis["has_metrics"]:
            analysis["probe_areas"].append("metrics")
        if not analysis["has_implementation"]:
            analysis["probe_areas"].append("implementation")
        if not analysis["has_challenges"]:
            analysis["probe_areas"].append("challenges")
            
        analysis["needs_probing"] = len(analysis["probe_areas"]) > 0 or analysis["vague_words"] > 2
        return analysis

    def validate_response(self, response: str) -> Tuple[bool, Optional[str]]:
        """Validate response and provide specific guidance"""
        if not response:
            return False, "Please provide a response to continue with the assessment."
            
        response = response.strip()
        
        # Check for inappropriate responses
        inappropriate = ["ur mom", "bleh", "idk", "whatever"]
        if any(word in response.lower() for word in inappropriate):
            return False, "Please provide a professional and thoughtful response."
        
        analysis = self._analyze_response_quality(response)
        
        if analysis["length"] < 50:
            suggestions = [
                "Share a specific example from your experience managing branches",
                "Describe how you would measure success in this situation",
                "Explain your implementation approach step by step",
                "Discuss potential challenges and your mitigation strategies"
            ]
            return False, f"Your response needs more detail. Consider:\n- {random.choice(suggestions)}"
        
        if analysis["vague_words"] > 2:
            return False, "Try to be more specific and confident. Instead of using words like 'maybe' or 'probably', share concrete approaches and examples."
            
        return True, None

    def _get_focused_probe(self, area: str, context: str) -> str:
        """Generate a focused probing question for a specific area"""
        probes = {
            "examples": [
                "Could you share a specific instance where you've implemented this approach?",
                "What's a concrete example of how you would handle this situation?",
                "Can you walk us through a real case where you've dealt with this?"
            ],
            "metrics": [
                "What specific metrics would you use to measure success?",
                "How would you track the effectiveness of this approach?",
                "What KPIs would help you monitor progress?"
            ],
            "implementation": [
                "What are the key steps in implementing this approach?",
                "How would you ensure consistent implementation across all 45 branches?",
                "What resources would you need to execute this plan?"
            ],
            "challenges": [
                "What potential obstacles do you anticipate?",
                "How would you address resistance from branch managers?",
                "What risks should be considered in this approach?"
            ]
        }
        
        return random.choice(probes.get(area, probes["examples"]))

    def generate_initial_question(self) -> str:
        """Generate focused initial question"""
        system_prompt = """You are conducting a professional role-play assessment.
        Focus on practical scenarios and maintain confidentiality.
        Questions should encourage specific examples while avoiding sensitive details."""
        
        initial_focus_areas = [
            "branch operations optimization",
            "customer service improvement",
            "team performance management",
            "service quality standards"
        ]
        
        self.current_focus = random.choice(initial_focus_areas)
        
        prompt = f"""Generate an initial question focusing on {self.current_focus}:

Role Context: General Manager overseeing 45 branches in Mumbai Region
Focus Area: {self.current_focus}

Question Requirements:
1. Focus specifically on {self.current_focus}
2. Ask for concrete examples and practical approaches
3. Avoid theoretical concepts
4. Maintain confidentiality (no internal metrics or sensitive data)

Format: Generate only the question."""
        
        return self._call_ollama(prompt, system_prompt)

    def _extract_key_themes(self, response: str) -> Dict[str, float]:
        """Extract key themes and their relevance from a response"""
        themes = {
            "customer_service": ["customer", "service", "satisfaction", "experience", "feedback"],
            "operations": ["process", "operation", "workflow", "efficiency", "system"],
            "team_management": ["team", "staff", "employee", "manager", "training"],
            "performance": ["performance", "metric", "kpi", "measure", "target"],
            "communication": ["communicate", "message", "inform", "share", "discuss"],
            "implementation": ["implement", "execute", "deploy", "roll out", "launch"],
            "challenges": ["challenge", "issue", "problem", "difficulty", "concern"]
        }
        
        words = response.lower().split()
        theme_scores = {theme: 0.0 for theme in themes}
        
        for word in words:
            for theme, keywords in themes.items():
                if any(keyword in word for keyword in keywords):
                    theme_scores[theme] += 1.0
                    
        # Normalize scores
        max_score = max(theme_scores.values()) if theme_scores.values() else 1.0
        if max_score > 0:
            theme_scores = {k: v/max_score for k, v in theme_scores.items()}
            
        return theme_scores

    def generate_followup_question(self, previous_response: str) -> Tuple[Optional[str], Optional[str]]:
        """Generate contextual follow-up questions"""
        if not self.current_metric or self.question_count >= 5:
            metrics = list(self.metrics['aspects'].keys())
            current_index = metrics.index(self.current_metric) if self.current_metric else -1
            if current_index + 1 < len(metrics):
                self.current_metric = metrics[current_index + 1]
                self.question_count = 0
                self.asked_topics.clear()
                self.probing_count = 0
            else:
                return None, None
        
        if not self.current_metric:
            self.current_metric = list(self.metrics['aspects'].keys())[0]
            
        metric_details = self.metrics['aspects'][self.current_metric]
        
        # Validate the previous response first
        is_valid, feedback = self.validate_response(previous_response)
        if not is_valid:
            # If response is invalid, use a probing question instead of moving forward
            self.probing_count += 1
            return self._get_focused_probe("examples", self.current_focus), self.current_metric
            
        self.conversation_history.append(("candidate", previous_response))
        
        # Extract themes and key topics from the response
        theme_scores = self._extract_key_themes(previous_response)
        dominant_themes = [theme for theme, score in theme_scores.items() if score > 0.3]
        
        # Extract specific topics mentioned
        words = previous_response.lower().split()
        key_topics = set(words) - set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'])
        key_topics = [t for t in key_topics if len(t) > 4]  # Filter short words
        
        # Analyze response quality
        analysis = self._analyze_response_quality(previous_response)
        
        # If response needs probing and we haven't probed too much
        if analysis["needs_probing"] and self.probing_count < 2:
            self.probing_count += 1
            probe_area = random.choice(analysis["probe_areas"]) if analysis["probe_areas"] else "examples"
            return self._get_focused_probe(probe_area, previous_response), self.current_metric
        
        # Reset probing count for new question
        self.probing_count = 0
        
        # Select a theme and topic to focus on
        selected_theme = random.choice(dominant_themes) if dominant_themes else random.choice(list(theme_scores.keys()))
        focus_topic = random.choice(key_topics) if key_topics else self.current_focus
        
        # Define question templates based on metric and theme
        theme_based_templates = {
            "customer_service": {
                "Clear Communication": [
                    "How do you ensure clear communication about {topic} to improve customer service?",
                    "What strategies do you use to communicate service changes related to {topic}?",
                    "How do you handle customer feedback about {topic} across branches?"
                ],
                "Engaging Discussions": [
                    "How do you facilitate discussions about {topic} with customer-facing staff?",
                    "What methods work best when discussing customer feedback about {topic}?",
                    "How do you ensure all branches share their experiences with {topic}?"
                ]
            },
            "operations": {
                "Clear Communication": [
                    "How do you communicate operational changes regarding {topic}?",
                    "What methods do you use to ensure clear understanding of {topic} procedures?",
                    "How do you handle communication about {topic} across different branches?"
                ]
            },
            "team_management": {
                "Clear Communication": [
                    "How do you communicate expectations about {topic} to your team?",
                    "What strategies do you use to ensure clear understanding of {topic} goals?",
                    "How do you handle feedback about {topic} management approaches?"
                ]
            }
        }
        
        # Get templates for current metric and theme
        templates = theme_based_templates.get(selected_theme, {}).get(metric_details['name'], [
            "How do you ensure effective communication about {topic}?",
            "What specific approaches have you used to discuss {topic}?",
            "How do you maintain consistency in {topic} communication?",
            "What challenges have you faced with {topic} and how did you address them?"
        ])
        
        # Generate question
        question = random.choice(templates).format(topic=focus_topic)
        
        # Update tracking
        self.asked_topics.add(focus_topic)
        self.question_count += 1
        
        return question, self.current_metric

    def evaluate_response(self, metric: str, response: str) -> Dict:
        """Evaluate response with specific criteria"""
        metric_details = self.metrics['aspects'][metric]
        analysis = self._analyze_response_quality(response)
        
        system_prompt = """You are evaluating role-play responses.
        Focus on demonstrated competencies and practical approaches.
        Maintain confidentiality in feedback."""
        
        prompt = f"""Evaluate this response for {metric_details['name']}:

Response: "{response}"

Response Analysis:
- Length: {analysis['length']} words
- Contains examples: {analysis['has_examples']}
- Contains metrics: {analysis['has_metrics']}
- Implementation details: {analysis['has_implementation']}
- Discusses challenges: {analysis['has_challenges']}
- Vague language count: {analysis['vague_words']}

Scoring Guide:
1.0 - Basic response lacking specifics
2.0 - General understanding with some examples
3.0 - Strong response with clear implementation
4.0 - Exceptional detail and practical insight

Format response as:
{{
    "score": X.X,
    "strengths": ["specific strength 1", "specific strength 2"],
    "areas_for_improvement": ["specific area 1", "specific area 2"],
    "feedback": "brief constructive feedback"
}}"""
        
        try:
            result = self._call_ollama(prompt, system_prompt)
            return json.loads(result)
        except:
            return {
                "score": 1.0,
                "strengths": [],
                "areas_for_improvement": ["Unable to evaluate response"],
                "feedback": "Error processing response"
            }

    def generate_final_feedback(self, metric_scores: Dict[str, List[Dict]]) -> Dict:
        """Generate comprehensive final feedback"""
        system_prompt = """You are providing final assessment feedback.
        Focus on observed behaviors and practical recommendations.
        Maintain confidentiality and professionalism."""
        
        feedback_prompt = f"""Generate final assessment feedback:

Performance Data:
{json.dumps(metric_scores, indent=2)}

Requirements:
1. Focus on demonstrated behaviors
2. Provide specific examples
3. Suggest practical development actions
4. Maintain confidentiality
5. Be constructive and actionable

Format response as:
{{
    "metrics": {{
        "metric_name": {{
            "score": X.X,
            "key_behaviors": ["observed behavior 1", "observed behavior 2"],
            "development_priorities": ["priority 1", "priority 2"],
            "action_steps": ["specific action 1", "specific action 2"]
        }}
    }},
    "overall_assessment": {{
        "score": X.X,
        "strengths": ["key strength 1", "key strength 2"],
        "development_areas": ["area 1", "area 2"],
        "recommendations": ["recommendation 1", "recommendation 2"]
    }}
}}"""
        
        try:
            result = self._call_ollama(feedback_prompt, system_prompt)
            return json.loads(result)
        except:
            return {
                "metrics": {},
                "overall_assessment": {
                    "score": 1.0,
                    "strengths": [],
                    "development_areas": ["Unable to generate feedback"],
                    "recommendations": ["System error - please review manually"]
                }
            }
