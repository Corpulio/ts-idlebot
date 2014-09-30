"""
Teamspeak auto-idle mover script
"""

import ConfigParser
import re
import select
import socket
import sys
import time

def sec2hm(seconds):
    return_string = []
    h = int(seconds/3600)
    m = int((seconds - h*3600)/60)
    hour_string = 'hour' if h == 1 else 'hours'
    minute_string = 'minute' if m == 1 else 'minutes'
    if h > 0:
        return_string.append('%d %s' % (h, hour_string))
    if m > 0:
        return_string.append('%d %s' % (m, minute_string))
    return ", ".join(return_string)

if len(sys.argv) < 2:
    print "Syntax: ts-idlebot.py <config file>"
    sys.exit(1)

c = ConfigParser.RawConfigParser()
c.readfp(open(sys.argv[1]))

host = c.get('idlebot', 'host')
port = c.getint('idlebot', 'port')
virtual_server = c.get('idlebot', 'virtual_server')
username = c.get('idlebot', 'admin_username')
password = c.get('idlebot', 'admin_password')
client_nickname = c.get('idlebot', 'client_nickname')
defined_afk_threshold_ms = c.getint('idlebot', 'afk_timeout_seconds') * 1000
target_afk_channel = c.getint('idlebot', 'target_channel_id')
afk_plaintext_message = c.get('idlebot', 'afk_plaintext_message')
afk_movement_message = re.sub(' ', '\\\s', re.sub('%time%', sec2hm(c.getint('idlebot', 'afk_timeout_seconds')), c.get('idlebot', 'afk_plaintext_message')))
afk_channel_ids = [id for id in c.get('idlebot', 'afk_channel_ids')]
debug = True if c.getint('idlebot', 'debug') == 1 else False

def _readsocket(socket):
    buffer = ""
    terminate = False
    while not terminate:
        try:
            (rlist, wlist, xlist) = select.select([socket], [], [], 1)
            if len(rlist) == 0:
                if len(buffer) == 0:
                    print "Expected something, but got nothing"
                    socket.close()
                else:
                    return buffer

            temp_buffer = socket.recv(4096)

            if len(temp_buffer) == 0:
                return buffer

            buffer = buffer + temp_buffer
        except:
            print "Communication error occurred (recv)"
            socket.close()
            return ""
    return buffer

def _writesocket(socket, data):
    try:
        socket.send(data)
        return True
    except:
        print "Communication error occurred (send)"
        socket.close()
        return False

def _closesocket(socket):
    try:
        socket.close()
        return True
    except:
        print "Couldn't close the socket for some reason"
        return False

def move_afkers():
    already_afk_nicks = []
    afk_client_ids = []
    new_afkers = []
    not_afkers = []

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    header = _readsocket(s)
    if "specific command" not in header:
        print "Failed to connect for some reason"
        return False

    _writesocket(s, "login {0} {1}\r\n".format(username, password))
    login_status = _readsocket(s)
    if "error id=0 msg=ok" not in login_status:
        print "Error logging in as {0}".format(username)
        return False

    _writesocket(s, "use sid={0}\r\n".format(virtual_server))
    sid = _readsocket(s)
    if "error id=0 msg=ok" not in sid:
        print "Error selecting virtual server"
        return False

    _writesocket(s, "clientupdate client_nickname={0}\r\n".format(client_nickname))
    nick_update = _readsocket(s)
    if "error id=0 msg=ok" not in nick_update:
        print "Error setting client nickname"
        return False

    _writesocket(s, "clientlist -times\r\n")
    clientinfo = _readsocket(s)
    if (len(clientinfo) == 0):
        print "Error getting client idle time info"
        return False

    else:
        clients = clientinfo.split('|')
        for item in clients:
            # actual client
            if 'client_type=0' in item:
                client_is_afk = False
                for channel_id in afk_channel_ids:
                    if 'cid={0}'.format(channel_id) in item:
                        client_is_afk = True
                # already afk
                if client_is_afk:
                    client_subset = item.split()
                    for subitem in client_subset:
                        if 'client_nickname' in subitem:
                            heading, nick = subitem.split('=')
                            nick = re.sub('\\\s', ' ', nick)
                            already_afk_nicks.append(nick)
                # anywhere else
                else:
                    client_subset = item.split()
                    for subitem in client_subset:
                        if 'client_nickname' in subitem:
                            heading, nick = subitem.split('=')
                            nick = re.sub('\\\s', ' ', nick)
                        if 'client_idle_time' in subitem:
                            heading, client_idle_time = subitem.split('=')
                        if 'clid' in subitem:
                            heading, client_id = subitem.split('=')
                    if nick is None or client_idle_time is None or client_id is None:
                        continue
                    else:
                        if debug:
                            print "{0} has been idle for {1} ms".format(nick, client_idle_time)
                        if int(client_idle_time) > defined_afk_threshold_ms:
                            afk_client_ids.append(client_id)
                            new_afkers.append(nick)
                        else:
                            not_afkers.append(nick)

        if debug:
            print "Already AFK: %s" % ", ".join(sorted(already_afk_nicks))
            print "Not idle: %s" % ", ".join(sorted(not_afkers))
            print "Idle and ready to move: %s" % ", ".join(sorted(new_afkers))

        for client_id in afk_client_ids:
            if debug:
                print "Messaging client ID {0} and moving to AFK channel".format(client_id)
            _writesocket(s, "sendtextmessage targetmode=1 target={0} msg={1}\r\n".format(client_id, afk_movement_message))
            message_status = _readsocket(s)
            if "error id=0 msg=ok" not in message_status:
                print "Error messaging client {0}, continuing anyway".format(client_id)
            
            _writesocket(s, "clientmove clid={0} cid={1}\r\n".format(client_id, target_afk_channel))
            move_status = _readsocket(s)
            if "error id=0 msg=ok" not in move_status:
                print "Error moving client {0}".format(client_id)

        _closesocket(s)

if __name__ == '__main__':
    move_afkers()
