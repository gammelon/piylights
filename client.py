import socket

#hostname = input("enter hostname: ")
hostname = "localhost"
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.connect((hostname, 12345))

while True:
    message = input("\n#")
    if message == "quit":
        sock.close()
        quit()
    sock.sendall(bytes(message, "utf-8"))
    data = sock.recv(1024)
    print("\n" + str(data,"utf-8"))
