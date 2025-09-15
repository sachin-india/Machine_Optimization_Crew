import pandas as pd
import numpy as np
from typing import List, Union, Dict, Any

class ToolSelector:
    def __init__(self, csv_path: str = "input/allocation_tools.csv"):
        """Initialize with CSV file containing machine data."""
        self.machines_df = pd.read_csv(csv_path)
        
    def select_tools(self, selection: Union[List[str], int], demand: int = 1000) -> Dict[str, Any]:
        """
        Select tools either by specific IDs or random selection.
        
        Args:
            selection: Either a list of Tool_IDs or an integer for random selection
            demand: Product demand (default: 1000)
            
        Returns:
            Dictionary formatted for CrewAI input
        """
        if isinstance(selection, list):
            # Select specific Tool_IDs
            tool_ids_str = [str(tid) for tid in selection]
            selected_df = self.machines_df[self.machines_df['Tool_ID'].astype(str).isin(tool_ids_str)]
            if len(selected_df) == 0:
                raise ValueError(f"No tools found with IDs: {selection}")
        elif isinstance(selection, int) and selection > 2:
            # Random selection - reset random seed each time for true randomness
            np.random.seed(None)
            if selection > len(self.machines_df):
                raise ValueError(f"Cannot select {selection} tools, only {len(self.machines_df)} available")
            selected_df = self.machines_df.sample(n=selection)
        else:
            raise ValueError("Selection must be a list of Tool_IDs or integer > 2")
        
        # Convert to CrewAI format
        machines = {}
        for _, row in selected_df.iterrows():
            tool_key = f"Tool_{row['Tool_ID']}"
            machines[tool_key] = {
                'capacity': int(row['capacity']),
                'variable_cost': float(row['variable_cost']),
                'fixed_cost': float(row['fixed_cost'])
            }
        
        return {
            'product_demand': demand,
            'machines': machines
        }