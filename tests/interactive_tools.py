import os
import sys
from typing import Optional
from nova.galaxy import Connection, Tool, Parameters
from nova.galaxy.tool import stop_all_tools_in_store

def run_tool_test( tool_id: str, params: Optional[Parameters] = None) -> bool:
    """
    Runs an integration test for a given tool ID with provided parameters
    """
    try:
        conn = Connection(galaxy_url = os.environ["GALAXY_URL"], galaxy_key = os.environ["API_KEY"])
        with conn.connect() as connection:
            d_store = connection.create_data_store(name = f"{tool_id}_test")
            d_store.persist()
            d_tool = Tool(id=tool_id)
            if params is None:
                params = Parameters()
            link = d_tool.run_interactive(d_store, params, max_tries = 600)
            print(f"Tool {tool_id} started successfully.")
            stop_all_tools_in_store(d_store)
            return True
    except Exception as e:
        print(f"Tool {tool_id} failed to start.")
        return False
    
if __name__ == "__main__":
    interactive_tools = {
        "interactive_tool_amira": None,
        # "interactive_tool_jana2020": None, https://code.ornl.gov/ndip/galaxy-tools/-/issues/158
        "neutrons_trame_garnet": None,
        "neutrons_trame_topaz": None,
        # "interactive_tool_paraview": None, https://code.ornl.gov/ndip/galaxy-tools/-/issues/159
        "interactive_tool_generic_output": None,
        "neutrons_airsans_demo": None,
        "neutrons_ctr": None,
        "interactive_tool_sasview": None,
        # "neutrons_interactive_tool_drtsans": None, https://code.ornl.gov/ndip/galaxy-tools/-/issues/160
        # "neutrons_trame_sans": None, https://code.ornl.gov/ndip/galaxy-tools/-/issues/161
        "neutrons_reflectometry_refl1d": None,
        # "neutrons_reduce120": None, https://code.ornl.gov/ndip/galaxy-tools/-/issues/162
        "neutrons_trame_gravitas": None,
        "neutrons_trame_time_resolved_vis": None,
        "neutrons_gravitas_phonopy": None,
        "neutrons_gravitas_sunny": None,
        "neutrons_cp2k_gui": None
    }

    status = True
    for tool_id, params in interactive_tools.items():
        if not run_tool_test(tool_id, params):
            status = False
    
    if not status:
        sys.exit(1)