#!/usr/bin/env python3

import aws_cdk as cdk

from cdk.cdk_stack import SniperBotStack


app = cdk.App()
SniperBotStack(app, "SniperBot")

app.synth()
