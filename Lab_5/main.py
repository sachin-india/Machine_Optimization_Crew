#!/usr/bin/env python3
"""
Manufacturing Optimization with Expert Panel
Demonstrates iterative improvement through expert feedback
"""

import sys
import warnings
from orchestrator import OptimizationOrchestrator
from reporter import OptimizationReporter
from tool_selector import ToolSelector

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def check_capacity_feasibility(machines, demand):
    """Check if machines have sufficient capacity and if optimization is needed"""
    total_capacity = sum(specs['capacity'] for specs in machines.values())
    
    print(f"\n🔍 CAPACITY ANALYSIS:")
    print(f"   Total Available Capacity: {total_capacity:,} units")
    print(f"   Required Demand: {demand:,} units")
    print(f"   Excess Capacity: {total_capacity - demand:,} units")
    
    if total_capacity < demand:
        print(f"\n❌ INSUFFICIENT CAPACITY!")
        print(f"   Cannot meet demand of {demand:,} units with available capacity of {total_capacity:,}")
        print(f"   Shortfall: {demand - total_capacity:,} units")
        return {'feasible': False, 'reason': 'insufficient_capacity'}
    
    if total_capacity == demand:
        print(f"\n⚠️  EXACT CAPACITY MATCH - NO OPTIMIZATION NEEDED!")
        print(f"   All machines must run at full capacity to meet demand")
        
        # Calculate the forced allocation
        forced_allocation = {name: specs['capacity'] for name, specs in machines.items()}
        total_cost = sum(
            specs['capacity'] * specs['variable_cost'] + specs['fixed_cost'] 
            for specs in machines.values()
        )
        
        return {
            'feasible': True, 
            'optimization_needed': False,
            'forced_allocation': forced_allocation,
            'forced_cost': total_cost,
            'reason': 'exact_capacity_match'
        }
    
    # Normal case: excess capacity available, optimization is meaningful
    print(f"\n✅ OPTIMIZATION VIABLE!")
    print(f"   Excess capacity of {total_capacity - demand:,} units allows for cost optimization")
    return {'feasible': True, 'optimization_needed': True, 'reason': 'optimization_viable'}

def main():
    print("=== MANUFACTURING OPTIMIZATION WITH EXPERT PANEL ===")

    # Select machines with sufficient capacity for demand that allow optimization
    selector = ToolSelector("input/allocation_tools.csv")
    
    # Let's use the random selection but with more machines to ensure sufficient capacity
    # and optimization opportunities
    problem_input = selector.select_tools(4, demand=3000)  # Select 4 machines for better optimization opportunities
    
    # Ensure we have enough capacity
    total_capacity = sum(specs['capacity'] for specs in problem_input['machines'].values())
    if total_capacity < 3000:
        print("⚠️ Insufficient capacity with random selection, trying targeted selection...")
        # Fall back to selecting specific high-capacity machines
        problem_input = selector.select_tools([2, 6, 13, 25], demand=3000)
    
    print("Selected machines:")
    for name, specs in problem_input['machines'].items():
        capacity = specs['capacity']
        var_cost = specs['variable_cost']
        fixed_cost = specs['fixed_cost']
        cost_per_unit = var_cost + (fixed_cost / capacity)  # Approximate cost per unit
        print(f"  {name}: Capacity={capacity}, Variable=${var_cost}, Fixed=${fixed_cost}, $/unit≈${cost_per_unit:.2f}")

    print(f"\nDemand: {problem_input['product_demand']} units")

    # Check capacity feasibility and optimization necessity
    capacity_check = check_capacity_feasibility(problem_input['machines'], problem_input['product_demand'])
    
    if not capacity_check['feasible']:
        # Insufficient capacity - cannot proceed
        print("\n" + "="*60)
        print("❌ OPTIMIZATION TERMINATED")
        print("="*60)
        print(f"Reason: {capacity_check['reason']}")
        print("Recommendation: Add more machines or reduce demand")
        print("="*60)
        return
    
    elif not capacity_check['optimization_needed']:
        # Exact capacity match - no optimization needed
        print("\n" + "="*60)
        print("📋 DIRECT SOLUTION (No Optimization Required)")
        print("="*60)
        print(f"🎯 Required Allocation: {capacity_check['forced_allocation']}")
        print(f"💰 Total Cost: ${capacity_check['forced_cost']:,.2f}")
        print(f"📊 Reason: {capacity_check['reason']}")
        print("All machines must operate at full capacity to meet exact demand")
        print("="*60)
        return

    # Run optimization using new orchestrator
    print("\n=== RUNNING ITERATIVE OPTIMIZATION ===")
    orchestrator = OptimizationOrchestrator()
    orchestrator.set_problem_context(
        machines=problem_input['machines'], 
        demand=problem_input['product_demand']
    )
    
    # Run the optimization with full visibility
    final_result = orchestrator.run_optimization_with_visibility()
    
    # Display final results
    print(f"\n" + "="*50)
    print("📋 FINAL OPTIMIZATION RESULTS")
    print("="*50)
    
    if 'error' not in final_result:
        print(f"🎯 Best Allocation: {final_result['final_allocation']}")
        print(f"💰 Final Cost: ${final_result['final_cost']:,.2f}")
        print(f"🔄 Total Iterations: {final_result['total_iterations']}")
        print(f"📈 Cost Improvement: {final_result['improvement']:.1f}%")
        
        print(f"\n📊 Optimization Journey:")
        for i, iteration in enumerate(final_result['optimization_history']):
            print(f"  Iteration {i+1}: ${iteration['total_cost']:,.2f}")
        
        # Generate comprehensive report using the reporter crew
        print(f"\n" + "="*50)
        print("📝 GENERATING OPTIMIZATION REPORT")
        print("="*50)
        
        try:
            reporter = OptimizationReporter()
            
            # Prepare problem context for the reporter
            problem_context = {
                'machines': problem_input['machines'],
                'demand': problem_input['product_demand']
            }
            
            # Generate the comprehensive report
            report_path = reporter.generate_report(final_result, problem_context)
            print(f"✅ Comprehensive report generated: {report_path}")
            
            # Also generate a quick summary report as backup
            summary_path = reporter.create_summary_report(final_result, problem_context)
            print(f"📄 Summary report generated: {summary_path}")
            
        except Exception as e:
            print(f"⚠️ Error generating report: {e}")
            print("Optimization completed successfully, but report generation failed.")
        
    else:
        print(f"❌ Error: {final_result['error']}")
    
    print("="*50)

if __name__ == "__main__":
    main()
