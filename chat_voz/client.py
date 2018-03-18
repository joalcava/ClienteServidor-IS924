import zmq
import sys
import os
import socket
import threading
import pyaudio

context = zmq.Context()
server = context.socket(zmq.REQ)
name = ''
ACCEPTCALLS = False
BUSY = False
CHUNK = 1024 # 0.5KB
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100


def getMyIp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def main():
    global name
    name = sys.argv[1]
    server_ip = sys.argv[2]
    server_port = sys.argv[3]
    server.connect("tcp://{}:{}".format(server_ip, server_port))
    current_ip = getMyIp()
    server.send_json(
        {
            'op': 'newClient',
            'name': name,
            'ip': current_ip
        }
    )
    port = server.recv_string()
    threading.Thread(target=listen, args=[port]).start()
    printOptions()


def listen(port):
    print('Listening for calls...')
    socket = context.socket(zmq.REP)
    print(port)
    socket.bind("tcp://*:{}".format(port))
    pyAudio = pyaudio.PyAudio()
    stream = pyAudio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK)
    global BUSY
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
            if ACCEPTCALLS: socket.send_string('1')
            else: socket.send_string('0')
            print('accepted.' if ACCEPTCALLS else 'rejected.')
        elif request['op'] == 'startCall':
            if BUSY:
                print("I'M IS BUSY IN ANOTHER CALL")
            else:
                BUSY = True
                client = context.socket(zmq.REQ)
                client.connect("tcp://{}:{}".format(request['ip'], request['port']))
                socket.send_string('ok')
                threading.Thread(target=recordAndSend, args=[client]).start()
        elif request['op'] == 'activeCallAudio':
            socket.send_string('ok')
            stream.write(request['audio'].encode('UTF-16', 'ignore'))
        else:
            print('invalid request recieved.')
    stream.stop_stream()
    stream.close()
    pyAudio.terminate()


def clearScreen():
    os.system('cls' if os.name == 'nt' else 'clear')


def requestClientsList():
    server.send_json({'op': 'getListOfClients'})
    response = server.recv_string()
    return response


def sendVoiceMessage():
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
    server.send_json(
        {
            'op': 'sendVoiceMessage',
            'audio': frames,
            'to': to
        }
    )
    server.recv_string()
    return 'Message has been sent.'
    

def requestCall():
    to = input("User's name to call: ")
    server.send_json(
        {
            'op': 'callRequest',
            'to': to,
            'from': name
        }
    )
    response = server.recv_string()
    if (response == '1'):
        result = 'Call accepted'
    else:
        result = 'Call rejected'
    return result


def recordAndSend(client):
    pyAudio = pyaudio.PyAudio()
    stream = pyAudio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    while True:
        audio = stream.read(CHUNK, """exception_on_overflow=False""")
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


def printOptions(callbackString = None):
    clearScreen()
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
        clients = requestClientsList()
        return printOptions(clients)
    elif option == '2':
        result = sendVoiceMessage()
        return printOptions(result)
    elif option == '3':
        result = requestCall()
        return printOptions(result)
    elif option == '4':
        ACCEPTCALLS = not ACCEPTCALLS
        if ACCEPTCALLS: message = "Now accepting calls"
        else: message = "Not accepting calls"
        return printOptions(message)
    else:
        return printOptions('-- INVALID OPTION !!.')


if __name__ == '__main__':
    main()