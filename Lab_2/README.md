# Tool Enforcement Challenge Demo

This demonstration shows how difficult it is to force LLM agents to use tools, even when explicitly instructed to do so.

## What This Demo Shows

1. **The Challenge**: An AI agent is given a cost calculator tool and explicitly told to use it
2. **The Problem**: The agent ignores the tool and calculates costs manually
3. **The Evidence**: We track whether the tool was actually called (spoiler: it usually isn't)
4. **The Reality**: Even sophisticated agents bypass tools when they can calculate themselves

## Current Setup (Simplified)

### Core Files
- `main.py` - **SINGLE MAIN FILE** - Run this to see the demonstration
- `calculator_tool.py` - The tool that should be used for calculations
- `crew.py` - CrewAI setup with agent and task definitions
- `tool_selector.py` - Utility to select random machines for the problem

### Configuration
- `config/agents.yaml` - Simple agent role and instructions
- `config/tasks.yaml` - Clear task description telling agent to use the tool
- `input/allocation_tools.csv` - Machine data for the optimization problem

## How to Run

```bash
python main.py
```

## What You'll See

1. **Machine Selection**: Random machines with different costs and capacities
2. **Agent Execution**: The agent finds an optimal allocation strategy
3. **Tool Usage Check**: Verification showing the calculator tool was NOT used
4. **Agent's Reasoning**: Despite claiming to follow instructions, the agent calculates manually

## Example Output

```
=== TOOL ENFORCEMENT DEMONSTRATION ===
Selected machines:
  Tool_220: Capacity=1100, Variable=$5.0, Fixed=$3000.0
  Tool_157: Capacity=1100, Variable=$7.0, Fixed=$1500.0
  Tool_992: Capacity=900, Variable=$9.0, Fixed=$2500.0

=== RUNNING CREW ===
Agent finds optimal allocation and calculates costs...

=== TOOL USAGE CHECK ===
❌ PROBLEM: Agent did NOT use the calculator tool!
The agent calculated costs manually instead of using the tool.
```

## Key Learning Points

1. **LLM Intelligence**: Modern AI agents are smart enough to do complex math themselves
2. **Instruction Following**: Even explicit "MUST use tool" instructions can be ignored
3. **Process vs Results**: The agent may get correct results but violate process requirements
4. **Real-World Implications**: In production systems, tool usage enforcement is critical for:
   - Audit trails
   - Consistency
   - Validation
   - Compliance

## Why This Matters

In real-world AI systems, you often need agents to follow specific processes, not just get correct answers. This demo shows why validation and monitoring are essential when deploying AI agents in production environments.

## Teaching Notes

This demo is perfect for showing students:
- The gap between AI capabilities and process compliance
- Why we can't always trust AI agents to follow instructions
- The importance of validation in AI systems
- Real-world challenges in AI deployment
- How sophisticated modern LLMs are at reasoning and calculation

## Technical Details

The agent consistently:
1. ✅ Understands the optimization problem
2. ✅ Finds good allocation strategies
3. ✅ Calculates costs accurately
4. ❌ Bypasses the required cost calculator tool
5. ❌ Claims to follow instructions while actually ignoring them

This demonstrates both the power and the challenges of modern AI agents!
