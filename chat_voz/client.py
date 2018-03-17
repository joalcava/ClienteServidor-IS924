import zmq
import sys
from voice_chat_client import VoiceChatClient

def main():
    print (sys.argv)
    client = VoiceChatClient(sys.argv[1], sys.argv[2], sys.argv[3])
    client.Start()

if __name__ == '__main__':
    main()