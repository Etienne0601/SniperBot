# Implementing Sniper Bot w/AWS & Slash Commands

## Goals
The first goal is to port over all the existing logic of the [sniper bot](https://github.com/maksymovi/sniperBot) to AWS Lambda and DynamoDB exactly as-is.

The next goal would be to optimize everything to minimize computational and storage costs for the lambda functions and for the data store(s). This might include making persistent leaderboards so that the leaderboard does not need to be recomputed on each request to view the leaderboard.

## Interface
The interface should be basically the same as the existing sniper bot, except using slash commands.

### Existing SniperBot Interface
snipe @mention - snipe another user. Note there can be multiple @mentions, and it will record a snipe for each. Note this will work for anything with snipe at the beginning and an @mention

snipe leaderboard - shows a leaderboard of top snipers and snipees

snipe rank - Shows your own stats and KDR

snipe admin setChannel - sets a channel where this bot can be run

snipe admin removeChannel - removes channel where this bot can be run

snipe admin void - voids all snipes recorded by some message ID

Admin commands require server administrator priviledges.

For the slash command structure, there will be a `/snipe` command to create a snipe, a `/snipe-leaderboard` command to view the snipe leaderboard, a `/snipe-rank` command to view your own stats and K/D ratio. The admin slash commands will be TBD, but they will include at least `/snipe-void` to void snipes by the SnipeId.

I discovered that via the "Manage Interactions" menu you can choose in which channels users can use the slash commands. I think that means there would not be a need to store which channels the bot can be used in like is done [here](https://github.com/maksymovi/sniperBot/blob/master/src/sniperbot.py#L57).

## Database Tables

### Snipe Table
(SnipeId INTEGER, SniperId INTEGER, SnipeeId INTEGER, Voided BOOL)
The SnipeId is a generated UUID, the SniperId is the ID of the message's author, the SnipeeId is the ID of one of the people mentioned in the message, the Voided field represents whether an admin has voided this snipe or not.

## Development Considerations

I'm going to implement everything as a single Lambda function first, and then maybe later work on splitting it into different Lambdas for the different operations. I am not really sure how to do this yet. I wonder if theres a way with API gateway to direct the request to different Lambdas depending on the slash command? Otherwise I could maybe use Step functions to split things up into different Lambdas.

For the main snipe command, I am having some trouble figuring how to have a variable number of parameters. I think that I am going to have to use optional options and just list a bunch of them (theres a limit of 25 options I believe according to [Application Command Structure](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-structure)). Maybe I'll start with 5 and see if that is enough.

Apparently there is no feature for variadic arguments with slash commands according to this [discussion](https://github.com/discord/discord-api-docs/discussions/3286).
