# Copyright (C) 2020-2021 HERE Europe B.V.
# SPDX-License-Identifier: Apache-2.0

"""
This is an utility module for sample notebooks.
"""

from typing import Optional

from here.platform import Platform

def multi_run_wrapper(args):
    return get_blob_(*args)


def get_blob_(partition_id, catalog_hrn, layer_id, version: Optional[int] = None):
    platform = Platform()
    cat = platform.get_catalog(catalog_hrn)
    layer = cat.get_layer(layer_id)
    # print(f"Partition id: {partition_id} Version: {version}")
    blob = next(layer.read_partitions(partition_ids=[partition_id], version = version))
    return blob
