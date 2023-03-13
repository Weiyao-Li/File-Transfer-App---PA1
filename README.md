## Weiyao Li, wl2872 ##
# File-Transfer-App---PA1

The objective of this project is to implement a file transfer application with at least 3 clients and a server using both the TCP and UDP protocol where the overall system offers at least 10 unique files. The program have two modes of operation, one is the server, and the other is the client. The server instance is used to keep track of all the clients in the network along with their IP addresses and the files they are sharing. This information is pushed to clients and the client instances use these to communicate directly with each other to initiate file transfers. All server-client communication is done over UDP, whereas clients communicate with each other over TCP.

# Functionalities
Registration, File Offering, File Listing, File Transfer, De-registration, Testing
