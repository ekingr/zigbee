#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
controller.py
Zigbee controller
Holding & caching system state, throtling interactions, managing interrupts & watchdog
'''

import asyncio
import logging
import time

from zigbee import State

# Minimum time between two SetState calls [seconds]
SETSTATE_MIN_PERIOD = 1.
# Periodic update of internal state with hardware [seconds]
UPDATE_PERIOD = 30.
# Watchdog: perdiod of inactivity (no connexion with gateway) after which to revert to a safe state [seconds]
WATCHDOG_PERIOD = 3*60*60 # 3h
WATCHDOG_SAFE_STATE = State.OFF
WATCHDOG_UNSAFE_STATES = [State.ON]


class ZBCtrl():
    '''Main controller for Zigbee, holding & caching system state'''

    def __init__(self, zbi, devices):
        '''Constructor: zbi ZBInterface object, devices list of known IDs (IEEE/EUI64)'''
        # Zigbee interface
        self.zbi = zbi
        # Internal state and its lock to R/W it
        self._state = {device: State.NA for device in devices}
        #self._state = {
        #        '70:ac:08:ff:fe:7e:0b:xx': State.OFF # IKEA of Sweden TRADFRI control outlet
        #}
        self.lock = asyncio.Lock()
        # Throttling: last change time and its lock to R/W it
        self.lastChange = time.time()
        self.lastChangeLock = asyncio.Lock()
        # Watchdog: last contact time and its lock to R/W it
        self.lastContact = time.time()
        self.lastContactLock = asyncio.Lock()
        # Periodic update & running state
        self.updateTask = None

    async def start(self):
        '''Start the controller, its timer and its dependencies (incl. ZBInterface)'''
        await self.zbi.start(self._stateChangeCallback)
        self.running = True
        self.updateTask = asyncio.create_task(self._periodicUpdate())
        #await self.updateTask

    async def stop(self):
        ''' Stop controller, its timer and its dependencies'''
        self.running = False
        self.updateTask.cancel()
        await self.zbi.stop()

    async def _stateChangeCallback(self, device, state):
        '''Handle state change event'''
        logging.info('Event: updating state: %s=%r' % (device, state))
        async with self.lock:
            devices = self._state.keys()
        if device in devices:
            async with self.lock:
                self._state[device] = state

    async def _periodicUpdate(self):
        '''Periodically update the internal state and let the watchdog out'''
        if self.running:
            logging.info('Running periodic update')
            # Internal state update
            logging.debug('  Updating internal state')
            async with self.lock:
                devices = self._state.keys()
            async def updateDeviceState(device):
                try:
                    newState = await self.zbi.getDeviceState(device)
                    async with self.lock:
                        self._state[device] = newState
                except Exception as e:
                    logging.error('Unable to get actual state for device %s: %r' % (device, e))
            await asyncio.gather(*[updateDeviceState(device) for device in devices])
            # Watchdog
            logging.debug('  Walking out the watchdog')
            async with self.lastContactLock:
                now = time.time()
                if now - self.lastContact > WATCHDOG_PERIOD:
                    logging.warning('    Watchdog: WOOF no news for too long, reverting to safe state')
                    async with self.lock:
                        unsafeDevices = [device for device in self._state if self._state[device] in WATCHDOG_UNSAFE_STATES]
                    async def setSafeDeviceState(device):
                        logging.info('    Reverting device %s to safe state: %s' % (device, WATCHDOG_SAFE_STATE))
                        try:
                            newState = await self.zbi.setDeviceState(device, WATCHDOG_SAFE_STATE)
                            async with self.lock:
                                self._state[device] = newState
                        except Exception as e:
                            logging.error('    Unable to revert device %s to safe state: %r' % (device, e))
                    await asyncio.gather(*[setSafeDeviceState(device) for device in unsafeDevices])
                    self.lastContact = time.time()
            logging.debug('  Periodic update completed. Waiting for %fs' % UPDATE_PERIOD)
            await asyncio.sleep(UPDATE_PERIOD)
            # Relaunching timer (rechecking if still running as it may have changed in between)
            if self.running:
                self.updateTask = asyncio.create_task(self._periodicUpdate())

    async def getState(self):
        # Reassuring watchdog
        async with self.lastContactLock:
            self.lastContact = time.time()
        # Returning state
        async with self.lock:
            return self._state.copy()

    async def setState(self, newState):
        # Reassuring watchdog
        async with self.lastContactLock:
            self.lastContact = time.time()
        # Throttling
        async with self.lastChangeLock:
            now = time.time()
            if now - self.lastChange < SETSTATE_MIN_PERIOD:
                logging.warning('Only %fs since last call, throttling!' % (now - self.lastChange))
                raise ValueError('Throttling: too many setState requests')
            self.lastChange = now
        # Applying changes
        stateChanges = {}
        async with self.lock:
            for device in self._state:
                if device in newState and self._state[device] != newState[device] and newState[device] in [State.ON, State.OFF]:
                    stateChanges[device] = newState[device]
        async def applyStateChange(device, newDeviceState):
            logging.info('Changing state: %s=%s' % (device, newDeviceState))
            actualNewDeviceState = await self.zbi.setDeviceState(device, newDeviceState)
            async with self.lock:
                self._state[device] = actualNewDeviceState
        await asyncio.gather(*[applyStateChange(device, stateChanges[device]) for device in stateChanges])


if __name__ == '__main__':
    from zigbee import ZBInterface
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s/%(funcName)s %(message)s', encoding='utf-8', level=logging.INFO)
    async def main():
        zbi = ZBInterface()
        devices = [
            '70:ac:08:ff:fe:7e:0b:xx', # IKEA of Sweden TRADFRI control outlet
        ]
        ctrl = ZBCtrl(zbi, devices)
        await ctrl.start()
        outlet = '70:ac:08:ff:fe:7e:0b:xx'
        logging.info(ctrl.getState())
        logging.info(await ctrl.setState({outlet: State.ON}))
        logging.info(ctrl.getState())
        await asyncio.sleep(15)
        logging.info(ctrl.getState())
        logging.info(await ctrl.setState({outlet: State.OFF}))
        await asyncio.sleep(15)
        logging.info(ctrl.getState())
        logging.info(await ctrl.setState({outlet: State.ON}))
        logging.info(ctrl.getState())
        await asyncio.sleep(15)
        logging.info(ctrl.getState())
        await ctrl.stop()
    asyncio.run(main())
