import zmq
from voice_chat_server import VoiceChatServer


def main():
    context = zmq.Context()
    main_socket = context.socket(zmq.REP)
    main_socket.bind("tcp://*:5555")
    voiceChatServer = VoiceChatServer(main_socket)
    voiceChatServer.Start()

if __name__ == '__main__':
    main()
