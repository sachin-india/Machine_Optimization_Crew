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

    # Handle allocation result (could be pydantic or dict from callback)
    allocation_result = None
    if allocation_task_output:
        # Check if we have a callback result (which should be a dict)
        raw_output = allocation_task_output.raw
        print(f"🔍 DEBUG: Raw task output = {raw_output}")
        print(f"🔍 DEBUG: Raw output type = {type(raw_output)}")
        
        if isinstance(raw_output, dict):
            # This is the callback result
            allocation_result = raw_output
            print(f"🔍 DEBUG: Using callback result as dict")
        else:
            # Try to parse as JSON or pydantic
            if hasattr(allocation_task_output, 'pydantic') and allocation_task_output.pydantic:
                allocation_result = allocation_task_output.pydantic
                print(f"🔍 DEBUG: Using pydantic result")
            else:
                # Try to parse JSON string
                try:
                    import json, re
                    result_str = str(raw_output).strip()
                    
                    # Try to extract JSON from markdown code blocks
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_str, re.S)
                    if json_match:
                        allocation_result = json.loads(json_match.group(1))
                        print(f"🔍 DEBUG: Parsed JSON from markdown")
                    elif result_str.startswith('{') and result_str.endswith('}'):
                        allocation_result = json.loads(result_str)
                        print(f"🔍 DEBUG: Parsed direct JSON")
                    else:
                        print(f"🔍 DEBUG: Could not parse result: {result_str[:100]}...")
                except Exception as e:
                    print(f"🔍 DEBUG: Error parsing allocation result: {e}")
                    allocation_result = None

    # Print allocation results
    print(f"\n=== ALLOCATION RESULTS ===")
    if allocation_result:
        # Handle pydantic object
        if hasattr(allocation_result, 'strategy_name'):
            strategy = allocation_result.strategy_name
            machine_allocations = allocation_result.machine_allocations
            total_cost = getattr(allocation_result, 'total_cost', 'Not calculated')
        else:
            # Handle dict
            strategy = allocation_result.get('strategy_name', 'Unknown')
            machine_allocations = allocation_result.get('machine_allocations', {})
            total_cost = allocation_result.get('total_cost', 0)
        
        print(f"Strategy: {strategy}")
        print(f"Allocation: {machine_allocations}")
        print(f"Total Cost: ${total_cost}")
    else:
        print("No allocation result available")
    print(f"\n=== EVALUATION RESULTS ===")
    print(evaluation_result)
    
    # Verify tool usage
    print(f"\n=== TOOL USAGE VERIFICATION ===")
    print(f"Allocator used calculator tool: {was_tool_called()}")
    print(f"Evaluator used oracle tool: {was_oracle_tool_called()}")
    print(f"Evaluator used calculator tool: {was_evaluator_calculator_called()}")

    # Authoritative cost via the tool (single final print)
    if allocation_result:
        try:
            print(f"\n=== COST VERIFICATION ===")
            # Handle pydantic object
            if hasattr(allocation_result, 'machine_allocations'):
                machine_allocations = allocation_result.machine_allocations
                total_cost = getattr(allocation_result, 'total_cost', 'Not calculated')
            else:
                machine_allocations = allocation_result.get('machine_allocations', {})
                total_cost = allocation_result.get('total_cost', 0)
            
            print(f"Allocation from agent: {machine_allocations}")
            
            enforced = manufacturing_cost_calculator(
                machines=problem_input['machines'],
                demand=problem_input['product_demand'],
                allocation=machine_allocations
            )
            print(f"Agent reported cost: ${total_cost}")
            print(f"Verified cost: ${enforced['total_cost']}")
            if float(total_cost) != float(enforced['total_cost']):
                print(f"❌ COST MISMATCH: Agent cost ≠ Verified cost")
            else:
                print(f"✅ COST MATCH: Agent and verification agree")
        except Exception as e:
            print(f"Could not compute enforced total cost: {e}")

if __name__ == "__main__":
    main()
