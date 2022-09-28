import json
import uuid
import os
import boto3
import datetime
import requests
import constants
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

HEADERS = {
    "Authorization": "Bot " + constants.BOT_TOKEN
}

dynamodb = boto3.client('dynamodb')

def lambda_handler(event, context):
    interaction_token = event['InteractionToken']
    message_url = f"https://discord.com/api/v10/webhooks/{constants.APP_ID}/{interaction_token}/messages/@original"
    # get the top 20 on both the Sniper leaderboard and the Snipee leaderboard and send it to discord via webhook
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
    
    if len(sniper_response['Items']) == 0 or len(snipee_response['Items']) == 0:
        data = {
            "tts": False,
            "content": "No data exists to display.",
            "embeds": [],
            "allowed_mentions": []
        }
        r = requests.patch(message_url, headers=HEADERS, json=data)
        return

    new_sniper_table = ""
    usernames_map = {} # map of user ids to user strings
    for rank, entry in enumerate(sniper_response['Items']):
        snipe_count = entry['AsSniper']['N']
        user_id = entry['UserId']['S']
        url = f"https://discord.com/api/v9/users/{user_id}"
        user_response = requests.get(url, headers=HEADERS)
        user_object = json.loads(user_response.content)
        username = user_object['username']
        usernames_map[user_id] = f"{username}#{user_object['discriminator']}"
        num_spaces = 16 - len(username)
        new_sniper_table += "`" + str(rank + 1) + ":  " + username + "#" + user_object['discriminator'] + (" " * num_spaces) + snipe_count + "`\n"
    new_sniper_table_field = [{"name":"`Rank   User         Snipes`","value":new_sniper_table,"inline":True}]
    
    new_snipee_table = ""
    for rank, entry in enumerate(snipee_response['Items']):
        snipe_count = entry['AsSnipee']['N']
        user_id = entry['UserId']['S']
        username = ""
        if user_id in usernames_map:
            username = usernames_map[user_id]
        else:
            url = f"https://discord.com/api/v9/users/{user_id}"
            user_response = requests.get(url, headers=HEADERS)
            user_object = json.loads(user_response.content)
            username = user_object['username'] + "#" + user_object['discriminator']
        num_spaces = 21 - len(username)
        new_snipee_table += "`" + str(rank + 1) + ":  " + username + (" " * num_spaces) + snipe_count + "`\n"
    new_snipee_table_field = [{"name":"`Rank   User         Snipes`","value":new_snipee_table,"inline":True}]
    data = {
        "tts": False,
        "content": "",
        "embeds": [
            {
                "title": "Sniper Leaderboard",
                "type": "rich",
                "color": 1752220,
                "fields": new_sniper_table_field
            },
            {
                "title": "Snipee Leaderboard",
                "type": "rich",
                "color": 1752220,
                "fields": new_snipee_table_field
            }
        ],
        "allowed_mentions": []
    }
    r = requests.patch(message_url, headers=HEADERS, json=data)
