#!/usr/bin/env python3
import time
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

METHOD = 'rtu' # rtu or ascii
RS4851 = '/dev/ttyRS485-1'
RS4852 = '/dev/ttyRS485-2'
BAUDRATE = 9600 # 9600, 19200, 115200
BYTESIZE = 8 # 6, 7, 8
STOPBITS = 2 # 1, 1.5, 2

client1 = ModbusClient(method = METHOD, port = RS4851, timeout = 1, stopbits = STOPBITS, bytesize = BYTESIZE,  parity = 'N', baudrate = BAUDRATE)
client1.connect()

client2 = ModbusClient(method = METHOD, port = RS4852, timeout = 1, stopbits = STOPBITS, bytesize = BYTESIZE,  parity = 'N', baudrate = BAUDRATE)
client2.connect()


MAO = 77 # Modbus address WB-MAO4
MAP3E = 107 # Modbus address WB-MAP3E
ADDRESS = 0 # regiser output1 MAO4
BITNESS = 64 # 16, 32, 64
ENDIAN = "little" # big or little
MULTIPLICATOR = 10**-5 # multiplication by this number
PL1 = 0x1204
PL2 = 0x1208

if BITNESS == 16:
	COUNT = 1
elif BITNESS == 32:
	COUNT = 2
elif BITNESS == 64:
	COUNT = 4

P1 = client1.read_holding_registers(unit=MAP3E,address=PL1,count=COUNT)
P2 = client1.read_holding_registers(unit=MAP3E,address=PL2,count=COUNT)

res1 = 0
res2 = 0
i = 0
while i < COUNT:
	res1 = res1 + P1.registers[i]*(2**(16*i))
	res2 = res2 + P2.registers[i]*(2**(16*i))
	i += 1

P01 = round(MULTIPLICATOR*res1, 6)
P02 = round(MULTIPLICATOR*res2, 6)
print()
print("*" * 60)
print('Start AP1: ', P01)
print('Start AP2: ', P02)
print("*" * 60)

client2.write_register(address=ADDRESS, value=10000,unit=MAO)

time.sleep(10)
a = 1
AP1_all = 0
AP2_all = 0
Acc = 0
ti = 10

while a == 1:
	print()
#------------------------------------------------------------------------------------
	start_t = time.time()
	result1 = client1.read_holding_registers(unit=MAP3E,address=PL1,count=COUNT)
	result2 = client1.read_holding_registers(unit=MAP3E,address=PL2,count=COUNT)
	r1 = 0
	r2 = 0
	i = 0
	while i < COUNT:
		r1 = r1 + result1.registers[i]*(2**(16*i))
		r2 = r2 + result2.registers[i]*(2**(16*i))
		i += 1

	res1 = round(MULTIPLICATOR*r1, 6)
	res2 = round(MULTIPLICATOR*r2, 6)

	stop_t = time.time()
#------------------------------------------------------------------------------------
	P1 = round(res1 - P01, 6) * 1000
	P2 = round(res2 - P02, 6) * 1000

	P01 = res1
	P02 = res2

	print("AP1 in Wt/h:", P1)
	print("AP2 in Wt/h:", P2)
	print()

	if ti > 0:
		V1 = round(P1/ti, 4)
		print("new v1 =", V1)
	else:
		print("old v1 =", V1)
	if P2 > 0:
		V2 = round(P2/10, 4)
		print("v2 =",V2)
	else:
		print("v2 = error")
		V2 = 0
	print()

	AP1_all = round(AP1_all + P1/1000, 6)
	AP2_all = round(AP2_all + P2/1000, 6)
	Acc = Acc + P1 - P2
	print(". " * 30)
	print()
	print("accumulated in Wt/h:", Acc)
	print()
	print(". " * 30)
	print()
	print("AP1_all in kWt/h:", AP1_all)
	print("AP2_all in kWt/h:", AP2_all)
	print()
	print("runtime in ms:", (stop_t-start_t)*1000)
	print()
	print("/ " * 30)

	if P2 == 0:
		ti = 0
		client2.write_register(address=ADDRESS, value=0,unit=MAO)
		print("line break")
		print("/ " * 30)
		time.sleep(10-ti)

	elif P1 == P2 and V1 > 0:

		t1 = P2/V1

		client2.write_register(address=ADDRESS, value=10000,unit=MAO)
		print("end correct time:", ti)
		print("/ " * 30)
		time.sleep(ti)
		client2.write_register(address=ADDRESS, value=0,unit=MAO)
		time.sleep(10-ti)

	elif V1 > 0 and V2 > 0:

		t1 = P2/V1
		t2 = Acc/V2
		ti = t1-t2

		if t2 > 10 or ti < 0:
			ti = 0
			client2.write_register(address=ADDRESS, value=0,unit=MAO)
			print("wait")
			print("/ " * 30)
			time.sleep(10-ti)
		elif ti < 10:
			client2.write_register(address=ADDRESS, value=10000,unit=MAO)
			print("correct time:", ti)
			print("/ " * 30)
			time.sleep(ti)
			client2.write_register(address=ADDRESS, value=0,unit=MAO)
			time.sleep(10-ti)
		else:
			ti = 10
			client2.write_register(address=ADDRESS, value=10000,unit=MAO)
			print("always on")
			print("/ " * 30)
			time.sleep(ti)

	else:
		ti = 10
		client2.write_register(address=ADDRESS, value=10000,unit=MAO)
		print("new loop")
		print("/ " * 30)
		time.sleep(ti)

	print()
	print("-" * 60)
