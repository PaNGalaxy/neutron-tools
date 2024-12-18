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
    env = os.getenv('ENVIRONMENT', 'unknown')

    registry = CollectorRegistry()
    gauge_outcome = Gauge('planemo_tool_tests', 'Planemo tool tests outcome (pass/fail)',
                          ['tool_id', 'pipeline_url', 'env'], registry=registry)

    for tool_id, result_info in test_results.items():
        outcome = int(result_info['outcome'])
        gauge_outcome.labels(tool_id, pipeline_url, env).set(outcome)

    prometheus_url = os.getenv('PROMETHEUS_URL')
    push_to_gateway(prometheus_url, job=f'planemo_tests_{env}', registry=registry)


if __name__ == "__main__":
    directory = sys.argv[1]
    test_results ={}
    for root, _, files in os.walk(directory):
        for file in files:
            if fnmatch.fnmatch(file, "test_output_*.json"):
                test_results.update(collect_test_results(os.path.join(root, file)))
    push_results_to_prometheus(test_results)
