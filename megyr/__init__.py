import argparse
import json
import os.path
import sys

import pandas as pd

from . import gyre
from . import mesa
from . import oscillations_summary
from . import parameters
from . import util

def run(config):
    validate_config(config)

    work_dir = "."
    output_dir = os.path.join(work_dir, config["output"]["output_dir"])

    util.create_dir(output_dir)

    mesa_params = config["stages"]["mesa_params"]
    mesa_grid = parameters.create_grid({}, [], mesa_params)

    for mesa_comb in mesa_grid:
        print("MESA: " + str(mesa_comb))

        util.set_num_mp_threads(config["settings"]["mesa_mp_threads"])

        mesa_dir_name, logs_dir_name = mesa.run_mesa(config, mesa_comb, work_dir, output_dir)

        mesa_data = load_or_collect_mesa_data(config, output_dir, mesa_dir_name, logs_dir_name)

        # TODO: Add preivously calculated mesa values to "values"

        if should_run_gyre(config):
            gyre_params = config["stages"]["gyre_params"](mesa_params, mesa_data)

            gyre_grid = parameters.create_grid({}, mesa_data, gyre_params)

            util.set_num_mp_threads(config["settings"]["gyre_mp_threads"])

            oscillations = pd.DataFrame()
            for gyre_comb in gyre_grid:
                print("GYRE: " + str(gyre_comb))
                ad_output_summary_file = gyre.run_gyre(config, mesa_comb, mesa_data, gyre_comb, work_dir, output_dir, mesa_dir_name, logs_dir_name)

                summary = oscillations_summary.read_oscillations_summary_file(ad_output_summary_file).data

                for key in gyre_comb:
                    v = gyre_comb[key]

                    summary[key] = v

                oscillations = pd.concat([oscillations, summary])

            oscillations_file = os.path.join(output_dir, mesa_dir_name, config["output"]["gyre_oscillations_summary_file"])
            oscillations.to_csv(oscillations_file, index=False)

def validate_config(config):
    pass

def should_run_gyre(config):
    return "gyre_config" in config["input"]

def load_or_collect_mesa_data(config, output_dir, mesa_dir_name, logs_dir_name):
    filename = config["output"]["mesa_profile_summary_file"]
    profiles_summary_file = os.path.join(output_dir, mesa_dir_name, filename)
    if os.path.isfile(profiles_summary_file):
        rows = pd.read_csv(profiles_summary_file)
    else:
        rows = mesa.get_mesa_data(config, output_dir, mesa_dir_name, logs_dir_name)

        rows.to_csv(profiles_summary_file, index=False)

    return rows
