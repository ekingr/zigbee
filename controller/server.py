#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
server.py
gRPC server
Offering API to interact with the Zigbee controller
'''

import asyncio
from concurrent import futures
import json
import logging

import grpc

from zbCtrl_pb2 import GetStateResponse, SetStateResponse
from zbCtrl_pb2_grpc import ZBCtrlServicer, add_ZBCtrlServicer_to_server
import zbCtrl_pb2_grpc


class ZBCtrlSrv(ZBCtrlServicer):
    '''gRPC server handling get/set requests to the contoller'''

    def __init__(self, ctrl, apikey):
        super().__init__()
        self.ctrl = ctrl
        self.apikey = apikey

    def _authReq(self, req):
        '''Autenticates a request with an API key'''
        return req.key == self.apikey
    
    async def GetState(self, req, ctx):
        logging.debug('Request recieved...')
        if not self._authReq(req):
            logging.warning('  Invalid API key')
            return await ctx.abort(grpc.StatusCode.UNAUTHENTICATED, 'Invalid API key')
        state = await self.ctrl.getState()
        res = GetStateResponse(state=json.dumps(state))
        logging.debug('Response sent.')
        return res

    async def SetState(self, req, ctx):
        logging.debug('Request recieved...')
        if not self._authReq(req):
            logging.warning('  Invalid API key')
            return await ctx.abort(grpc.StatusCode.UNAUTHENTICATED, 'Invalid API key')
        try:
            newState = json.loads(req.state)
        except Exception as e:
            logging.error('  Error parsing JSON: %r' % e)
            return await ctx.abort(grpc.StatusCode.INVALID_ARGUMENT, 'Unable to parse state as JSON')
        try:
            await self.ctrl.setState(newState)
            res = SetStateResponse(success=True)
            logging.debug('Response sent.')
            return res
        except Exception as e:
            logging.error('  Error setting new state: %r' % e)
            return await ctx.abort(grpc.StatusCode.INTERNAL, 'Error while setting new state')


if __name__ == '__main__':
    import os
    def getCfg(env, helpmsg=''):
        cfg = os.getenv(env)
        if not cfg:
            raise RuntimeError('Error: missing %s env config%s' % (env, helpmsg))
        return cfg

    SRV_PORT = getCfg('ZBCTRLADDR', ', eg. localhost:xxx')
    SSL_CERT = getCfg('ZBCTRLCERT', ', eg. ./fullchain.pem')
    SSL_KEY = getCfg('ZBCTRLCERTKEY', ', eg. ./key.pem')
    API_KEY = getCfg('ZBCTRLAPIKEY')
    ZB_DB = getCfg('ZBCTRLDB', ', eg. ./zigpy.db')
    ZB_ADAPTER = getCfg('ZBCTRLADAPTER', ', eg. /dev/ttyUSB0')

    DEVICES = [
        '70:ac:08:ff:fe:7e:0b:xx', # 0x7A3D IKEA of Sweden TRADFRI control outlet
        '34:25:b4:ff:fe:bd:7c:yy', # 0x2488 IKEA of Sweden TRADFRI control outlet
        'f4:b3:b1:ff:fe:9b:26:zz', # 0x1F17 IKEA of Sweden TRADFRIbulbG125E27WSopal470lm
    ]

    from zigbee import ZBInterface
    from controller import ZBCtrl
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s/%(funcName)s %(message)s', encoding='utf-8', level=logging.INFO)
    with open(SSL_CERT, 'rb') as f:
        sslCert = f.read()
    with open(SSL_KEY, 'rb') as f:
        sslKey = f.read()

    _cleanup = None

    async def main():
        logging.info('Starting up!')
        server = grpc.aio.server()
        creds = grpc.ssl_server_credentials(((sslKey, sslCert),))

        zbi = ZBInterface(zpDbPath=ZB_DB, adapterPath=ZB_ADAPTER)
        ctrl = ZBCtrl(zbi, DEVICES)
        srv = ZBCtrlSrv(ctrl, API_KEY)
        await ctrl.start()
        add_ZBCtrlServicer_to_server(srv, server)

        server.add_secure_port(SRV_PORT, creds)
        logging.info('Starting server on %s' % SRV_PORT)
        await server.start()

        async def shutdown():
            logging.info('Shutting down rpc server')
            await server.stop(2)
            logging.info('Shutting down controller')
            await ctrl.stop()
        global _cleanup
        _cleanup = shutdown()

        logging.info('Launching server loop')
        await server.wait_for_termination()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        logging.info('Reached exit: cleaning up...')
        loop.run_until_complete(_cleanup)
        loop.close()

