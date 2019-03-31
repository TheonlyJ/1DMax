from socket import *

sock = socket(AF_INET)
sock.settimeout(5)
sock.connect(('127.0.0.1',2805))
while True:
    data = input('Your command?').encode('ascii', 'ignore')
    sock.send(data)

