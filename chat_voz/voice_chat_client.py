from urllib.request import urlopen
import sys
import os
import pyaudio
import wave
import threading
import json
import zmq
import socket

FILE_CHUNK_MARK = 512 # 0.5KB
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
ACCEPTCALLS = False

def RecordAndSend(server, reciever):
    pyAudio = pyaudio.PyAudio()
    stream = pyAudio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=FILE_CHUNK_MARK)
    while True:
        print('Recording...')
        audio = stream.read(FILE_CHUNK_MARK)
        print('Sending')
        server.send_json(
            {
                'op': 'ActiveCallAudio',
                'reciever': reciever,
                'audio': audio.decode('UTF-16', 'ignore')
            })
        print('sendend')
        server.recv_json()
        print('callback recieved')
    stream.stop_stream()
    stream.close()
    pyAudio.terminate()


def Listen(server_sc, self_sc):
    print('Thread listening for calls...')
    pyAudio = pyaudio.PyAudio()
    stream = pyAudio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=FILE_CHUNK_MARK)
    while True:
        request = self_sc.recv_json()
        if request['op'] == 'IncomingCall':
            print('\n\n*** Incomming call from {} ***'.format(request['from']))
            if ACCEPTCALLS:
                print('Accepting the call...')
                accept = True
            else:
                print('Rejecting the call...')
                accept = False
            if accept:
                self_sc.send_json({ 'op': 'CallAccepted' })
                print('THE CALL HAS STARTED.')
                threading.Thread(target=RecordAndSend, args=[server_sc, request['from']]).start()
            else:
                self_sc.send_json({'op': 'CallRejected'})
        elif request['op'] == 'ActiveCallAudio':
            print('Downloading...')
            self_sc.send_json('ok')
            print('Playing')
            audio = request['audio'].encode('UTF-16', 'ignore')
            stream.write(audio)
            print('Played')
        stream.stop_stream()
        stream.close()
        pyAudio.terminate()


class VoiceChatClient:

    def __init__(self, client_name, server_ip, server_port):
        self.context = zmq.Context()
        self.server_sc = self.context.socket(zmq.REQ)
        self.server_sc.connect("tcp://{}:{}".format(server_ip, server_port))
        self.name = client_name
        self.ip = self.__getClientIp()

    def __getClientIp(self):
        #print("Fetching client ip...")
        #client_ip = json.load(urlopen('http://jsonip.com'))['ip']
        #print("Your ip: {}".format(client_ip))
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
        # return socket.gethostbyname(socket.gethostbyname())

    def Start(self):
        self.server_sc.send_json(
            {
                'op': 'NewClient',
                'name': self.name,
                'ip': self.ip
            }
        )
        response = self.server_sc.recv_json()
        self.CheckResponse(response, 'port')
        # Listen for calls
        port = response['port']
        self_sc = self.context.socket(zmq.REP)
        self_sc.bind("tcp://*:{}".format(port))
        threading.Thread(target = Listen, args = [self.server_sc, self_sc]).start()
        self.ThrowOptions()

    def ThrowOptions(self, callbackString = None):
        self.__clearScreen()
        if callbackString: print("\n\n{}\n\n".format(callbackString))
        print("1. Clients list")
        print("2. Send Voice Message")
        print("3. Start Call")
        global ACCEPTCALLS
        if not ACCEPTCALLS:
            print("4. Start accepting calls")
        else: print("4. Stop accepting calls")
        option = input('Choose one: ')
        if option == '1':
            clients = self.RequestClientsList()
            return self.ThrowOptions(clients)
        elif option == '2':
            self.SendVoiceMessage()
        elif option == '3':
            result = self.StartCall()
            return self.ThrowOptions(result)
        elif option == '4':
            ACCEPTCALLS = not ACCEPTCALLS
            if ACCEPTCALLS: message = "Now accepting calls"
            else: message = "Not accepting calls"
            return self.ThrowOptions(message)
        else:
            return self.ThrowOptions('-- INVALID OPTION !!.')

    def RequestClientsList(self):
        self.server_sc.send_json({ 'op': 'GetListOfClients' })
        response = self.server_sc.recv_json()
        self.CheckResponse(response, 'clients')
        return response['clients']

    def StartCall(self):
        userToCall = input("User's name to call: ")
        self.server_sc.send_json(
            {
                'op': 'Call',
                'emitter': self.name,
                'receiver': userToCall
            })
        response = self.server_sc.recv_json()
        self.CheckResponse(response, 'response')
        if response['response'] == 'rejected':
            return 'The call was rejected...'
        else:
            print('\nTHE CALL HAS STARTED.')
            threading.Thread(target=RecordAndSend, args=[self.server_sc, userToCall]).start()
            input('Press <enter> in any moment to finish the call.\n')


    def SendVoiceMessage(self):
        pass

    def CheckResponse(self, response, needed_key):
        if response['op'] == 'result':
            if response['result'] == 'ok':
                if needed_key in response:
                    return
                else:
                    raise Exception('Server didnt send the expected key')
            elif response['result'] == 'error':
                if 'error' in response:
                    raise Exception(response['error'])
                else:
                    raise Exception('An error has occurred in server')
            else:
                raise Exception('Unexpected response from server.')

    def __clearScreen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
