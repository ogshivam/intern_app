from typing import Dict, List, Tuple
import json
from datetime import datetime

class ResponseEvaluator:
    def __init__(self, metrics: Dict):
        self.metrics = metrics
        self.max_score = 10  # Max score per question
        self.criteria = {
            "Clear Communication": {
                "clarity": 0.3,  # Weight for clarity of response
                "structure": 0.2,  # Weight for organized structure
                "completeness": 0.3,  # Weight for completeness of response
                "examples": 0.2   # Weight for relevant examples
            },
            "Engaging Discussions": {
                "interaction": 0.3,  # Weight for interactive elements
                "depth": 0.3,      # Weight for depth of discussion
                "relevance": 0.2,   # Weight for topic relevance
                "flow": 0.2        # Weight for conversation flow
            },
            "Active Engagement": {
                "initiative": 0.3,  # Weight for taking initiative
                "responsiveness": 0.3,  # Weight for response quality
                "contribution": 0.2,    # Weight for meaningful contributions
                "consistency": 0.2      # Weight for consistent engagement
            }
        }
        
    def evaluate_response(self, metric: str, response: str) -> Dict:
        """Evaluate a single response based on metric criteria"""
        weights = self.criteria[metric]
        scores = {}
        
        # Evaluate each criterion
        for criterion, weight in weights.items():
            score = self._evaluate_criterion(criterion, response)
            scores[criterion] = score * weight * self.max_score
            
        total_score = sum(scores.values())
        return {
            "scores": scores,
            "total": total_score,
            "max_possible": self.max_score,
            "percentage": (total_score / self.max_score) * 100
        }
        
    def _evaluate_criterion(self, criterion: str, response: str) -> float:
        """Evaluate a specific criterion in the response"""
        response = response.lower()
        score = 0.0
        
        # Clarity evaluation
        if criterion == "clarity":
            words = len(response.split())
            if words >= 50:  # Good length for clarity
                score += 0.5
            if any(marker in response for marker in ["first", "second", "then", "finally"]):
                score += 0.3
            if not any(vague for vague in ["maybe", "probably", "might", "could be"]):
                score += 0.2
                
        # Structure evaluation
        elif criterion == "structure":
            if any(marker in response for marker in ["first", "second", "then", "finally"]):
                score += 0.4
            if response.count(".") >= 3:  # Multiple complete sentences
                score += 0.3
            if any(marker in response for marker in ["because", "therefore", "thus", "hence"]):
                score += 0.3
                
        # Completeness evaluation
        elif criterion == "completeness":
            if len(response.split()) >= 75:  # Comprehensive response
                score += 0.4
            if response.count(",") >= 2:  # Multiple points
                score += 0.3
            if any(marker in response for marker in ["for example", "such as", "including"]):
                score += 0.3
                
        # Examples evaluation
        elif criterion == "examples":
            if any(marker in response for marker in ["for example", "such as", "like", "instance"]):
                score += 0.6
            if response.count("example") > 1:  # Multiple examples
                score += 0.4
                
        # Interaction evaluation
        elif criterion == "interaction":
            if any(marker in response for marker in ["agree", "disagree", "suggest", "propose"]):
                score += 0.5
            if "?" in response:  # Asking questions
                score += 0.5
                
        # Depth evaluation
        elif criterion == "depth":
            if len(response.split()) >= 100:  # Detailed response
                score += 0.4
            if any(marker in response for marker in ["because", "therefore", "however", "although"]):
                score += 0.3
            if response.count(",") >= 3:  # Multiple points
                score += 0.3
                
        # Default minimum score
        return max(0.3, min(score, 1.0))  # Ensure score is between 0.3 and 1.0
        
    def generate_final_feedback(self, responses: List[Tuple[str, str]]) -> Dict:
        """Generate comprehensive feedback and scores"""
        metric_scores = {}
        total_score = 0
        max_possible = 0
        
        # Calculate scores per metric
        for metric in self.metrics['aspects'].keys():
            metric_responses = [r for m, r in responses if m == metric]
            if metric_responses:
                scores = [self.evaluate_response(metric, r) for r in metric_responses]
                avg_score = sum(s['total'] for s in scores) / len(scores)
                max_score = sum(s['max_possible'] for s in scores) / len(scores)
                metric_scores[metric] = {
                    "average_score": avg_score,
                    "max_possible": max_score,
                    "percentage": (avg_score / max_score) * 100,
                    "individual_scores": scores
                }
                total_score += avg_score
                max_possible += max_score
        
        # Calculate overall score out of 30
        overall_score = (total_score / max_possible) * 30
        
        return {
            "metrics": metric_scores,
            "overall_score": overall_score,
            "max_score": 30,
            "percentage": (overall_score / 30) * 100
        }

class ConversationTracker:
    def __init__(self):
        self.conversation = []
        self.start_time = datetime.now()
        
    def add_interaction(self, role: str, content: str):
        """Add an interaction to the conversation"""
        self.conversation.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def generate_summary(self) -> Dict:
        """Generate a summary of the conversation"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_interactions": len(self.conversation),
            "conversation": self.conversation
        }
        
    def save_session(self, evaluation_results: Dict, file_path: str):
        """Save the complete session data"""
        session_data = {
            "summary": self.generate_summary(),
            "evaluation": evaluation_results,
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat()
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2)
