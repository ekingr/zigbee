#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
zigbee.py
Zigbee interface
Communicating withe the Zigbee network and managing its coordinator
'''

import asyncio
from enum import IntEnum
import logging

#import zigpy
import zigpy.device # Device
import zigpy.config # various constants
import zigpy.types # MACStatus, named.EUI64
import zigpy.exceptions # DeliveryError
import zigpy.profiles # ZHA profile
import zigpy.zcl.foundation # Status, GeneralCommand, TypeValue
from zigpy_znp.zigbee.application import ControllerApplication

from listener import ZBListenerBase


class ZBListener(ZBListenerBase):
    '''Listener of the ControllerApplication to capture events'''

    def __init__(self, callbalckOnOff):
        self.callbalckOnOff = callbalckOnOff

    def handleAttrReport(self, device, cluster, attribute, value):
        '''Handle `Report_Attributes` (ie. state changes)'''
        logging.info('>>> state change of %s: %s.%s = %s' % (device.ieee, cluster.name, attribute.name, value.name))
        if cluster.cluster_id == DEVICE_ONOFF_CLUSTER and attribute.name == DEVICE_ONOFF_ATTR:
            asyncio.create_task(self.callbalckOnOff(str(device.ieee), State.ON if value else State.OFF))


    def handle_message(self, device, profile, cluster, src_ep, dst_ep, message):
        '''Generic message handling'''
        # Log
        super().handle_message(device, profile, cluster, src_ep, dst_ep, message)
        try:
            if not profile == zigpy.profiles.zha.PROFILE_ID:
                #logging.warning('profile not OK')
                return
            if not src_ep in device.endpoints:
                #logging.warning('src_ep not OK')
                return
            endpoint = device.endpoints[src_ep]
            if not cluster in endpoint.in_clusters:
                #logging.warning('cluster not OK')
                return
            cluster = endpoint.in_clusters[cluster]
            msg = cluster.deserialize(message)
            if not msg[0].frame_control.is_general:
                #logging.warning('frame is not general')
                return
            if not msg[0].command_id == zigpy.zcl.foundation.GeneralCommand.Report_Attributes:
                #logging.warning('command not Report_Attributes')
                return
            for attReport in msg[1].attribute_reports:
                if not attReport.attrid in cluster.attributes:
                    #logging.warning('attribute not OK')
                    continue
                attribute = cluster.attributes[attReport.attrid]
                value = attReport.value
                if type(value) == zigpy.zcl.foundation.TypeValue:
                    value = value.value
                self.handleAttrReport(device, cluster, attribute, value)
        except Exception as e:
            logging.warning(e)
            return
        


DEVICE_INFO_ENDPOINT = 1
DEVICE_INFO_CLUSTER = 0 # zigpy.zcl.clusters.general.Basic.cluster_id
DEVICE_INFO_ATTRIBUTES = [
#   'zcl_version',                  # zigpy.zcl.clusters.general.Basic.attributes[0]
#   'app_version',                  # zigpy.zcl.clusters.general.Basic.attributes[1]
#   'stack_version',                # zigpy.zcl.clusters.general.Basic.attributes[2]
#   'hw_version',                   # zigpy.zcl.clusters.general.Basic.attributes[3]
    'manufacturer',                 # zigpy.zcl.clusters.general.Basic.attributes[4]
    'model',                        # zigpy.zcl.clusters.general.Basic.attributes[5]
#   'date_code',                    # zigpy.zcl.clusters.general.Basic.attributes[6]
    'power_source',                 # zigpy.zcl.clusters.general.Basic.attributes[7]
    'generic_device_class',         # zigpy.zcl.clusters.general.Basic.attributes[8]
    'generic_device_type',          # zigpy.zcl.clusters.general.Basic.attributes[9]
    'product_code',                 # zigpy.zcl.clusters.general.Basic.attributes[10]
    'product_url',                  # zigpy.zcl.clusters.general.Basic.attributes[11]
    'manufacturer_version_details', # zigpy.zcl.clusters.general.Basic.attributes[12]
    'serial_number',                # zigpy.zcl.clusters.general.Basic.attributes[13]
    'product_label',                # zigpy.zcl.clusters.general.Basic.attributes[14]
    'location_desc',                # zigpy.zcl.clusters.general.Basic.attributes[16]
#   'physical_env',                 # zigpy.zcl.clusters.general.Basic.attributes[17]
#   'device_enabled',               # zigpy.zcl.clusters.general.Basic.attributes[18]
#   'alarm_mask',                   # zigpy.zcl.clusters.general.Basic.attributes[19]
#   'disable_local_config',         # zigpy.zcl.clusters.general.Basic.attributes[20]
#   'sw_build_id',                  # zigpy.zcl.clusters.general.Basic.attributes[16384]
#   'cluster_revision',             # zigpy.zcl.clusters.general.Basic.attributes[65533]
#   'reporting_status',             # zigpy.zcl.clusters.general.Basic.attributes[65534]
]
DEVICE_ONOFF_ENDPOINT = 1
DEVICE_ONOFF_CLUSTER = 6 # zigpy.zcl.clusters.general.OnOff.cluster_id
DEVICE_ONOFF_ATTRIBUTES = [
    'on_off',               # zigpy.zcl.clusters.general.OnOff.attributes[0]
    'global_scene_control', # zigpy.zcl.clusters.general.OnOff.attributes[16384]
    'on_time',              # zigpy.zcl.clusters.general.OnOff.attributes[16385]
    'off_wait_time',        # zigpy.zcl.clusters.general.OnOff.attributes[16386]
    'start_up_on_off',      # zigpy.zcl.clusters.general.OnOff.attributes[16387]
    'cluster_revision',     # zigpy.zcl.clusters.general.OnOff.attributes[65533]
#   'reporting_status',     # zigpy.zcl.clusters.general.OnOff.attributes[65534]
]
DEVICE_ONOFF_ATTR = 'on_off' # zigpy.zcl.clusters.general.OnOff.attributes[0].name


class State(IntEnum):
    '''State of an on/off device'''
    OFF = 0 # Switched off
    ON = 1 # Switched on
    NA = -1 # Device not powered on / accessible


class ZBInterface():
    '''Interface allowing to communicate with Zigbee network devices'''

    def __init__(self, zpDbPath='zigpy.db', adapterPath='/dev/ttyUSB0', zbChannel=20):
        self.zpConfig = {
            zigpy.config.CONF_DEVICE: {
                zigpy.config.CONF_DEVICE_PATH: adapterPath,
            },
            zigpy.config.CONF_DATABASE: zpDbPath,
            zigpy.config.CONF_NWK_CHANNEL: zbChannel,
        }
        self.za = None
        self.listener = None

    async def start(self, updateCallback):
        '''Start zigpy'''
        logging.info('Starting Zigpy...')
        self.za = await ControllerApplication.new(
            config=ControllerApplication.SCHEMA(self.zpConfig),
            auto_form=True,
            start_radio=True,
        )
        self.listener = ZBListener(updateCallback)
        self.za.add_listener(self.listener)
        self.za.groups.add_listener(self.listener)
        logging.info('Zigpy started')

    async def stop(self):
        '''Stop zigpy'''
        logging.info('Shutting down Zigpy...')
        if self.za:
            await self.za.shutdown()
            logging.info('Zigpy stopped')

    def _getDevice(self, deviceId):
        '''Check that device is of the right type, and return relevant zigpy objects: (device, infoCluster, onoffCluster)'''
        dId = zigpy.types.named.EUI64.convert(deviceId)
        if dId not in self.za.devices:
            raise ValueError('Unknown device ID')
        device = self.za.devices[dId]
        # Info cluster
        if DEVICE_INFO_ENDPOINT not in device.endpoints:
            raise ValueError('Endpoint #%d not available, make sure device is of the right type' % DEVICE_INFO_ENDPOINT)
        if DEVICE_INFO_CLUSTER not in device.endpoints[DEVICE_INFO_ENDPOINT].in_clusters:
            raise ValueError('Cluster #%d not available, make sure device is of the right type' % DEVICE_INFO_CLUSTER)
        infoCluster = device.endpoints[DEVICE_INFO_ENDPOINT].in_clusters[DEVICE_INFO_CLUSTER]
        # OnOffCluster
        if DEVICE_ONOFF_ENDPOINT not in device.endpoints:
            raise ValueError('Endpoint #%d not available, make sure device is of the right type' % DEVICE_ONOFF_ENDPOINT)
        if DEVICE_ONOFF_CLUSTER not in device.endpoints[DEVICE_ONOFF_ENDPOINT].in_clusters:
            raise ValueError('Cluster #%d not available, make sure device is of the right type' % DEVICE_ONOFF_CLUSTER)
        onoffCluster = device.endpoints[DEVICE_ONOFF_ENDPOINT].in_clusters[DEVICE_ONOFF_CLUSTER]
        return device, infoCluster, onoffCluster
    
    async def getAllDeviceInfo(self, deviceId):
        '''Return all the info about the device and its state'''
        device, infoCluster, onoffCluster = self._getDevice(deviceId)
        attrInfoOk, attrInfoKo = await infoCluster.read_attributes(DEVICE_INFO_ATTRIBUTES)
        attrOnoffOk, attrOnoffKo = await onoffCluster.read_attributes(DEVICE_ONOFF_ATTRIBUTES)
        return (attrInfoOk | attrOnoffOk, attrInfoKo | attrOnoffKo)

    async def getDeviceState(self, deviceId):
        '''Querry device state (deviceId = EUI64 string)'''
        logging.debug('Getting state of device %s' % deviceId)
        _, _, onoffCluster = self._getDevice(deviceId)
        logging.debug('  Requesting device state: %s' % deviceId)
        try:
            rOk, rKo = await onoffCluster.read_attributes([DEVICE_ONOFF_ATTR])
        except zigpy.exceptions.DeliveryError as e:
            if e.status == zigpy.types.MACStatus.MAC_NO_ACK:
                logging.debug('  Unable to reach device: %r' % e)
                return State.NA
            else:
                raise e
        logging.debug('  Got state ok=%s, ko=%s' % (rOk, rKo))
        if DEVICE_ONOFF_ATTR not in rOk:
            logging.debug('Unable to get on/off value: %r' % rKo)
            return State.NA
        return State.ON if rOk[DEVICE_ONOFF_ATTR] else State.OFF

    async def setDeviceState(self, deviceId, newState):
        '''Send command to set device state'''
        logging.info('Setting state of %s to %s' % (deviceId, newState))
        _, _, onoffCluster = self._getDevice(deviceId)
        if newState not in [State.ON, State.OFF]:
            logging.warning('  Invalid newState %r' % newState)
            raise ValueError('Invalid newState, should be State.ON or State.OFF')
        cmd = 1 if newState == State.ON else 0
        # cmd=2 would be to toggle state, not needed here
        logging.debug('  Sending command: %s < %s' % (deviceId, cmd))
        try:
            res = await onoffCluster.command(cmd)
        except zigpy.exceptions.DeliveryError as e:
            if e.status == zigpy.types.MACStatus.MAC_NO_ACK:
                logging.info('  Unable to reach device: %r' % e)
                return State.NA
            else:
                raise e
        if res.status != zigpy.zcl.foundation.Status.SUCCESS:
            logging.warning('  Error setting state: %r', res)
            return State.NA
        return newState

    async def allowPair(self, duration=60):
        '''CLI: Sets the controller in state to allow devices pairing'''
        return await self.za.permit(duration)

    def listDevices(self):
        '''CLI: List knonw devices'''
        return self.za.devices.values()

    def detailDevice(self, deviceId):
        '''CLI: Detail all known info about a device'''
        dId = zigpy.types.named.EUI64.convert(deviceId)
        if dId not in self.za.devices:
            raise ValueError('Unknown device ID')
        device = self.za.devices[dId]
        print('  DEVICE: ieee = %s' % device.ieee)
        print('          nwk = %s' % device.nwk)
        print('          manufacturer = %s' % device.manufacturer)
        print('          model = %s' % device.model)
        print('          is initialised = %s' % device.is_initialized)
        for ep in sorted(device.endpoints.keys()):
            endpoint = device.endpoints[ep]
            if not type(endpoint) == zigpy.endpoint.Endpoint:
                continue
            print('  Endpoint #%d (status: %s)' % (ep, endpoint.status))
            print('  INPUT clusters:')
            for cl in sorted(endpoint.in_clusters.keys()):
                cluster = endpoint.in_clusters[cl]
                print('    % 4d %s %s' % (cl, cluster.name, type(cluster)))
                for c in sorted(cluster.server_commands.keys()):
                    cmd = cluster.server_commands[c]
                    print('      % 6d %s' % (c, cmd.name))
            print('  OUTPUT clusters:')
            for cl in sorted(endpoint.out_clusters.keys()):
                cluster = endpoint.out_clusters[cl]
                print('    % 4d %s %s' % (cl, cluster.name, type(cluster)))
                for c in sorted(cluster.server_commands.keys()):
                    cmd = cluster.server_commands[c]
                    print('      % 6d %s' % (c, cmd.name))



if __name__ =="__main__":
    import time
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s/%(funcName)s %(message)s', encoding='utf-8', level=logging.INFO)
    ZP_DB_PATH = 'zigpy.db'
    ADAPTER_PATH = '/dev/ttyUSB0'
    ZB_CHANNEL = 20
    async def main():
        zbi = ZBInterface(ZP_DB_PATH, ADAPTER_PATH, ZB_CHANNEL)
        await zbi.start(lambda device, state: logging.info('State change: %s=%r' % (device, state)))
        while True:
            print('''
Commands:
  LIST: list known devices
  INFO ID: detail all relevant information about device #ID
  STATUS ID: show status of device #ID
  SET ID STATUS: set status of device #ID to STATUS
  PAIR: allow pairing for 60s
  EXIT: exit program''')
            i = input('command> ')
            cmds = i.upper().split()
            cmd = cmds[0] if cmds else ''
            if cmd == 'EXIT':
                print('Exiting, bye!')
                break
            elif cmd == 'LIST':
                print('Listing known devices:')
                for d in zbi.listDevices():
                    print('  %s %s %s %s %s' % (d.ieee, d.nwk, d.manufacturer, d.model, d.is_initialized))
            elif cmd == 'INFO':
                if len(cmds) != 2 or not cmds[1]:
                    print('Invalid command, please provide ID (ieee format).')
                    continue
                print('Detailing information about device %s:' % cmds[1])
                try:
                    zbi.detailDevice(cmds[1])
                except Exception as e:
                    print(e)
                    continue
                print('Requesting status info from device %s:' % cmds[1])
                try:
                    ok, ko = await zbi.getAllDeviceInfo(cmds[1])
                    print('  OK: Properties with usable values:')
                    for key, value in ok.items():
                        print('  - %s = %s' % (key, value))
                    print('  KO: Properties with unusable values:')
                    for key, value in ko.items():
                        print('  - %s = %s' % (key, value))
                except Exception as e:
                    print(e)
                    continue
            elif cmd == 'STATUS':
                if len(cmds) != 2 or not cmds[1]:
                    print('Invalid command, please provide ID (ieee format).')
                    continue
                print('Fetching status of device %s:' % cmds[1])
                try:
                    print(await zbi.getDeviceState(cmds[1]))
                except Exception as e:
                    print(e)
                    continue
            elif cmd == 'SET':
                if len(cmds) != 3 or not cmds[1] or not cmds[2]:
                    print('Invalid command, please provide ID (ieee format).')
                    continue
                status = cmds[2]
                if status in ['1', '0']:
                    status = int(status)
                elif status.upper() in ['ON']:
                    status = State.ON
                elif status.upper() in ['OFF']:
                    status = State.OFF
                else:
                    print('Invalid STATUS, must be 1 or 0')
                    continue
                print('Requesting status of device %s to be set to %s' % (cmds[1], cmds[2]))
                try:
                    print(await zbi.setDeviceState(cmds[1], status))
                except Exception as e:
                    print(e)
                    continue
            elif cmd == 'PAIR':
                print('Allowing pairing for 60s')
                await zbi.allowPair(60)
                await asyncio.sleep(60)
                print('Disabling pairing')
            else:
                print('Unknown command')
        await zbi.stop()
    asyncio.run(main())
