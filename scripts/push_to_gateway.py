import fnmatch
import json
import os
import sys

from prometheus_client import CollectorRegistry, Gauge, Info, push_to_gateway

def collect_test_results(filename):
    try:
        with open(filename, 'r') as file:
            report_data = json.load(file)

        test_results = {}
        for item in report_data['tests']:
            tool_id = item['data']['tool_id']
            outcome = item['data']['status'] == 'success'
            test_results[tool_id] = {'outcome': outcome}

        return test_results

    except FileNotFoundError:
        print("JSON report not found. Make sure pytest was run with --json option.")
        return {}

def push_results_to_prometheus(test_results):
    pipeline_url = f"{os.environ.get('CI_PROJECT_URL')}/-/pipelines/{os.environ.get('CI_PIPELINE_ID')}"
    auth_mode = os.getenv("AUTH_MODE", "unknown")
    env = os.getenv("ENVIRONMENT", "unknown")

    registry = CollectorRegistry()
    gauge_outcome = Gauge('planemo_tool_tests', 'Planemo tool tests outcome (pass/fail)',
                          ['tool_id', 'pipeline_url', 'env'], registry=registry)

    for tool_id, result_info in test_results.items():
        outcome = int(result_info['outcome'])
        gauge_outcome.labels(tool_id, pipeline_url, env).set(outcome)

    prometheus_url = os.getenv("PROMETHEUS_URL")
    push_to_gateway(
        prometheus_url, job=f"planemo_tests_{env}_{auth_mode}", registry=registry
    )


def collect_pytest_test_results(filename=None):
    """
    Collects pytest test results from JSON files in a directory.
    It looks for files matching 'test_output_*.json' or '*_report.json'
    but will only successfully parse those in pytest-json format.

    Args:
        directory: Directory to search for JSON files

    Returns:
        A dictionary of pytest_results.
    """
    pytest_results = {}
    files_to_process = []

    if filename and os.path.isfile(filename):
        files_to_process.append(filename)

    print(f"Found {len(files_to_process)} file to process.")
    for file_path in files_to_process:
        file_results = _process_pytest_json_file(file_path)
        pytest_results.update(file_results)

    print(pytest_results)
    return pytest_results

def _process_pytest_json_file(filename):
    """
    Process a pytest-json output file.
    
    Returns a tuple: (report_type, results_dict).
    report_type is 'pytest' if the format is recognized, otherwise None.
    """
    try:
        with open(filename, 'r') as file:
            report_data = json.load(file)
        
        results = {}
        
        # Verify it's a pytest-json format
        if 'report' in report_data and 'tests' in report_data['report']:
            for item in report_data['report']['tests']:
                test_name = item['name']
                # Extract the tool_id from test_name if it's in the format test_interactive_tool[tool_id-params]
                if '[' in test_name and ']' in test_name:
                    tool_part = test_name.split('[')[1].split(']')[0]
                    if '-' in tool_part:
                        tool_id = tool_part.split('-')[0]
                    else:
                        tool_id = tool_part
                else:
                    tool_id = test_name

                outcome = item['outcome'] == 'passed'
                results[tool_id] = {
                    'outcome': outcome
                }

                # Add error information if available
                if not outcome and 'call' in item and 'longrepr' in item['call']:
                    results[tool_id]['error_message'] = item['call']['longrepr']
        
        return results

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error processing pytest JSON file {filename}: {str(e)}")
        return None, {}

def push_pytest_results_to_prometheus(pytest_results):
    """
    Push pytest results to Prometheus gateway using appropriate metrics/jobs.

    Args:
        pytest_results: Dictionary of pytest test results.
    """
    pipeline_url = f"{os.environ.get('CI_PROJECT_URL')}/-/pipelines/{os.environ.get('CI_PIPELINE_ID')}"
    auth_mode = os.getenv("AUTH_MODE", "unknown")
    env = os.getenv("ENVIRONMENT", "unknown")

    prometheus_url = os.getenv('PROMETHEUS_URL')
    if not prometheus_url:
        print("PROMETHEUS_URL environment variable not set. Skipping metrics push.")
        return

    pytest_registry = CollectorRegistry()
    pytest_gauge = Gauge('galaxy_tool_tests', 'Galaxy tool tests outcome (pass/fail)',
                            ['tool_id', 'pipeline_url', 'env'], registry=pytest_registry)
    pytest_error_info = Info('galaxy_tool_test_errors', 'Galaxy tool test error messages',
                            ['tool_id', 'pipeline_url', 'env'], registry=pytest_registry)
    for tool_id, result_info in pytest_results.items():
        outcome = int(result_info['outcome'])
        pytest_gauge.labels(tool_id, pipeline_url, env).set(outcome)
        if not outcome and 'error_message' in result_info:
            pytest_error_info.labels(tool_id, pipeline_url, env).info({
                'error_message': str(result_info['error_message'])[:1024] # Limit length
            })
    try:
        push_to_gateway(
            prometheus_url,
            job=f"galaxy_tools_tests_{env}_{auth_mode}",
            registry=pytest_registry,
        )
        print(f"Successfully pushed {len(pytest_results)} pytest results.")
    except Exception as e:
        print(f"Error pushing pytest results to Prometheus: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python push_to_gateway.py <directory_or_file>")
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isdir(path):
        test_results ={}
        for root, _, files in os.walk(path):
            for file in files:
                if fnmatch.fnmatch(file, "test_output_*.json"):
                    test_results.update(collect_test_results(os.path.join(root, file)))
            push_results_to_prometheus(test_results)
    elif os.path.isfile(path):
        pytest_results = collect_pytest_test_results(path)
        if pytest_results:
            push_pytest_results_to_prometheus(pytest_results)
        else:
            print(f"No pytest test results found in directory: {path}")
            sys.exit(1)
    else:
        print(f"Error: Path '{path}' is not a valid file or directory.")
        sys.exit(1)
