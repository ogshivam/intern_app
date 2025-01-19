#!/usr/bin/env python3
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
from llm_handler import LLMHandler
from evaluator import ResponseEvaluator, ConversationTracker

def load_json(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        return json.load(f)

class AssessmentCLI:
    def __init__(self):
        self.case_doc = load_json('case_doc.json')
        self.metrics = load_json('metrics.json')
        self.llm_handler = LLMHandler(self.case_doc, self.metrics)
        self.evaluator = ResponseEvaluator(self.metrics)
        self.conversation = ConversationTracker()
        self.responses = []
        self.current_metric = None
        self.questions_per_metric = 5  # Default value
        
    def get_assessment_mode(self) -> int:
        """Get the assessment mode from user"""
        while True:
            print("\nSelect Assessment Mode:")
            print("1. Quick Assessment (3 questions, 1 per metric)")
            print("2. Full Assessment (15 questions, 5 per metric)")
            
            try:
                choice = input("\nEnter your choice (1 or 2): ").strip()
                if choice == "1":
                    return 1
                elif choice == "2":
                    return 5
                else:
                    print("Please enter either 1 or 2.")
            except ValueError:
                print("Invalid input. Please enter 1 or 2.")
        
    def get_valid_response(self, question: str) -> Optional[str]:
        """Get and validate user response"""
        max_attempts = 3  # Maximum attempts for invalid responses
        attempts = 0
        
        # Track assessor question
        self.conversation.add_interaction("assessor", question)
        
        while attempts < max_attempts:
            # Only print question on first attempt
            if attempts == 0:
                print(f"\nAssessor: {question}")
                
            response = input("\nYour response: ").strip()
            
            # Track candidate response
            self.conversation.add_interaction("candidate", response)
            
            # Check for exit command
            if response.lower() in ['exit', 'quit']:
                print("\nEnding assessment. Thank you for participating!")
                return None
                
            # Validate response
            is_valid, feedback = self.llm_handler.validate_response(response)
            if is_valid:
                return response
                
            print(f"\n{feedback}")
            print("Please try again with a more detailed response.")
            attempts += 1
            
            # Track feedback
            self.conversation.add_interaction("system", feedback)
            
        print("\nToo many invalid responses. Moving to next question...")
        return None
        
    def display_metric_scores(self, metric_scores: Dict):
        """Display scores for each metric"""
        print("\nDetailed Scores by Metric:")
        print("=" * 50)
        
        for metric, scores in metric_scores.items():
            print(f"\n{self.metrics['aspects'][metric]['name']}:")
            print(f"Average Score: {scores['average_score']:.2f}/{scores['max_possible']:.2f}")
            print(f"Percentage: {scores['percentage']:.1f}%")
            print("\nBreakdown of Individual Responses:")
            
            for i, score in enumerate(scores['individual_scores'], 1):
                print(f"\nResponse {i}:")
                for criterion, value in score['scores'].items():
                    print(f"- {criterion.title()}: {value:.2f}")
                print(f"Total: {score['total']:.2f}/{score['max_possible']}")
                
    def display_overall_score(self, overall_score: float, max_score: float, percentage: float):
        """Display overall assessment score"""
        print("\nOverall Assessment Score:")
        print("=" * 50)
        print(f"\nFinal Score: {overall_score:.2f}/{max_score:.2f}")
        print(f"Percentage: {percentage:.1f}%")
        
        # Add performance level
        if percentage >= 90:
            level = "Exceptional"
        elif percentage >= 80:
            level = "Advanced"
        elif percentage >= 70:
            level = "Proficient"
        elif percentage >= 60:
            level = "Developing"
        else:
            level = "Needs Improvement"
            
        print(f"Performance Level: {level}")
        
    def display_welcome(self):
        """Display welcome message and assessment instructions"""
        print("\n=== Prime Finance Role Play Assessment ===")
        print("\nScenario:", self.case_doc['context']['description'])
        print("\nYour Role:", self.case_doc['context']['roles']['general_manager']['responsibility'])
        print("\nInstructions:")
        for instruction in self.case_doc['instructions']:
            print(f"- {instruction}")
            
    def run_assessment(self):
        """Run the main assessment loop"""
        self.display_welcome()
        print("\nYou have 25 minutes for this assessment.")
        print("Take 5 minutes to prepare, then we'll begin the interaction.")
        
        # 5-minute preparation time
        for i in range(5, 0, -1):
            print(f"\rPreparation time remaining: {i} minutes...", end='')
            # In real implementation, use time.sleep(60)
            
        print("\n\nTime's up! Let's begin the assessment.")
        input("\nPress Enter when you're ready...")
        
        # Get assessment mode
        self.questions_per_metric = self.get_assessment_mode()
        mode_name = "Quick" if self.questions_per_metric == 1 else "Full"
        total_questions = self.questions_per_metric * 3  # 3 metrics
        
        print(f"\nStarting {mode_name} Assessment")
        print(f"Total questions: {total_questions} ({self.questions_per_metric} per metric)")
        
        # Initial question about case understanding
        print("\nFirst, let's discuss your understanding of the case.")
        initial_question = self.llm_handler.generate_initial_question()
        
        # Get initial response
        response = self.get_valid_response(initial_question)
        if not response:
            return
            
        self.responses.append(("initial", response))
        
        # Main assessment loop
        question_count = 0
        while True:
            # Generate follow-up question
            result = self.llm_handler.generate_followup_question(response)
            if not result:
                break
                
            question, metric = result
            
            # Check if we've reached the limit for this metric
            if self.responses.count((metric, None)) >= self.questions_per_metric:
                continue
                
            # Print metric header if changing metrics
            if metric != self.current_metric:
                self.current_metric = metric
                print(f"\n=== Now let's focus on {self.metrics['aspects'][metric]['name']} ===")
                print(f"We'll evaluate your {self.metrics['aspects'][metric]['description'].lower()}")
            
            # Get response with validation
            response = self.get_valid_response(question)
            if not response:
                continue  # Skip to next question if response is invalid
                
            # Store response and evaluate
            self.responses.append((metric, response))
            evaluation = self.evaluator.evaluate_response(metric, response)
            
            # Update question count
            question_count += 1
            if question_count >= total_questions:
                break
            
        # Generate final feedback and scores
        print("\n=== Assessment Complete ===")
        results = self.evaluator.generate_final_feedback(self.responses)
        
        # Display detailed scores
        self.display_metric_scores(results['metrics'])
        self.display_overall_score(
            results['overall_score'],
            results['max_score'],
            results['percentage']
        )
        
        # Save session data
        session_file = f"assessment_session_{mode_name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.conversation.save_session(results, session_file)
        print(f"\nSession data saved to: {session_file}")

def main():
    try:
        cli = AssessmentCLI()
        cli.run_assessment()
    except KeyboardInterrupt:
        print("\nAssessment terminated by user.")
        # In real implementation, use sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        # In real implementation, use sys.exit(1)

if __name__ == "__main__":
    main()
