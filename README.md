# File Transfer App #

## Weiyao Li, wl2872

### Server Side:
_python main.py -s 5000_

### Client Side:
1. **Registration:**\
**client1:** _python main.py -c Dave 127.0.0.1 5000 5008 5009_\
**client2:** _python main.py -c Alice 127.0.0.1 5000 5004 5005_\
**client3:** _python main.py -c Bob 127.0.0.1 5000 5002 5003_\
<br/>
2. **File Offering:**\
**Set Directory:** _setdir /Users/weiyaoli/Desktop/testdir (USE YOUR OWN TEST DIR)_<br/>
**Offer Files:** _offer file1.py file2.pdf file3.pdf (CREATE YOUR OWN TEST FILES)_<br/>
<br/>
3. onging...
### Project Objective:
Implement a file transfer application with at least 3 clients and a server using both the TCP and UDP protocol where the overall system offers at least 10 unique files. The program have two modes of operation, one is the server, and the other is the client. The server instance is used to keep track of all the clients in the network along with their IP addresses and the files they are sharing. This information is pushed to clients and the client instances use these to communicate directly with each other to initiate file transfers. All server-client communication is done over UDP, whereas clients communicate with each other over TCP.

### Functionalities
Registration, File Offering, File Listing, File Transfer, De-registration, Testing
