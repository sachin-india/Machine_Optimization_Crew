#!/usr/bin/env python3
"""
Simple demonstration of tool enforcement challenges in CrewAI
This shows how hard it is to force an LLM agent to use a tool.
"""

import sys
import warnings
from crew import SimpleManufacturingCrew
from tool_selector import ToolSelector
from calculator_tool import (
    reset_tool_tracker, 
    manufacturing_cost_calculator,
    was_tool_called,
    was_oracle_tool_called,
    was_evaluator_calculator_called
)

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def main():
    print("=== MANUFACTURING OPTIMIZATION WITH EVALUATION ===")

    # Select machines and demand
    selector = ToolSelector("input/allocation_tools.csv")
    problem_input = selector.select_tools(3, demand=3000)

    print("Selected machines:")
    for name, specs in problem_input['machines'].items():
        print(f"  {name}: Capacity={specs['capacity']}, Variable=${specs['variable_cost']}, Fixed=${specs['fixed_cost']}")

    print(f"\nDemand: {problem_input['product_demand']} units")

    # Reset tool tracker and run the crew
    reset_tool_tracker()
    print("\n=== RUNNING CREW WITH EVALUATION ===")
    crew = SimpleManufacturingCrew()
    crew.set_problem_context(problem_input)
    crew_output = crew.crew().kickoff(inputs=problem_input)
    
    # Extract allocation result and evaluation
    tasks_output = crew_output.tasks_output
    allocation_task_output = tasks_output[0] if tasks_output else None
    evaluation_result = tasks_output[1].raw if len(tasks_output) > 1 else "No evaluation available"

    # Handle allocation result (get the CALLBACK result, not the raw agent response)
    allocation_result = None
    if allocation_task_output:
        # The callback should return the verified tool result
        raw_output = allocation_task_output.raw
        
        # Check if we have the callback result (should be a dict with verified costs)
        if isinstance(raw_output, dict) and 'machine_allocations' in raw_output:
            # This is the verified callback result
            allocation_result = raw_output
        elif hasattr(allocation_task_output, 'pydantic') and allocation_task_output.pydantic:
            # Try pydantic result
            allocation_result = allocation_task_output.pydantic
        else:
            # Fallback: try to parse from the task output
            allocation_result = raw_output

    # Print allocation results with VERIFIED cost from evaluation
    print(f"\n" + "="*50)
    print("📋 FINAL RESULTS")
    print("="*50)
    if allocation_result:
        # Handle allocation data
        if hasattr(allocation_result, 'machine_allocations'):
            machine_allocations = allocation_result.machine_allocations
        else:
            machine_allocations = allocation_result.get('machine_allocations', {})
        
        print(f"Allocation: {machine_allocations}")
        
        # Get VERIFIED cost from evaluation result instead of potentially wrong agent cost
        if evaluation_result and isinstance(evaluation_result, dict):
            verified_cost = evaluation_result.get('allocator_cost', 'Not available')
            print(f"Total Cost: ${verified_cost:,.2f} (verified)")
        else:
            # Fallback to agent's cost if evaluation not available
            total_cost = getattr(allocation_result, 'total_cost', 0) if hasattr(allocation_result, 'total_cost') else allocation_result.get('total_cost', 0)
            print(f"Total Cost: ${total_cost:,.2f} (agent reported)")
    else:
        print("No allocation result available")
    
    # Print simple evaluation
    if evaluation_result and isinstance(evaluation_result, dict):
        if evaluation_result.get('is_optimal'):
            print("🎯 Evaluation: OPTIMAL SOLUTION FOUND!")
        else:
            cost_diff = evaluation_result.get('cost_difference', 0)
            efficiency = evaluation_result.get('efficiency_percentage', 0)
            print(f"💰 Could save: ${cost_diff:,.2f}")
            print(f"📊 Efficiency: {efficiency:.1f}%")
            optimal_allocation = evaluation_result.get('optimal_allocation', {})
            print(f"🎯 Optimal would be: {optimal_allocation}")
    print("="*50)

if __name__ == "__main__":
    main()
