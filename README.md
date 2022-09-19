# Sniper Game Discord Bot
A port of https://github.com/maksymovi/sniperBot to Discord slash commands and AWS. As far as the AWS resources used, it currently uses API Gateway to handle the slash commands HTTP post request, DynamoDB for the leaderboards table and the snipes table, and Lambda to handle the slash command events. Eventually I'll probably add some CloudFormation templates to automate the AWS infrastructure creation.

The code is very much still a work in progress.

This bot supports a simple game that involves taking a photo of an unsuspecting player when running across them, without them noticing, and posting said photo in chat to score a point.

The PUBLIC_KEY and BOT_TOKEN should be added to a file named `constants.py` in the same directory as `lambda_function.py`.

## User Guide
/snipe <@mention> ... - snipe another user. There can be up to five @mentions, and it will record a snipe for each.

/snipe-leaderboard - shows a leaderboard of top snipers and snipees

/snipe-rank - Shows your own stats and KDR

/snipe-void <SnipeId> - voids a specific snipe by its SnipeId. Note that this command requires server administrator priviledges to run.
