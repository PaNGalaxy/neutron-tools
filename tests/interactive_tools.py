import os
import sys
from typing import Optional
from nova_galaxy import Nova, Tool, Parameters

def run_tool_test( tool_id: str, params: Optional[Parameters] = None) -> bool:
    """
    Runs an integration test for a given tool ID with provided parameters
    """
    try:
        nova = Nova(galaxy_url = os.environ["GALAXY_URL"], api_key = os.environ["API_KEY"])
        with nova.connect() as connection:
            d_store = connection.create_data_store(name = f"{tool_id}_test")
            d_store.persist()
            d_tool = Tool(id=tool_id)
            if params is None:
                params = Parameters()
            link = d_tool.run_interactive(d_store, params)
            print(f"Tool {tool_id} started successfully.")
            return True
    except Exception as e:
        print(f"Tool {tool_id} failed to start.")
        return False
    
if __name__ == "__main__":
    interactive_tools = {
        "interactive_tool_amira": None,
        "interactive_tool_jana2020": None
    }

    status = True
    for tool_id, params in interactive_tools.items():
        if not run_tool_test(tool_id, params):
            status = False
    if not status:
        sys.exit(1)