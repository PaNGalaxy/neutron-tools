import fnmatch
import json
import os
import sys

from prometheus_client import CollectorRegistry, Gauge, Info, push_to_gateway

def collect_test_results(filename=None, directory=None):
    """
    Collects test results from either a single JSON file or a directory
    of JSON files. Can handle both Planemo and pytest JSON formats.

    Args:
        filename: Path to a specific JSON file to process
        directory: Directory to search for JSON files

    Returns:
        A tuple containing two dictionaries: (planemo_results, pytest_results)
    """
    planemo_results = {}
    pytest_results = {}

    files_to_process = []
    if filename and os.path.isfile(filename):
        files_to_process.append(filename)
    elif directory:
        for root, _, files in os.walk(directory):
            for file in files:
                if fnmatch.fnmatch(file, "test_output_*.json") or fnmatch.fnmatch(file, "*_report.json"):
                    files_to_process.append(os.path.join(root, file))

    for file_path in files_to_process:
        report_type, file_results = _process_json_file(file_path)
        if report_type == 'planemo':
            planemo_results.update(file_results)
        elif report_type == 'pytest':
            pytest_results.update(file_results)

    return planemo_results, pytest_results

def _process_json_file(filename):
    """
    Process a JSON file which could be in various formats:
    - Planemo test output format
    - pytest-json output format
    
    Returns a tuple: (report_type, results_dict).
    report_type is 'planemo', 'pytest', or None if format is unrecognized.
    """
    try:
        with open(filename, 'r') as file:
            report_data = json.load(file)
        
        results = {}
        report_type = None
        # Check if it's a Planemo report format
        if 'tests' in report_data and isinstance(report_data['tests'], list):
            for item in report_data['tests']:
                if 'data' in item and 'tool_id' in item['data']:
                    # Planemo format
                    report_type = 'planemo'
                    tool_id = item['data']['tool_id']
                    outcome = item['data']['status'] == 'success'
                    results[tool_id] = {'outcome': outcome}
        
        # Check if it's a pytest-json format
        elif 'report' in report_data and 'tests' in report_data['report']:
            report_type = 'pytest'
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
        
        return report_type, results

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error processing JSON file {filename}: {str(e)}")
        return None, {}

def push_results_to_prometheus(planemo_results, pytest_results):
    """
    Push Planemo and pytest results to Prometheus gateway using appropriate metrics/jobs.

    Args:
        planemo_results: Dictionary of Planemo test results.
        pytest_results: Dictionary of pytest test results.
    """
    pipeline_url = f"{os.environ.get('CI_PROJECT_URL')}/-/pipelines/{os.environ.get('CI_PIPELINE_ID')}"
    env = os.getenv('ENVIRONMENT', 'unknown')

    prometheus_url = os.getenv('PROMETHEUS_URL')
    if not prometheus_url:
        print("PROMETHEUS_URL environment variable not set. Skipping metrics push.")
        return

    # Push Planemo results
    if planemo_results:
        planemo_registry = CollectorRegistry()
        planemo_gauge = Gauge('planemo_tool_tests', 'Planemo tool tests outcome (pass/fail)',
                              ['tool_id', 'pipeline_url', 'env'], registry=planemo_registry)
        for tool_id, result_info in planemo_results.items():
            outcome = int(result_info['outcome'])
            planemo_gauge.labels(tool_id, pipeline_url, env).set(outcome)
        try:
            push_to_gateway(prometheus_url, job=f'planemo_tests_{env}', registry=planemo_registry)
            print(f"Successfully pushed {len(planemo_results)} Planemo results.")
        except Exception as e:
            print(f"Error pushing Planemo results to Prometheus: {e}")

    # Push pytest results
    if pytest_results:
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
            push_to_gateway(prometheus_url, job=f'galaxy_tools_tests_{env}', registry=pytest_registry)
            print(f"Successfully pushed {len(pytest_results)} pytest results.")
        except Exception as e:
            print(f"Error pushing pytest results to Prometheus: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python push_to_gateway.py <directory_or_file>")
        sys.exit(1)
        
    path = sys.argv[1]
    if os.path.isfile(path):
        planemo_results, pytest_results = collect_test_results(filename=path)
    elif os.path.isdir(path):
        planemo_results, pytest_results = collect_test_results(directory=path)
    else:
        print(f"Error: Path '{path}' is not a valid file or directory.")
        sys.exit(1)

    if planemo_results or pytest_results:
        push_results_to_prometheus(planemo_results, pytest_results)
    else:
        print("No test results found.")
        sys.exit(1)
