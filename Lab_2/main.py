#!/usr/bin/env python3
"""
Simple demonstration of tool enforcement challenges in CrewAI
This shows how hard it is to force an LLM agent to use a tool.
"""

import sys
import warnings
from crew import SimpleManufacturingCrew
from tool_selector import ToolSelector
from calculator_tool import reset_tool_tracker, was_tool_called

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def main():
    print("=== TOOL ENFORCEMENT DEMONSTRATION ===")
    print("This demo shows how agents can bypass tool usage even when instructed to use them.\n")
    
    # Select some machines
    selector = ToolSelector("input/allocation_tools.csv")
    problem_input = selector.select_tools(3, demand=3000)
    
    print("Selected machines:")
    for name, specs in problem_input['machines'].items():
        print(f"  {name}: Capacity={specs['capacity']}, Variable=${specs['variable_cost']}, Fixed=${specs['fixed_cost']}")
    
    print(f"\nDemand: {problem_input['product_demand']} units")
    
    # Reset tool tracker
    reset_tool_tracker()
    
    # Run the crew
    print("\n=== RUNNING CREW ===")
    crew = SimpleManufacturingCrew()
    result = crew.crew().kickoff(inputs=problem_input)
    
    # Check if tool was used
    print(f"\n=== TOOL USAGE CHECK ===")
    if was_tool_called():
        print("✅ SUCCESS: Agent used the calculator tool!")
    else:
        print("❌ PROBLEM: Agent did NOT use the calculator tool!")
        print("The agent calculated costs manually instead of using the tool.")
    
    print(f"\n=== LEARNING POINTS ===")
    print("1. LLM agents are smart and prefer to calculate manually")
    print("2. Even strong instructions may not force tool usage")
    print("3. Validation and monitoring are essential in production systems")
    print("4. Tool enforcement is a real challenge in AI systems")

if __name__ == "__main__":
    main()
