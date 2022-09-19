from cgitb import handler
from json import JSONDecoder, JSONEncoder
from platform import architecture
from typing import Mapping
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    Duration,
)

# taken from https://oozio.medium.com/serverless-discord-bot-55f95f26f743
requestSchema = "##  See http:\/\/docs.aws.amazon.com\/apigateway\/latest\/developerguide\/api-gateway-mapping-template-reference.html\r\n##  This template will pass through all parameters including path, querystring, header, stage variables, and context through to the integration endpoint via the body\/payload\r\n##  'rawBody' allows passthrough of the (unsurprisingly) raw request body; similar to flask.request.data\r\n#set($allParams = $input.params())\r\n{\r\n\"rawBody\": \"$util.escapeJavaScript($input.body).replace(\"\\'\", \"'\")\",\r\n\"body-json\" : $input.json('$'),\r\n\"params\" : {\r\n#foreach($type in $allParams.keySet())\r\n    #set($params = $allParams.get($type))\r\n\"$type\" : {\r\n    #foreach($paramName in $params.keySet())\r\n    \"$paramName\" : \"$util.escapeJavaScript($params.get($paramName))\"\r\n        #if($foreach.hasNext),#end\r\n    #end\r\n}\r\n    #if($foreach.hasNext),#end\r\n#end\r\n},\r\n\"stage-variables\" : {\r\n#foreach($key in $stageVariables.keySet())\r\n\"$key\" : \"$util.escapeJavaScript($stageVariables.get($key))\"\r\n    #if($foreach.hasNext),#end\r\n#end\r\n},\r\n\"context\" : {\r\n    \"account-id\" : \"$context.identity.accountId\",\r\n    \"api-id\" : \"$context.apiId\",\r\n    \"api-key\" : \"$context.identity.apiKey\",\r\n    \"authorizer-principal-id\" : \"$context.authorizer.principalId\",\r\n    \"caller\" : \"$context.identity.caller\",\r\n    \"cognito-authentication-provider\" : \"$context.identity.cognitoAuthenticationProvider\",\r\n    \"cognito-authentication-type\" : \"$context.identity.cognitoAuthenticationType\",\r\n    \"cognito-identity-id\" : \"$context.identity.cognitoIdentityId\",\r\n    \"cognito-identity-pool-id\" : \"$context.identity.cognitoIdentityPoolId\",\r\n    \"http-method\" : \"$context.httpMethod\",\r\n    \"stage\" : \"$context.stage\",\r\n    \"source-ip\" : \"$context.identity.sourceIp\",\r\n    \"user\" : \"$context.identity.user\",\r\n    \"user-agent\" : \"$context.identity.userAgent\",\r\n    \"user-arn\" : \"$context.identity.userArn\",\r\n    \"request-id\" : \"$context.requestId\",\r\n    \"resource-id\" : \"$context.resourceId\",\r\n    \"resource-path\" : \"$context.resourcePath\"\r\n    }\r\n}"

class SniperBotStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #Making a layer for the lambda


        layer = _lambda.LayerVersion(
            self,
            id + 'Layer',
            code=_lambda.Code.from_asset('dependencies.zip'),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
            compatible_architectures=[_lambda.Architecture.X86_64]
        )

        # Defines an AWS Lambda resource
        my_lambda = _lambda.Function(
            self,
            id + 'Handler',
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset('src'),
            handler='lambda_function.lambda_handler',
            timeout=Duration.seconds(3),
            architecture= _lambda.Architecture.X86_64,
            layers=[layer]
        )
        api = apigw.RestApi(
            self, id + 'Endpoint',
            default_cors_preflight_options= apigw.CorsOptions(
                allow_origins= ["discord.com"]
            )
        )
        eventResource = api.root.add_resource('event')
        eventResource.add_method(
            'POST',
            method_responses=[apigw.MethodResponse(status_code="200"), apigw.MethodResponse(status_code="401")],
            integration=apigw.LambdaIntegration(
                handler=my_lambda,
                proxy=False,
                passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
                integration_responses=[
                    apigw.IntegrationResponse(status_code="401", selection_pattern=".*[UNAUTHORIZED].*"),
                    apigw.IntegrationResponse(status_code="200")],
                    request_templates= {
                        "application/json" : requestSchema
                    }
                ),
            )