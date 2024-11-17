import serial
import PyCCMDV2 as pyccmd




radioSerial = serial.Serial('COM64', 19200, timeout = 2)


ownID = 6210
otherID = 4324
msg = 'Hello World'

radio = pyccmd.Transceiver(radioSerial, ownID, verbose=True, mode = False)
txFlag = False
rxFlag = False


print(radio.getChannel())
print(radio.getESN())
print(radio.getVolume())
print(radio.getCloneComment(linenr=1))
print(radio.getCloneComment(linenr=2))
print(radio.getFreq())

radio.setFreq(145500000,145000000)
