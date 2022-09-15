import json
import uuid
import os
import boto3
import datetime
import requests
from dotenv import load_dotenv
from prettytable import PrettyTable
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

load_dotenv()

PUBLIC_KEY = os.getenv('PUBLIC_KEY')
AUTH_HEADER = "Bot " + os.getenv('BOT_TOKEN')

PING_PONG = {"type": 1}

dynamodb = boto3.client('dynamodb')

def does_userid_exist(userid):
    response = dynamodb.get_item(
        TableName='SnipeLeaderboards',
        Key={'UserId':{'S':userid}}
    )
    return 'Item' in response

def verify_signature(event):
    raw_body = event.get("rawBody")
    auth_sig = event['params']['header'].get('x-signature-ed25519')
    auth_ts  = event['params']['header'].get('x-signature-timestamp')
    
    message = auth_ts.encode() + raw_body.encode()
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))
    verify_key.verify(message, bytes.fromhex(auth_sig)) # raises an error if unequal


def process_snipe(evnt_body):
    current_time = str(datetime.datetime.now(datetime.timezone.utc))
    recorded_snipeids = []
    sniper_id = evnt_body['member']['user']['id']
    # loop through the snipees to verify that the sniper did not try to snipe themself
    for option in evnt_body['data']['options']:
        if option['value'] == sniper_id:
            return {
                "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
                "data": {
                    "tts": False,
                    "content": "ERROR: you cannot snipe yourself, please retry",
                    "embeds": [],
                    "allowed_mentions": []
                }
            }
    # loop though the snipees
    for option in evnt_body['data']['options']:
        snipe_id = str(uuid.uuid4())
        snipee_id = option['value']
        snipeid_username = (snipe_id, evnt_body['data']['resolved']['users'][snipee_id]['username'])
        recorded_snipeids.append(snipeid_username)
        # add the snipe entry to the Snipes database
        dynamodb.put_item(
            TableName='Snipes',
            Item={
                'SnipeId':{'S':snipe_id},
                'SniperId':{'S':sniper_id},
                'SnipeeId':{'S':snipee_id},
                'DateTime':{'S':current_time},
                'Voided':{'BOOL':False}
            }
        )
        # now we need to update the score for the Snipee leaderboard
        # theres definitely a better approach to do this with condition expressions or something,
        # to avoid making an additional call to check if the item is in the table
        if does_userid_exist(snipee_id):
            # if the item is already in the table then update it
            dynamodb.update_item(
                TableName='SnipeLeaderboards',
                Key={'UserId':{'S':snipee_id}},
                ExpressionAttributeValues={':inc':{'N':'1'}},
                UpdateExpression="ADD AsSnipee :inc"
            )
        else:
            # if the item is not yet in the table, then create it
            dynamodb.put_item(
                TableName='SnipeLeaderboards',
                Item={
                    'UserId':{'S':snipee_id},
                    'AsSnipee':{'N':'1'},
                    'AsSniper':{'N':'0'},
                    'Game':{'S':'SNIPE'}
                }
            )
    # now we need to increment the score for the Sniper leaderboard by len(evnt_body['data']['options'])
    if does_userid_exist(sniper_id):
        # if the item is already in the table then update it
        dynamodb.update_item(
            TableName='SnipeLeaderboards',
            Key={'UserId':{'S':sniper_id}},
            ExpressionAttributeValues={':inc':{'N':str(len(evnt_body['data']['options']))}},
            UpdateExpression="ADD AsSniper :inc"
        )
    else:
        # if the item is not yet in the table, then create it
        dynamodb.put_item(
            TableName='SnipeLeaderboards',
            Item={
                'UserId':{'S':sniper_id},
                'AsSnipee':{'N':'0'},
                'AsSniper':{'N':str(len(evnt_body['data']['options']))},
                'Game':{'S':'SNIPE'}
            }
        )
    
    message = "Entry recorded with (SnipeId, Snipee)"
    for username_snipeid in recorded_snipeids:
        message += ", `" + str(username_snipeid) + "`"
    
    return {
        "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
        "data": {
            "tts": False,
            "content": message,
            "embeds": [],
            "allowed_mentions": []
        }
    }

# Should we later add a feature to tell the user their actual numberical rank rather than just their stats?
# what info to tell the user?
#   how many times theyve sniped others
#   how many times theyve been sniped
#   their K/D ratio
def get_own_rank(author_id):
    response_table = PrettyTable()
    response_table.field_names = ["As Sniper Count", "As Snipee Count", "K/D Ratio"]
    response = dynamodb.get_item(
        TableName='SnipeLeaderboards',
        Key={'UserId':{'S':author_id}}
    )
    if 'Item' in response:
        response_table.add_row([
            response['Item']['AsSniper']['N'],
            response['Item']['AsSnipee']['N'],
            str(round(int(response['Item']['AsSniper']['N'])/int(response['Item']['AsSnipee']['N']), 3))
        ])
    else:
        response_table.add_row(["0", "0", "N/A"])
    
    message = "```\n" + response_table.get_string() + "\n```"
    
    return {
        "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
        "data": {
            "tts": False,
            "content": message,
            "embeds": [],
            "allowed_mentions": []
        }
    }

# prints the top 20 on both the Sniper leaderboard and the Snipee leaderboard
def get_top():
    # query the SniperLeaderboard GSI
    sniper_response = dynamodb.query(
        TableName='SnipeLeaderboards',
        IndexName='SniperLeaderboard',
        Select='SPECIFIC_ATTRIBUTES',
        Limit=20,
        ScanIndexForward=False, # descending order
        ReturnConsumedCapacity='NONE',
        ProjectionExpression='UserId, AsSniper',
        KeyConditionExpression='Game = :game',
        ExpressionAttributeValues={
            ':game': {'S': 'SNIPE'}
        }
    )
    
    # query the SnipeeLeaderboard GSI
    snipee_response = dynamodb.query(
        TableName='SnipeLeaderboards',
        IndexName='SnipeeLeaderboard',
        Select='SPECIFIC_ATTRIBUTES',
        Limit=20,
        ScanIndexForward=False, # descending order
        ReturnConsumedCapacity='NONE',
        ProjectionExpression='UserId, AsSnipee',
        KeyConditionExpression='Game = :game',
        ExpressionAttributeValues={
            ':game': {'S': 'SNIPE'}
        }
    )
    
    
    sniper_table = PrettyTable()
    sniper_table.field_names = ["RANK", "USER", "SNIPES"]
    for rank, entry in enumerate(sniper_response['Items']):
        snipe_count = entry['AsSniper']['N']
        url = "https://discord.com/api/v9/users/" + entry['UserId']['S']
        headers = {"Authorization": AUTH_HEADER}
        user_response = requests.get(url, headers=headers)
        user_object = json.loads(user_response.content)
        sniper_table.add_row([str(rank + 1), user_object['username'] + "#" + user_object['discriminator'], snipe_count])
    
    
    snipee_table = PrettyTable()
    snipee_table.field_names = ["RANK", "USER", "SNIPES"]
    for rank, entry in enumerate(snipee_response['Items']):
        snipe_count = entry['AsSnipee']['N']
        url = "https://discord.com/api/v9/users/" + entry['UserId']['S']
        headers = {"Authorization": AUTH_HEADER}
        user_response = requests.get(url, headers=headers)
        user_object = json.loads(user_response.content)
        snipee_table.add_row([str(rank + 1), user_object['username'] + "#" + user_object['discriminator'], snipe_count])
    
    message = "```\nSNIPER LEADERBOARD\n" + sniper_table.get_string() + "\n```\n```\nSNIPEE LEADERBOARD\n" + snipee_table.get_string() + "\n```"
    
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
    # verify the signature
    try:
        verify_signature(event)
    except Exception as e:
        raise Exception(f"[UNAUTHORIZED] Invalid request signature: {e}")

    # check if message is a ping
    if event['body-json']['type'] == 1:
        return PING_PONG
    
    operation = event['body-json']['data']['name']
    if operation == "snipe-leaderboard":
        return get_top()
    elif operation == "snipe-rank":
        return get_own_rank(event['body-json']['member']['user']['id'])
    elif operation == "snipe":
        return process_snipe(event['body-json'])
    else:
        # this should not happen
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": "something went wrong",
                "embeds": [],
                "allowed_mentions": []
            }
        }
