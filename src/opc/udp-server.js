import { createSocket } from 'dgram';
import { parseOPCMessage } from './parser';

/**
 * Open Pixel Control server implementation of the driverFactory.driver interface.
 * Given a context containing a list of spi device specifications,
 * Configure UDP server callbacks to handle OPC commands.
 * @param {object} context The context under which the driver operates
 */
export const opcUDPServer = context => {
  const { opc_port } = context;
  console.log(`About to create OPC UDP server on port ${opc_port}`);

  context.server = createSocket('udp4', () => {
    console.log('socket create callback');
  });

  context.server.on('error', err => {
    console.log(`server error:\n${err.stack}`);
    context.server.close();
  });

  context.server.on('message', (msg, rinfo) => {
    console.log(`server got: ${msg} from ${rinfo.address}:${rinfo.port}`);
    parseOPCMessage(context, msg);
  });

  context.server.on('listening', () => {
    const address = context.server.address();
    console.log(`server listening ${address.address}:${address.port}`);
  });

  context.server.bind(opc_port, '127.0.0.1', () => {
    console.log('socket bind callback');
  });

  console.log(`After bind ${context.server}`);

  // context.server.close(() => {
  //   console.log('socket close callback');
  // });

  // console.log(`After close ${context.server}`);
  return context;
};
