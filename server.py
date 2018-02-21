import zmq
import sys
import os

FILE_CHUNK_MARK = 1024

def loadFiles(path):
    files = {}
    dataDir = os.fsencode(path)
    for file in os.listdir(dataDir):
        filename = os.fsdecode(file)
        print("Loading {}".format(filename))
        files[filename] = file
    return files

def listFiles():
    pass

def main():
    if len(sys.argv) != 2:
        print('Enter directory data')
        exit()
    # Read available files
    path = sys.argv[1]
    print("Serving files from {}".format(path))
    files = loadFiles(path)
    print("Load info on {} files.".format(len(files)))

    # Create the socket and the context
    context = zmq.Context()
    s = context.socket(zmq.REP)
    s.bind("tcp://*:5555")

    while True:
        msg = s.recv_json()
        if msg['op'] == 'list':
            s.send_json({"files": list(files.keys())})
        elif msg['op'] == 'download':
            with open(sys.arg[1]+msg['file'], 'rb') as input:
                data = input.read()
                s.send(data)
        elif ms['op'] == 'download_by_parts':
            pass

if __name__ == '__main__' :
    main()    