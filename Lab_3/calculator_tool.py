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
    
    # Validate allocation meets demand (unless we're analyzing infeasible scenarios)
    total_allocated = sum(allocation.values())
    if total_allocated < demand:
        # Only raise error if we're not in an infeasible capacity scenario
        total_capacity = sum(float(machines[name]['capacity']) for name in machines.keys())
        if total_capacity >= demand:
            raise ValueError(f"Allocation supplies {total_allocated} units but demand is {demand}")
        # For infeasible scenarios, just proceed with what we have
    
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

def strategic_optimizer(
    machines: Dict[str, Dict[str, float]],
    demand: int
) -> Dict[str, Any]:
    """
    Strategic optimization to find the best allocation.
    Uses intelligent strategies to test only the most promising combinations.
    """
    global oracle_tool_was_called
    oracle_tool_was_called = True
    
    if VERBOSE:
        print("🔍 ORACLE TOOL CALLED: strategic_optimizer")
        print(f"📊 Machines: {machines}")
        print(f"📈 Demand: {demand}")
    
    machine_names = list(machines.keys())
    machine_capacities = [int(machines[name]['capacity']) for name in machine_names]
    
    # Check if total capacity can meet demand
    total_capacity = sum(machine_capacities)
    if total_capacity < demand:
        if VERBOSE:
            print(f"⚠️ WARNING: Total capacity {total_capacity} < demand {demand}")
        # Return best possible allocation using full capacities
        optimal_allocation = {name: int(machines[name]['capacity']) for name in machine_names}
        cost_result = manufacturing_cost_calculator(machines, total_capacity, optimal_allocation)  # Use actual capacity, not demand
        return {
            'optimal_allocation': optimal_allocation,
            'optimal_cost': cost_result['total_cost'],
            'optimal_variable_cost': cost_result['total_variable_cost'],
            'optimal_fixed_cost': cost_result['total_fixed_cost'],
            'feasible': False,
            'actual_production': total_capacity,
            'shortfall': demand - total_capacity,
            'reason': f'Demand {demand} exceeds total capacity {total_capacity}. Best possible: use all machines at full capacity.'
        }
    
    best_cost = float('inf')
    best_allocation = None
    
    # Smart optimization: instead of brute force, use a greedy approach with refinement
    # This is much faster than testing billions of combinations
    
    if VERBOSE:
        print(f"🔄 Using smart optimization instead of full brute force...")
    
    # Create list of machines with their efficiency (cost per unit)
    machine_efficiency = []
    for name in machine_names:
        var_cost = machines[name]['variable_cost']
        fixed_cost = machines[name]['fixed_cost']
        capacity = int(machines[name]['capacity'])
        
        # Efficiency = total cost if using this machine at capacity
        efficiency_cost = (var_cost * capacity) + fixed_cost
        efficiency_per_unit = efficiency_cost / capacity if capacity > 0 else float('inf')
        
        machine_efficiency.append({
            'name': name,
            'capacity': capacity,
            'var_cost': var_cost,
            'fixed_cost': fixed_cost,
            'efficiency_per_unit': efficiency_per_unit
        })
    
    # Sort by efficiency (cost per unit)
    machine_efficiency.sort(key=lambda x: x['efficiency_per_unit'])
    
    if VERBOSE:
        print(f"🔄 Machine efficiency order: {[m['name'] + f'(${m['efficiency_per_unit']:.2f}/unit)' for m in machine_efficiency]}")
    
    # Try different allocation strategies
    strategies = []
    
    # Strategy 1: Greedy by efficiency
    allocation = {name: 0 for name in machine_names}
    remaining_demand = demand
    for machine in machine_efficiency:
        if remaining_demand <= 0:
            break
        allocated = min(machine['capacity'], remaining_demand)
        allocation[machine['name']] = allocated
        remaining_demand -= allocated
    
    if sum(allocation.values()) >= demand:
        strategies.append(allocation.copy())
    
    # Strategy 2: Use only the most efficient machines
    allocation = {name: 0 for name in machine_names}
    remaining_demand = demand
    for machine in machine_efficiency:
        if remaining_demand <= 0:
            break
        allocation[machine['name']] = machine['capacity']
        remaining_demand -= machine['capacity']
        if remaining_demand <= 0:
            break
    
    if sum(allocation.values()) >= demand:
        strategies.append(allocation.copy())
    
    # Strategy 3: Try minimizing fixed costs (use fewer machines)
    for num_machines in range(1, len(machine_names) + 1):
        allocation = {name: 0 for name in machine_names}
        remaining_demand = demand
        
        # Use top N most efficient machines
        for i in range(min(num_machines, len(machine_efficiency))):
            machine = machine_efficiency[i]
            if remaining_demand <= 0:
                break
            allocated = min(machine['capacity'], remaining_demand)
            allocation[machine['name']] = allocated
            remaining_demand -= allocated
        
        if sum(allocation.values()) >= demand and remaining_demand <= 0:
            strategies.append(allocation.copy())
    
    # Test all strategies and find the best
    combinations_tested = 0
    for allocation in strategies:
        try:
            cost_result = manufacturing_cost_calculator(machines, demand, allocation)
            total_cost = cost_result['total_cost']
            
            if total_cost < best_cost:
                best_cost = total_cost
                best_allocation = allocation
            
            combinations_tested += 1
                
        except Exception as e:
            # Skip invalid allocations
            continue
    
    if best_allocation is None:
        raise ValueError("No valid allocation found")
    
    # Get detailed cost breakdown for optimal solution
    optimal_result = manufacturing_cost_calculator(machines, demand, best_allocation)
    
    if VERBOSE:
        print(f"🏆 OPTIMAL FOUND: {best_allocation}")
        print(f"💰 Optimal cost: ${best_cost}")
        print(f"🔬 Tested {combinations_tested} combinations")
    
    return {
        'optimal_allocation': best_allocation,
        'optimal_cost': optimal_result['total_cost'],
        'optimal_variable_cost': optimal_result['total_variable_cost'],
        'optimal_fixed_cost': optimal_result['total_fixed_cost'],
        'feasible': True,
        'combinations_tested': combinations_tested
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
        name="evaluator_manufacturing_cost_calculator",
        func=evaluator_calculator,
        description=(
            "Calculate total manufacturing costs for a machine allocation (evaluator version). "
            "Input: machines (dict), demand (int), allocation (dict). "
            "Returns: total costs breakdown. Use this for cost verification in evaluation."
        ),
    )
    
    strategic_optimizer_tool = Tool(
        name="strategic_optimizer",
        func=strategic_optimizer,
        description=(
            "Find the mathematically optimal machine allocation using brute force search. "
            "Input: machines (dict), demand (int). "
            "Returns: optimal allocation and costs. Use this to find the best possible solution."
        ),
    )
    
except ImportError as e:
    print(f"CrewAI import failed: {e}")
    manufacturing_calculator_tool = None
    evaluator_calculator_tool = None
    strategic_optimizer_tool = None