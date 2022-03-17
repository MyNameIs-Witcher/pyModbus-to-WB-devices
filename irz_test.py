from pymodbus.client.sync import ModbusTcpClient as ModbusClient

import logging

from pymodbus.pdu import ModbusExceptions
logging.basicConfig(level = logging.INFO)


server_IP = "172.16.17.131"
server_PORT = 50009

res = 0

client = ModbusClient(server_IP, port = server_PORT)

client.connect()
if client.is_socket_open() == True:
    print ("Connect OK")
    logging.info("Reading...")
    rr = client.read_holding_registers(address = 0x1204, count = 4, unit = 107)
    logging.info(rr)

    for i in range (0, 4, 1):
        res = res + rr.registers[i]*(2**(16*i))

    print("res:",res/(10**5))

    client.close()
else: 
    print("Connection false")

