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
    brute_force_optimizer_tool,
    brute_force_optimizer,
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
        if brute_force_optimizer_tool is not None:
            tools.append(brute_force_optimizer_tool)
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

    @task
    def optimize_structured_with_callback(self) -> Task:
        """Task that enforces tool usage via a post-task callback"""
        def enforce_tool_callback(task_output):
            """Callback inspects agent output and forces tool if needed."""
            try:
                # If tool was already called by the agent, do nothing
                if was_tool_called():
                    return task_output

                # Try to extract allocation from structured output (pydantic or dict)
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
                        print(f"🔧 FIXING: {machine_name} allocated {units} > capacity {capacity}")
                        allocation[machine_name] = int(capacity)
                        allocation_fixed = True
                
                # Recalculate total after capacity fixes
                total_alloc = sum(allocation.values())
                
                # If total is now less than demand, scale up proportionally
                if total_alloc < demand:
                    print(f"🔧 SCALING: Total {total_alloc} < demand {demand}")
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
                    print(f"🔧 SCALING DOWN: Total {total_alloc} > demand {demand}")
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

                # Construct enforced structured result
                enforced = {
                    'strategy_name': getattr(task_output, 'strategy_name', 'Enforced_Strategy'),
                    'machine_allocations': allocation,
                    'total_variable_cost': tool_result['total_variable_cost'],
                    'total_fixed_cost': tool_result['total_fixed_cost'],
                    'total_cost': tool_result['total_cost'],
                    'reasoning': 'Costs computed via enforced manufacturing_cost_calculator.'
                }

                return enforced

            except Exception:
                # On any enforcement failure, return the original task output
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
            try:
                # If oracle tool was already called by the agent, return output
                if was_oracle_tool_called():
                    return task_output
                
                # Force oracle tool usage
                machines = getattr(self, '_last_problem_inputs', {}).get('machines')
                demand = getattr(self, '_last_problem_inputs', {}).get('product_demand')
                if not machines or demand is None:
                    return task_output
                
                # Call oracle tool to get optimal solution
                oracle_result = brute_force_optimizer(machines=machines, demand=demand)
                
                # Create evaluation report
                evaluation_text = f"""
EVALUATION REPORT (Oracle Tool Enforced):

OPTIMAL SOLUTION (via brute force optimizer):
- Optimal Allocation: {oracle_result['optimal_allocation']}
- Optimal Cost: ${oracle_result['optimal_cost']}
- Optimal Variable Cost: ${oracle_result['optimal_variable_cost']}
- Optimal Fixed Cost: ${oracle_result['optimal_fixed_cost']}

COMPARISON & RECOMMENDATIONS:
The allocator's solution vs optimal solution analysis is enforced via oracle tool.
Agent attempted: {str(task_output)[:500]}...

Oracle tool was enforced to ensure mathematically optimal comparison.
"""
                return evaluation_text
                
            except Exception as e:
                return f"Evaluation failed: {str(e)}\nOriginal output: {task_output}"
        
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
