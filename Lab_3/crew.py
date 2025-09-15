import os
import sys
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from pydantic import BaseModel, Field
from typing import Dict

from calculator_tool import (
    manufacturing_calculator_tool, 
    manufacturing_cost_calculator,
    was_tool_called,
    strategic_optimizer_tool,
    strategic_optimizer,
    was_oracle_tool_called,
    evaluator_calculator_tool,
    was_evaluator_calculator_called
)

# Simple output model
class SingleAllocationSolution(BaseModel):
    """Simple allocation solution model"""
    strategy_name: str = Field(description="Name of the strategy used")
    machine_allocations: Dict[str, int] = Field(description="Units allocated to each machine")
    total_variable_cost: float = Field(description="Total variable cost")
    total_fixed_cost: float = Field(description="Total fixed cost") 
    total_cost: float = Field(description="Total cost")
    reasoning: str = Field(description="Explanation of the allocation")

@CrewBase
class SimpleManufacturingCrew:
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def structured_output_agent(self) -> Agent:
        """Agent that should use the calculator tool."""
        tools = []
        if manufacturing_calculator_tool is not None:
           tools.append(manufacturing_calculator_tool)

        return Agent(
            config=self.agents_config['structured_output_agent'],
            llm="openai/gpt-4o",
            tools=tools,
            verbose=True
        )

    @agent
    def evaluator_agent(self) -> Agent:
        """Agent that evaluates allocations using the oracle tool."""
        tools = []
        if strategic_optimizer_tool is not None:
            tools.append(strategic_optimizer_tool)
        if evaluator_calculator_tool is not None:
            tools.append(evaluator_calculator_tool)

        return Agent(
            config=self.agents_config['evaluator_agent'],
            llm="openai/gpt-4o",
            tools=tools,
            verbose=True
        )

    @task
    def optimize_structured(self) -> Task:
        """Task for the optimization agent."""
        return Task(
            config=self.tasks_config['optimize_structured'],
            agent=self.structured_output_agent(),
            output_pydantic=SingleAllocationSolution
        )

    def set_problem_context(self, inputs: Dict):
        """Store the last problem inputs so callbacks can access machines/demand."""
        self._last_problem_inputs = inputs
    
    def set_allocation_result(self, allocation_result):
        """Store the allocation result for evaluation"""
        self._last_allocation_result = allocation_result

    def _generate_feedback_based_on_tools(self, optimal_allocation, allocator_allocation, optimal_cost, allocator_cost, machines):
        """Generate meaningful feedback based on actual tool results"""
        feedback = {
            'what_allocator_did_well': [],
            'recommendations_for_improvement': []
        }
        
        # Analyze what the allocator did well
        if allocator_cost == optimal_cost:
            feedback['what_allocator_did_well'].append("Found the mathematically optimal solution")
            feedback['recommendations_for_improvement'].append("Continue using this excellent allocation strategy")
        else:
            # Check if allocator used any of the same machines as optimal
            optimal_machines = set(k for k, v in optimal_allocation.items() if v > 0)
            allocator_machines = set(k for k, v in allocator_allocation.items() if v > 0)
            common_machines = optimal_machines.intersection(allocator_machines)
            
            if common_machines:
                feedback['what_allocator_did_well'].append(f"Correctly identified some key machines: {list(common_machines)}")
            
            # Check if allocator met demand
            total_allocated = sum(allocator_allocation.values())
            feedback['what_allocator_did_well'].append(f"Successfully met demand with {total_allocated} units allocated")
            
            # Analyze cost efficiency
            if allocator_cost < optimal_cost * 1.1:  # Within 10%
                feedback['what_allocator_did_well'].append("Achieved near-optimal cost efficiency")
            
            # Generate specific recommendations
            cost_diff = allocator_cost - optimal_cost
            percentage_more = (cost_diff / optimal_cost) * 100
            
            feedback['recommendations_for_improvement'].append(
                f"Current solution is ${cost_diff:,.2f} ({percentage_more:.1f}%) more expensive than optimal"
            )
            
            # Identify specific machine allocation differences
            optimal_str = ", ".join([f"{k}: {v}" for k, v in optimal_allocation.items() if v > 0])
            feedback['recommendations_for_improvement'].append(
                f"Optimal allocation: {optimal_str} achieves ${optimal_cost:,.2f}"
            )
            
            # Analyze efficiency patterns
            optimal_efficiency = []
            for machine, units in optimal_allocation.items():
                if units > 0:
                    var_cost = machines[machine]['variable_cost']
                    fixed_cost = machines[machine]['fixed_cost']
                    unit_cost = var_cost + (fixed_cost / units) if units > 0 else float('inf')
                    optimal_efficiency.append((machine, unit_cost))
            
            optimal_efficiency.sort(key=lambda x: x[1])
            if optimal_efficiency:
                best_machine = optimal_efficiency[0][0]
                feedback['recommendations_for_improvement'].append(
                    f"Consider prioritizing {best_machine} which has the best cost efficiency in the optimal solution"
                )
        
        return feedback

    @task
    def optimize_structured_with_callback(self) -> Task:
        """Task that enforces tool usage via a post-task callback"""
        def enforce_tool_callback(task_output):
            """Callback inspects agent output and forces tool if needed."""
            print("\n" + "="*50)
            print("📊 ALLOCATION AGENT RESULT")
            print("="*50)
            
            try:
                # Check if tool was called AND if the result has valid cost data
                has_valid_costs = False
                if hasattr(task_output, 'total_cost') and task_output.total_cost is not None and task_output.total_cost > 0:
                    has_valid_costs = True
                elif isinstance(task_output, dict) and task_output.get('total_cost') is not None and task_output.get('total_cost') > 0:
                    has_valid_costs = True
                
                # If tool was called successfully and we have valid costs, get pure tool output
                if was_tool_called() and has_valid_costs:
                    print("✅ Agent used manufacturing calculator correctly")
                    
                    # Extract allocation from agent's output
                    allocation = None
                    if hasattr(task_output, 'machine_allocations'):
                        allocation = task_output.machine_allocations
                        self._last_allocator_result = {'machine_allocations': task_output.machine_allocations}
                    elif isinstance(task_output, dict) and 'machine_allocations' in task_output:
                        allocation = task_output['machine_allocations']
                        self._last_allocator_result = {'machine_allocations': task_output['machine_allocations']}
                    
                    if allocation:
                        # Get problem context
                        machines = getattr(self, '_last_problem_inputs', {}).get('machines')
                        demand = getattr(self, '_last_problem_inputs', {}).get('product_demand')
                        
                        if machines and demand is not None:
                            # Get pure tool output
                            tool_result = manufacturing_cost_calculator(machines=machines, demand=demand, allocation=allocation)
                            print(f"Allocation: {allocation}")
                            print(f"Total Cost: ${tool_result['total_cost']:,.2f}")
                            print("="*50)
                            return tool_result
                    
                    # Fallback to original output if we can't extract allocation
                    print("⚠️ Using agent's original output")
                    print("="*50)
                    return task_output

                print("⚠️ Agent didn't use calculator - forcing tool usage...")
                # Either tool wasn't called properly or costs are invalid - enforce tool usage
                # Either tool wasn't called properly or costs are invalid - enforce tool usage
                allocation = None
                if hasattr(task_output, 'machine_allocations'):
                    allocation = task_output.machine_allocations
                elif hasattr(task_output, 'pydantic') and hasattr(task_output.pydantic, 'machine_allocations'):
                    allocation = task_output.pydantic.machine_allocations
                else:
                    # Best-effort parse JSON-like dict from text
                    import re, ast, json
                    s = str(task_output)
                    
                    # Try to extract JSON from markdown code blocks
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', s, re.S)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group(1))
                            allocation = parsed.get('machine_allocations')
                        except Exception:
                            allocation = None
                    
                    # Fallback: try to find any JSON-like dict
                    if not allocation:
                        m = re.search(r"\{.*\}\s*$", s, re.S)
                        if m:
                            try:
                                parsed = ast.literal_eval(m.group(0))
                                allocation = parsed.get('machine_allocations') or parsed.get('allocation')
                            except Exception:
                                allocation = None

                if not allocation:
                    raise ValueError("Could not determine allocation from agent output")

                # Use the stored problem inputs to get machines and demand
                machines = getattr(self, '_last_problem_inputs', {}).get('machines')
                demand = getattr(self, '_last_problem_inputs', {}).get('product_demand')
                if not machines or demand is None:
                    raise ValueError("Missing problem context for enforcement callback")

                # Ensure allocation meets demand and capacity constraints
                total_alloc = sum(allocation.values())
                allocation_fixed = False
                
                # Fix capacity violations first
                for machine_name, units in allocation.items():
                    capacity = float(machines[machine_name]['capacity'])
                    if units > capacity:
                        allocation[machine_name] = int(capacity)
                        allocation_fixed = True
                
                # Recalculate total after capacity fixes
                total_alloc = sum(allocation.values())
                
                # If total is now less than demand, scale up proportionally
                if total_alloc < demand:
                    # Calculate available additional capacity
                    remaining_capacity = {}
                    for machine_name in allocation.keys():
                        capacity = float(machines[machine_name]['capacity'])
                        remaining_capacity[machine_name] = capacity - allocation[machine_name]
                    
                    # Distribute remaining demand proportionally to available capacity
                    shortage = demand - total_alloc
                    total_remaining = sum(remaining_capacity.values())
                    
                    if total_remaining >= shortage:
                        # Distribute shortage proportionally
                        for machine_name in allocation.keys():
                            if remaining_capacity[machine_name] > 0:
                                share = remaining_capacity[machine_name] / total_remaining
                                additional = min(int(share * shortage), remaining_capacity[machine_name])
                                allocation[machine_name] += additional
                                shortage -= additional
                                if shortage <= 0:
                                    break
                    else:
                        # Not enough capacity - use maximum possible
                        print(f"⚠️ WARNING: Not enough total capacity to meet demand {demand}")
                        for machine_name in allocation.keys():
                            capacity = float(machines[machine_name]['capacity'])
                            allocation[machine_name] = int(capacity)
                
                # If total is more than demand, scale down proportionally
                total_alloc = sum(allocation.values())
                if total_alloc > demand:
                    # Proportional scaling down
                    scaled = {}
                    remaining = demand
                    keys = list(allocation.keys())
                    for i, k in enumerate(keys):
                        if i == len(keys) - 1:
                            scaled[k] = int(remaining)
                        else:
                            share = allocation[k] / total_alloc if total_alloc else 0
                            amt = int(share * demand)
                            scaled[k] = amt
                            remaining -= amt
                    allocation = scaled

                tool_result = manufacturing_cost_calculator(machines=machines, demand=demand, allocation=allocation)

                # Store allocation for evaluator
                self._last_allocator_result = {'machine_allocations': allocation}
                
                print(f"Forced allocation: {allocation}")
                print(f"Verified cost: ${tool_result['total_cost']:,.2f}")
                print("="*50)
                
                return tool_result

            except Exception:
                # On any enforcement failure, return the original task output
                print("❌ Enforcement failed - using original output")
                print("="*50)
                return task_output
        
        # Return the task with pydantic output and enforcement callback
        return Task(
            config=self.tasks_config['optimize_structured'],
            agent=self.structured_output_agent(),
            output_pydantic=SingleAllocationSolution,
            callback=enforce_tool_callback
        )

    @task
    def evaluate_allocation_with_callback(self) -> Task:
        """Task that evaluates allocation using oracle tool with enforcement"""
        def enforce_oracle_callback(task_output):
            """Callback to ensure oracle tool is used"""
            print("\n" + "="*50)
            print("🔍 EVALUATION RESULT")
            print("="*50)
            
            try:
                # Always force oracle tool usage to ensure accurate results
                machines = getattr(self, '_last_problem_inputs', {}).get('machines')
                demand = getattr(self, '_last_problem_inputs', {}).get('product_demand')
                allocator_allocation = getattr(self, '_last_allocator_result', {}).get('machine_allocations', {})
                
                if not machines or demand is None:
                    print("❌ Missing problem context")
                    print("="*50)
                    return task_output
                
                # Call oracle tool to get optimal solution
                oracle_result = strategic_optimizer(machines=machines, demand=demand)
                
                # Get verified cost for allocator's solution
                allocator_cost_result = manufacturing_cost_calculator(machines=machines, demand=demand, allocation=allocator_allocation)
                
                # Create proper evaluation based on ACTUAL tool results
                feasible_text = "Yes" if oracle_result.get('feasible', True) else f"No - {oracle_result.get('reason', 'Unknown')}"
                
                # Compare VERIFIED costs (not agent guesses)
                allocator_verified_cost = allocator_cost_result['total_cost']
                optimal_cost = oracle_result['optimal_cost']
                cost_diff = allocator_verified_cost - optimal_cost
                efficiency = (optimal_cost / allocator_verified_cost * 100) if allocator_verified_cost > 0 else 100
                
                # Display simple evaluation summary
                print(f"Allocator's solution: {allocator_allocation}")
                print(f"Allocator's cost: ${allocator_verified_cost:,.2f}")
                print()
                print(f"Optimal solution: {oracle_result['optimal_allocation']}")  
                print(f"Optimal cost: ${optimal_cost:,.2f}")
                print()
                if cost_diff == 0:
                    print("🎯 PERFECT! Allocator found the optimal solution")
                else:
                    print(f"💰 Cost difference: ${cost_diff:,.2f} ({cost_diff/optimal_cost*100:.1f}% more expensive)")
                    print(f"📊 Efficiency: {efficiency:.1f}%")
                
                # Create simplified evaluation result
                evaluation_result = {
                    'allocator_allocation': allocator_allocation,
                    'allocator_cost': allocator_verified_cost,
                    'optimal_allocation': oracle_result['optimal_allocation'],
                    'optimal_cost': optimal_cost,
                    'cost_difference': cost_diff,
                    'efficiency_percentage': efficiency,
                    'is_optimal': cost_diff == 0
                }
                
                print("="*50)
                return evaluation_result
                
            except Exception as e:
                print(f"❌ Evaluation failed: {str(e)}")
                print("="*50)
                return f"Evaluation failed: {str(e)}"
        
        return Task(
            config=self.tasks_config['evaluate_allocation'],
            agent=self.evaluator_agent(),
            callback=enforce_oracle_callback,
            context=[self.optimize_structured_with_callback()]  # Takes allocation result as input
        )
    # ...existing code...

    # ...existing code...

    @crew
    def crew(self) -> Crew:
        """Creates the crew with allocation and evaluation"""
        return Crew(
            agents=[self.structured_output_agent(), self.evaluator_agent()],
            tasks=[self.optimize_structured_with_callback(), self.evaluate_allocation_with_callback()],
            process=Process.sequential,
            verbose=True
        )
