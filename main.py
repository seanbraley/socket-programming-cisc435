# -*- coding: utf-8 -*-
"""
CISC 435
Sean Braley, 10026302, 1SB36

Using exerpts from the textbook

Designed on Python 2.7.8

Running instructions:
    `python main.py`
    MUST USE CTRL-C to exit

Copyright seanbraley

"""

from socket import AF_INET, SOCK_STREAM
from socket import socket
from socket import error as socket_error
from sys import argv
import random
import json
from threading import Thread
from datetime import datetime, timedelta

class RequestSocket(Thread):
    """
    Purpose: 
        This socket asynchronously waits for connections 
        after a general request is sent out.
    """
    def __init__(self, client, serverName='localhost', port=0):
        super(RequestSocket, self).__init__()
        self.serverName = serverName
        self.client = client
        self.matches = []
        # Get socket
        self.serv = socket(AF_INET, SOCK_STREAM)
        # Bind to port
        self.serv.bind((self.serverName, port))
        # Get port so tracker can send it to servers
        self.port = self.serv.getsockname()[1]
    def run(self):
        # Stack up to 100 requests
        self.serv.listen(5000)
        # Get current time
        now = datetime.now()
        # Get datetime for 2 seconds in the future
        twoSecondsInFuture = now + timedelta(0,2)
        # Configure socket to timeout
        self.serv.settimeout(2.0)
        # Configure while loop to exit on timeout
        while twoSecondsInFuture > datetime.now():
            try:
                # Accept incoming request
                connectionSocket, addr = self.serv.accept()
                # Get message
                message = connectionSocket.recv(1024)
                # Decode message
                message = json.loads(message)
                # If it is a request repsonse
                if message['type'] == 'request-response':
                    # Add server to list of matches
                    self.matches.append(message['name'])
            # Timeout error happens
            except:
                pass
        # Show matches found
        print "Central: Sending match reply to ", self.client[0]
        # Get socket
        clientSocket = socket(AF_INET, SOCK_STREAM)
        # Connect to client, three-tuple (virtualname, virtualhost, port)
        clientSocket.connect((self.client[1],self.client[2]))
        # Encode data
        data = dict(
            type="request-response",
            servers=self.matches,
        )
        # Send data
        clientSocket.send(json.dumps(data))
        clientSocket.close()


class TrackerSocket(Thread):
    """
    Purpose:
        This socket acts as the main tracker for the other sockets.
        The other sockets send a Hi or Hello message to register
        themselves. Requests are routed through here and RequestSockets
        are spawned from here. 
    """
    def __init__(self, n, serverName='localhost', port=12123):
        super(TrackerSocket, self).__init__()
        self.completed = 0
        self.n = n
        self.serverName = serverName
        self.port = port
        self.servers = []
        self.clients = []

    def run(self):
        # Get socket
        serv = socket(AF_INET, SOCK_STREAM)
        # Bind to specific port (12123)
        serv.bind((self.serverName, self.port))
        # stack up to 100 requests
        serv.listen(5000)
        # Loop while there are still requests
        while True:
            # Accept connection
            connectionSocket, addr = serv.accept()
            # Get message
            message = connectionSocket.recv(1024)
            try:
                # Decode the message
                message = json.loads(message)
                # If it's an announcement message
                if message['type'] == "announce":
                    # If its from a 'server'
                    if message['virtualName'][:1] == "S":
                        print "Central: Hello received from: ", message['virtualName']
                        # Add to list of known servers
                        self.servers.append((message['virtualName'], addr[0], message["listenPort"]))
                    # If its a 'client'
                    elif message['virtualName'][:1] == "C":
                        # Add to list of known clients
                        print "Central: Hi received from: ", message['virtualName']
                        self.clients.append((message['virtualName'], addr[0]))
                # If it's a request from a client
                elif message['type'] == "request":
                    # Create listener
                    print "Central: Process match request from: ", message['virtualName']
                    listener = RequestSocket(client=(message['virtualName'], message['virtualhost'], message['port']) )
                    # Start listener
                    listener.start()
                    # Iterate through known servers
                    for server in self.servers:
                        # Get socket
                        clientSocket = socket(AF_INET, SOCK_STREAM)
                        # Connect to server
                        clientSocket.connect((server[1],server[2]))
                        # Encode data
                        data = dict(
                            type="request",
                            virtualName="Central",
                            value=message['value'],
                            host='localhost',
                            port=listener.port,
                        )
                        # Send data
                        clientSocket.send(json.dumps(data))
                        clientSocket.close()
                # Count clients finishing        
                elif message['type'] == "done":
                    self.completed += 1
                    if self.completed == self.n:
                        # Send message to servers to end
                        for server in self.servers:
                            # Get socket
                            clientSocket = socket(AF_INET, SOCK_STREAM)
                            # Connect to server
                            clientSocket.connect((server[1],server[2]))
                            # Encode data
                            data = dict(
                                type="done",
                            )
                            # Send data
                            clientSocket.send(json.dumps(data))
                            clientSocket.close()
                        # End this thread
                        break
            # For when you accidentally get a not-json message
            except ValueError:
                pass

class ServerSocket(Thread):
    """
    Purpose:
        This socket acts as a 'server' and waits for connection requests
        after announcing itself to the tracker. On a request it checks its
        random number against the request, and replies if there is a match.
    """
    def __init__(self, serverNumber, serverName='', port=0):
        super(ServerSocket, self).__init__()
        self.completed = 0
        self.serverNumber = serverNumber
        self.serverName = serverName
        self.port = port
        self.randNumber = random.randint(1,10)

    def run(self):
        # Get a socket (for later requests)
        serv = socket(AF_INET, SOCK_STREAM)
        # Bind to the socket, use any free port
        serv.bind((self.serverName, self.port))
        # Get port for reference
        self.port = serv.getsockname()[1]
        # Stack up to 100 requests
        serv.listen(5000)

        # Announce to tracker
        print "S"+str(self.serverNumber)+": sending \"Hello\" to Central"
        # Pick a random number
        print "S"+str(self.serverNumber)+": selected random number is "+str(self.randNumber)
        # Get a socket
        clientSocket = socket(AF_INET, SOCK_STREAM)
        # Connect to tracker socket
        clientSocket.connect((self.serverName,12123))
        # Encode data
        data = dict(
            type="announce",
            virtualName="S"+str(self.serverNumber),
            listenPort=self.port,
        )
        # Send data
        clientSocket.send(json.dumps(data))
        clientSocket.close()

        # Wait for requests
        while True:
            # Accept request
            connectionSocket, addr = serv.accept()
            # Load data
            message = connectionSocket.recv(1024)
            # Decode data
            message = json.loads(message)
            # If its a request message
            if message['type']=='request':
                # If the request is relevant to us
                if int(message['value']) == self.randNumber:
                    # Get socket
                    requestSocket = socket(AF_INET, SOCK_STREAM)
                    # Open socket to request thread
                    requestSocket.connect((message['host'], message['port']))
                    # Encode data
                    data = dict(
                        type='request-response',
                        name='S'+str(self.serverNumber),
                        host=self.serverName,   
                        port=self.port,
                    )
                    # Send data
                    requestSocket.send(json.dumps(data))
                    requestSocket.close()
            # Special end message from tracker
            elif message['type']=='done':
                print "EXITING"
                break
            connectionSocket.close()
        

class ClientSocket(Thread):
    """
    Purpose:
        This socket acts as a 'client' and after announcing itself to the
        tracker it will send out random request for numbers to the tracker.
    """
    def __init__(self, clientNumber, clientName='localhost', port=0):
        super(ClientSocket, self).__init__()
        self.clientNumber = clientNumber
        self.clientName = clientName
        self.port = port

    def run(self):
        # Tell everyone whats going on
        print "C"+str(self.clientNumber)+": sending \"Hi\" to Central"
        # Get Socket
        clientSocket = socket(AF_INET, SOCK_STREAM)
        # Connect to tracker socket
        clientSocket.connect((self.clientName,12123))
        # Encode data
        data = dict(
            type="announce",
            virtualName="C"+str(self.clientNumber),
        )
        # Send data
        clientSocket.send(json.dumps(data))
        clientSocket.close()
        
        # Send random request
        for i in range(5):
            # Generate number
            rand = random.randint(1,10)
            print "C"+str(self.clientNumber)+": Find match of", rand
            # Get sockets
            clientSocket = socket(AF_INET, SOCK_STREAM)
            listenSocket = socket(AF_INET, SOCK_STREAM)
            # Connect to tracker socket
            clientSocket.connect((self.clientName,12123))
            # Bind to port
            listenSocket.bind ((self.clientName, 0))
            # Encode request
            data = dict(
                type="request",
                virtualName="C"+str(self.clientNumber),
                value=rand,
                virtualhost=self.clientName,
                port=listenSocket.getsockname()[1],
            )
            # Send data
            clientSocket.send(json.dumps(data))
            clientSocket.close()

            # Wait for response, for 4 seconds (HAS TO BE MORE THAN REQUEST SOCKET)
            listenSocket.settimeout(4.0)
            # Accept incoming request
            try:
                # Listen but only stack 1 request
                listenSocket.listen(1)
                connectionSocket, addr = listenSocket.accept()
                # Get message
                message = connectionSocket.recv(1024)
                # Decode the message
                message = json.loads(message)
                # If proper message
                if message['type'] == "request-response":
                    if message['servers'] != []:
                        print "C"+str(self.clientNumber)+ ": Matches found on: "+", ".join(message['servers'])
                    else:
                        print "C"+str(self.clientNumber)+ ": No matches found"
            # Timeout error
            except socket_error as e:
                pass
        clientSocket = socket(AF_INET, SOCK_STREAM)
        # Connect to tracker socket
        clientSocket.connect((self.clientName,12123))
        # Encode data
        data = dict(
            type="done",
            virtualName="C"+str(self.clientNumber),
        )
        # Send data
        clientSocket.send(json.dumps(data))
        clientSocket.close()

# This runs the script
if __name__=="__main__":
    
    try:
        number = int(argv[1])
        # Must start at least 2 servers and clients
        if number <= 2:
            print "ERROR! Please enter a number higher than 2"
        else:
            tracker = TrackerSocket(int(argv[1]), "localhost")
            tracker.start()    
            for i in range(number):
                ServerSocket(i, 'localhost').start()
                ClientSocket(i, 'localhost').start()
    except:
        print "ERROR! Not a number or some other error"
