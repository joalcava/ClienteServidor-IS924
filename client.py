import zmq
import sys

def printJson(json):
    pass

def main():
    if len(sys.argv) < 2:
        print('Enter operation')
        exit()
    # Create the socket and the context
    context = zmq.Context()
    s = context.socket(zmq.REQ)
    s.connect("tcp://localhost:5555")

    operation = sys.argv[1]
    if operation == 'list':
        s.send_json({'op': 'list'})
        files = s.recv_json()
        #printJson(files)
        print(files)
    elif operation == 'download':
        fileName = sys.argv[2]
        s.send_json({'op': 'download', 'file': fileName})
        file = s.recv()
        with open("down-" + operation, 'wb') as output:
            output.write(file)
    elif operation == 'download_by_parts':
        fileName = sys.argv[2]
        s.send_json(
            {
                'op': 'download_by_parts',
                'file': fileName
            }
        )
        fileData = s.recv_json()
        parts = fileData['parts']
        print('Downloading', parts, 'parts')
        for part in range(1, parts + 1):
            s.send_json(
                {
                    'op': 'download_part',
                    'file': fileName,
                    'part': part
                }
            )
            print('Downloading part', part)
            filePart = s.recv()
            with open("down-" + fileName, 'ab') as output:
                output.write(filePart)
                output.close()

if __name__ == '__main__':
    main()