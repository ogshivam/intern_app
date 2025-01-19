#!/usr/bin/env python3
import json
import sys
import time
from typing import Dict, List, Optional, Tuple
from llm_handler import LLMHandler
from utils import load_json_file, format_score

class AssessmentCLI:
    def __init__(self):
        self.case_doc = load_json_file('case_doc_latest.json')
        self.metrics = load_json_file('metrics.json')
        self.llm_handler = LLMHandler(self.case_doc, self.metrics)
        self.responses = []
        self.current_metric = None
        
    def display_welcome(self):
        """Display welcome message and assessment instructions"""
        print("\n=== Prime Finance Role Play Assessment ===")
        print("\nScenario:", self.case_doc['context']['description'])
        print("\nYour Role:", self.case_doc['context']['roles']['general_manager']['responsibility'])
        print("\nInstructions:")
        for instruction in self.case_doc['instructions']:
            print(f"- {instruction}")
            
    def get_valid_response(self, question: str) -> Optional[str]:
        """Get and validate user response"""
        max_attempts = 3  # Maximum attempts for invalid responses
        attempts = 0
        
        while attempts < max_attempts:
            # Only print question on first attempt
            if attempts == 0:
                print(f"\nAssessor: {question}")
                
            response = input("\nYour response: ").strip()
            
            # Check for exit command
            if response.lower() in ['exit', 'quit']:
                print("\nEnding assessment. Thank you for participating!")
                sys.exit(0)
                
            # Validate response
            is_valid, feedback = self.llm_handler.validate_response(response)
            if is_valid:
                return response
                
            print(f"\n{feedback}")
            print("Please try again with a more detailed response.")
            attempts += 1
            
        print("\nToo many invalid responses. Moving to next question...")
        return None
        
    def run_assessment(self):
        """Run the main assessment loop"""
        self.display_welcome()
        print("\nYou have 25 minutes for this assessment.")
        print("Take 5 minutes to prepare, then we'll begin the interaction.")
        
        # 5-minute preparation time
        for i in range(5, 0, -1):
            print(f"\rPreparation time remaining: {i} minutes...", end='')
            time.sleep(1)  # In real implementation, use time.sleep(60)
            
        print("\n\nTime's up! Let's begin the assessment.")
        input("\nPress Enter when you're ready...")
        
        # Initial question about case understanding
        print("\nFirst, let's discuss your understanding of the case.")
        initial_question = self.llm_handler.generate_initial_question()
        
        # Get initial response
        response = self.get_valid_response(initial_question)
        if not response:
            return
            
        self.responses.append(("initial", response))
        
        # Main assessment loop
        while True:
            # Generate follow-up question
            result = self.llm_handler.generate_followup_question(response)
            if not result:
                break
                
            question, metric = result
            
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
            evaluation = self.llm_handler.evaluate_response(metric, response)
            
        # Assessment complete
        print("\n=== Assessment Complete ===")
        
        # Generate final feedback
        feedback = self.llm_handler.generate_final_feedback(self.responses)
        self.display_results(feedback)
        
    def display_results(self, feedback: Dict):
        """Display assessment results and feedback"""
        print("\n=== Assessment Results ===")
        
        # Display individual metric results
        for metric, details in feedback['metrics'].items():
            metric_name = self.metrics['aspects'][metric]['name']
            print(f"\n{metric_name}:")
            print(f"Score: {format_score(details['average_score'])}")
            print("Strengths:", details['strengths'])
            print("Areas for Improvement:", details['improvements'])
            if 'action_items' in details:
                print("Action Items:", details['action_items'])
            
        # Display overall results
        print(f"\nOverall Score: {format_score(feedback['overall_score'])}")
        print("\nSummary:", feedback['summary'])

def main():
    try:
        cli = AssessmentCLI()
        cli.run_assessment()
    except KeyboardInterrupt:
        print("\nAssessment terminated by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
