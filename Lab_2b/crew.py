import os
import sys
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from pydantic import BaseModel, Field
from typing import Dict

from calculator_tool import manufacturing_calculator_tool, manufacturing_cost_calculator, was_tool_called

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
                    import re, ast
                    s = str(task_output)
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

                # Ensure allocation meets demand; if not, scale proportionally
                total_alloc = sum(allocation.values())
                if total_alloc < demand:
                    # Proportional scaling
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
        # Return the task configured with the enforcement callback
        return Task(
            config=self.tasks_config['optimize_structured'],
            agent=self.structured_output_agent(),
            callback=enforce_tool_callback,
            output_pydantic=SingleAllocationSolution,
        )
    # ...existing code...

    # ...existing code...
    @crew
    def crew(self) -> Crew:
        """Creates the crew"""
        return Crew(
            agents=[self.structured_output_agent()],
            tasks=[self.optimize_structured_with_callback()],
            process=Process.sequential,
            verbose=True
        )
