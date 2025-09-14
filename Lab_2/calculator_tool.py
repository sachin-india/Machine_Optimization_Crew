from typing import Dict, Any, Optional

# Simple tool to track if it gets called
tool_was_called = False

def manufacturing_cost_calculator(
    machines: Dict[str, Dict[str, float]],
    demand: int,
    allocation: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """Calculate manufacturing costs for a given allocation."""
    global tool_was_called
    tool_was_called = True
    
    print("🔧 TOOL CALLED: manufacturing_cost_calculator")
    print(f"� Allocation received: {allocation}")
    
    if demand <= 0:
        raise ValueError("Demand must be positive")
    
    if allocation is None:
        raise ValueError("Allocation must be provided")
    
    # Calculate costs
    total_variable = 0.0
    total_fixed = 0.0
    
    for machine_name, units in allocation.items():
        if units > 0:  # Only count if machine is used
            specs = machines[machine_name]
            variable_cost = float(specs['variable_cost']) * units
            fixed_cost = float(specs['fixed_cost'])
            
            total_variable += variable_cost
            total_fixed += fixed_cost
    
    total_cost = total_variable + total_fixed
    
    print(f"💰 TOOL RESULT: Total cost = ${total_cost}")
    
    return {
        'machine_allocations': allocation,
        'total_variable_cost': round(total_variable, 2),
        'total_fixed_cost': round(total_fixed, 2),
        'total_cost': round(total_cost, 2)
    }

def was_tool_called():
    """Check if the tool was actually called."""
    return tool_was_called

def reset_tool_tracker():
    """Reset the tool call tracker."""
    global tool_was_called
    tool_was_called = False

# Create the CrewAI tool
try:
    from crewai import Tool
    manufacturing_calculator_tool = Tool(
        name="manufacturing_cost_calculator",
        func=manufacturing_cost_calculator,
        description=(
            "Calculate total manufacturing costs for a machine allocation. "
            "Input: machines (dict), demand (int), allocation (dict). "
            "Returns: total costs breakdown. Use this for all cost calculations."
        ),
    )
except ImportError:
    manufacturing_calculator_tool = None
