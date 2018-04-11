import zmq


class Server:

    PORT_COUNTER = 4000

    def __init__(self):
        self.context = zmq.Context()
        self.clients = {}
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
            else:
                print('Invalid operation')

    def addNewClient(self, request):
        print('Adding a new client: {}'.format(request['name']))
        Server.PORT_COUNTER += 1
        ip = request['ip']
        sc = self.context.socket(zmq.REQ)
        sc.connect("tcp://{}:{}".format(request['ip'], Server.PORT_COUNTER))
        self.clients[request['name']] = (sc, ip, Server.PORT_COUNTER)
        self.socket.send_string(str(Server.PORT_COUNTER))
        print('{} added.'.format(request['name']))

    def getListOfClients(self):
        print('Serving list of clients.')
        self.socket.send_string(str(list(self.clients.keys())))
        print('served.')

    def callRequest(self, request):
        print('Doing call request')
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
        print('Sending voice message')
        to = self.clients[request['to']][0]
        to.send_json(request)
        to.recv_string()
        self.socket.send_string('ok')
        print('sent.')

if __name__ == '__main__':
    port = input('Enter the port listen port: ')
    server = Server()
    server.start(port)

