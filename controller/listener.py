#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
listener.py
Zigbee interface base listener
Base class for event listener
'''

import datetime
import logging
from typing import Any

import zigpy.group # Group
import zigpy. endpoint # Endpoint
import zigpy.device # Device
import zigpy.backups # NetworkBackup
import zigpy.types # Relays, EUI64, uint8_t, uint16_t
import zigpy.zdo.types # Neighbor, Route
import zigpy.zcl.foundation # ZCLHeader


class ZBListenerBase:
    '''Listener of the ControllerApplication, to capture events.
    Events are triggered by `listener_event(method_name: str, *args)`
    and captured by the eponymous methods.
    The folling list has been created by searching through zigpy source code'''

    # zigpy/group.py
    def member_added(self, group: zigpy.group.Group, endpoint: zigpy.endpoint.Endpoint):
        logging.debug('>member_added:', group, endpoint)
    def member_removed(self, group: zigpy.group.Group, endpoint: zigpy.endpoint.Endpoint):
        logging.debug('>member_removed:', group, endpoint)
    def group_added(self, group: zigpy.group.Group):
        logging.debug('>group_added:', group)
    def group_removed(self, group: zigpy.group.Group):
        logging.debug('>group_removed:', group)
    def group_member_added(self, group: zigpy.group.Group, endpoint: zigpy.endpoint.Endpoint):
        logging.debug('>group_member_added:', group, endpoint)
    def group_member_removed(self, group: zigpy.group.Group, endpoint: zigpy.endpoint.Endpoint):
        logging.debug('>group_member_removed:', group, endpoint)
    # zigpy/device.py
    def device_last_seen_updated(self, value: datetime.datetime | int | float):
        logging.debug('>device_last_seen_updated:', value)
    def device_init_failure(self, device: zigpy.device.Device):
        logging.debug('>device_init_failure:', device)
    def device_relays_updated(self, relays: zigpy.types.Relays):
        logging.debug('>device_relays_updated:', relays)
    # zigpy/application.py
    def raw_device_initialized(self, device: zigpy.device.Device):
        logging.debug('>raw_device_initialized:', device)
    def device_initialized(self, device: zigpy.device.Device):
        logging.debug('>device_initialized:', device)
    def device_removed(self, device: zigpy.device.Device):
        logging.debug('>device_removed:', device)
    def device_joined(self, device: zigpy.device.Device):
        logging.debug('>device_joined:', device)
    def device_left(self, device: zigpy.device.Device):
        logging.debug('>device_left:', device)
    # zigpy/endpoint.py
    def unknown_cluster_message(self, cmdId: zigpy.types.uint8_t, args: list[Any]):
        logging.debug('>unknown_cluster_message:', cmdId, args)
    # zigpy/topology.py
    def neighbors_updated(self, ieee: zigpy.types.EUI64, neighbors: list[zigpy.zdo.types.Neighbor]):
        logging.debug('>neighbors_updated:', ieee, neighbors)
    def routes_updated(self, ieee: zigpy.types.EUI64, routes: list[zigpy.zdo.types.Route]):
        logging.debug('>routes_updated:', ieee, routes)
    # zigpy/backups.py
    def network_backup_removed(self, backup: zigpy.backups.NetworkBackup):
        logging.debug('>network_backup_removed:', backup)
    def network_backup_created(self, backup: zigpy.backups.NetworkBackup):
        logging.debug('>network_backup_created:', backup)
    # zigpy/zdo/__init__.py
    # zdo_{hdr.command_id.name.lower()}
    def device_announce(self, device: zigpy.device.Device):
        logging.debug('>device_announce:', device)
    def permit_duration(self, duration: int):
        logging.debug('>permit_duration:', duration)
    # zigpy/zcl/__init__.py
    def cluster_command(self, tsn: zigpy.types.uint8_t, cmdId: zigpy.types.uint8_t, args: list[Any]):
        logging.debug('>cluster_command:', tsn, cmdId, args)
    def general_command(self, hdr: zigpy.zcl.foundation.ZCLHeader, args: list[Any]):
        logging.debug('>general_command:', hdr, args)
    def attribute_updated(self, attrId: int | zigpy.types.uint16_t, value: Any, now: datetime.datetime):
        logging.debug('>attribute_updated:', attrId, value, now)
    def unsupported_attribute_added(self, attr: int):
        logging.debug('>unsupported_attribute_added:', int)
    def unsupported_attribute_removed(self, attr: int):
        logging.debug('>unsupported_attribute_removed:', int)

    # Generic handler:
    def handle_message(self, device: zigpy.device.Device, profile: int, cluster: int, src_ep: int, dst_ep: int, message: bytes):
        logging.debug(f'>handle_message {device.ieee} profile:{profile} cluster:{cluster} src_ep:{src_ep} dst_ep:{dst_ep} message:{message}')


