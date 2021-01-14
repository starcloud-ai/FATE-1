#
#  Copyright 2019 The FATE Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import argparse
import json

from pipeline.backend.pipeline import PipeLine
from pipeline.component.dataio import DataIO
from pipeline.component.hetero_feature_selection import HeteroFeatureSelection
from pipeline.component.homo_feature_binning import HomoFeatureBinning
from pipeline.component.reader import Reader
from pipeline.interface.data import Data
from pipeline.runtime.entity import JobParameters
from pipeline.utils.tools import load_job_config


def main(config="../../config.yaml", namespace=""):
    # obtain config
    if isinstance(config, str):
        config = load_job_config(config)
    parties = config.parties
    guest = parties.guest[0]
    host = parties.host
    host = [10000, 10001, 10002]
    arbiter = parties.arbiter[0]
    backend = config.backend
    work_mode = config.work_mode

    guest_train_data = {"name": "default_credit_guest", "namespace": f"experiment{namespace}"}
    host_train_data_0 = {"name": "default_credit_host1", "namespace": f"experiment{namespace}"}
    host_train_data_1 = {"name": "default_credit_host2", "namespace": f"experiment{namespace}"}
    host_train_data_2 = {"name": "default_credit_test", "namespace": f"experiment{namespace}"}

    # initialize pipeline
    pipeline = PipeLine()
    # set job initiator
    pipeline.set_initiator(role='guest', party_id=guest)
    # set participants information
    pipeline.set_roles(guest=guest, host=host, arbiter=arbiter)

    # define Reader components to read in data
    reader_0 = Reader(name="reader_0")
    # configure Reader for guest
    reader_0.get_party_instance(role='guest', party_id=guest).component_param(table=guest_train_data)
    # configure Reader for host
    reader_0.get_party_instance(role='host', party_id=host[0]).component_param(table=host_train_data_0)
    reader_0.get_party_instance(role='host', party_id=host[1]).component_param(table=host_train_data_1)
    reader_0.get_party_instance(role='host', party_id=host[2]).component_param(table=host_train_data_2)

    # define DataIO components
    dataio_0 = DataIO(name="dataio_0", with_label=True, output_format="dense")  # start component numbering at 0

    selection_param = {
        "filter_methods": [
            "manually"
        ],
        "manually_param": {
            "left_col_indexes": [1]
        }}
    selection_0 = HeteroFeatureSelection(name='selection_0', **selection_param)
    homo_binning_0 = HomoFeatureBinning(name='homo_binning_0', method="recursive_query", error=0.0)

    # add components to pipeline, in order of task execution
    pipeline.add_component(reader_0)
    pipeline.add_component(dataio_0, data=Data(data=reader_0.output.data))
    pipeline.add_component(selection_0, data=Data(data=dataio_0.output.data))
    # set data input sources of intersection components
    pipeline.add_component(homo_binning_0, data=Data(data=selection_0.output.data))
    # pipeline.add_component(homo_binning_0, data=Data(data=dataio_0.output.data))

    # compile pipeline once finished adding modules, this step will form conf and dsl files for running job
    pipeline.compile()

    # fit model
    job_parameters = JobParameters(backend=backend, work_mode=work_mode)
    pipeline.fit(job_parameters)
    # query component summary
    print(json.dumps(pipeline.get_component("homo_binning_0").get_summary(), indent=4, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("PIPELINE DEMO")
    parser.add_argument("-config", type=str,
                        help="config file")
    args = parser.parse_args()
    if args.config is not None:
        main(args.config)
    else:
        main()