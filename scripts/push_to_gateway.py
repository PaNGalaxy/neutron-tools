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
        Dictionary mapping tool_id/test_name to outcome information
    """
    test_results = {}
    
    if filename and os.path.isfile(filename):
        test_results.update(_process_json_file(filename))
    
    elif directory:
        for root, _, files in os.walk(directory):
            for file in files:
                if fnmatch.fnmatch(file, "test_output_*.json") or fnmatch.fnmatch(file, "*_report.json"):
                    file_path = os.path.join(root, file)
                    test_results.update(_process_json_file(file_path))
                    
    return test_results

def _process_json_file(filename):
    """
    Process a JSON file which could be in various formats:
    - Planemo test output format
    - pytest-json output format
    
    Returns a dictionary of test results regardless of input format
    """
    try:
        with open(filename, 'r') as file:
            report_data = json.load(file)
        
        results = {}
        
        # Check if it's a Planemo report format
        if 'tests' in report_data and isinstance(report_data['tests'], list):
            for item in report_data['tests']:
                if 'data' in item and 'tool_id' in item['data']:
                    # Planemo format
                    tool_id = item['data']['tool_id']
                    outcome = item['data']['status'] == 'success'
                    results[tool_id] = {'outcome': outcome}
        
        # Check if it's a pytest-json format
        elif 'report' in report_data and 'tests' in report_data['report']:
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
        print(f"Error processing JSON file {filename}: {str(e)}")
        return {}

def push_results_to_prometheus(test_results):
    """
    Push test results to Prometheus gateway
    
    Args:
        test_results: Dictionary mapping tool_id/test_name to outcome information
    """
    pipeline_url = f"{os.environ.get('CI_PROJECT_URL')}/-/pipelines/{os.environ.get('CI_PIPELINE_ID')}"
    env = os.getenv('ENVIRONMENT', 'unknown')

    registry = CollectorRegistry()
    gauge_outcome = Gauge('galaxy_tool_tests', 'Galaxy tool tests outcome (pass/fail)',
                          ['tool_id', 'pipeline_url', 'env'], registry=registry)
    
    info_error = Info('galaxy_tool_test_errors', 'Galaxy tool test error messages',
                      ['tool_id', 'pipeline_url', 'env'], registry=registry)

    for tool_id, result_info in test_results.items():
        outcome = int(result_info['outcome'])
        gauge_outcome.labels(tool_id, pipeline_url, env).set(outcome)
        
        # Add error information if available
        if not outcome and 'error_message' in result_info:
            info_error.labels(tool_id, pipeline_url, env).info({
                'error_message': str(result_info['error_message'])[:1024]  # Limit length
            })

    prometheus_url = os.getenv('PROMETHEUS_URL')
    if not prometheus_url:
        print("PROMETHEUS_URL environment variable not set. Skipping metrics push.")
        return
        
    push_to_gateway(prometheus_url, job=f'galaxy_tools_tests_{env}', registry=registry)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python push_to_gateway.py <directory_or_file>")
        sys.exit(1)
        
    path = sys.argv[1]
    if os.path.isfile(path):
        test_results = collect_test_results(filename=path)
    else:
        test_results = collect_test_results(directory=path)
        
    if test_results:
        push_results_to_prometheus(test_results)
    else:
        print("No test results found.")
        sys.exit(1)
