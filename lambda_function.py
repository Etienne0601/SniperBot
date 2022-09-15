import json
import uuid
import os
import boto3
import datetime
from dotenv import load_dotenv
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

load_dotenv()

PUBLIC_KEY = os.getenv('PUBLIC_KEY')

PING_PONG = {"type": 1}

dynamodb = boto3.client('dynamodb')

def verify_signature(event):
    raw_body = event.get("rawBody")
    auth_sig = event['params']['header'].get('x-signature-ed25519')
    auth_ts  = event['params']['header'].get('x-signature-timestamp')
    
    message = auth_ts.encode() + raw_body.encode()
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
    verify_key.verify(message, bytes.fromhex(auth_sig)) # raises an error if unequal

def ping_pong(body):
    if body.get("type") == 1:
        return True
    return False


def process_snipe(evnt_body):
    current_time = str(datetime.datetime.now(datetime.timezone.utc))
    recorded_snipeids = []
    for option in evnt_body['data']['options']:
        snipe_id = str(uuid.uuid4())
        recorded_snipeids.append(snipe_id)
        dynamodb.put_item(TableName='Snipes',
            Item={
                'SnipeId':{'S':snipe_id},
                'SniperId':{'S':evnt_body['member']['user']['id']},
                'SnipeeId':{'S':option['value']},
                'DateTime':{'S':current_time},
                'Voided':{'BOOL':False}
            }
        )
    
    message = "Entry recorded with SnipeId(s)"
    for snipe_id in recorded_snipeids:
        message += ", " + snipe_id
    
    return {
        "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
        "data": {
            "tts": False,
            "content": message,
            "embeds": [],
            "allowed_mentions": []
        }
    }


def lambda_handler(event, context):
    print("Processing event...")
    print(f"event {event}") # debug print
    
    # verify the signature
    try:
        verify_signature(event)
    except Exception as e:
        raise Exception(f"[UNAUTHORIZED] Invalid request signature: {e}")

    # check if message is a ping
    body = event.get('body-json')
    if ping_pong(body):
        return PING_PONG
    
    
    # TODO: logic goes here
    operation = event['body-json']['data']['name']
    
    
    if operation == "snipe-leaderboard":
        # return get_top(message)
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": "TODO snipe-leaderboard",
                "embeds": [],
                "allowed_mentions": []
            }
        }
    elif operation == "snipe-rank":
        # return get_own_rank(message)
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": "TODO snipe-rank",
                "embeds": [],
                "allowed_mentions": []
            }
        }
    elif operation == "snipe":
        return process_snipe(event['body-json'])
    else:
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": "TODO something went wrong",
                "embeds": [],
                "allowed_mentions": []
            }
        }
