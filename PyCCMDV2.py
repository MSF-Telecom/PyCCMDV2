import time
from collections import namedtuple
"""
PyCCMDV2 - a Python library for PC-CMD V2 protocol, used by the majority of ICOM Professional radios.
Frédéric Druppel - Manoel Casquilho


"""



class Transceiver :
  def __init__(self, PyCCMDV2, ownID, MSGCH = -1, DEFCH = -1, timeout = 2, mode=True, verbose = False):
    """
    Parameters :
    • PyCCMDV2 [serial] : The serial object of the transceiver
    • ownID [int] : The ID of the transceiver
    • MSGCH [int] : The channel to use for sending messages, defaults to current set channel
    • DEFCH [int] : The channel to use for receiving messages, defaults to current set channel
    • timeout [int] : The global timeout in seconds, defaults to 2
    • mode [bool] : The mode used by the radio. True for dPMR, False for NXDN
    """
    self.PyCCMDV2 = PyCCMDV2
    self.ownID = ownID
    self.timeout = timeout
    self.ownID = ownID
    self.mode = mode
    self.verbose = verbose

    self.bol = b'\x02'
    self.eol = b'\x03'

    if MSGCH == -1 :
      self.MSGCH = self.getChannel()
    else :
      self.MSGCH = MSGCH
    
    if DEFCH == -1 :
      self.DEFCH = self.getChannel()
    else :
      self.DEFCH = DEFCH

    self.setChannel(self.DEFCH)

  def sendCommand(self, command):
    """
    Parameters :
    • command [string] : The command to send to the radio
    Returns :
    • Nothing
    """
    data = self.bol + command.encode("utf-8") + self.eol
    self.PyCCMDV2.write(data)

  def sendMessage(self, message, otherID, timeout = 10, verbose = False):
    """
    Parameters :
    • message [string] : The message to send
    • otherID [int] : The ID of the receiver
    • timeout [int] : The timeout in seconds
    • verbose [bool] : If true, print the response of the radio while the message is being sent
    Returns :
    • ACK [string] : The response of the radio :
      ACK_OK if the message was sent, 
      ACK_NG if the message was not sent, TIMEOUT_ERROR if the timeout was reached,
      UNKNOWN_ERROR if an unknown error occured
    """
    self.setChannel(self.MSGCH, resetDefault = True)

    if self.mode :
      command = '*SET,DPMR,TXMSG,IND,{},{},MSG,"{}",ACK'.format(self.zfill(str(otherID), 7), self.zfill(str(self.ownID), 7), message)
    else :
      command = '*SET,IDAS,TXMSG,IND,{},{},MSG,"{}",ACK'.format(str(otherID), str(self.ownID), message)
    if verbose :
      print('TX {}'.format(command))
    self.sendCommand(command)

    response = ''

    
    if self.mode :
      condition = '*NTF,DPMR,TXMSG,IND,'
    else :
      condition = '*NTF,IDAS,TXMSG,IND,'
    while not condition in response :
      response = self.receiveCommand(timeout)
      if response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR' :
        if verbose :
          print(response)
        self.setChannel(self.DEFCH)
        return response
      if verbose :
        print('RX {}'.format(response))

    if '"' + message + '",ACK,OK' in response :
      self.setChannel(self.DEFCH)
      return 'ACK_OK'
    elif '"' + message + '",ACK,NG' in response :
      self.setChannel(self.DEFCH)
      return 'ACK_NG'
    else :
      self.setChannel(self.DEFCH)
      return 'UNKNOWN_ERROR'

    

  def sendStatus(self, status, otherID, timeout = 10, verbose = False):
    """
    Parameters :
    • status [int] : The status to send to the radio
    Returns :
    • ACK [string] : The response of the radio :
      ACK_OK if the status was sent,
      ACK_NG if the status was not sent,
      TIMEOUT_ERROR if the timeout was reached,
      UNKNOWN_ERROR if an unknown error occured
    """
    
    self.setChannel(self.MSGCH, resetDefault = True)

    if self.mode :
      command = '*SET,DPMR,TXSTAT,IND,{},{},{},ACK'.format(self.zfill(str(otherID), 7), self.zfill(str(self.ownID), 7), str(status))
    else :
      command = '*SET,IDAS,TXSTAT,IND,{},{},{},ACK'.format(str(otherID), str(self.ownID), str(status))      
    if verbose :
      print('-> {}'.format(command))
    self.sendCommand(command)

    response = ''

    if self.mode :
      condition = '*NTF,DPMR,TXSTAT,IND,'
    else :
      condition = '*NTF,IDAS,TXSTAT,IND,'
    while condition not in response :
      response = self.receiveCommand(timeout)
      if response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR' :
        if verbose :
          print(response)
        self.setChannel(self.DEFCH)
        return response
      if verbose :
        print('<- {}'.format(response))
      if 'NG' in response :
        self.setChannel(self.DEFCH)
        return 'STAT_NG'
    
    if '' + str(status) + ',ACK,OK' in response :
      self.setChannel(self.DEFCH)
      return 'ACK_OK'
    elif '' + str(status) + ',ACK,NG' in response :
      self.setChannel(self.DEFCH)
      return 'ACK_NG'
    else :
      self.setChannel(self.DEFCH)
      return 'UNKNOWN_ERROR'

  def receiveCommand(self, timeout = 2, verbose = False):
    """
    Parameters :
    • timeout [int] : The timeout in seconds
    Returns :
    • response [string] : The response of the radio
    """
    # TODO : Verify & test function
    response = b''
    byteread = b''
    beginTime = time.time()
    while not (byteread==self.eol):
      if(time.time() - beginTime > timeout):
        return 'TIMEOUT_ERROR'
      byteread = self.PyCCMDV2.read(1)
      try :
        response += byteread
      except :
        response = response

    #self.PyCCMDV2.flush()
    try :
      command = response.decode("utf-8")[1:-1]
    except :
      command = 'CMD_UNICODE_ERROR'
    if verbose :
      print(command)
    return command     


  def receiveMessage(self, timeout = 2, verbose = False):
    """
    Parameters :
    • timeout [int] : The timeout in seconds
    • verbose [bool] : If true, print the response of the radio while the message is being received
    Returns :
    • msgReturn [namedtuple] : The received & parsed message with messageType, senderID, destID, testType, messageContents, all [str]
    """
    response = ''
    # messageType:
    #CH (channel change - contents: channel nr),
    #AUD (audio channel, contents: ON or OFF)
    #SQL (squelch, either CLOSED or displays an RSSI value),
    #RXI (digital call, only RSSI, contents RSSI)
    #RXV (digital call received, contents: IDs and RSSI),
    #ENCR (Scrambler status, contents: encryption value info)
    #CCRAN (digital Color Code or RAN, contents: CC or RAN)
    #MSG (text message),
    #GPS (text message, contents: coordinates in NMEA),
    #STAT (status message, contents: status value),
    #NA (unsupported),
    #ERR (error, timeout or wrong command)
    MsgReturn = namedtuple('msgReturn', ['messageType', 'senderID', 'destID', 'destType', 'messageContents'])
    msgReturn = MsgReturn('NA', '', '', '', '')
    beginTime = time.time()
      
    while not '*NTF,' in response :
      response = self.receiveCommand(timeout)
      if response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR' :
        if verbose : print(response)
        msgReturn = MsgReturn('ERR', '', '', '', response)
        return msgReturn
      if verbose : print('RX {}'.format(response))
    parsedResponse = response.split(',')

    #Digital (dPMR or NXDN) frames
    if parsedResponse[1]=='IDAS' or parsedResponse[1]=='DPMR':
        if parsedResponse[2]=='RXVCALL':
          msgReturn = MsgReturn('RXV', parsedResponse[5], parsedResponse[4], parsedResponse[3], parsedResponse[7])
        elif parsedResponse[2]=='RXMSG' and parsedResponse[8]=='MSG':
          msgReturn = MsgReturn('MSG', parsedResponse[5], parsedResponse[4], parsedResponse[3], response.split(',MSG,"')[-1].split('"')[0])
        elif parsedResponse[2]=='RXMSG' and parsedResponse[8]=='GPS':
          msgReturn = MsgReturn('MSG', parsedResponse[5], parsedResponse[4], parsedResponse[3], response.split(',GPS,"')[-1].split('"')[0])
        elif parsedResponse[2]=='RXSTAT':
          msgReturn = MsgReturn('STAT', parsedResponse[5], parsedResponse[4], parsedResponse[3], parsedResponse[8])
        elif parsedResponse[2]=='RXENCRYPT':
          msgReturn = MsgReturn('ENCR', '', '', '', parsedResponse[3])
        elif parsedResponse[2]=='RXRAN' or parsedResponse[2]=='RXCC':
          msgReturn = MsgReturn('CCRAN', '', '', '', parsedResponse[3])

    #Channel control frames
    elif parsedResponse[1]=='MCH' :
      if parsedResponse[2]=='SEL' :
        msgReturn = MsgReturn('CH', 0, 0, '', parsedResponse[3])

    #General status frames
    elif parsedResponse[1]=='CTRL':
      if parsedResponse[2]=='SQL' and parsedResponse[3]=='OPEN':
        msgReturn = MsgReturn('SQL', 0, 0, '', parsedResponse[5])
      elif parsedResponse[2]=='SQL' and parsedResponse[3]=='CLOSE':
        msgReturn = MsgReturn('SQL', 0, 0, '', parsedResponse[3])
      elif parsedResponse[2]=='AUD' :
        msgReturn = MsgReturn('AUD', 0, 0, '', parsedResponse[3])
      if parsedResponse[2]=='DBUSY' and parsedResponse[3]=='ON':
        msgReturn = MsgReturn('RXI', 0, 0, '', parsedResponse[5])
      elif parsedResponse[2]=='DBUSY' and parsedResponse[3]=='OFF':
        msgReturn = MsgReturn('RXI', 0, 0, '', parsedResponse[3])
        
    # Unsupported command
    else:
      print(response)
      msgReturn = MsgReturn('NA', '', '', '', '')

    return msgReturn
        
    

  def setChannel(self, channel, resetDefault = False, verbose = False):
    """
    Parameters :
    • channel [int] : The channel to set
    • resetDefault [bool] : If true, reset the default channel to the current set channel
    Returns :
    • Nothing
    """
    if resetDefault:
      self.DEFCH = self.getChannel()
    
    command = '*SET,MCH,SEL,{}'.format(str(channel))
    self.sendCommand(command)

    response = ''
    while not '*NTF,MCH,SEL,' in response :
      response = self.receiveCommand()
      if response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR' :
        if verbose :
          print(response)
        return response
      if verbose :
        print('<- {}'.format(response))
    if '*NTF,MCH,SEL,{}'.format(channel) in response :
      return 'OK'
    else :
      return 'NG'

  def getChannel(self, resetDefault = False):
    """
    Parameters :
    • resetDefault [bool] : If true, reset the default channel to the current set channel
    Returns :
    • channel [int] : The current channel
    """
    command = '*GET,MCH,SEL'
    self.sendCommand(command)
    response = ""
    while not '*NTF,MCH,SEL,' in response :
      response = self.receiveCommand(self.timeout)
      if(response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR'):
        return -1

    currentChannel = int(response.split(',')[-1])
    if resetDefault :
      self.DEFCH = currentChannel
    return currentChannel

  def setVolume(self, volume):
    """
    Parameters :
    • volume [int] : Volume value, between 0 and 255
    Returns :
    • Nothing
    """
    command = '*SET,UI,AFVOL,{}'.format(str(volume))
    self.sendCommand(command)

  def getVolume(self):
    """
    Parameters :
    • Nothing
    Returns :
    • volume [int] : Volume value, between 0 and 255
    """
    command = '*GET,UI,AFVOL'
    self.sendCommand(command)
    response = ""
    while not '*NTF,UI,AFVOL,' in response :
      response = self.receiveCommand(self.timeout)
      if(response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR'):
        return -1

    volumeValue = int(response.split(',')[-1])
    return volumeValue
    
  def setRadioID(self, radioid, talkgroupid):
    """
    Parameters :
    • radioid [int] : Unique radio identifier
    • talkgroupid [int] : talkgroup identifier
    Returns :
    • Nothing
    """
    command = '*SET,IDAS,SENDID,TG,{}'.format(str(talkgroupid)+','+str(radioid))
    self.sendCommand(command)

  def getRadioID(self):
    """
    Parameters :
    • Nothing
    Returns :
    • radioid [int] : Unique radio identifier
    • talkgroupid [int] : talkgroup identifier
    """
    command = '*GET,IDAS,SENDID'
    self.sendCommand(command)
    response = ""
    while not '*NTF,IDAS,SENDID,' in response :
      response = self.receiveCommand(self.timeout)
      if(response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR'):
        return -1
    
    radioid = int(response.split(',')[-1])
    talkgroupid = int(response.split(',')[-2])
    return radioid, talkgroupid  

  def setFreq(self, txFreq, rxFreq):
    """
    Parameters :
    • txFreq [int] : TX Frequency value in Hz
    • rxFreq [int] : RX Frequency value in Hz
    Returns :
    • Nothing
    """
    command = '*SET,MCH,FREQ,{}'.format(str(txFreq)+','+str(rxFreq))
    self.sendCommand(command)
 
  def getFreq(self):
    """
    Parameters :
    • Nothing
    Returns :
    • txfreq [int] : TX Frequency value in Hz
    • rxfreq [int] : RX Frequency value in Hz
    """
    command = '*GET,MCH,FREQ'
    self.sendCommand(command)
    response = ""
    while not '*NTF,MCH,FREQ,' in response :
      response = self.receiveCommand(self.timeout)
      if(response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR'):
        return -1

    rxFreq = int(response.split(',')[-1])
    txFreq = int(response.split(',')[-2])
    return txFreq, rxFreq
  

  def getCloneComment(self, linenr = 1):
    """
    Parameters :
    • linenr [int] : line number (1 or 2)
    Returns :
    • line [str] : Comment field's content
    """
    command = '*GET,INFO,COMMENT,{}'.format(str(linenr))
    self.sendCommand(command)
    response = ""
    while not '*NTF,INFO,COMMENT' in response :
      response = self.receiveCommand(self.timeout)
      if(response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR'):
        return -1

    lineContents = response.split(',')[-1]
    return lineContents


  def getESN(self):
    """
    Parameters :
    • Nothing
    Returns :
    • channel [int] : Radio's serial number
    """
    command = '*GET,INFO,ESN'
    self.sendCommand(command)
    response = ""
    while not '*NTF,INFO,ESN' in response :
      response = self.receiveCommand(self.timeout)
      if(response == 'TIMEOUT_ERROR' or response == 'CMD_UNICODE_ERROR'):
        return -1

    serialNumber = int(response.split(',')[-1])
    return serialNumber


  def setUItext(self, message = ""):
    """
    Parameters :
    • message [string] : The message to display on the UI, if set to "" the UI will be cleared
    Returns :
    • Nothing
    """
    command = '*SET,UI,TEXT,"{}"'.format(message)
    self.sendCommand(command)


  def reset(self):
    """
    Parameters :
    • Nothing
    Returns :
    • Nothing
    """
    command = '*SET,UI,RESET'
    self.sendCommand(command)    
  
  def zfill(self, string, length):
    """
    Parameters :
    • string [string] : The string to fill
    • length [int] : The length of the string to fill
    Returns :
    • string [string] : The filled string
    """
    return '{:0>{l}}'.format(string, l=length)


if __name__ == '__main__':
  help(Transceiver)

