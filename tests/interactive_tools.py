import os
import sys
import time
import pytest
from nova.galaxy import Connection, Tool
from nova.galaxy.tool import stop_all_tools_in_store


def test_interactive_tool(interactive_tool: str) -> bool:
    """
    Runs an integration test for a given tool ID with provided parameters
    """
    try:
        conn = Connection(
            galaxy_url=os.environ["GALAXY_URL"], galaxy_key=os.environ["API_KEY"]
        )
        with conn.connect() as connection:
            d_store = connection.create_data_store(name=f"{interactive_tool}_test")
            d_store.persist()
            d_tool = Tool(id=interactive_tool)
            d_tool.run_interactive(d_store, max_tries=900)
            print(f"Tool {interactive_tool} started successfully.")
            stop_all_tools_in_store(d_store)
            return True
    except Exception as e:
        print(f"Tool {interactive_tool} failed to start: {str(e)}")

        try:
            # Give Galaxy time to record job metrics.
            time.sleep(30)
            print(d_tool._job.get_console_output(0, sys.maxsize - 1))
            print(
                d_tool._job.galaxy_instance.jobs.get_destination_params(d_tool._job.id)
            )
        except Exception:
            # We couldn't fetch any details about the tool, giving up completely :(
            pass

        return False


if __name__ == "__main__":
    # Path for test results
    result_dir = os.environ.get("TEST_RESULTS_DIR", ".")
    test_results_dir = os.path.join(result_dir, "test_results")

    # Create test_results directory if it doesn't exist
    os.makedirs(test_results_dir, exist_ok=True)
    json_path = os.path.join(test_results_dir, "interactive_tests_report.json")

    # Run the tests
    current_dir = os.path.dirname(os.path.abspath(__file__))
    exit_code = pytest.main(
        ["-v", f"--json={json_path}", os.path.join(current_dir, "interactive_tools.py")]
    )

    # Push results to Prometheus if requested
    if "--push-metrics" in sys.argv:
        try:
            parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            sys.path.insert(0, parent_dir)
            from scripts.push_to_gateway import (
                collect_pytest_test_results,
                push_pytest_results_to_prometheus,
            )

            json_path = os.path.join(test_results_dir, "interactive_tests_report.json")
            test_results = collect_pytest_test_results(json_path)
            if test_results:
                push_pytest_results_to_prometheus(test_results)
        except Exception as e:
            print(f"Failed to push results to Prometheus: {str(e)}")

    sys.exit(exit_code)
