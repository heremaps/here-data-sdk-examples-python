# Copyright (C) 2020-2021 HERE Europe B.V.
# SPDX-License-Identifier: Apache-2.0

"""
This module provides data for the EV Charging Dashboard.
"""

from here.platform import Platform
from here.geopandas_adapter import GeoPandasAdapter
import here.geotiles.heretile as ht
from shapely.geometry import Point
from shapely.ops import nearest_points
import pandas as pd
import geopandas
import geojson


def empty_geojson():
    """
    Create Empty Geojson, used for cleaning the mao
    :return:
    """
    return geojson.FeatureCollection([])


def nearest_messages(ev_df, tf_df):
    """
    Find the nearest messages from the EV Charging Station

    :param ev_df:
    :param tf_df:
    :return:
    """

    def get_nearest_count(row, other_gdf, point_column='geometry', value_column="geometry"):
        # Create an union of the other GeoDataFrame's geometries:
        other_points = other_gdf["geometry"].unary_union
        # Find the nearest points
        nearest_geoms = nearest_points(row[point_column], other_points)
        # Get corresponding values from the other df
        nearest_data = other_gdf.loc[other_gdf["geometry"] == nearest_geoms[1]]
        return nearest_data.shape[0]

    name_list = []
    count_list = []
    location_list = []
    for index, row in ev_df.iterrows():
        name_list.append(row['name'])
        location_list.append(row['geometry'])
        count = get_nearest_count(row, tf_df, point_column='geometry', value_column="geometry")
        count_list.append(count)
    # create the dataframe
    df = pd.DataFrame(
        {'name': pd.Series(name_list),
         'geometry': pd.Series(location_list),
         'count': pd.Series(count_list),
         })
    return df


def get_partition_list(x1, y1, x2, y2):
    """
    Get list of partitions in a bounding box

    :param x1:
    :param y1:
    :param x2:
    :param y2:
    :return:
    """
    return list(ht.between_points(Point(x1, y1), Point(x2, y2), level=12, fully_contained=False))


class EVStation:
    """
    Extract the EV Charging Station Data

    """
    CATALOG_HRN = 'hrn:here:data::olp-here:rib-2'
    LAYER_ID = 'electric-vehicle-charging-stations'

    def __init__(self):
        self.platform = Platform()
        self.catalog = self.platform.get_catalog(EVStation.CATALOG_HRN)
        self.layer = self.catalog.get_layer(EVStation.LAYER_ID)
        self.data = None

    def _get_blobs(self, tile_ids):
        blobs = self.layer.read_partitions(tile_ids, decode=True)
        schema = self.layer.get_schema()
        parsed_blobs = []
        for p, blob in blobs:
            parsed_blobs.append(blob)
        return parsed_blobs

    def _get_data(self, tile_ids, x1, y1, x2, y2):
        location_ref_identifier = []
        place_name = []
        place_lang = []
        location_identifier = []
        location_display_position_latitude = []
        location_display_position_longitude = []
        days_of_week = []
        days_of_week_in_words = []
        match_level = []
        days_dict = {1: 'Sun', 2: 'Mon', 3: 'Tue', 4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat'}
        c1, c3 = 0, 0
        parsed_blobs = self._get_blobs(tile_ids)

        for blob in parsed_blobs:
            c1, c3 = 0, 0
            for item in getattr(blob, 'place'):
                location_ref_identifier.append(item.location_ref.identifier)
                place_name.append(item.name[0].text.value)
                place_lang.append(item.name[0].text.language)
                days_of_week.append([0])
                c1 += 1

            for item in getattr(blob, 'location'):
                location_identifier.append(item.identifier)
                location_display_position_latitude.append(item.display_position.latitude)
                location_display_position_longitude.append(item.display_position.longitude)

            days_of_week.extend([[-1]] * c1)
            days_of_week_in_words.extend('N' * c1)
            for item in getattr(blob, 'operating_time'):
                days = item.operating_time[0].days_of_week.day_of_week
                days_arr = [days_dict[d] for d in days]
                for i in item.place_index:
                    days_of_week[i] = days
                    days_of_week_in_words[i] = ','.join(days_arr)

        # create the dataframe
        df = pd.DataFrame(
            {'location_ref': pd.Series(location_ref_identifier),
             'name': pd.Series(place_name),
             'language': pd.Series(place_lang),
             'location_identifier': pd.Series(location_identifier),
             'latitude': pd.Series(location_display_position_latitude),
             'longitude': pd.Series(location_display_position_longitude),
             'days_of_week': pd.Series(days_of_week),
             'days_of_week_words': pd.Series(days_of_week_in_words)
             })
        ## Create geopanda from Panda
        geoPanda = geopandas.GeoDataFrame(
            df, geometry=geopandas.points_from_xy(df.longitude, df.latitude))
        ## filter the data in the bounding box
        filt_geoData = geoPanda.cx[x1:x2, y1:y2]
        return filt_geoData

    def get_geojson(self, tile_ids, x1, y1, x2, y2):
        """
        Get the data as geojson

        :param tile_ids:
        :param x1:
        :param y1:
        :param x2:
        :param y2:
        :return:
        """
        self.data = self._get_data(tile_ids, x1, y1, x2, y2)
        features = []
        insert_features = lambda X: features.append(
            geojson.Feature(geometry=geojson.Point((X["longitude"],
                                                    X["latitude"]
                                                    )),
                            properties=dict(name=X["name"],
                                            description=X["language"],
                                            days=X['days_of_week_words']
                                            )))
        self.data.apply(insert_features, axis=1)
        geo_json_layer = geojson.FeatureCollection(features)

        return geo_json_layer


class TrafficMessage:
    """
    Fetch Traffic Messages in a bounding box

    """
    CATALOG_HRN_TRAFFIC = 'hrn:here:data::olp-here:olp-traffic-1'
    CATALOG_HRN_RIB = 'hrn:here:data::olp-here:rib-2'
    LAYER_ID_TRAFFIC = 'traffic-flow'
    LAYER_ID_GEOMETRY = 'topology-geometry'
    TRAFFIC_FIELDS = ['topology_segment.topology_segment_id', 'topology_segment.start_offset',
                      'topology_segment.end_offset']
    GEO_FIELDS = ['segment_ref.identifier', 'geometry']
    GEO_VERSION_NO = 1831

    def __init__(self):
        self.platform = Platform(adapter=GeoPandasAdapter())
        self.catalog_traffic = self.platform.get_catalog(TrafficMessage.CATALOG_HRN_TRAFFIC)
        self.catalog_rib = self.platform.get_catalog(TrafficMessage.CATALOG_HRN_RIB)
        self.layer_traffic = self.catalog_traffic.get_layer(TrafficMessage.LAYER_ID_TRAFFIC)
        self.layer_geo = self.catalog_rib.get_layer(TrafficMessage.LAYER_ID_GEOMETRY)
        self.data = None

    def _get_data(self, tile_ids, x1, y1, x2, y2):
        traffic_df = self.layer_traffic.read_partitions(tile_ids,record_path="items", 
                                                        columns=TrafficMessage.TRAFFIC_FIELDS)
        traffic_df = traffic_df.explode("topology_segment.topology_segment_id")
        traffic_df.columns = ['partition_id','topology_segment_id', 'start_offset','end_offset']
        traffic_df['topology_segment_id'] = 'here:cm:segment:' + traffic_df['topology_segment_id'].astype(str)
        geo_df = self.layer_geo.read_partitions(tile_ids, record_path='node')
        geo_df_expl = geo_df[["partition_id", "segment_ref", "geometry.latitude", "geometry.longitude"]].explode("segment_ref")
        geo_df_expl['identifier'] = geo_df_expl['segment_ref'].apply(lambda x: x.get('identifier'))
        df_expl = geo_df_expl.drop(columns=['segment_ref'])
        geo_df_rib  = geopandas.GeoDataFrame(df_expl, geometry=geopandas.points_from_xy(df_expl['geometry.longitude'], 
                                          df_expl['geometry.latitude']))
        # merge these two data frames
        merged_df = traffic_df.merge(geo_df_rib, left_on=['partition_id',
                                                      'topology_segment_id'],
                                     how='inner', right_on=['partition_id', 'identifier'])
        # drop columns not required
        merged_df.drop(['partition_id', 'topology_segment_id', 'start_offset', 'end_offset'], axis=1, inplace=True)
        geo_tf = geopandas.GeoDataFrame(merged_df)
        filtered_df = geo_tf.cx[x1:x2, y1:y2]

        return filtered_df

    def get_geojson(self, tile_ids, x1, y1, x2, y2):
        features = []
        self.data = self._get_data(tile_ids, x1, y1, x2, y2)
        insert_features = lambda X: features.append(
            geojson.Feature(geometry=X['geometry'],
                            properties=dict(name=X["identifier"])))
        self.data.apply(insert_features, axis=1)

        return geojson.FeatureCollection(features)
