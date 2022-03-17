#!/usr/bin/env python

print("\nHello, I'm Modbus Server/Slave programm by Vasiliy Andreev\n")
# --------------------------------------------------------------------------- #
# import the modbus libraries we need
# --------------------------------------------------------------------------- #
from pymodbus.version import version
from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

import time
import csv

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian


# --------------------------------------------------------------------------- #
# import the twisted libraries we need
# --------------------------------------------------------------------------- #
from twisted.internet.task import LoopingCall

# --------------------------------------------------------------------------- #
# configure the service logging
# --------------------------------------------------------------------------- #
import logging
logging.basicConfig(level = logging.INFO)

# --------------------------------------------------------------------------- #
# define constants
# --------------------------------------------------------------------------- #
server_IP = "0.0.0.0"
server_PORT = 5020

METHOD = 'rtu' # rtu or ascii
RS4851 = '/dev/ttymxc1' # port RS485-1
RS4852 = '/dev/ttymxc3' # port RS485-2
BAUDRATE = 9600 # 9600, 19200, 115200
BYTESIZE = 8 # 6, 7, 8
STOPBITS = 2 # 1, 1.5, 2

MAP3E = int(input("Write Modbus address \n")) # Modbus address WB-MAP3E

#data registers
PL1 = 0x1204
PL2 = 0x1208
PL3 = 0x120C
PLA = 0x1200
PLR = 0x1220

BITNESS = 64 # 16, 32, 64
ENDIAN = "little" # big or little
MULTIPLICATOR = 10**-5 # multiplication by this number

if BITNESS == 16:
        COUNT = 1
elif BITNESS == 32:
        COUNT = 2
elif BITNESS == 64:
        COUNT = 4

# Manual:
# PL1, PL2, PL3, PLA, PLR - data registers
# P1, P2, P3, AP, RP - holding registers from MAP3E
# res[] - list() data in dec
# P[], B[] - list() data * multiplicator = correct answer
# A[] - list() values per minute

res = [0, 0, 0, 0, 0]
P = [0, 0, 0, 0, 0]
A = [0, 0, 0, 0, 0]
B = [0, 0, 0, 0, 0]
n = [0, 0, 0, 0, 0]
k = [0, 0, 0, 0, 0]
data = []

# --------------------------------------------------------------------------- #
# define Modbus_RTU connect
# --------------------------------------------------------------------------- #
client1 = ModbusClient(method = METHOD, port = RS4851, timeout = 1, stopbits = STOPBITS, bytesize = BYTESIZE,  parity = 'N', baudrate = BAUDRATE)
client1.connect()
print("Hello, Modbus! \n");

# --------------------------------------------------------------------------- #
# reading start values
# --------------------------------------------------------------------------- #
P1 = client1.read_holding_registers(unit=MAP3E,address=PL1,count=COUNT)
P2 = client1.read_holding_registers(unit=MAP3E,address=PL2,count=COUNT)
P3 = client1.read_holding_registers(unit=MAP3E,address=PL3,count=COUNT)
AP = client1.read_holding_registers(unit=MAP3E,address=PLA,count=COUNT)
RP = client1.read_holding_registers(unit=MAP3E,address=PLR,count=COUNT)

for i in range (0, len(res)-1, 1):
    res[0] = res[0] + P1.registers[i]*(2**(16*i))
    res[1] = res[1] + P2.registers[i]*(2**(16*i))
    res[2] = res[2] + P3.registers[i]*(2**(16*i))
    res[3] = res[3] + AP.registers[i]*(2**(16*i))
    res[4] = res[4] + RP.registers[i]*(2**(16*i))

for i in range (len(res)):
    P[i] = round(MULTIPLICATOR*res[i], 6)
    n[i] = res[i]

client1.close()

print()
print("*" * 60)
print(" Start AP+(L1): ", P[0], "(kWt/h) \n", "Start AP+(L2): ", P[1], "(kWt/h) \n", "Start AP+(L3): ", P[2], "(kWt/h) \n", "Start AP+: ", P[3], "(kWt/h) \n", "Start RP-: ", P[4], "(kVAR/h)")
print("*" * 60)

# --------------------------------------------------------------------------- #
# define your callback process
# --------------------------------------------------------------------------- #
def updating_writer(a):
    """
    A worker process that runs every so often and
    updates live values of the context. It should be noted
    that there is a race condition for the update. 
    """
    logging.info(" updating the context")
    context = a[0]
    register = 3
    slave_id = 0x00
    address = 0x10
    Count = 5

    for i in range (len(res)): res[i] = 0

    client1.connect()

    start_t = time.time()

    P1 = client1.read_holding_registers(unit=MAP3E,address=PL1,count=COUNT)
    P2 = client1.read_holding_registers(unit=MAP3E,address=PL2,count=COUNT)
    P3 = client1.read_holding_registers(unit=MAP3E,address=PL3,count=COUNT)
    AP = client1.read_holding_registers(unit=MAP3E,address=PLA,count=COUNT)
    RP = client1.read_holding_registers(unit=MAP3E,address=PLR,count=COUNT)

    for i in range (0, len(res)-1, 1):
        res[0] = res[0] + P1.registers[i]*(2**(16*i))
        res[1] = res[1] + P2.registers[i]*(2**(16*i))
        res[2] = res[2] + P3.registers[i]*(2**(16*i))
        res[3] = res[3] + AP.registers[i]*(2**(16*i))
        res[4] = res[4] + RP.registers[i]*(2**(16*i))

    for i in range (len(res)):
        B[i] = round(MULTIPLICATOR*res[i], 6)

    for i in range (len(res)):
        k[i] = res[i] - n[i]
        A[i] = round(B[i] - P[i], 6)
        P[i] = B[i]
        n[i] = res[i]

    stop_t = time.time()

    client1.close()
    
    sec = time.time() + 3*60*60
    struct = time.localtime(sec)
    date = time.strftime('%d.%m.%Y %H:%M:%S', struct)
    data.clear()
    data.append(date)
    data.extend(A)

    # ----------------------------------------------------------------------- #
    # write to .scv file on the Board
    # ----------------------------------------------------------------------- #
    with open("/opt/file.csv", mode="a", newline = '') as w_file:
        w = csv.writer(w_file)
        w.writerow(data)
        w_file.close()

    print("*" * 60)
    print(date, "\n")
    print(" AP+(L1): ", A[0], "(kWt/h) \n", "AP+(L2): ", A[1], "(kWt/h) \n", "AP+(L3): ", A[2], "(kWt/h) \n", "AP+: ", A[3], "(kWt/h) \n", "RP-: ", A[4], "(kVAR/h)")
    print()
    print("Time: ", round((stop_t - start_t), 3), "sec.")
    print("*" * 60)

    # ----------------------------------------------------------------------- #
    # update the values
    # ----------------------------------------------------------------------- #
    values = context[slave_id].getValues(register, address, count=Count)
    values = [k[i] for i in range (len(k))]
    logging.info(f" new values: {values} on address: {int(address)} and count: {Count}")
    context[slave_id].setValues(register, address, values)

def run_server():
    # ----------------------------------------------------------------------- #
    # initialize your data store
    # ----------------------------------------------------------------------- #
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [17]*100),
        co=ModbusSequentialDataBlock(0, [17]*100),
        hr=ModbusSequentialDataBlock(0, [17]*100),
        ir=ModbusSequentialDataBlock(0, [17]*100))
    context = ModbusServerContext(slaves=store, single=True)


    # ----------------------------------------------------------------------- #
    # run the server you want
    # ----------------------------------------------------------------------- #
    time = 30  # 30 seconds delay
    loop = LoopingCall(f=updating_writer, a=(context,))
    loop.start(time, now=False) # initially delay by time
    StartTcpServer(context, address=(server_IP, server_PORT))


if __name__ == "__main__":
    run_server()

