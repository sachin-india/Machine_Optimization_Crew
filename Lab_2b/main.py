#!/usr/bin/env python3
"""
Simple demonstration of tool enforcement challenges in CrewAI
This shows how hard it is to force an LLM agent to use a tool.
"""

import sys
import warnings
from crew import SimpleManufacturingCrew
from tool_selector import ToolSelector
from calculator_tool import reset_tool_tracker, was_tool_called, manufacturing_cost_calculator

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def main():
    print("=== SIMPLE TOOL ENFORCEMENT ===")

    # Select machines and demand
    selector = ToolSelector("input/allocation_tools.csv")
    problem_input = selector.select_tools(3, demand=3000)

    print("Selected machines:")
    for name, specs in problem_input['machines'].items():
        print(f"  {name}: Capacity={specs['capacity']}, Variable=${specs['variable_cost']}, Fixed=${specs['fixed_cost']}")

    print(f"\nDemand: {problem_input['product_demand']} units")

    # Reset tool tracker and run the crew
    reset_tool_tracker()
    print("\n=== RUNNING CREW ===")
    crew = SimpleManufacturingCrew()
    crew.set_problem_context(problem_input)
    crew_output = crew.crew().kickoff(inputs=problem_input)
    result = crew_output.pydantic

    # Print concise results
    print(f"\n=== RESULTS ===")
    print(f"Strategy: {result.strategy_name}")
    print(f"Allocation: {result.machine_allocations}")

    # Authoritative cost via the tool (single final print)
    try:
        enforced = manufacturing_cost_calculator(
            machines=problem_input['machines'],
            demand=problem_input['product_demand'],
            allocation=result.machine_allocations
        )
        print(f"Total Cost (tool): ${enforced['total_cost']}")
    except Exception as e:
        print(f"Could not compute enforced total cost: {e}")
        print(f"Total Cost (agent): ${getattr(result, 'total_cost', 'N/A')}")

    # Tool usage check (concise)
    print(f"\n=== TOOL USAGE CHECK ===")
    if was_tool_called():
        print("✅ SUCCESS: Agent used the calculator tool!")
    else:
        print("❌ PROBLEM: Agent did NOT use the calculator tool!")
        print("Router enforcement will compute authoritative totals (if possible).")
        try:
            allocation = result.machine_allocations
            enforced = manufacturing_cost_calculator(
                machines=problem_input['machines'],
                demand=problem_input['product_demand'],
                allocation=allocation
            )
            print(f"Enforced Total Cost (tool): ${enforced['total_cost']}")
        except Exception as e:
            print(f"Router enforcement failed: {e}")

if __name__ == "__main__":
    main()
