import requests
import constants

url = "https://discord.com/api/v10/applications/{}/commands".format(constants.APP_ID)
# view permissions: /applications/{application.id}/guilds/{guild.id}/commands/{command.id}/permissions

# CHAT_INPUT or Slash Command, with a type of 1

command_list = [
{
    "name": "snipe",
    "description": "Record one or more snipes",
    "options": [
        {
            "type": 6, # USER
            "name": "snipee0",
            "description": "A snipee who was successfully sniped",
            "required": True,
        },
        {
            "type": 6,
            "name": "snipee1",
            "description": "A snipee who was successfully sniped",
            "required": False,
        },
        {
            "type": 6,
            "name": "snipee2",
            "description": "A snipee who was successfully sniped",
            "required": False,
        },
        {
            "type": 6,
            "name": "snipee3",
            "description": "A snipee who was successfully sniped",
            "required": False,
        },
        {
            "type": 6,
            "name": "snipee4",
            "description": "A snipee who was successfully sniped",
            "required": False,
        }
    ],
    "type": 1
},
{
    "name": "snipe-leaderboard",
    "description": "View leaderboards of top snipers and snipees",
    "type": 1
},
{
    "name": "snipe-rank",
    "description": "View your own stats and K/D ratio",
    "type": 1
}
]

headers = {
    "Authorization": "Bot " + constants.BOT_TOKEN
}

for json_command in command_list:
    r = requests.post(url, headers=headers, json=json_command)
    print(r)
    print(r.content)