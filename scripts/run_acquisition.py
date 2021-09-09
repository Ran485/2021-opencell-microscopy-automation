import os
import re
import sys
import glob
import json
import time
import shutil
import datetime
import tifffile
import argparse
import numpy as np
import pandas as pd

HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.join(HERE, os.pardir)

sys.path.insert(0, PROJECT_ROOT)
from dragonfly_automation.acquisitions.pipeline_plate_acquisition import PipelinePlateAcquisition
from dragonfly_automation.fov_models import PipelineFOVScorer


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--data-dirpath',
        dest='data_dirpath',
        type=str,
        required=False,
        default=os.path.join('D:', 'PipelineML', 'data')
    )

    parser.add_argument('--pml-id', dest='pml_id', type=str, required=True)
    parser.add_argument('--plate-id', dest='plate_id', type=str, required=True)
    parser.add_argument('--platemap-type', dest='platemap_type', type=str, required=True)

    # run mode: 'test' or 'prod'
    parser.add_argument('--mode', dest='mode', type=str, default='prod', required=False)

    # optional well to visit when mode is 'test'
    parser.add_argument('--test-well', dest='test_well', type=str, default=None, required=False)

    # time delay, in minutes, to add before starting the acquisition
    parser.add_argument('--delay', dest='delay', type=int, default=None, required=False)

   # mode for the mocked API ('overexposure' or 'underexposre')
    parser.add_argument('--mocked-mode', type=str, default=None, required=False)

    # CLI args whose presence in the command sets them to True
    action_arg_names = ['acquire_brightfield_stacks', 'skip_fov_scoring', 'mock_micromanager_api']

    for arg_name in action_arg_names:
        parser.add_argument(
            '--%s' % arg_name.replace('_', '-'), 
            dest=arg_name,
            action='store_true',
            required=False
        )

    for arg_name in action_arg_names:
        parser.set_defaults(**{arg_name: False})
    
    args = parser.parse_args()
    return args


def main():

    args = parse_args()

    pml_id = args.pml_id
    if args.mode == 'test':
        pml_id = '%s-test' % pml_id    
    acquisition_dirpath_base = os.path.join(args.data_dirpath, pml_id)

    # create a new directory for the acquisition
    acquisition_dirpath = None
    attempt_count = 0
    while acquisition_dirpath is None or os.path.isdir(acquisition_dirpath):
        attempt_count += 1
        acquisition_dirpath = '%s-%s' % (acquisition_dirpath_base, attempt_count)
    
    # load the FOV scoring model
    fov_scorer = PipelineFOVScorer(
        save_dir=os.path.join(PROJECT_ROOT, 'models', '2019-10-08'),
        mode='prediction',
        model_type='regression',
        random_state=(42 if args.mock_micromanager_api else None)
    )
    fov_scorer.load()
    fov_scorer.train()
    fov_scorer.validate()

    acquisition = PipelinePlateAcquisition(
        root_dir=acquisition_dirpath, 
        pml_id=args.pml_id,
        plate_id=args.plate_id,
        platemap_type=args.platemap_type,
        mock_micromanager_api=args.mock_micromanager_api,
        mocked_mode=args.mocked_mode,
        fov_scorer=fov_scorer,
        skip_fov_scoring=args.skip_fov_scoring,
        acquire_brightfield_stacks=args.acquire_brightfield_stacks,
    )
    acquisition.setup()

    if args.delay is not None:
        print('Delaying acquisition by %d minutes' % args.delay)
        time.sleep(args.delay*60)

    acquisition.run(mode=args.mode, test_mode_well_id=args.test_well)


if __name__ == '__main__':
    main()
