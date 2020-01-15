#!/usr/bin/python3
import socket
import struct
import random
import sys
import time
from threading import Timer
import datetime
import select

ACK = 4
DATA = 3
ERROR = 5
LAST_ACK = 7
SOCKET_DICT = {}
READ_READY = []
WRITE_READY = []
ORIGIN_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
UDP_IP = "0.0.0.0"
INIT_PORT = int(sys.argv[1])
SUCCESS = 1
ERROR_RECEIVED = -1
ERROR_UNDEFINED = 1000
ERROR_FILE_NOT_FOUND = 1001
ERROR_ACCESS = 1002
ERROR_DISK_FULL = 1003
ERROR_ILLEGAL_TFTP = 1004
ERROR_UNKNOWN_ID = 1005
ERROR_FILE_EXISTS = 1006
ERROR_NO_USR = 1007
tid_array = [INIT_PORT]


class SocketInfo:
    def __init__(self, address=None, block_num=0, file_name=None, file_position=0, timer=Timer(0.0, None),
                data_out="", data_in=b"", out_type=None, retransmissions=int(sys.argv[3]), is_timeout=0, is_finished=0, error_code=0):
        self.name = "Socket " + str(random.randint(0, 15))
        self.address = address
        self.block_nun = block_num
        self.file_name = file_name
        self.data_out = data_out
        self.data_in = data_in
        self.retransmissions = retransmissions
        self.is_timeout = is_timeout
        self.out_type = out_type
        self.timer = timer
        self.file_position = file_position
        self.is_finished = is_finished
        self.error_code = error_code


def timeout_handler(timed_out_socket):
    READ_READY.remove(timed_out_socket)
    info = SOCKET_DICT[timed_out_socket]
    info.timer.cancel()
    print (info.name, "is timed out!", datetime.datetime.now())
    if info.retransmissions == 0:
        print (info.name, "is Closed for multiple timeouts")
        close_socket(timed_out_socket, timed_out_socket.getsockname()[1])
        return None
    info.retransmissions -= 1
    WRITE_READY.append(timed_out_socket)


def initiate_timer(t_socket):
    info = SOCKET_DICT[t_socket]
    info.timer = Timer(int(sys.argv[2]), timeout_handler, [t_socket])
    info.timer.start()
    print("Timer for", info.name, "started:", datetime.datetime.now())


# returns the Meaning of an Error code
def error_string(code):
    switcher = {
        0: "Undefined Error.",
        1: "File not found.",
        2: "Access violation.",
        3: "Disk full or allocation exceeded.",
        4: "Illegal TFTP operation.",
        5: "Unknown transfer ID.",
        6: "File already exists.",
        7: "No such user."
    }
    return switcher.get(code)

    # get() method of dictionary data type returns
    # value of passed argument if it is present
    # in dictionary otherwise second argument will
    # be assigned as default value of passed argument


# sends Error packet with the correct code & Meaning
def error_handler(socket_name):  # Courtesy, no use for try & exception
    code = SOCKET_DICT[socket_name].out_type % 1000
    addr = SOCKET_DICT[socket_name].address
    SOCKET_DICT[socket_name].is_finished = 1
    error_str = bytes(error_string(code), 'ascii')
    string_length = str(len(error_str))
    print(code)
    try:
        socket_name.sendto(struct.pack('>hh' + string_length + 'sx'.format(len(error_str)), 5, code, error_str), addr)
    except socket.error as e:
        print ("Had an error and failed sending error message to client")


def establish_connection(bytes_data, address):
    tid = random.randint(3000, 65535)
    while tid in tid_array:
        tid = random.randint(3000, 65535)  # check server and client doesnt have same port
    tid_array.append(tid)
    code = struct.unpack_from('>h', bytes_data[:2])
    code = code[0]
    bytes_data = bytes_data[2:]
    data_arr = bytes_data
    data_arr = data_arr.split(b'\x00')
    file_name, mode = struct.unpack('>{}sx{}sx'.format(len(data_arr[0]), len(data_arr[1])), bytes_data)
    if code == 1:
        out_action = DATA
        print("Reading from server process")
    elif code == 2:
        out_action = ACK
        print("Writing to server process")
    else:
        return ERROR_ILLEGAL_TFTP, tid, None
    print('Connection Establishment success! tid - ', tid)
    return out_action, tid, file_name.decode('ascii')


def data_pack(block, send_data, bytes_len):
    form = '>hh'+str(bytes_len)+'s'
    return struct.pack(form, 3, block, send_data)


def aka_response(curr_socket):
    info = SOCKET_DICT[curr_socket]
    try:
        curr_socket.sendto(struct.pack('>hh', 4, info.block_nun), info.address)
    except socket.error as e:
        print(str(e))
        info.out_type = ERROR
        info.error_code = ERROR_UNDEFINED
        print ("socket aka error")
    print("Sent Ack")


def open_file(file_loc):
    try:
        with open(file_loc, "rb") as data_file:
            data_file.seek(0)
            data_out = data_file.read()
            data_file.close()
    except (OSError, IOError) as e:
        return ERROR_FILE_NOT_FOUND
    return data_out


def handle_receive(current_socket):
    info = SOCKET_DICT[current_socket]
    print ("my action is", info.out_type)
    new_data, addr = current_socket.recvfrom(516)
    info.timer.cancel()
    pack_size = len(new_data) - 4
    try:
        code, block, input_bytes = struct.unpack('>hh' + str(pack_size) + 's', new_data)
    except OSError as e:
        info.error_code = ERROR_ILLEGAL_TFTP
    print("Code is ", code, "block is", block)
    if code == 5:  # ERROR packet
        SOCKET_DICT[sock].is_finished = 1
    if code == 3:  # DATA packet
        print ("DATA packet")
        try:
            if addr != info.address:  # received message from a different usr
                print("error address")
                info.error_code = ERROR_NO_USR
                info.out_type = ERROR
                return
        except socket.error as e:
            print(str(e))
            info.error_code = ERROR_NO_USR
            info.out_type = ERROR
            print ("socket error")
            return
        try:
            code, block, input_bytes = struct.unpack('>hh'+str(pack_size)+'s', new_data)
        except OSError as e:
            info.out_type = ERROR_ILLEGAL_TFTP
            info.out_type = ERROR
            print ("pack error")
            return
        if block > info.block_nun + 1:
            info.out_type = ERROR_ILLEGAL_TFTP
            info.out_type = ERROR
            print ("block error")
            return
        elif block < info.block_nun + 1:
            return
        info.data_in += input_bytes
        print ("got", len(input_bytes), "bytes from block ", block)
        print ("pack size is", pack_size)
        info.block_nun = block
        if pack_size < 512:
            try:
                with open(info.file_name, "wb+") as data_file:
                    if data_file.mode == "wb+":
                        data_file.write(info.data_in)
                        data_file.close()
            except (OSError, IOError) as e:
                info.error_code = ERROR_DISK_FULL
                info.out_type = ERROR
                return
            print ("last DATA recieved")
            info.out_type = LAST_ACK
            return
    elif code == 4:  # ACK packet
        if block > info.block_nun:
            info.error_code = ERROR_ILLEGAL_TFTP
            info.out_type = ERROR
        elif block < info.block_nun:
            return
        else:
            info.block_nun += 1
            info.file_position += 512
    else:  # packet is not Data/ACK/ERROR packet
        info.error_code = ERROR_ILLEGAL_TFTP
        info.out_type = ERROR
    print ("my mode is", info.out_type)


def handle_send(curr_socket):
    info = SOCKET_DICT[curr_socket]
    if info.out_type == ACK:
        aka_response(curr_socket)
    elif info.out_type == LAST_ACK:
        aka_response(curr_socket)
        info.is_finished = 1
    elif info.out_type == DATA:
        if info.block_nun == 0:
            info.block_nun += 1
            info.data_out = open_file(info.file_name)
            if info.data_out == ERROR_FILE_NOT_FOUND:
                print("file not found")
                info.error_code = ERROR_UNDEFINED
                error_handler(curr_socket)
                return
            print("open success")
        if len(info.data_out) - info.file_position < 512:
            info.is_finished = 1
        send_data = info.data_out[info.file_position:info.file_position + 512]
        try:
            curr_socket.sendto(data_pack(info.block_nun, send_data, len(send_data)), info.address)   ##### we had a mistake fttp??
            print('Sent', len(send_data), 'bytes from block', info.block_nun)
        except socket.error as e:
            return ERROR_UNDEFINED   #### should save error to info???
        print("send success")
        if not info.is_finished:
            initiate_timer(curr_socket)
    else:
        print ("ERROR")
        error_handler(sock)
    print("BLOCK= ", info.block_nun)
    print("out - ", info.out_type)
    return SUCCESS


def close_socket(sock, tid):
    tid_array.remove(tid)
    del SOCKET_DICT[sock]
    sock.close()


try:
    ORIGIN_SOCKET.bind((UDP_IP, INIT_PORT))
except socket.error as e:
    print (e)
    print ("Error in initial original socket binding")
    quit()
READ_READY.append(ORIGIN_SOCKET)
while True:
    for socet in SOCKET_DICT:
        print ("socket", socet, "Address:", SOCKET_DICT[socet].address)
    print("TO WRITE:",WRITE_READY,"\nTO READ:", READ_READY)
    r_list, w_list, x_list = select.select(READ_READY, WRITE_READY,[] , 2)
    print("Write Ready: ")
    for sock in w_list:
        print(SOCKET_DICT[sock].name)
    print("Read Ready: ")
    for sock in r_list:
        if sock != ORIGIN_SOCKET:
            print(SOCKET_DICT[sock].name)
    for sock in w_list:
        handle_send(sock)
        print("handle success")
        WRITE_READY.remove(sock)
        if SOCKET_DICT[sock].is_finished:
            close_socket(sock, sock.getsockname()[1])
            print("Socket ", sock, " is Done!")
        else:
            READ_READY.append(sock)
    for sock in r_list:
        if sock == ORIGIN_SOCKET:
            data, address = ORIGIN_SOCKET.recvfrom(516)
            action, tid, file_name = establish_connection(data, address)
            new_socket_info = SocketInfo()
            new_socket_info.out_type, new_socket_info.address, new_socket_info.file_name = action, address, file_name
            WRITE_READY.append(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
            try:
                new_socket = WRITE_READY[-1]
                new_socket.bind((UDP_IP, tid))
            except socket.error as e:
                print ('Error while binding')
                WRITE_READY.remove(socket)
            SOCKET_DICT[WRITE_READY[-1]] = new_socket_info
        else:
            handle_receive(sock)
            READ_READY.remove(sock)
            if SOCKET_DICT[sock].is_finished:
                SOCKET_DICT[sock].timer.cancel()
                close_socket(sock, sock.getsockname()[1])
                print("Socket ", sock, " is Done!")
            else:
                WRITE_READY.append(sock)
    print("\n\n")
# 








