import json
import uuid
import os
import boto3
import datetime
import requests
import constants
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

PING_PONG = {"type": 1}

dynamodb = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')

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
    verify_key = VerifyKey(bytes.fromhex(constants.PUBLIC_KEY))
    verify_key.verify(message, bytes.fromhex(auth_sig)) # raises an error if unequal

def process_snipe(evnt_body):
    current_time = str(datetime.datetime.now(datetime.timezone.utc))
    snipee_ids = {}
    sniper_id = evnt_body['member']['user']['id']
    # loop through the snipees to verify that the sniper did not try to snipe themself
    # and also that there are no duplicate snipees
    for option in evnt_body['data']['options']:
        snipee_id = option['value']
        if snipee_id == sniper_id:
            return {
                "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
                "data": {
                    "tts": False,
                    "content": "ERROR: You cannot snipe yourself, please retry.",
                    "embeds": [],
                    "allowed_mentions": []
                }
            }
        if snipee_id in snipee_ids:
            return {
                "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
                "data": {
                    "tts": False,
                    "content": "ERROR: You cannot snipe a player more than once, please retry.",
                    "embeds": [],
                    "allowed_mentions": []
                }
            }
        snipe_id = str(uuid.uuid4()).split('-')[0]
        username = evnt_body['data']['resolved']['users'][snipee_id]['username']
        snipee_ids[snipee_id] = f"{snipe_id}#{username}"
    
    # loop though the snipees to update the databases
    for snipee_id, snipeid_username in snipee_ids.items():
        snipe_id, username = snipeid_username.split('#')
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
        # to avoid making an additional API call to check if the item is in the table
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
    
    new_snipes_table = ""
    for snipee_id, snipeid_username in snipee_ids.items():
        snipe_id, username = snipeid_username.split('#')
        new_snipes_table += "`" + snipe_id + "   " + username + "`\n"
    new_snipes_table_field = [{"name":"`SnipeId    Snipee`","value":new_snipes_table,"inline":True}]
    
    return {
        "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
        "data": {
            "tts": False,
            "content": "",
            "embeds": [{
                "title": "Snipes Recorded",
                "type": "rich",
                "color": 1752220,
                "fields": new_snipes_table_field
            }],
            "allowed_mentions": []
        }
    }

def void_snipe(snipe_id, author_perms):
    # check if the author is not an admin
    if not author_perms & 8:
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": "You are not an administrator, please ping an administrator if you need to issue this command.",
                "embeds": [],
                "allowed_mentions": []
            }
        }
    
    # now verify that the snipe_id corresponds to a real snipe
    response = dynamodb.get_item(
        TableName='Snipes',
        Key={'SnipeId':{'S':snipe_id}}
    )
    if 'Item' not in response:
        message = f"ERROR: SnipeId `{snipe_id}` does not exist."
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": message,
                "embeds": [],
                "allowed_mentions": []
            }
        }
    
    # check if the item has already been voided
    if response['Item']['Voided']['BOOL']:
        message = f"ERROR: SnipeId `{snipe_id}` has already been voided."
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": message,
                "embeds": [],
                "allowed_mentions": []
            }
        }
    
    # set the Voided attribute to True
    dynamodb.update_item(
        TableName='Snipes',
        Key={'SnipeId':{'S':snipe_id}},
        ExpressionAttributeValues={':newValue':{'BOOL':True}},
        UpdateExpression="SET Voided = :newValue"
    )
    
    sniper_id = response['Item']['SniperId']['S']
    snipee_id = response['Item']['SnipeeId']['S']
    # now update the SnipeLeaderboards table to remove the point from both the sniper and snipee
    # Assuming that the relevant items exist in the SnipeLeaderboards table, since it
    # should be kept in sync with the Snipes table
    dynamodb.update_item(
        TableName='SnipeLeaderboards',
        Key={'UserId':{'S':sniper_id}},
        ExpressionAttributeValues={':inc':{'N':'-1'}},
        UpdateExpression="ADD AsSniper :inc"
    )
    dynamodb.update_item(
        TableName='SnipeLeaderboards',
        Key={'UserId':{'S':snipee_id}},
        ExpressionAttributeValues={':inc':{'N':'-1'}},
        UpdateExpression="ADD AsSnipee :inc"
    )
    
    message = f"Successfully voided `{snipe_id}`"
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
def get_own_rank(author_id):
    fields = []
    response = dynamodb.get_item(
        TableName='SnipeLeaderboards',
        Key={'UserId':{'S':author_id}}
    )
    if 'Item' in response:
        fields.append({"name":"Sniper Count","value":response['Item']['AsSniper']['N'],"inline":False})
        fields.append({"name":"Snipee Count","value":response['Item']['AsSnipee']['N'],"inline":False})
        as_snipee_count = int(response['Item']['AsSnipee']['N'])
        if as_snipee_count == 0:
            fields.append({"name":"K/D Ratio","value":"N/A","inline":False})
        else:
            fields.append({"name":"K/D Ratio","value":str(round(int(response['Item']['AsSniper']['N'])/as_snipee_count, 3)),"inline":False})
    else:
        fields.append({"name":"Sniper Count","value":"0","inline":False})
        fields.append({"name":"Snipee Count","value":"0","inline":False})
        fields.append({"name":"K/D Ratio","value":"N/A","inline":False})
    
    return {
        "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
        "data": {
            "tts": False,
            "content": "",
            "embeds": [{
                "title": "Stats",
                "type": "rich",
                "color": 1752220,
                "fields": fields
            }],
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
        params = {'InteractionToken': event['body-json']['token']}
        response = lambda_client.invoke(
            FunctionName='SniperBotCommandHandler',
            Payload=json.dumps(params),
            InvocationType='Event'
        )
        return {
            "type": 4, # CHANNEL_MESSAGE_WITH_SOURCE
            "data": {
                "tts": False,
                "content": "Getting Data...",
                "embeds": [],
                "allowed_mentions": []
            }
        }
    elif operation == "snipe-rank":
        return get_own_rank(event['body-json']['member']['user']['id'])
    elif operation == "snipe-void":
        return void_snipe(event['body-json']['data']['options'][0]['value'], int(event['body-json']['member']['permissions']))
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
