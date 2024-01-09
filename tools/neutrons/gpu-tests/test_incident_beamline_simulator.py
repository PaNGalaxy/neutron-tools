import os
import pytest
from bioblend import galaxy

@pytest.fixture(scope='session')
def galaxy_instance():
    galaxy_url = os.getenv("GALAXY_URL")
    galaxy_user_api_key = os.getenv("GALAXY_API_KEY")
    instance = galaxy.GalaxyInstance(url=galaxy_url, key=galaxy_user_api_key)
    return instance

@pytest.fixture(scope='session')
def history_id(galaxy_instance):
    new_history = galaxy_instance.histories.create_history(name='test_history')['id']
    yield new_history
    galaxy_instance.histories.delete_history(new_history, purge=True)

def test_incident_beamline_simulator(galaxy_instance, history_id):
    # Upload the input file
    uploaded_file = galaxy_instance.tools.upload_file('test-data/input_SNS_SEQ.txt', history_id)['outputs'][0]

    # Define the tool inputs
    tool_inputs = {
        'input_mode|manual_input': 'false',
        'input_mode|facility': 'SNS',
        'input_mode|instrument': 'SEQUOIA',
        'input': uploaded_file['id'],
        'n': '1e4',
        'nproc': '1',
        'gpu': 'true',
        'debug_output': 'false'
    }

    # Run the tool
    run_tool_response = galaxy_instance.tools.run_tool(history_id, 'neutrons_mcu_ibs', tool_inputs)

    # Retrieve and validate output
    output_dataset_id = run_tool_response['outputs'][0]['id']
    galaxy_instance.datasets.wait_for_dataset(output_dataset_id)
    output_dataset = galaxy_instance.datasets.show_dataset(output_dataset_id)

    # Here, perform your validations/assertions based on the expected output characteristics
    assert output_dataset['file_ext'] == 'gz', 'Output file format is incorrect'

# Additional tests can be written to cover different parameters and edge cases.
