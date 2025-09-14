import os
import sys
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from pydantic import BaseModel, Field
from typing import Dict

from calculator_tool import manufacturing_calculator_tool

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

    @crew
    def crew(self) -> Crew:
        """Creates the crew"""
        return Crew(
            agents=[self.structured_output_agent()],
            tasks=[self.optimize_structured()],
            process=Process.sequential,
            verbose=True
        )
