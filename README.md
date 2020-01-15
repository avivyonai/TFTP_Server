# TFTP_Server
a TFTP server
The Program is creating a different UDP sockets for every request it receives, when the socket that receives those request is ORIGIN_SOCKET which binds to the input port, and receives initial packets. It does not terminate by itself. All the others sockets are terminated when the process is finished.
The Program maintains at all times: SOCKET_DICT - a dictionary of socket:SocketInfo READ_LIST - the first list we pass to select WRITE_LIST - the second list we pass to select
Class SocketInfo:
Maintains the required data for each socket.
Program Flow
• TheProgrammainLoopisinitiatedafterORIGINAL_SOCKETisbindandonREAD_LIST
• TheFunctionestablish_connection(data) iscalledwhenselectreturnedORIGIN_SOCKET:
• creates a random TID (between 3000-65535)
• unpacks the first RRQ/WRQ Packet
• Returnsthekindofprocess,thenewrandomTIDandthefile_name
• Anewsocketiscreatedwhichbindstotheaddress(clients_ip,TID)
• TheSocketInfoofthenewsocketisupdated
• ThenewsocketisaddedtoSEND_LIST
• Thesendprocesscallshandle_send(socket)functionwhichhandlesthesendofeachready-to-sendsocket
according to its SocketInfo, and passes the socket to READ_LIST
• Whenasocketissentatimer(whichispartofitsSocketInfo)isinitiated.
• Thereceiveprocesscallshandle_receive(socket)functionwhichhandlesthereceiveofeachready-to-
receive socket according to its SocketInfo, and passes the socket to WRITE_LIST
• WhenasocketisreceivedthetimerinitsSocketInfoiscanceled.
• Aftereverysocketisbeinghandledbytheabovefunctionsitischeckedifthatsocketisfinishedandifsoit
closes.
