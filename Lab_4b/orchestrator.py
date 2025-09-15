"""
Manufacturing Optimization Orchestrator
Manages the iterative process between allocator agent and optimization strategist
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

class StrategistFeedback(BaseModel):
    """Structured feedback from optimization strategist"""
    assessment_rating: str = Field(description="Rating: poor, acceptable, good, or optimal")
    key_recommendations: List[str] = Field(description="List of specific actionable recommendations")
    concerns: List[str] = Field(description="List of identified concerns or issues")
    applied_strategies: List[str] = Field(description="List of optimization strategies used in analysis")
    mathematically_verified: bool = Field(description="Whether optimality has been mathematically proven")
    alternatives_tested: bool = Field(description="Whether alternative allocations were tested")
    verification_details: str = Field(description="Details of mathematical verification performed")


class SimpleConvergenceManager:
    """Simple convergence management with 3 clear criteria"""
    
    def __init__(self):
        self.max_iterations = 5
        self.cost_threshold = 0.02  # 2% improvement threshold
        
    def check_convergence(self, iteration: int, history: List[Dict], strategist_feedback: Dict) -> Dict[str, Any]:
        """Check if optimization should stop based on mathematical verification"""
        
        # Always run at least 2 iterations
        if iteration < 2:
            return {"converged": False, "reason": "minimum_iterations"}
        
        # Check max iterations first (hard stop)
        if iteration >= self.max_iterations:
            return {"converged": True, "reason": "max_iterations_reached"}
        
        # Priority 1: Mathematical verification (best case)
        if self._check_mathematical_verification(strategist_feedback):
            return {"converged": True, "reason": "mathematical_optimality_proven"}
        
        # Priority 2: Check if alternatives need to be tested
        if not self._check_alternatives_tested(strategist_feedback):
            return {"converged": False, "reason": "alternatives_need_testing"}
        
        # Priority 3: Cost improvement threshold (fallback)
        if self._check_cost_convergence(history):
            return {"converged": True, "reason": "cost_improvement_below_threshold"}
        
        # Priority 4: Strategist approval (last resort)
        if self._check_strategist_approval(strategist_feedback):
            return {"converged": True, "reason": "strategist_approval_with_verification"}
        
        return {"converged": False, "reason": "continue_optimization"}
    
    def _check_mathematical_verification(self, strategist_feedback: Dict) -> bool:
        """Check if strategist has mathematically verified optimality"""
        return strategist_feedback.get('mathematically_verified', False)
    
    def _check_alternatives_tested(self, strategist_feedback: Dict) -> bool:
        """Check if strategist has tested alternative allocations"""
        return strategist_feedback.get('alternatives_tested', False)
    
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
    
    def _check_strategist_approval(self, strategist_feedback: Dict) -> bool:
        """Stop when strategist rates allocation as 'good' or 'optimal'"""
        assessment = strategist_feedback.get('assessment', '').lower()
        return any(word in assessment for word in ['good', 'optimal', 'excellent'])


@CrewBase
class OptimizationOrchestrator:
    """Orchestrates the optimization process between allocator and strategist"""
    
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
    def optimization_strategist(self) -> Agent:
        """Single strategist with access to optimization knowledge base and verification tools"""
        # Load optimization strategies knowledge base
        strategies_path = os.path.join(os.path.dirname(__file__), 'optimization_strategies.md')
        strategies_content = ""
        if os.path.exists(strategies_path):
            with open(strategies_path, 'r', encoding='utf-8') as f:
                strategies_content = f.read()
        
        verification_instructions = """
        
        CRITICAL: You MUST perform mathematical verification of any allocation you assess as 'optimal'.
        
        VERIFICATION REQUIREMENTS:
        1. Calculate cost per unit for each machine (variable_cost + fixed_cost/capacity)
        2. Rank machines by efficiency (lowest cost per unit first)
        3. Generate greedy optimal allocation using efficiency ranking
        4. Compare current allocation with greedy optimal
        5. Test at least 2 alternative allocation strategies
        6. Only mark 'mathematically_verified: true' if current allocation matches proven optimal
        7. Set 'alternatives_tested: true' only after testing multiple approaches
        
        VERIFICATION OUTPUT FORMAT:
        - mathematically_verified: true/false (true only if proven optimal)
        - alternatives_tested: true/false (true only if alternatives were actually tested)
        - verification_details: string explaining your mathematical analysis
        
        If allocation is NOT optimal, provide specific recommendations for improvement.
        """
        
        return Agent(
            config=self.agents_config['optimization_strategist'],
            llm="openai/gpt-4o",
            verbose=True,
            tools=[],
            system_message=f"""You are a Manufacturing Optimization Strategist with access to a comprehensive 
            knowledge base of optimization strategies and mathematical verification capabilities.

            {strategies_content}

            {verification_instructions}

            Use this knowledge base to analyze allocations, perform mathematical verification, and provide expert feedback using proven optimization strategies."""
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
    def strategist_evaluation_task(self) -> Task:
        """Task for strategist evaluation with structured output"""
        return Task(
            config=self.tasks_config['strategist_evaluation_task'],
            agent=self.optimization_strategist(),
            output_pydantic=StrategistFeedback
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
            cost_per_unit = var_cost + (fixed_cost / capacity)
            print(f"   {machine}: Capacity={capacity}, VarCost=${var_cost}, FixedCost=${fixed_cost}, $/unit≈${cost_per_unit:.2f}")
        
        print("=" * 80)
        
        for iteration in range(self.convergence_manager.max_iterations):
            print(f"\n🔄 ITERATION {iteration + 1}")
            print("-" * 40)
            
            # Get allocation from allocator agent
            allocation_result = self._get_allocation(iteration)
            print(f"💡 Allocator Decision: {allocation_result['allocation']}")
            print(f"💰 Calculated Cost: ${allocation_result['total_cost']:,.2f}")
            
            # Get strategist feedback
            strategist_feedback = self._get_strategist_feedback(allocation_result)
            print(f"\n🎯 Optimization Strategist Feedback:")
            print(f"   Assessment: {strategist_feedback['assessment']}")
            print(f"   Mathematical Verification: {'✅ PROVEN' if strategist_feedback.get('mathematically_verified') else '❌ NOT VERIFIED'}")
            if strategist_feedback.get('recommendations'):
                print(f"   Key Recommendations: {strategist_feedback['recommendations'][0]}")
            
            # Store iteration result
            self.history.append({
                'iteration': iteration,
                'allocation': allocation_result['allocation'],
                'total_cost': allocation_result['total_cost'],
                'reasoning': allocation_result.get('reasoning', ''),
                'strategist_feedback': strategist_feedback
            })
            
            # Check convergence
            convergence = self.convergence_manager.check_convergence(
                iteration, self.history, strategist_feedback
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
            'strategist_feedback_history': self._format_strategist_feedback()
        }
        
        # Create and run allocation task
        crew = Crew(
            agents=[self.allocator_agent()],
            tasks=[self.allocation_task()],
            process=Process.sequential,
            verbose=False  # Reduced verbosity
        )
        
        result = crew.kickoff(inputs=context)
        
        # Extract structured result
        if result.tasks_output and hasattr(result.tasks_output[0], 'pydantic'):
            allocation_result = result.tasks_output[0].pydantic
            
            # Validate and fix allocation
            fixed_allocation = self._validate_and_fix_allocation(allocation_result.allocation)
            
            return {
                'allocation': fixed_allocation,
                'total_cost': self._calculate_cost(fixed_allocation),
                'reasoning': allocation_result.reasoning
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
    
    def _get_strategist_feedback(self, allocation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Get structured feedback from optimization strategist"""
        
        context = {
            'machines': self.machines,
            'demand': self.demand,
            'allocation': allocation_result['allocation'],
            'total_cost': allocation_result['total_cost'],
            'reasoning': allocation_result.get('reasoning', '')
        }
        
        try:
            crew = Crew(
                agents=[self.optimization_strategist()],
                tasks=[self.strategist_evaluation_task()],
                process=Process.sequential,
                verbose=False
            )
            
            result = crew.kickoff(inputs=context)
            
            if result.tasks_output and hasattr(result.tasks_output[0], 'pydantic'):
                feedback = result.tasks_output[0].pydantic
                return {
                    'assessment': feedback.assessment_rating,
                    'recommendations': feedback.key_recommendations,
                    'concerns': feedback.concerns,
                    'applied_strategies': feedback.applied_strategies,
                    'mathematically_verified': feedback.mathematically_verified,
                    'alternatives_tested': feedback.alternatives_tested,
                    'verification_details': feedback.verification_details
                }
            else:
                # Fallback for unstructured output
                feedback_text = str(result.tasks_output[0].raw) if result.tasks_output else "No feedback available"
                return {
                    'assessment': 'acceptable',  # Default rating
                    'recommendations': ['Review allocation for improvements'],
                    'concerns': ['Unable to provide structured feedback'],
                    'applied_strategies': ['Fallback analysis'],
                    'mathematically_verified': False,
                    'alternatives_tested': False,
                    'verification_details': 'Fallback: No verification performed due to parsing error'
                }
        except Exception as e:
            print(f"Error getting feedback from Optimization Strategist: {e}")
            return {
                'assessment': 'acceptable',
                'recommendations': ['Review allocation'],
                'concerns': ['Strategist evaluation failed'],
                'applied_strategies': ['Error handling'],
                'mathematically_verified': False,
                'alternatives_tested': False,
                'verification_details': f'Error occurred during evaluation: {str(e)}'
            }
    
    def _validate_and_fix_allocation(self, allocation: Dict[str, int]) -> Dict[str, int]:
        """Validate allocation against capacity constraints and fix if needed"""
        fixed_allocation = {}
        total_demand = self.demand
        allocated_so_far = 0
        violations_found = []
        
        # First pass: fix capacity violations
        for machine, units in allocation.items():
            if machine in self.machines:
                capacity = int(self.machines[machine]['capacity'])
                if units > capacity:
                    violations_found.append(f"{machine}: {units} > {capacity}")
                    units = capacity
                fixed_units = min(units, capacity)
                fixed_allocation[machine] = fixed_units
                allocated_so_far += fixed_units
        
        if violations_found:
            print(f"⚠️  Fixed capacity violations: {', '.join(violations_found)}")
        
        # Second pass: if we haven't met demand, try to allocate more
        if allocated_so_far < total_demand:
            remaining_demand = total_demand - allocated_so_far
            print(f"⚠️  Allocating remaining {remaining_demand} units to efficient machines")
            
            # Sort machines by efficiency
            machine_efficiency = []
            for machine, specs in self.machines.items():
                var_cost = specs['variable_cost']
                fixed_cost = specs['fixed_cost']
                capacity = specs['capacity']
                cost_per_unit = var_cost + (fixed_cost / (capacity * 0.5))
                machine_efficiency.append((machine, cost_per_unit, capacity))
            
            machine_efficiency.sort(key=lambda x: x[1])
            
            # Allocate remaining demand to most efficient machines
            for machine, _, capacity in machine_efficiency:
                if remaining_demand <= 0:
                    break
                current_allocation = fixed_allocation.get(machine, 0)
                available_capacity = capacity - current_allocation
                additional_allocation = min(remaining_demand, available_capacity)
                
                if additional_allocation > 0:
                    fixed_allocation[machine] = current_allocation + additional_allocation
                    remaining_demand -= additional_allocation
        
        # Ensure all machines are represented (even with 0 allocation)
        for machine in self.machines:
            if machine not in fixed_allocation:
                fixed_allocation[machine] = 0
        
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
    
    def _format_strategist_feedback(self) -> str:
        """Format strategist feedback for allocator context with more detail"""
        if not self.history:
            return "No previous strategist feedback available."
        
        latest_feedback = self.history[-1].get('strategist_feedback', {}) if self.history else {}
        
        if not latest_feedback:
            return "No strategist feedback available from previous iteration."
        
        assessment = latest_feedback.get('assessment', 'No assessment')
        recommendations = latest_feedback.get('recommendations', [])
        concerns = latest_feedback.get('concerns', [])
        applied_strategies = latest_feedback.get('applied_strategies', [])
        
        feedback_parts = [f"Strategist Assessment: {assessment}"]
        
        if recommendations:
            feedback_parts.append(f"RECOMMENDS: {' | '.join(recommendations[:3])}")  # Up to 3 recommendations
        if concerns:
            feedback_parts.append(f"CONCERNS: {' | '.join(concerns[:2])}")  # Up to 2 concerns
        if applied_strategies:
            feedback_parts.append(f"STRATEGIES USED: {', '.join(applied_strategies[:3])}")
        
        return " - ".join(feedback_parts)
    
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
            'optimization_history': self.history,
            'final_strategist_feedback': best_iteration.get('strategist_feedback', {})
        }