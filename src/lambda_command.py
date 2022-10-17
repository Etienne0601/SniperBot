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

TABLE_HEADER = "`    User                   Snipes`"

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
    calc_rank = 0
    last_snipe_count = 100000 # TODO change to max int
    for rank, entry in enumerate(sniper_response['Items']):
        snipe_count = entry['AsSniper']['N']
        calc_rank_str = "  "
        if int(snipe_count) < last_snipe_count:
            calc_rank = rank + 1
            calc_rank_str = "#" + str(calc_rank)
            last_snipe_count = int(snipe_count)
        user_id = entry['UserId']['S']
        url = f"https://discord.com/api/v9/users/{user_id}"
        user_response = requests.get(url, headers=HEADERS)
        user_object = json.loads(user_response.content)
        username = f"{user_object['username']}#{user_object['discriminator']}"
        usernames_map[user_id] = username
        rank_padding = " " * (4 - len(calc_rank_str))
        num_spaces = 24 - len(username) - len(snipe_count)
        num_spaces = max(num_spaces, 2)
        new_leaderboard_entry = f"`{calc_rank_str:3.3} {username:25.25}{snipe_count:>4.4}`\n"
        new_sniper_table += new_leaderboard_entry
    new_sniper_table_field = [{"name":TABLE_HEADER,"value":new_sniper_table,"inline":True}]
    

    new_snipee_table = ""
    calc_rank = 0
    last_snipe_count = 100000 # TODO change to max int
    for rank, entry in enumerate(snipee_response['Items']):
        snipe_count = entry['AsSnipee']['N']
        calc_rank_str = "  "
        if int(snipe_count) < last_snipe_count:
            calc_rank = rank + 1
            calc_rank_str = "#" + str(calc_rank)
            last_snipe_count = int(snipe_count)
        user_id = entry['UserId']['S']
        username = ""
        if user_id in usernames_map:
            username = usernames_map[user_id]
        else:
            url = f"https://discord.com/api/v9/users/{user_id}"
            user_response = requests.get(url, headers=HEADERS)
            user_object = json.loads(user_response.content)
            username = f"{user_object['username']}#{user_object['discriminator']}"
        rank_padding = " " * (4 - len(calc_rank_str))
        num_spaces = 24 - len(username) - len(snipe_count)
        num_spaces = max(num_spaces, 2)
        new_leaderboard_entry = f"`{calc_rank_str:3.3} {username:25.25}{snipe_count:>4.4}`\n"
        new_snipee_table += new_leaderboard_entry
    new_snipee_table_field = [{"name":TABLE_HEADER,"value":new_snipee_table,"inline":True}]

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
