from ChatClient import ChatClient
from threading import Thread, Lock
import threading
import _thread
import time
import sys

chatMode = False
#placeholder value for clientID; should be explicitly set during log in
clientID = 0
destID = 0
# Forces client to wait for server response before initiating chat
servReqMutex = Lock()
# Use this to ensure main acquires servReqMutex when it is released
# This is a bit complicated but it works
servReqMutex2 = Lock()
# Client must wait for chat to end for new Log on to commence
# Release whenever Log off happens
newChatMutex = Lock()
receivedLogOff = False

def connectToServer():
    global client, msg
    client = ChatClient()
    #for testing
    #print(clientID)
    client.send('HELLO {0}'.format(clientID))
    msg = client.receive()  # Blocking. Waits for server response
    if msg == 'CONNECTED':
        print('Connected Successfully!')
        return True
    elif msg == 'DECLINED':
        print('Server failed to verify client.')
        return False

# Listens for CHAT_REQUEST or CHAT_STARTED
# Breaks once chat has started
def protocolListen(client):
    global chatMode, chatStarted
    while True:
        servReqMutex.acquire() #Ensures that client must wait for server response before starting chat
        #for testing
        #print('acquire in protocolListen')
        protocolMessage = client.receive()

        if 'CHAT_STARTED' in protocolMessage:
            chatMode = True
            destID = protocolMessage.split()[2]
            servReqMutex.release()
            #Echo the CHAT_STARTED message
            client.send(protocolMessage)
            enterChatMode(client, destID)
            #print('In chat started protocol')
            #should only stop listening once we receive CHAT_STARTED
            break
        elif 'UNREACHABLE' in protocolMessage:
            #for testing
            print('we unreachable bois')
            servReqMutex.release()
        #This is here to make sure this thread doesn't immediately acquire serReqMutex
        # so the main thread has a chance to acquire it
        servReqMutex2.acquire()
        servReqMutex2.release()
        # For testing
        #print('2 catch/release')

#Prints out incoming messages
def messageListen(client,destID):
    global receivedLogOff
    while True:
        receivedMessage = client.receive()

        if receivedMessage != "" and receivedMessage.split()[0] != "END_NOTIF":
            #Erases the current line, prints the new message, and reprints the input() message
            print("", end="\r")
            print("Client {0}: {1}".format(destID,receivedMessage))
            print("Client {0}: ".format(clientID), end="")
            sys.stdout.flush()
        #End the 
        elif receivedMessage.split()[0] == "END_NOTIF":
            print("", end="\r")
            print("Chat Ended")
            # We will receive this argument if 
            if len(receivedMessage.split()) == 2 and receivedMessage.split()[1] == "NOT_LOG_OFF":
                receivedLogOff = True
            client.close()
            newChatMutex.release()
            break

def enterChatMode(client,destID):
    global chatMode, receivedLogOff
    print('we in chatMode bois')
    messageListenThread = threading.Thread(target=messageListen,args=(client,destID))
    messageListenThread.start()
    print('\nChat started with client {0}. Type "Log Off" to end.'.format(destID))
    while chatMode:
        messageToSend = input('Client {0}: '.format(clientID))


        if messageToSend.capitalize().strip() == 'Log Off'.capitalize().strip():
            client.send("END_REQUEST")
            chatMode = False
            break
        elif receivedLogOff:
            receivedLogOff = False
            break
        

        client.send(messageToSend)

# TODO: figure out how to make this run multiple times
if __name__ == '__main__':

    while True:
        #for testing
        print("new loop can log in again")
        newChatMutex.acquire()
        #This will help enterChatMode thread exit when we receive a log off notification
        if receivedLogOff:
            print('Press enter to continue...')

        # This block waits for the log on command
        # Should enter 'Log on [clientID]
        command = input('Enter command like \"Log on [clientID]\": ')

        #Check if 'Log on' was entered
        while 'Log on' not in command.capitalize() or len(command.split()) != 3:
            command = input('You must enter Log on [Client ID] to continue: ')

        # Assumes clientID will be an int
        clientID = command.split()[2]

        #for testing clientID
        #print('we got da clientid {0}'.format(clientID))

        # If we send an invalid clientID, request a valid one til we get a connection
        while connectToServer() != True:
            clientID = input('Please enter a valid clientID: ')

        command = input('Would you like to send a chat request? (yes or no): ')

        # Now that we're connected, we start listening for CHAT_REQUESTs or CHAT_STARTEDs
        protocolListenThread = threading.Thread(target=protocolListen, args=(client,))
        protocolListenThread.start()

        if(command.capitalize() == 'Yes'):
            # Only loop this while chatMode is not activated
            # Waiting for chat initiation or request to chat from protocolListenThread
            while True:
                
                command = input('Enter chat request: ')
                destID = command.split()[1]
                #Let user know we are waiting on chat request response
                client.send('CHAT_REQUEST {0}'.format(destID))

                servReqMutex2.acquire()
                #for testing
                #print('acquire 2 in main')
                servReqMutex.acquire() # Waits for protocolListen to recieve confirmation that chat session has begun
                servReqMutex.release()

                if(chatMode):
                    break

                # If you get here then the Client is unreachable
                print('client {0} unreachable'.format(command.split()[1]))
                
                servReqMutex2.release()

        elif(command.capitalize() == 'No'):
            print('Awaiting chat request from another client')