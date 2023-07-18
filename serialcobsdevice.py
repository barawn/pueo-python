from cobs import cobs
import serial
from time import sleep

class SerialCOBSDevice:
	def __init__(self, port, baudrate):
		self.dev = serial.Serial(port, baudrate)
		self.reset()

	def reset(self):		
		# flushy-flushy
		self.dev.write([0x00,0x00,0x00,0x00])
		rx = self.dev.in_waiting
		# and dump
		if rx:
			self.dev.read(rx)




        # Multiread isn't necessarily supported for all addresses, be careful!
	def multiread(self, addr, num):
		tx = bytearray(4)
		tx[0] = (addr & 0x7F0000)>>16
		tx[1] = (addr & 0xFF00)>>8
		tx[2] = addr & 0xFF
		tx[3] = num - 1
		toWrite = cobs.encode(tx)
		# print(toWrite)
		self.dev.write(toWrite)
		self.dev.write(b'\x00')
		# expect num+3 bytes back + 1 overhead + 1 framing
		rx = self.dev.read(num + 5)
		pk = cobs.decode(rx[:(num+5-1)])
		return pk[3:]

	def read(self, addr):
		pk = self.multiread(addr, 4)
		val = pk[0]
		val |= (pk[1] << 8)
		val |= (pk[2] << 16)
		val |= (pk[3] << 24)
		return val

	def multiwrite(self, addr, data):
		self.writeto(addr, data)
		# expect 4 bytes back + 1 overhead + 1 framing
		rx = self.dev.read(6)
		pk = cobs.decode(rx[:5])
		return pk[3]

	def write(self, addr, val):
		tx = bytearray(4)
		tx[0] = val & 0xFF
		tx[1] = (val & 0xFF00)>>8
		tx[2] = (val & 0xFF0000)>>16
		tx[3] = (val & 0xFF000000)>>24
		return self.multiwrite(addr, tx)
		
	# supes-dangerous, only do this if you KNOW there won't be a response
	def writeto(self, addr, data):
		tx = bytearray(3)
		tx[0] = (addr & 0x7F0000)>>16
		tx[0] |= 0x80
		tx[1] = (addr & 0xFF00)>>8
		tx[2] = addr & 0xFF
		tx.extend(data)
		self.dev.write(cobs.encode(tx))
		self.dev.write(b'\x00')
		
	