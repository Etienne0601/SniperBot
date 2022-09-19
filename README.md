# Sniper Game Discord Bot
A port of https://github.com/maksymovi/sniperBot to Discord slash commands and AWS. As far as the AWS resources used, it currently uses API Gateway to handle the slash commands HTTP post request, DynamoDB for the leaderboards table and the snipes table, and Lambda to handle the slash command events. Eventually I'll probably add some CloudFormation templates to automate the AWS infrastructure creation.

The code is very much still a work in progress.

This bot supports a simple game that involves taking a photo of an unsuspecting player when running across them, without them noticing, and posting said photo in chat to score a point.

The PUBLIC_KEY and BOT_TOKEN should be added to a file named `constants.py` in the same directory as `lambda_function.py`. APP_ID should also be in there to run the registerCommands.py file. Currently this isn't too secure, using AWS Secrets Manager remains a TODO. 

## User Guide
/snipe <@mention> ... - snipe another user. There can be up to five @mentions, and it will record a snipe for each.

/snipe-leaderboard - shows a leaderboard of top snipers and snipees

/snipe-rank - Shows your own stats and KDR

/snipe-void <SnipeId> - voids a specific snipe by its SnipeId. Note that this command requires server administrator priviledges to run.


## Deployment

This app uses AWS CDK to deploy automatically. To do this you will need to have aws cli installed and cdk. 

To deploy with CDK, run `cdk deploy`. This assumes you have aws configure setup and you have cdk installed (`npm install -g aws-cdk` to install). `cdk deploy` will return a api endpoint, append `event` to that endpoint and plug they into your Discord application's interactions endpoint.

Command registration right now is manual and is run by the registerCommands.py file. Simply run this file locally and it should handle everything. You may need to `python3 -m pip install -r requirements.txt` to get the necessary dependencies to run locally however. 

build_dependencies.sh builds and packages the dependencies specified by requirements.txt and packages them into dependencies.zip. These are required for the AWS Lambda layer environment. build_dependencies.sh uses docker to build them because AWS Lambda doesn't play nice with locally built dependencies apparently and needs to build in an AWS environment. To make this easier if you don't have docker, I am uploading an already prebuilt dependencies.zip, therefore this step is optional, though if you see this package 5 years down the line its probably wise to build them.
