import zmq
import os
import socket
import threading
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100


class Client:

    PORT_MAYBE = 5000

    def __init__(self, name):
        self.context = zmq.Context()
        self.server_sc = self.context.socket(zmq.REQ)
        self.name = name
        self.group = []
        self.__BUSY = False
        self.__ACCEPTCALLS = False

    def start(self, server_ip, server_port):
        self.server_sc.connect("tcp://{}:{}".format(server_ip, server_port))
        current_ip = self.getMyIp()
        self.server_sc.send_json(
            {
                'op':   'newClient',
                'name': self.name,
                'ip':   current_ip
            }
        )
        port = self.server_sc.recv_string()
        threading.Thread(target=self.listen, args=[port]).start()
        self.printOptions()

    def getMyIp(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    def listen(self, port):
        print('Listening for calls on port {}'.format(port))
        socket = self.context.socket(zmq.REP)
        socket.bind("tcp://*:{}".format(port))
        pyAudio = pyaudio.PyAudio()
        stream = pyAudio.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              output=True,
                              frames_per_buffer=CHUNK)
        while True:
            request = socket.recv_json()
            if request['op'] == 'sendVoiceMessage':
                print('Voice message recieved. Playing...')
                for audio in request['audio']:
                    stream.write(audio.encode('UTF-16', 'ignore'))
                socket.send_string('ok')
                print('played.')
            elif request['op'] == 'callRequest':
                print('Incoming call from: {}'.format(request['from']))
                if self.__ACCEPTCALLS:
                    socket.send_string('1')
                else:
                    socket.send_string('0')
                print('accepted.' if self.__ACCEPTCALLS else 'rejected.')
            elif request['op'] == 'startCall':
                if self.__BUSY:
                    print("I'M IS BUSY IN ANOTHER CALL")
                else:
                    self.__BUSY = True
                    client = self.context.socket(zmq.REQ)
                    client.connect(
                        "tcp://{}:{}".format(request['ip'], request['port']))
                    socket.send_string('ok')
                    threading.Thread(target=self.recordAndSend, args=[client]).start()
            elif request['op'] == 'activeCallAudio':
                socket.send_string('ok')
                stream.write(request['audio'].encode('UTF-16', 'ignore'))
            elif request['op'] == 'serveGroupCall':
                self.__ACCEPTCALLS = False
                self.__BUSY = True
                socket.send_string('ok')
            elif request['op'] == 'subscribeToClient':
                threading.Thread(target=self.subscribeToClient, args=[request]).start()
                socket.send_string('ok')
            else:
                print('invalid request recieved.')
        stream.stop_stream()
        stream.close()
        pyAudio.terminate()

    def clearScreen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def subscribeToClient(self, request):
        socket = self.context.socket(zmq.SUB)
        socket.bind("tcp://{}:{}".format(request['ip'], request['port']))
        socket.setsockopt_string(zmq.SUBSCRIBE, '1')
        pyAudio = pyaudio.PyAudio()
        stream = pyAudio.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              output=True,
                              frames_per_buffer=CHUNK)
        while True:
            data = socket.recv_string()
            print('Data Recieved')
            code, audio = data.split()
            stream.write(audio.encode('UTF-16', 'ignore'))
            print('Audio played')

    def requestClientsList(self):
        self.server_sc.send_json({'op': 'getListOfClients'})
        response = self.server_sc.recv_string()
        return response

    def sendVoiceMessage(self):
        to = input("Enter the user's name to send the message: ")
        pyAudio = pyaudio.PyAudio()
        frames = []

        def callback(in_data, frame_count, time_info, status):
            frames.append(in_data.decode('UTF-16', 'ignore'))
            return (in_data, pyaudio.paContinue)

        stream = pyAudio.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              input=True,
                              stream_callback=callback)
        stream.start_stream()
        input('Press <enter> to stop recording.')
        stream.stop_stream()
        stream.close()
        pyAudio.terminate()
        self.server_sc.send_json(
            {
                'op': 'sendVoiceMessage',
                'audio': frames,
                'to': to
            }
        )
        self.server_sc.recv_string()
        return 'Message has been sent.'

    def requestCall(self):
        to = input("User's name to call: ")
        self.server_sc.send_json(
            {
                'op': 'callRequest',
                'to': to,
                'from': self.name
            }
        )
        response = self.server_sc.recv_string()
        if (response == '1'):
            result = 'Call accepted'
        else:
            result = 'Call rejected'
        return result

    def recordAndSend(self, client):
        pyAudio = pyaudio.PyAudio()
        stream = pyAudio.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              input=True,
                              frames_per_buffer=CHUNK)
        while True:
            audio = stream.read(CHUNK)  # exception_on_overflow ?
            client.send_json(
                {
                    'op': 'activeCallAudio',
                    'audio': audio.decode('UTF-16', 'ignore')
                }
            )
            client.recv_string()

        stream.stop_stream()
        stream.close()
        pyAudio.terminate()

    def printOptions(self, callbackString=None):
        self.clearScreen()
        if callbackString:
            print("\n\n{}\n\n".format(callbackString))

        print("1. Clients list")
        print("2. Send Voice Message")
        print("3. Start Call")

        if not self.__ACCEPTCALLS:
            print("4. Start accepting calls")
        else:
            print("4. Stop accepting calls")
        
        print("\n") 
        print("5. List all active group calls")
        print("6. Join to group call")
        print("7. Start a group call")

        option = input('Choose one: ')
        if option == '1':
            clients = self.requestClientsList()
            return self.printOptions(clients)
        elif option == '2':
            result = self.sendVoiceMessage()
            return self.printOptions(result)
        elif option == '3':
            result = self.requestCall()
            return self.printOptions(result)
        elif option == '4':
            self.__ACCEPTCALLS = not self.__ACCEPTCALLS
            message = "Now accepting calls" if self.__ACCEPTCALLS else "Not accepting calls"
            return self.printOptions(message)
        elif option == '5':
            result = self.requestListOfActiveGroups()
            return self.printOptions(result)
        elif option == '6':
            result = self.joinToGroupCall()
            return self.printOptions(result)
        elif option == '7':
            result = self.startGroupCall()
            return self.printOptions(result)
        else:
            return self.printOptions('-- INVALID OPTION !!.')
    
    def requestListOfActiveGroups(self):
        self.server_sc.send_json({
            'op': 'listActiveGroupCalls'
        })
        response = self.server_sc.recv_string()
        return response

    def joinToGroupCall(self):
        groupName = input('Enter the group name to join: ')
        Client.PORT_MAYBE += 5
        my_port = Client.PORT_MAYBE
        my_ip = self.getMyIp()
        self.server_sc.send_json({
            'op': 'joinToGroupCall',
            'group': groupName,
            'name': self.name,  # My name
            'port': my_port,  # My port
            'ip': my_ip  # My IP 
        })
        response = self.server_sc.recv_string()
        if response == 'NO':
            return "THAT GROUP CALL DONT EXIST."
        else:
            threading.Thread(target=self.startBroadcastingCall, args=[my_ip, my_port]).start()
            input('Press <enter> to exit.')
            return "Call finished."

    def startBroadcastingCall(self, ip, port):
        pub_sc = self.context.socket(zmq.PUB)
        pub_sc.bind('tcp://*:{}'.format(port))

        pyAudio = pyaudio.PyAudio()
        stream = pyAudio.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              input=True,
                              frames_per_buffer=CHUNK)
        while True:
            audio = stream.read(CHUNK)
            print('Audio recorded')
            pub_sc.send_string("%i %s" % (1, audio.decode('UTF-16', 'ignore')))
            print('Audio sended')
        stream.stop_stream()
        stream.close()
        pyAudio.terminate()

    def startGroupCall(self):
        if self.__BUSY:
            return('YOU ARE BUSY')

        self.server_sc.send_json({
            'op': 'startGroupCall',
            'name': self.name,
        })
        self.server_sc.recv_string()
        print('YOU ARE IN A GROUP CALL')
        input('Press <enter> to finish the call')
        return "Call finished"


if __name__ == '__main__':
    name = input('Enter your nickname: ')
    server_ip = input('Enter the server ip: ')
    server_port = input('Enter the server port: ')
    client = Client(name)
    client.start(server_ip, server_port)
