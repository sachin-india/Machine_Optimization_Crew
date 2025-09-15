# Lab 5: Manufacturing Optimization with Expert Panel and Reporting

## Overview

Lab 5 implements an advanced manufacturing optimization system that uses multiple expert agents to iteratively improve machine allocation decisions. The system finds the optimal allocation of production demand across different machines while minimizing total manufacturing costs.

## Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Tool Selector │    │   Orchestrator  │    │    Reporter     │
│                 │    │                 │    │                 │
│ - Machine DB    │───▶│ - Optimization  │───▶│ - Report Gen    │
│ - Selection     │    │ - Expert Panel  │    │ - Analysis      │
│ - Validation    │    │ - Convergence   │    │ - Insights      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ allocation_     │    │ optimization_   │    │ markdown_       │
│ tools.csv       │    │ history.json    │    │ reports/        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Agent Architecture

```
Orchestrator
├── Allocator Agent (Main Decision Maker)
│   └── Generates allocation proposals with detailed reasoning
│
└── Expert Panel (5 Specialized Agents)
    ├── Cost Expert → Overall cost minimization
    ├── Efficiency Expert → Machine utilization optimization
    ├── Variable Cost Expert → Variable cost reduction
    ├── Fixed Cost Expert → Fixed cost optimization
    └── Batch Optimization Expert → Economies of scale

Reporter (Separate Crew)
└── Optimization Reporter → Comprehensive report generation
```

## System Flow

### 1. Initialization Phase
```python
# Machine Selection
selector = ToolSelector("input/allocation_tools.csv")
problem_input = selector.select_tools(4, demand=3000)
```

- **Tool Selector** loads machine database from CSV
- Selects 4 random machines or specific machines if needed
- Validates sufficient capacity for demand (3000 units)

### 2. Optimization Phase
```python
# Iterative Optimization
orchestrator = OptimizationOrchestrator()
final_result = orchestrator.run_optimization_with_visibility()
```

#### Iteration Loop:
1. **Allocator Agent** proposes machine allocation
2. **Expert Panel** evaluates the proposal (5 agents in parallel)
3. **Convergence Check** determines if optimization should continue
4. **Feedback Integration** for next iteration

#### Convergence Criteria:
- Maximum 5 iterations (hard stop)
- Cost improvement < 2% (diminishing returns)
- Expert consensus achieved (3+ experts approve)

### 3. Reporting Phase
```python
# Report Generation
reporter = OptimizationReporter()
report_path = reporter.generate_report(final_result, problem_context)
```

- **Comprehensive Report**: Detailed analysis by AI agent
- **Summary Report**: Quick overview with key metrics
- **Markdown Format**: Professional documentation

## File Structure

```
Lab_5/
├── main.py                 # Entry point and coordination
├── orchestrator.py         # Optimization orchestration
├── reporter.py            # Report generation crew
├── tool_selector.py       # Machine selection logic
├── config/
│   ├── agents.yaml        # Agent configurations
│   └── tasks.yaml         # Task definitions
├── input/
│   └── allocation_tools.csv # Machine database
└── reports/               # Generated reports
    ├── optimization_report_*.md
    └── optimization_summary_*.md
```

## Key Features

### 1. Multi-Agent Expert System
- **Specialized Expertise**: Each expert focuses on specific optimization aspects
- **Parallel Evaluation**: All experts evaluate proposals simultaneously
- **Structured Feedback**: Consistent assessment format with ratings and recommendations

### 2. Iterative Improvement
- **Learning Loop**: Each iteration incorporates previous expert feedback
- **Cost Tracking**: Monitors cost improvements across iterations
- **Transparency**: Detailed logging of decisions and reasoning

### 3. Intelligent Convergence
- **Multiple Criteria**: Cost, consensus, and iteration limits
- **Early Stopping**: Prevents over-optimization
- **Flexible Thresholds**: Configurable convergence parameters

### 4. Comprehensive Reporting
- **Dual Format**: Both detailed and summary reports
- **Business Focus**: Actionable insights and recommendations
- **Professional Output**: Markdown format suitable for documentation

## Configuration

### Machine Selection Options

#### Random Selection (Default)
```python
problem_input = selector.select_tools(4, demand=3000)
```

#### Specific Machine IDs
```python
problem_input = selector.select_tools([2, 6, 13, 25], demand=3000)
```

### Demand Configuration
```python
# Change demand in main.py
problem_input = selector.select_tools(4, demand=5000)  # 5000 units
```

### Convergence Parameters
```python
# In orchestrator.py - SimpleConvergenceManager
self.max_iterations = 5         # Maximum iterations
self.cost_threshold = 0.02      # 2% improvement threshold
self.consensus_threshold = 3    # Expert consensus requirement
```

## Agent Configurations

### Allocator Agent
- **Role**: Manufacturing Allocation Specialist
- **Goal**: Find optimal allocation through step-by-step reasoning
- **Output**: Structured allocation with cost calculations

### Expert Agents
Each expert has specialized knowledge:

- **Cost Expert**: Overall cost minimization strategies
- **Efficiency Expert**: Machine utilization and capacity optimization
- **Variable Cost Expert**: Variable cost reduction techniques
- **Fixed Cost Expert**: Fixed cost optimization strategies  
- **Batch Expert**: Economies of scale and batch optimization

### Reporter Agent
- **Role**: Manufacturing Optimization Report Analyst
- **Goal**: Create comprehensive markdown reports
- **Output**: Professional analysis with insights and recommendations

## Running the System

### Prerequisites
```bash
# Install dependencies
pip install crewai pandas numpy openai
```

### Execution
```bash
# Navigate to Lab_5 directory
cd Lab_5

# Run optimization
python main.py
```

### Expected Output
1. **Console Output**: Real-time optimization progress
2. **Reports Directory**: Generated markdown reports
3. **Cost Analysis**: Iteration-by-iteration cost improvements

## Example Output

### Console Progress
```
🏭 Manufacturing Optimization Process Starting...
📊 Problem: Allocate 3000 units across 4 machines

🔄 ITERATION 1
💡 Allocator Decision: {'Tool_6': 1600, 'Tool_2': 800, 'Tool_13': 600, 'Tool_25': 0}
💰 Calculated Cost: $20,700.00
👥 Expert Panel Feedback: [Cost: acceptable, Efficiency: good, ...]

✅ OPTIMIZATION COMPLETE: expert_consensus_achieved
```

### Generated Reports
- `optimization_report_YYYYMMDD_HHMMSS.md`: Comprehensive analysis
- `optimization_summary_YYYYMMDD_HHMMSS.md`: Executive summary

## Customization Options

### 1. Machine Database
Modify `input/allocation_tools.csv` to add/change machines:
```csv
Tool_ID,fixed_cost,variable_cost,capacity
1,5000,9,1400
2,3000,3,800
...
```

### 2. Expert Panel
Add new experts in `config/agents.yaml` and `config/tasks.yaml`:
```yaml
sustainability_expert:
  role: Environmental Impact Expert
  goal: Minimize environmental footprint of manufacturing
```

### 3. Convergence Logic
Modify `SimpleConvergenceManager` in `orchestrator.py`:
```python
def __init__(self):
    self.max_iterations = 10        # More iterations
    self.cost_threshold = 0.01      # Stricter improvement threshold
    self.consensus_threshold = 4    # Higher consensus requirement
```

### 4. Reporting Format
Customize report templates in `reporter.py`:
```python
# Add new sections, modify analysis depth, change output format
```

## Technical Details

### Data Flow
1. **Input**: Machine specifications + demand requirements
2. **Processing**: Multi-agent iterative optimization
3. **Output**: Optimal allocation + comprehensive analysis

### Cost Calculation
```python
total_cost = sum(
    (variable_cost * units + fixed_cost) 
    for machine, units in allocation.items() 
    if units > 0
)
```

### Validation
- **Capacity Constraints**: No allocation exceeds machine capacity
- **Demand Fulfillment**: Total allocation equals exact demand
- **Cost Accuracy**: Mathematical verification of cost calculations

## Troubleshooting

### Common Issues

1. **Insufficient Capacity**
   - Solution: Add more machines or reduce demand
   - Check: `allocation_tools.csv` for machine capacities

2. **Convergence Problems**
   - Solution: Adjust convergence thresholds
   - Check: Expert feedback quality and consistency

3. **Report Generation Failures**
   - Solution: Check OpenAI API connectivity
   - Fallback: Summary report always generates

### Debug Mode
Enable verbose logging in `orchestrator.py`:
```python
verbose=True  # In Crew initialization
```

## Performance Considerations

- **Iterations**: Typically converges in 2-4 iterations
- **Time**: ~30-60 seconds for complete optimization
- **Scalability**: Handles 100+ machines efficiently
- **Memory**: Minimal requirements for typical problems

## Future Enhancements

1. **Multi-Objective Optimization**: Include sustainability, quality metrics
2. **Dynamic Pricing**: Real-time cost adjustments
3. **Capacity Planning**: Long-term demand forecasting
4. **Integration**: API endpoints for external systems
5. **Visualization**: Interactive charts and graphs

## Support

For issues or questions:
1. Check console output for error messages
2. Verify configuration files syntax
3. Review machine database format
4. Check convergence criteria settings

---

*Last Updated: September 2025*
*Version: 1.0*