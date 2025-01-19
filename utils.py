import json
from typing import Dict

def load_json_file(filename: str) -> Dict:
    """Load and parse a JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise Exception(f"Required file '{filename}' not found")
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON format in '{filename}'")
    except Exception as e:
        raise Exception(f"Error loading '{filename}': {str(e)}")

def format_score(score: float) -> str:
    """Format a score with one decimal place"""
    return f"{score:.1f}/4.0"
