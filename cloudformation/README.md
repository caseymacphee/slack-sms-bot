# slack-sms

## Initial setup

### Redis

Before deploying our application, first create a stack for the Redis node.
```
aws cloudformation create-stack --stack-name slackSMSRedis \
  --template-body file://redis.yaml \
  --parameters file://redisLabsAccountParams.json \
  --capabilities CAPABILITY_IAM --profile default --region us-west-2
```

### S3 Bucket

Create bucket for application code:

```
aws s3 mb s3://myaccount-slackbot-sms --region us-west-2
```

## Deploying the Slackbot

Get AWS SAM template:
```
aws cloudformation package \
   --template-file slackSMS.yaml \
   --output-template-file slackSMS-output.yaml \
   --s3-bucket myaccount-slackbot-sms --profile default
```

Deploy application:
```
aws cloudformation deploy \
   --template-file slackSMS-output.yaml \
   --stack-name slackSMS \
   --capabilities CAPABILITY_IAM --profile default

```
