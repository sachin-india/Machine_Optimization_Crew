"""
Manufacturing Optimization Reporter
Generates comprehensive markdown reports from optimization results
"""

import os
from typing import Dict, List, Any
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew


@CrewBase
class OptimizationReporter:
    """Generates comprehensive reports from optimization results"""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(self):
        self.output_dir = "reports"
        # Create reports directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    @agent
    def optimization_reporter(self) -> Agent:
        """Reporter agent that analyzes optimization data and creates reports"""
        return Agent(
            config=self.agents_config['optimization_reporter'],
            llm="openai/gpt-4o",
            verbose=True
        )
    
    @task
    def optimization_reporting_task(self) -> Task:
        """Task for generating comprehensive optimization report"""
        return Task(
            config=self.tasks_config['optimization_reporting_task'],
            agent=self.optimization_reporter()
        )
    
    @crew
    def reporter_crew(self) -> Crew:
        """Crew focused on generating optimization reports"""
        return Crew(
            agents=[self.optimization_reporter()],
            tasks=[self.optimization_reporting_task()],
            process=Process.sequential,
            verbose=True
        )
    
    def generate_report(self, optimization_results: Dict[str, Any], 
                       problem_context: Dict[str, Any]) -> str:
        """
        Generate a comprehensive optimization report
        
        Args:
            optimization_results: Results from orchestrator optimization
            problem_context: Original problem setup (machines, demand, etc.)
        
        Returns:
            Path to generated markdown report file
        """
        
        print("📝 Starting report generation...")
        
        # Prepare context for the reporter
        report_context = {
            **problem_context,
            **optimization_results,
            'convergence_reason': self._extract_convergence_reason(optimization_results),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Run the reporter crew
        result = self.reporter_crew().kickoff(inputs=report_context)
        
        # Extract the report content
        if result.tasks_output and result.tasks_output[0]:
            report_content = result.tasks_output[0].raw
        else:
            report_content = "Error: Could not generate report"
        
        # Save the report to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimization_report_{timestamp}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📊 Report generated successfully: {filepath}")
        return filepath
    
    def _extract_convergence_reason(self, optimization_results: Dict[str, Any]) -> str:
        """Extract convergence reason from optimization history"""
        history = optimization_results.get('optimization_history', [])
        if not history:
            return "Unknown"
        
        # Look for convergence indicators in the history
        total_iterations = optimization_results.get('total_iterations', 0)
        if total_iterations >= 5:
            return "Maximum iterations reached"
        
        # Check for cost improvement patterns
        if len(history) >= 2:
            last_cost = history[-1]['total_cost']
            prev_cost = history[-2]['total_cost']
            improvement = (prev_cost - last_cost) / prev_cost if prev_cost > 0 else 0
            
            if improvement < 0.02:  # Less than 2% improvement
                return "Cost improvement below threshold (2%)"
        
        return "Expert consensus achieved"
    
    def create_summary_report(self, optimization_results: Dict[str, Any], 
                            problem_context: Dict[str, Any]) -> str:
        """
        Create a quick summary report without using the crew
        (Fallback option for simple reporting)
        """
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Manufacturing Optimization Report
*Generated on {timestamp}*

## Executive Summary

The optimization process analyzed {len(problem_context['machines'])} machines to meet a demand of {problem_context['demand']} units.

**Key Results:**
- Final Cost: ${optimization_results['final_cost']:,.2f}
- Total Iterations: {optimization_results['total_iterations']}
- Cost Improvement: {optimization_results['improvement']:.1f}%

## Final Allocation

| Machine | Units Allocated | Capacity Utilization |
|---------|----------------|---------------------|
"""
        
        # Add allocation table
        for machine, units in optimization_results['final_allocation'].items():
            if machine in problem_context['machines']:
                capacity = problem_context['machines'][machine]['capacity']
                utilization = (units / capacity * 100) if capacity > 0 else 0
                report += f"| {machine} | {units:,} | {utilization:.1f}% |\n"
        
        report += f"""
## Cost Analysis

**Final Cost Breakdown:**
"""
        
        # Add cost breakdown
        total_var_cost = 0
        total_fixed_cost = 0
        
        for machine, units in optimization_results['final_allocation'].items():
            if units > 0 and machine in problem_context['machines']:
                specs = problem_context['machines'][machine]
                var_cost = specs['variable_cost'] * units
                fixed_cost = specs['fixed_cost']
                total_var_cost += var_cost
                total_fixed_cost += fixed_cost
                report += f"- {machine}: ${var_cost:,.2f} (variable) + ${fixed_cost:,.2f} (fixed) = ${var_cost + fixed_cost:,.2f}\n"
        
        report += f"""
**Total: ${total_var_cost:,.2f} (variable) + ${total_fixed_cost:,.2f} (fixed) = ${total_var_cost + total_fixed_cost:,.2f}**

## Optimization Journey

| Iteration | Total Cost | Cost Change |
|-----------|------------|-------------|
"""
        
        # Add iteration history
        for i, iteration in enumerate(optimization_results['optimization_history']):
            cost = iteration['total_cost']
            if i == 0:
                change = "Initial"
            else:
                prev_cost = optimization_results['optimization_history'][i-1]['total_cost']
                change = f"${prev_cost - cost:,.2f} saved"
            report += f"| {i+1} | ${cost:,.2f} | {change} |\n"
        
        report += """
## Recommendations

1. **Monitor Performance**: Track actual production costs against optimized allocation
2. **Capacity Planning**: Consider machine capacity constraints for future demand changes
3. **Continuous Optimization**: Re-run optimization when machine costs or capacities change

---
*Report generated by Manufacturing Optimization System*
"""
        
        # Save the summary report
        timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimization_summary_{timestamp_file}.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filepath