import sys
import os
import threading
import json
import zmq

# Result types:
# ok, next_as:bytes, error,



class VoiceChatServer:

    def __init__(self, mainSocket):
        self.mainSocket = mainSocket
        self.inputPort = 4000
        self.clients = {}
        self.context = zmq.Context()

    def Start(self):
        while True:
            request = self.mainSocket.recv_json()
            response = self.AttendRequest(request)
            if (request['op'] == 'ActiveCallAudio'):
                continue
            else:
                self.mainSocket.send_json(response)

    def AttendRequest(self, request):
        if request['op'] == 'NewClient':
            client_name = request['name']
            client_ip = request['ip']
            port = self.AddNewClient(client_name, client_ip)
            return {'op': 'result', 'result': 'ok', 'port': port}
        elif request['op'] == 'GetListOfClients':
            result = self.GetListOfClients()
            return {'op': 'result', 'result': 'ok', 'clients': result}
        elif request['op'] == 'Call':
            response = self.Call(request)
            return {'op': 'result', 'result': 'ok', 'response': response}
        elif request['op'] == 'SendMessage':
            self.SendMessage(request)
            return {'op': 'result', 'result': 'ok'}
        elif request['op'] == 'ActiveCallAudio':
            self.mainSocket.send_json('ok')
            reciever = self.clients[request['reciever']]
            reciever.send_json(request)
            reciever.recv_json()
            return ''
        else:
            print('Invalid operation')
            return {
                'op': 'result',
                'result': 'error',
                'error': 'Invalid operation'
            }

    def AddNewClient(self, client_name, client_ip):
        print('Adding a new client...')
        self.inputPort += 1
        client_socket = self.context.socket(zmq.REQ)
        client_socket.connect("tcp://localhost:{}".format(self.inputPort))
        self.clients[client_name] = client_socket
        return self.inputPort

    def GetListOfClients(self):
        print('Serving list of clients...')
        return list(self.clients.keys())

    def Call(self, request):
        print('Calling a client...')
        emitter = request['emitter']
        userToCall = request['receiver']
        sc = self.clients[userToCall]
        sc.send_json(
            {
                'op': 'IncomingCall',
                'from': emitter
            }
        )
        response = sc.recv_json()
        if response['op'] == 'CallAccepted':
            print('The call was accepted. Now their are talking')
            return 'accepted'
        print('The call was rejected...')
        return 'rejected'

    def SendMessage(self, request):
        pass
