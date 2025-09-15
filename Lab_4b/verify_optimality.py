#!/usr/bin/env python3
"""
Verify if the allocation is actually optimal
"""

def calculate_cost(allocation, machines):
    """Calculate total cost for given allocation"""
    total_cost = 0
    for machine, units in allocation.items():
        if units > 0:
            specs = machines[machine]
            total_cost += units * specs['variable_cost'] + specs['fixed_cost']
    return total_cost

def verify_optimality():
    """Check if the found solution is actually optimal"""
    
    # Machines from the test run
    machines = {
        'Tool_157': {'capacity': 1100, 'variable_cost': 7.0, 'fixed_cost': 1500.0},
        'Tool_673': {'capacity': 1000, 'variable_cost': 4.0, 'fixed_cost': 1500.0},
        'Tool_127': {'capacity': 2000, 'variable_cost': 3.0, 'fixed_cost': 500.0},
        'Tool_377': {'capacity': 900, 'variable_cost': 7.0, 'fixed_cost': 5000.0}
    }
    
    demand = 3000
    found_allocation = {'Tool_127': 2000, 'Tool_673': 1000, 'Tool_157': 0, 'Tool_377': 0}
    found_cost = calculate_cost(found_allocation, machines)
    
    print(f"🔍 OPTIMALITY VERIFICATION")
    print(f"Found Solution: {found_allocation}")
    print(f"Found Cost: ${found_cost:,.2f}")
    print()
    
    # Calculate cost per unit for each machine (including amortized fixed cost)
    print("📊 MACHINE EFFICIENCY ANALYSIS:")
    machine_efficiency = []
    for name, specs in machines.items():
        var_cost = specs['variable_cost']
        fixed_cost = specs['fixed_cost']
        capacity = specs['capacity']
        
        # Cost per unit at full capacity
        cost_per_unit_full = var_cost + (fixed_cost / capacity)
        machine_efficiency.append((name, var_cost, fixed_cost, capacity, cost_per_unit_full))
        
        print(f"  {name}: Variable=${var_cost}, Fixed=${fixed_cost}, Capacity={capacity}")
        print(f"    → Cost/unit at full capacity: ${cost_per_unit_full:.2f}")
    
    print()
    
    # Sort by efficiency (cost per unit)
    machine_efficiency.sort(key=lambda x: x[4])  # Sort by cost per unit
    
    print("🏆 MACHINES RANKED BY EFFICIENCY (cost per unit):")
    for i, (name, var_cost, fixed_cost, capacity, cost_per_unit) in enumerate(machine_efficiency, 1):
        print(f"  {i}. {name}: ${cost_per_unit:.2f}/unit")
    
    print()
    
    # Test greedy allocation (should be optimal for this type of problem)
    print("🧮 GREEDY ALGORITHM VERIFICATION:")
    greedy_allocation = {name: 0 for name in machines.keys()}
    remaining_demand = demand
    
    for name, var_cost, fixed_cost, capacity, cost_per_unit in machine_efficiency:
        if remaining_demand <= 0:
            break
        
        allocation = min(remaining_demand, capacity)
        greedy_allocation[name] = allocation
        remaining_demand -= allocation
        
        print(f"  Allocate {allocation} units to {name} (remaining demand: {remaining_demand})")
    
    greedy_cost = calculate_cost(greedy_allocation, machines)
    
    print()
    print(f"🎯 GREEDY SOLUTION:")
    print(f"Allocation: {greedy_allocation}")
    print(f"Cost: ${greedy_cost:,.2f}")
    print()
    
    # Compare solutions
    print("⚖️  COMPARISON:")
    print(f"Found Solution Cost:  ${found_cost:,.2f}")
    print(f"Greedy Solution Cost: ${greedy_cost:,.2f}")
    
    if found_cost == greedy_cost:
        print("✅ VERIFICATION: Found solution matches optimal greedy solution!")
        print("   The allocation agent did find the mathematically optimal solution.")
    else:
        print("❌ PROBLEM: Found solution is NOT optimal!")
        print(f"   Potential savings: ${found_cost - greedy_cost:,.2f}")
    
    print()
    
    # Alternative allocation analysis
    print("🔄 TESTING ALTERNATIVE ALLOCATIONS:")
    
    # Test using different machine combinations
    alternatives = [
        # Try Tool_157 instead of Tool_673
        {'Tool_127': 2000, 'Tool_157': 1000, 'Tool_673': 0, 'Tool_377': 0},
        # Try mixed approach
        {'Tool_127': 1500, 'Tool_673': 1000, 'Tool_157': 500, 'Tool_377': 0},
        # Try minimizing machines used
        {'Tool_127': 2000, 'Tool_673': 1000, 'Tool_157': 0, 'Tool_377': 0},  # Current
    ]
    
    for i, alt_allocation in enumerate(alternatives, 1):
        alt_cost = calculate_cost(alt_allocation, machines)
        total_allocated = sum(alt_allocation.values())
        
        if total_allocated == demand:  # Valid allocation
            print(f"  Alternative {i}: {alt_allocation}")
            print(f"    Cost: ${alt_cost:,.2f} (diff: ${alt_cost - found_cost:+,.2f})")

if __name__ == "__main__":
    verify_optimality()