import zmq
import sys
import os
import math

FILE_CHUNK_MARK = 1048576

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
            with open(sys.argv[1]+msg['file'], 'rb') as input:
                data = input.read()
                s.send(data)
                input.close()

        elif msg['op'] == 'download_by_parts':
            with open(sys.argv[1] + '/' + msg['file'], 'rb') as input:
                input.seek(0,2)
                parts = math.ceil(input.tell() / FILE_CHUNK_MARK)
            s.send_json({
                'op': 'download_by_parts',
                'parts': parts
            })
            input.close()
            
        elif msg['op'] == 'download_part':
            fileName = msg['file']
            part = msg['part']
            print('Sending', fileName, 'part', part)
            with open(sys.argv[1] + '/' + msg['file'], 'rb') as input:
                pos = math.floor(part/FILE_CHUNK_MARK)
                input.seek(pos)
                data = input.read(FILE_CHUNK_MARK)
                s.send(data)
                input.close()

if __name__ == '__main__' :
    main()    