import os
import sys
import pytest
from typing import Optional, Dict, Any
from nova.galaxy import Connection, Tool, Parameters
from nova.galaxy.tool import stop_all_tools_in_store


def run_tool_test(tool_id: str, params: Optional[Parameters] = None) -> bool:
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
            link = d_tool.run_interactive(d_store, params, max_tries = 900)
            print(f"Tool {tool_id} started successfully.")
            stop_all_tools_in_store(d_store)
            return True
    except Exception as e:
        print(f"Tool {tool_id} failed to start: {str(e)}")
        return False

# Dictionary of interactive tools to test
INTERACTIVE_TOOLS_BOTH = {
    "nova-interactive-tool-jana2020": None,
    "interactive_tool_jupyter_notebook": None,
    "nova-neutrons-trame-topaz": None,
    "nova-interactive-tool-sasview": None,
    "nova-neutrons-reflectometry-refl1d": None,
    "neutrons_gravitas_sunny": None,
    "nova-neutrons-cp2k-gui": None
}
INTERACTIVE_TOOLS_TEST = {
    "neutrons_airsans_demo": None,
    "neutrons_trame_garnet": None,
    "nova-interactive-tool-amira": None,
    "neutrons_ctr": None,
    "neutrons_gravitas_phonopy": None,
    "nova-neutrons-trame-time-resolved-vis": None,
}

# Probably will never need to test something in prod without also testing in test but it's here just in case.
INTERACTIVE_TOOLS_PROD = {

}

if os.environ.get("ENVIRONMENT") == "calvera-test":
    INTERACTIVE_TOOLS_BOTH.update(INTERACTIVE_TOOLS_TEST)
elif os.environ.get("ENVIRONMENT") == "calvera":
    INTERACTIVE_TOOLS_BOTH.update(INTERACTIVE_TOOLS_PROD)

# Create a test function for each interactive tool
@pytest.mark.parametrize("tool_id,params", list(INTERACTIVE_TOOLS_BOTH.items()))
def test_interactive_tool(tool_id: str, params: Optional[Dict[str, Any]]):
    """
    Parameterized test function that tests each interactive tool
    """
    assert run_tool_test(tool_id, params), f"Tool {tool_id} failed to start"

def pytest_configure(config):
    pass

if __name__ == "__main__":
    # Path for test results
    result_dir = os.environ.get("TEST_RESULTS_DIR", ".")
    test_results_dir = os.path.join(result_dir, "test_results")
    
    # Create test_results directory if it doesn't exist
    os.makedirs(test_results_dir, exist_ok=True)
    json_path = os.path.join(test_results_dir, "interactive_tests_report.json")
    
    # Run the tests
    current_dir = os.path.dirname(os.path.abspath(__file__))
    exit_code = pytest.main(["-v", f"--json={json_path}", os.path.join(current_dir, "interactive_tools.py")])
    
    # Push results to Prometheus if requested
    if "--push-metrics" in sys.argv:
        try:
            parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            sys.path.insert(0, parent_dir)
            from scripts.push_to_gateway import collect_pytest_test_results, push_pytest_results_to_prometheus
            json_path = os.path.join(test_results_dir, "interactive_tests_report.json")
            test_results = collect_pytest_test_results(json_path)
            if test_results:
                push_pytest_results_to_prometheus(test_results)
        except Exception as e:
            print(f"Failed to push results to Prometheus: {str(e)}")
    
    sys.exit(exit_code)
