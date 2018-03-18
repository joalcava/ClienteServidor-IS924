import zmq
import sys

context = zmq.Context()
client_port_counter = 4000
clients = {}
socket = context.socket(zmq.REP)

def main():
    socket.bind("tcp://*:{}".format(sys.argv[1]))
    listen()

def listen():
    print('listening...')
    while True:
        request = socket.recv_json()
        if request['op'] == 'newClient':
            addNewClient(request)
        elif request['op'] == 'getListOfClients':
            getListOfClients()
        elif request['op'] == 'callRequest':
            callRequest(request)
        elif request['op'] == 'sendVoiceMessage':
            sendVoiceMessage(request)
        # elif request['op'] == 'ActiveCallAudio':
        #     activeCallAudio(request)
        else:
            print('Invalid operation')

def addNewClient(request):
    print('Adding a new client: {}'.format(request['name']))
    global client_port_counter
    client_port_counter += 1
    client_sc = context.socket(zmq.REQ)
    client_sc.connect("tcp://{}:{}".format(request['ip'], client_port_counter))
    clients[request['name']] = (client_sc, request['ip'], client_port_counter)
    socket.send_string(str(client_port_counter))
    print('{} added.'.format(request['name']))

def getListOfClients():
    print('Serving list of clients.')
    socket.send_string(str(list(clients.keys())))
    print('served.')

def callRequest(request):
    print('Doing call request')
    _to = clients[request['to']]
    _from = clients[request['from']]
    _to[0].send_json({'op': 'callRequest', 'from': request['from']})
    response = _to[0].recv_string()
    socket.send_string(response)
    if (response == '1'):
        _to[0].send_json({'op': 'startCall', 'ip': _from[1], 'port': _from[2]})
        _to[0].recv_string()
        _from[0].send_json({'op': 'startCall', 'ip': _to[1], 'port': _to[2]})
        _from[0].recv_string()
    else:
        print('call rejected')
    print('done.')

def sendVoiceMessage(request):
    print('Sending voice message')
    print('sent.')

# def activeCallAudio(request):
#     print('streaming call')
#     print('ok.')

if __name__ == '__main__':
    main()
