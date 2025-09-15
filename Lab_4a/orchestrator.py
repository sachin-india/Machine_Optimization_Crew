"""
Manufacturing Optimization Orchestrator
Manages the iterative process between allocator agent and expert panel
"""

import os
from typing import Dict, List, Any
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from pydantic import BaseModel, Field


class AllocationResult(BaseModel):
    """Structured allocation result from allocator agent"""
    allocation: Dict[str, int] = Field(description="Machine allocations mapping machine names to units")
    total_cost: float = Field(description="Total calculated cost")
    reasoning: str = Field(description="Detailed reasoning for the allocation decision")
    iteration: int = Field(description="Current iteration number")

class ExpertFeedback(BaseModel):
    """Structured feedback from expert agents"""
    expert_type: str = Field(description="Type of expert (cost, efficiency, variable_cost, fixed_cost, batch_optimization)")
    assessment_rating: str = Field(description="Rating: poor, acceptable, good, or optimal")
    key_recommendations: List[str] = Field(description="List of specific actionable recommendations")
    concerns: List[str] = Field(description="List of identified concerns or issues")


class SimpleConvergenceManager:
    """Simple convergence management with 3 clear criteria"""
    
    def __init__(self):
        self.max_iterations = 5
        self.cost_threshold = 0.02  # 2% improvement threshold
        self.consensus_threshold = 3  # out of 5 experts need to approve
        
    def check_convergence(self, iteration: int, history: List[Dict], expert_feedback: List[Dict]) -> Dict[str, Any]:
        """Check if optimization should stop based on simple criteria"""
        
        # Always run at least 2 iterations
        if iteration < 2:
            return {"converged": False, "reason": "minimum_iterations"}
        
        # Check max iterations first (hard stop)
        if iteration >= self.max_iterations:
            return {"converged": True, "reason": "max_iterations_reached"}
        
        # Check cost improvement
        if self._check_cost_convergence(history):
            return {"converged": True, "reason": "cost_improvement_below_threshold"}
        
        # Check expert consensus
        if self._check_expert_consensus(expert_feedback):
            return {"converged": True, "reason": "expert_consensus_achieved"}
        
        return {"converged": False, "reason": "continue_optimization"}
    
    def _check_cost_convergence(self, history: List[Dict]) -> bool:
        """Simple: Stop when cost improvement drops below 2%"""
        if len(history) < 2:
            return False
        
        prev_cost = history[-2]['total_cost']
        curr_cost = history[-1]['total_cost']
        
        if prev_cost <= 0:  # Avoid division by zero
            return False
            
        improvement = (prev_cost - curr_cost) / prev_cost
        return improvement < self.cost_threshold
    
    def _check_expert_consensus(self, expert_feedback: List[Dict]) -> bool:
        """Simple: Stop when 4+ experts agree allocation is 'good enough'"""
        positive_feedback_count = 0
        for expert in expert_feedback:
            assessment = expert.get('assessment', '').lower()
            if any(word in assessment for word in ['good', 'optimal', 'excellent', 'satisfactory']):
                positive_feedback_count += 1
        
        return positive_feedback_count >= self.consensus_threshold


@CrewBase
class OptimizationOrchestrator:
    """Orchestrates the optimization process between allocator and expert panel"""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(self):
        self.convergence_manager = SimpleConvergenceManager()
        self.history = []
        self.machines = {}
        self.demand = 0
        
    def set_problem_context(self, machines: Dict, demand: int):
        """Set the optimization problem context"""
        self.machines = machines
        self.demand = demand
        self.history = []
        
    @agent
    def allocator_agent(self) -> Agent:
        """Agent that provides allocations through step-by-step reasoning"""
        return Agent(
            config=self.agents_config['allocator_agent'],
            llm="openai/gpt-4o",
            verbose=True
        )
    
    @agent 
    def cost_expert(self) -> Agent:
        """Expert focused on cost minimization"""
        return Agent(
            config=self.agents_config['cost_expert'],
            llm="openai/gpt-4o",
            verbose=True
        )
    
    @agent
    def efficiency_expert(self) -> Agent:
        """Expert focused on machine efficiency and utilization"""
        return Agent(
            config=self.agents_config['efficiency_expert'],
            llm="openai/gpt-4o",
            verbose=True
        )
    
    @agent
    def variable_cost_expert(self) -> Agent:
        """Expert focused on variable cost minimization"""
        return Agent(
            config=self.agents_config['variable_cost_expert'],
            llm="openai/gpt-4o",
            verbose=True
        )
    
    @agent
    def fixed_cost_expert(self) -> Agent:
        """Expert focused on fixed cost optimization"""
        return Agent(
            config=self.agents_config['fixed_cost_expert'],
            llm="openai/gpt-4o",
            verbose=True
        )
    
    @agent
    def batch_optimization_expert(self) -> Agent:
        """Expert focused on batch sizing and setup cost optimization"""
        return Agent(
            config=self.agents_config['batch_optimization_expert'],
            llm="openai/gpt-4o",
            verbose=True
        )
    
    @task
    def allocation_task(self) -> Task:
        """Task for getting allocation from allocator agent with structured output"""
        return Task(
            config=self.tasks_config['allocation_task'],
            agent=self.allocator_agent(),
            output_pydantic=AllocationResult
        )
    
    @task
    def cost_evaluation_task(self) -> Task:
        """Task for cost expert evaluation with structured output"""
        return Task(
            config=self.tasks_config['cost_evaluation_task'],
            agent=self.cost_expert(),
            output_pydantic=ExpertFeedback
        )
    
    @task
    def efficiency_evaluation_task(self) -> Task:
        """Task for efficiency expert evaluation with structured output"""
        return Task(
            config=self.tasks_config['efficiency_evaluation_task'],
            agent=self.efficiency_expert(),
            output_pydantic=ExpertFeedback
        )
    
    @task
    def variable_cost_evaluation_task(self) -> Task:
        """Task for variable cost expert evaluation with structured output"""
        return Task(
            config=self.tasks_config['variable_cost_evaluation_task'],
            agent=self.variable_cost_expert(),
            output_pydantic=ExpertFeedback
        )
    
    @task
    def fixed_cost_evaluation_task(self) -> Task:
        """Task for fixed cost expert evaluation with structured output"""
        return Task(
            config=self.tasks_config['fixed_cost_evaluation_task'],
            agent=self.fixed_cost_expert(),
            output_pydantic=ExpertFeedback
        )
    
    @task
    def batch_optimization_evaluation_task(self) -> Task:
        """Task for batch optimization expert evaluation with structured output"""
        return Task(
            config=self.tasks_config['batch_optimization_evaluation_task'],
            agent=self.batch_optimization_expert(),
            output_pydantic=ExpertFeedback
        )
    
    def run_optimization_with_visibility(self) -> Dict[str, Any]:
        """Run the optimization process with clear visibility into each step"""
        
        print("🏭 Manufacturing Optimization Process Starting...")
        print(f"📊 Problem: Allocate {self.demand} units across {len(self.machines)} machines")
        
        # Show machine details
        print("\n📋 Available Machines:")
        for machine, specs in self.machines.items():
            var_cost = specs['variable_cost']
            fixed_cost = specs['fixed_cost'] 
            capacity = specs['capacity']
            cost_per_unit = var_cost + (fixed_cost / capacity)  # Rough cost per unit at full capacity
            print(f"   {machine}: Capacity={capacity}, VarCost=${var_cost}, FixedCost=${fixed_cost}, $/unit≈${cost_per_unit:.2f}")
        
        print("=" * 80)
        
        for iteration in range(self.convergence_manager.max_iterations):
            print(f"\n🔄 ITERATION {iteration + 1}")
            print("-" * 40)
            
            # Get allocation from allocator agent
            allocation_result = self._get_allocation(iteration)
            print(f"💡 Allocator Decision: {allocation_result['allocation']}")
            print(f"💰 Calculated Cost: ${allocation_result['total_cost']:,.2f}")
            
            # Show cost breakdown
            self._print_cost_breakdown(allocation_result['allocation'])
            
            # Get expert panel feedback
            expert_feedback = self._get_expert_feedback(allocation_result)
            print(f"\n👥 Expert Panel Feedback:")
            for expert in expert_feedback:
                role = expert['role']
                assessment = expert['assessment']
                recommendations = expert.get('recommendations', [])
                concerns = expert.get('concerns', [])
                
                print(f"   • {role}: {assessment}")
                if recommendations:
                    print(f"     Recommends: {'; '.join(recommendations[:2])}")
                if concerns:
                    print(f"     Concerns: {'; '.join(concerns[:2])}")
            
            # Store iteration result
            self.history.append({
                'iteration': iteration,
                'allocation': allocation_result['allocation'],
                'total_cost': allocation_result['total_cost'],
                'reasoning': allocation_result.get('reasoning', ''),
                'expert_feedback': expert_feedback
            })
            
            # Check convergence
            convergence = self.convergence_manager.check_convergence(
                iteration, self.history, expert_feedback
            )
            
            print(f"\n🎯 Convergence Check: {convergence['reason']}")
            
            if convergence['converged']:
                print(f"\n✅ OPTIMIZATION COMPLETE: {convergence['reason']}")
                break
            else:
                print("   → Continuing to next iteration...")
        
        return self._finalize_result()
    
    def _get_allocation(self, iteration: int) -> Dict[str, Any]:
        """Get allocation from allocator agent with improved feedback processing"""
        
        # Prepare context for allocator with simplified feedback
        context = {
            'machines': self.machines,
            'demand': self.demand,
            'iteration': iteration,
            'previous_attempts': self._format_previous_attempts(),
            'expert_feedback_history': self._format_expert_feedback()
        }
        
        # Debug: Print context being passed
        print(f"🔧 DEBUG - Context for iteration {iteration}:")
        print(f"   Previous attempts: {context['previous_attempts']}")
        print(f"   Expert feedback: {context['expert_feedback_history'][:300]}...")  # First 300 chars
        
        # Create and run allocation task
        crew = Crew(
            agents=[self.allocator_agent()],
            tasks=[self.allocation_task()],
            process=Process.sequential,
            verbose=True  # Enable verbose to see agent reasoning
        )
        
        result = crew.kickoff(inputs=context)
        
        # Debug: Print raw result
        print(f"🔧 DEBUG - Raw allocation result type: {type(result)}")
        
        # Extract structured result
        if result.tasks_output and hasattr(result.tasks_output[0], 'pydantic'):
            allocation_result = result.tasks_output[0].pydantic
            
            print(f"🔧 DEBUG - Structured allocation: {allocation_result.allocation}")
            print(f"🔧 DEBUG - Agent reasoning: {allocation_result.reasoning[:300]}...")
            
            # Validate and fix allocation
            fixed_allocation = self._validate_and_fix_allocation(allocation_result.allocation)
            
            return {
                'allocation': fixed_allocation,
                'total_cost': self._calculate_cost(fixed_allocation),
                'reasoning': allocation_result.reasoning,
                'raw_allocation': allocation_result.allocation  # Keep original for debugging
            }
        else:
            # Fallback: create a reasonable allocation
            print("⚠️ Failed to get structured output, using fallback allocation")
            fallback_allocation = self._create_optimal_allocation()
            return {
                'allocation': fallback_allocation,
                'total_cost': self._calculate_cost(fallback_allocation),
                'reasoning': "Fallback allocation due to parsing failure"
            }
    
    def _get_expert_feedback(self, allocation_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get structured feedback from all expert agents"""
        
        context = {
            'machines': self.machines,
            'demand': self.demand,
            'allocation': allocation_result['allocation'],
            'total_cost': allocation_result['total_cost'],
            'reasoning': allocation_result.get('reasoning', '')
        }
        
        expert_feedback = []
        
        # Get feedback from each expert with structured output
        experts = [
            (self.cost_expert(), self.cost_evaluation_task(), 'Cost Expert'),
            (self.efficiency_expert(), self.efficiency_evaluation_task(), 'Efficiency Expert'),
            (self.variable_cost_expert(), self.variable_cost_evaluation_task(), 'Variable Cost Expert'),
            (self.fixed_cost_expert(), self.fixed_cost_evaluation_task(), 'Fixed Cost Expert'),
            (self.batch_optimization_expert(), self.batch_optimization_evaluation_task(), 'Batch Optimization Expert')
        ]
        
        for agent, task, role in experts:
            try:
                crew = Crew(
                    agents=[agent],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=False
                )
                
                result = crew.kickoff(inputs=context)
                
                if result.tasks_output and hasattr(result.tasks_output[0], 'pydantic'):
                    feedback = result.tasks_output[0].pydantic
                    expert_feedback.append({
                        'role': role,
                        'assessment': feedback.assessment_rating,
                        'recommendations': feedback.key_recommendations,
                        'concerns': feedback.concerns
                    })
                else:
                    # Fallback for unstructured output
                    feedback_text = str(result.tasks_output[0].raw) if result.tasks_output else "No feedback available"
                    expert_feedback.append({
                        'role': role,
                        'assessment': 'acceptable',  # Default rating
                        'recommendations': ['Review allocation for improvements'],
                        'concerns': ['Unable to provide structured feedback']
                    })
            except Exception as e:
                print(f"Error getting feedback from {role}: {e}")
                expert_feedback.append({
                    'role': role,
                    'assessment': 'acceptable',
                    'recommendations': ['Review allocation'],
                    'concerns': ['Expert evaluation failed']
                })
        
        return expert_feedback
    
    def _validate_and_fix_allocation(self, allocation: Dict[str, int]) -> Dict[str, int]:
        """Validate allocation against capacity constraints and fix if needed with clear feedback"""
        fixed_allocation = {}
        total_demand = self.demand
        allocated_so_far = 0
        violations_found = []
        
        print(f"🔧 VALIDATION - Original allocation: {allocation}")
        
        # First pass: fix capacity violations
        for machine, units in allocation.items():
            if machine in self.machines:
                capacity = int(self.machines[machine]['capacity'])
                if units > capacity:
                    violations_found.append(f"{machine}: {units} > {capacity} (capacity)")
                    units = capacity
                fixed_units = min(units, capacity)  # Don't exceed capacity
                fixed_allocation[machine] = fixed_units
                allocated_so_far += fixed_units
        
        if violations_found:
            print(f"⚠️  CAPACITY VIOLATIONS DETECTED:")
            for violation in violations_found:
                print(f"   - {violation}")
        
        # Second pass: if we haven't met demand, try to allocate more
        if allocated_so_far < total_demand:
            remaining_demand = total_demand - allocated_so_far
            print(f"⚠️  DEMAND SHORTFALL: {remaining_demand} units not allocated")
            
            # Sort machines by efficiency (cost per unit)
            machine_efficiency = []
            for machine, specs in self.machines.items():
                var_cost = specs['variable_cost']
                fixed_cost = specs['fixed_cost']
                capacity = specs['capacity']
                # Calculate cost per unit if using at 50% capacity (rough efficiency measure)
                cost_per_unit = var_cost + (fixed_cost / (capacity * 0.5))
                machine_efficiency.append((machine, cost_per_unit, capacity))
            
            machine_efficiency.sort(key=lambda x: x[1])  # Sort by cost per unit
            
            # Allocate remaining demand to most efficient machines
            for machine, _, capacity in machine_efficiency:
                if remaining_demand <= 0:
                    break
                current_allocation = fixed_allocation.get(machine, 0)
                available_capacity = capacity - current_allocation
                additional_allocation = min(remaining_demand, available_capacity)
                
                if additional_allocation > 0:
                    print(f"   → Adding {additional_allocation} units to {machine}")
                    fixed_allocation[machine] = current_allocation + additional_allocation
                    remaining_demand -= additional_allocation
        
        # Ensure all machines are represented (even with 0 allocation)
        for machine in self.machines:
            if machine not in fixed_allocation:
                fixed_allocation[machine] = 0
        
        print(f"🔧 VALIDATION - Final allocation: {fixed_allocation}")
        
        # Verify total demand is met
        total_allocated = sum(fixed_allocation.values())
        if total_allocated != total_demand:
            print(f"⚠️  WARNING: Total allocated ({total_allocated}) != Demand ({total_demand})")
        
        return fixed_allocation
        
        return fixed_allocation
    
    def _create_optimal_allocation(self) -> Dict[str, int]:
        """Create an optimal allocation as fallback"""
        # Simple greedy allocation by cost efficiency
        machines = list(self.machines.keys())
        allocation = {machine: 0 for machine in machines}
        remaining_demand = self.demand
        
        # Sort machines by variable cost (simple efficiency measure)
        sorted_machines = sorted(machines, key=lambda m: self.machines[m]['variable_cost'])
        
        for machine in sorted_machines:
            if remaining_demand <= 0:
                break
            capacity = int(self.machines[machine]['capacity'])
            allocation[machine] = min(remaining_demand, capacity)
            remaining_demand -= allocation[machine]
        
        return allocation
    
    def _format_previous_attempts(self) -> str:
        """Format previous attempts for allocator context"""
        if not self.history:
            return "No previous attempts"
        
        formatted = []
        for i, attempt in enumerate(self.history):
            formatted.append(f"Attempt {i+1}: {attempt['allocation']} -> Cost: ${attempt['total_cost']:,.2f}")
        
        return "; ".join(formatted)
    
    def _format_expert_feedback(self) -> str:
        """Format expert feedback for allocator context with more detail"""
        if not self.history:
            return "No previous expert feedback available."
        
        latest_feedback = self.history[-1].get('expert_feedback', []) if self.history else []
        
        if not latest_feedback:
            return "No expert feedback available from previous iteration."
        
        formatted = []
        for feedback in latest_feedback:
            role = feedback.get('role', 'Unknown')
            assessment = feedback.get('assessment', 'No assessment')
            recommendations = feedback.get('recommendations', [])
            concerns = feedback.get('concerns', [])
            
            feedback_parts = [f"{role} says: {assessment}"]
            
            if recommendations:
                feedback_parts.append(f"RECOMMENDS: {' | '.join(recommendations[:3])}")  # Up to 3 recommendations
            if concerns:
                feedback_parts.append(f"CONCERNS: {' | '.join(concerns[:2])}")  # Up to 2 concerns
            
            formatted.append(" - ".join(feedback_parts))
        
        return "\n".join(formatted)
    
    def _calculate_cost(self, allocation: Dict[str, int]) -> float:
        """Calculate total cost for an allocation"""
        total_cost = 0
        
        for machine, units in allocation.items():
            if units > 0 and machine in self.machines:
                machine_specs = self.machines[machine]
                variable_cost = machine_specs['variable_cost'] * units
                fixed_cost = machine_specs['fixed_cost']
                total_cost += variable_cost + fixed_cost
        
        return total_cost
    
    def _print_cost_breakdown(self, allocation: Dict[str, int]):
        """Print detailed cost breakdown for transparency"""
        print("   💰 Cost Breakdown:")
        total_var_cost = 0
        total_fixed_cost = 0
        
        for machine, units in allocation.items():
            if units > 0 and machine in self.machines:
                specs = self.machines[machine]
                var_cost = specs['variable_cost'] * units
                fixed_cost = specs['fixed_cost']
                total_var_cost += var_cost
                total_fixed_cost += fixed_cost
                print(f"     {machine}: {units} units × ${specs['variable_cost']} + ${fixed_cost} = ${var_cost + fixed_cost}")
        
        print(f"     TOTAL: Variable=${total_var_cost} + Fixed=${total_fixed_cost} = ${total_var_cost + total_fixed_cost}")
    
    def _finalize_result(self) -> Dict[str, Any]:
        """Return final optimization result"""
        if not self.history:
            return {"error": "No optimization iterations completed"}
        
        best_iteration = min(self.history, key=lambda x: x['total_cost'])
        
        return {
            'final_allocation': best_iteration['allocation'],
            'final_cost': best_iteration['total_cost'],
            'total_iterations': len(self.history),
            'improvement': (self.history[0]['total_cost'] - best_iteration['total_cost']) / self.history[0]['total_cost'] * 100,
            'optimization_history': self.history
        }