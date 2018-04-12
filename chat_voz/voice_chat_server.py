import zmq


class Server:

    PORT_COUNTER = 4000

    def __init__(self):
        self.context = zmq.Context()
        self.clients = {} # (socker, ip, port)
        self.groups = {} # { 'name': {'name': socket, ...}}
        self.socket = self.context.socket(zmq.REP)

    def start(self, port):
        self.socket.bind("tcp://*:{}".format(port))
        self.listen()

    def listen(self):
        print('listening...')
        while True:
            request = self.socket.recv_json()
            if request['op'] == 'newClient':
                self.addNewClient(request)
            elif request['op'] == 'getListOfClients':
                self.getListOfClients()
            elif request['op'] == 'callRequest':
                self.callRequest(request)
            elif request['op'] == 'sendVoiceMessage':
                self.sendVoiceMessage(request)
            elif request['op'] == 'listActiveGroupCalls':
                self.listActiveGroupCalls(request)
            elif request['op'] == 'joinToGroupCall':
                self.joinToGroupCall(request)
            elif request['op'] == 'startGroupCall':
                self.startGroupCall(request)
            else:
                print('Invalid operation')

    def listActiveGroupCalls(self, request):
        print('\nServing list of all active group calls')
        self.socket.send_string(str(list(self.groups.keys())))
        print('served.')

    def joinToGroupCall(self, request):
        clientName = request['name']
        groupName = request['group']
        clientPort = request['port']
        clientIp = request['ip']
        print('\nTrying to join {} to {} call'.format(clientName, groupName))
        if groupName in self.groups:
            self.socket.send_string('YES')
            # Say to all participants to subscribe the new client
            clientsInCall = list(self.groups[groupName].keys())
            for name in clientsInCall:
                cl_sc = self.groups[groupName][name][0]
                cl_sc.send_json({
                    'op': 'subscribeToClient',
                    'name': clientName,
                    'ip': clientIp,
                    'port': clientPort
                })
            # Adds the new client to the group call
            self.groups[groupName][clientName] = self.clients[clientName]
            print('SUCCESSFULLY JOINED.')
        else:
            print("THE CALL DOESNT EXIST")
            self.socket.send_string('NO')

    def startGroupCall(self, request):
        print('\nStarting a group call')
        self.groups[request['name'] + "'s_call"] = {
            request['name']: self.clients[request['name']]
        }
        self.socket.send_string('ok')
        client_sc = self.clients[request['name']][0]
        client_sc.send_json({ 'op': 'serveGroupCall' })
        client_sc.recv_string()
        print('Group call started.')

    def addNewClient(self, request):
        print('\nAdding a new client: {}'.format(request['name']))
        Server.PORT_COUNTER += 1
        ip = request['ip']
        sc = self.context.socket(zmq.REQ)
        sc.connect("tcp://{}:{}".format(request['ip'], Server.PORT_COUNTER))
        self.clients[request['name']] = (sc, ip, Server.PORT_COUNTER)
        self.socket.send_string(str(Server.PORT_COUNTER))
        print('{} added.'.format(request['name']))

    def getListOfClients(self):
        print('\nServing list of clients.')
        self.socket.send_string(str(list(self.clients.keys())))
        print('served.')

    def callRequest(self, request):
        print('\nDoing call request')
        _to = self.clients[request['to']]
        _from = self.clients[request['from']]
        _to[0].send_json({'op': 'callRequest', 'from': request['from']})
        response = _to[0].recv_string()
        self.socket.send_string(response)
        if (response == '1'):
            _to[0].send_json(
                {
                    'op':   'startCall',
                    'ip':   _from[1],
                    'port': _from[2]
                })
            _to[0].recv_string()
            _from[0].send_json(
                {
                    'op':  'startCall',
                    'ip':   _to[1],
                    'port': _to[2]
                })
            _from[0].recv_string()
        else:
            print('call rejected')
            print('done.')

    def sendVoiceMessage(self, request):
        print('\nSending voice message')
        to = self.clients[request['to']][0]
        to.send_json(request)
        to.recv_string()
        self.socket.send_string('ok')
        print('sent.')

if __name__ == '__main__':
    port = input('\nEnter the listen port: ')
    server = Server()
    server.start(port)

