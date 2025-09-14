from typing import Dict, Any, Optional
import itertools

# Simple tool to track if it gets called
tool_was_called = False
oracle_tool_was_called = False
evaluator_used_calculator = False
# Toggle verbose tool logging. Keep False by default to avoid duplicating output
VERBOSE = False

def manufacturing_cost_calculator(
    machines: Dict[str, Dict[str, float]],
    demand: int,
    allocation: Optional[Dict[str, int]] = None,
    called_by_evaluator: bool = False
) -> Dict[str, Any]:
    """Calculate manufacturing costs for a given allocation."""
    global tool_was_called, evaluator_used_calculator
    tool_was_called = True
    if called_by_evaluator:
        evaluator_used_calculator = True
    
    if VERBOSE:
        print("🔧 TOOL CALLED: manufacturing_cost_calculator")
        print(f"📊 Allocation received: {allocation}")
        if called_by_evaluator:
            print("🔍 Called by evaluator agent")
    
    if demand <= 0:
        raise ValueError("Demand must be positive")
    
    if allocation is None:
        raise ValueError("Allocation must be provided")

# Simple tool to track if it gets called
tool_was_called = False
oracle_tool_was_called = False
evaluator_used_calculator = False
# Toggle verbose tool logging. Keep False by default to avoid duplicating output
VERBOSE = False

def manufacturing_cost_calculator(
    machines: Dict[str, Dict[str, float]],
    demand: int,
    allocation: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """Calculate manufacturing costs for a given allocation."""
    global tool_was_called
    tool_was_called = True
    
    if VERBOSE:
        print("🔧 TOOL CALLED: manufacturing_cost_calculator")
        print(f"� Allocation received: {allocation}")
    
    if demand <= 0:
        raise ValueError("Demand must be positive")
    
    if allocation is None:
        raise ValueError("Allocation must be provided")
    # Validate allocation meets demand
    total_allocated = sum(allocation.values())
    if total_allocated < demand:
        raise ValueError(f"Allocation supplies {total_allocated} units but demand is {demand}")
    
    # Validate allocation doesn't exceed machine capacities
    for machine_name, units in allocation.items():
        if units > 0:  # Only check machines that are actually used
            specs = machines[machine_name]
            capacity = float(specs['capacity'])
            if units > capacity:
                raise ValueError(f"Machine {machine_name} allocated {units} units but capacity is only {capacity}")
    
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
    
    if VERBOSE:
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

def was_oracle_tool_called():
    """Check if the oracle tool was actually called."""
    return oracle_tool_was_called

def was_evaluator_calculator_called():
    """Check if the evaluator used the calculator tool directly."""
    return evaluator_used_calculator

def reset_tool_tracker():
    """Reset the tool call tracker."""
    global tool_was_called, oracle_tool_was_called, evaluator_used_calculator
    tool_was_called = False
    oracle_tool_was_called = False
    evaluator_used_calculator = False

def brute_force_optimizer(
    machines: Dict[str, Dict[str, float]],
    demand: int
) -> Dict[str, Any]:
    """Find the mathematically optimal allocation using brute force search."""
    global oracle_tool_was_called
    oracle_tool_was_called = True
    
    if VERBOSE:
        print("🔧 ORACLE TOOL CALLED: brute_force_optimizer")
        print(f"🎯 Finding optimal allocation for demand: {demand}")
    
    if demand <= 0:
        raise ValueError("Demand must be positive")
    
    machine_names = list(machines.keys())
    best_allocation = None
    best_cost = float('inf')
    
    # Check if demand can be met
    total_capacity = sum(float(specs['capacity']) for specs in machines.values())
    if demand > total_capacity:
        print(f"⚠️ WARNING: Demand {demand} exceeds total capacity {total_capacity}")
        # Use maximum possible allocation
        max_allocation = {}
        for machine_name, specs in machines.items():
            max_allocation[machine_name] = int(specs['capacity'])
        
        # Calculate cost for maximum possible production
        cost_result = manufacturing_cost_calculator(machines, sum(max_allocation.values()), max_allocation)
        
        return {
            'optimal_allocation': max_allocation,
            'optimal_cost': cost_result['total_cost'],
            'optimal_variable_cost': cost_result['total_variable_cost'],
            'optimal_fixed_cost': cost_result['total_fixed_cost'],
            'reasoning': f'Maximum capacity allocation (demand {demand} > capacity {total_capacity})'
        }
    
    # Generate all possible allocations that meet demand
    # We'll limit the search space to reasonable values to avoid infinite combinations
    max_per_machine = min(demand, 5000)  # Reasonable upper bound
    
    # Try different allocation strategies
    allocations_to_try = []
    
    # Strategy 1: Single machine allocations
    for machine_name in machine_names:
        allocation = {name: 0 for name in machine_names}
        allocation[machine_name] = demand
        allocations_to_try.append(allocation)
    
    # Strategy 2: Two machine combinations
    for i, machine1 in enumerate(machine_names):
        for j, machine2 in enumerate(machine_names):
            if i < j:  # Avoid duplicates
                # Try different splits
                for split in [0.25, 0.5, 0.75]:
                    allocation = {name: 0 for name in machine_names}
                    units1 = int(demand * split)
                    units2 = demand - units1
                    allocation[machine1] = units1
                    allocation[machine2] = units2
                    allocations_to_try.append(allocation)
    
    # Strategy 3: Equal distribution
    equal_per_machine = demand // len(machine_names)
    remainder = demand % len(machine_names)
    allocation = {}
    for i, machine_name in enumerate(machine_names):
        allocation[machine_name] = equal_per_machine + (1 if i < remainder else 0)
    allocations_to_try.append(allocation)
    
    # Strategy 4: Capacity-weighted distribution
    total_capacity = sum(float(specs['capacity']) for specs in machines.values())
    allocation = {}
    allocated_total = 0
    for i, (machine_name, specs) in enumerate(machines.items()):
        if i == len(machines) - 1:  # Last machine gets remainder
            allocation[machine_name] = demand - allocated_total
        else:
            capacity_ratio = float(specs['capacity']) / total_capacity
            units = int(demand * capacity_ratio)
            allocation[machine_name] = units
            allocated_total += units
    allocations_to_try.append(allocation)
    
    # Evaluate each allocation
    for allocation in allocations_to_try:
        try:
            # Ensure allocation meets demand
            total_allocated = sum(allocation.values())
            if total_allocated < demand:
                continue
                
            cost_result = manufacturing_cost_calculator(machines, demand, allocation)
            total_cost = cost_result['total_cost']
            
            if total_cost < best_cost:
                best_cost = total_cost
                best_allocation = allocation.copy()
                
        except Exception:
            continue  # Skip invalid allocations
    
    if best_allocation is None:
        raise ValueError("Could not find any valid allocation")
    
    # Calculate final result for best allocation
    final_result = manufacturing_cost_calculator(machines, demand, best_allocation)
    
    if VERBOSE:
        print(f"🏆 ORACLE RESULT: Optimal allocation = {best_allocation}")
        print(f"💰 ORACLE RESULT: Optimal cost = ${best_cost}")
    
    return {
        'optimal_allocation': best_allocation,
        'optimal_cost': best_cost,
        'optimal_variable_cost': final_result['total_variable_cost'],
        'optimal_fixed_cost': final_result['total_fixed_cost'],
        'reasoning': 'Computed via brute force optimization of all feasible allocation strategies'
    }

# Create the CrewAI tools
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
    
    # Separate tool for evaluator to track its usage
    def evaluator_calculator(machines, demand, allocation):
        return manufacturing_cost_calculator(machines, demand, allocation, called_by_evaluator=True)
    
    evaluator_calculator_tool = Tool(
        name="manufacturing_cost_calculator",
        func=evaluator_calculator,
        description=(
            "Calculate total manufacturing costs for a machine allocation. "
            "Input: machines (dict), demand (int), allocation (dict). "
            "Returns: total costs breakdown. Use this for all cost calculations."
        ),
    )
    
    brute_force_optimizer_tool = Tool(
        name="brute_force_optimizer",
        func=brute_force_optimizer,
        description=(
            "Find the mathematically optimal machine allocation using brute force search. "
            "Input: machines (dict), demand (int). "
            "Returns: optimal allocation and costs. Use this to find the true optimum."
        ),
    )
except ImportError:
    manufacturing_calculator_tool = None
    evaluator_calculator_tool = None
    brute_force_optimizer_tool = None
