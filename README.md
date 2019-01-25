# slack-sms

## Description

This is an initial implimentation and is a work in progress. Currently the bot supports /sms @user commands and an interactive bot that will prompt you to send your message as an SMS to the user if they are marked 'away' using the number on the user profile. You need a Flowroute account and Flowroute number to use this bot. You will need to grant certain permissions to this bot so it can use the api to get account info and receive public channel messages to search for mentions. This project is currently meant to be deployed as an AWS Lambda function with API Gateway in front along with an Elasticache Redis for persistence.

