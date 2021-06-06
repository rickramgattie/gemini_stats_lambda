# gemini_stat_lambda
Gemini Stats Lambda

## Description
AWS Lambda app that will query the Gemini API for purchases and send an email with the amount bought, money spent, and the USD value of tokens current holdings. 

## Instructions
1. Create a Python 3.8 AWS Lambda function and upload `gemini_stats_lambda.py` as the source code.
2. Create a [GMail App Password](https://support.google.com/accounts/answer/185833?hl=en) with the appropiate permissions and store it in [Secrets Manager](https://stackoverflow.com/a/58767046) as `gmail_app_password`.
3. Create a [Gemini API Key](https://support.gemini.com/hc/en-us/articles/360031080191-How-do-I-create-an-API-key-) with the appropiate permissions and store the `secret` and `key` in [Secrets Manager](https://stackoverflow.com/a/58767046) as `gemini_api_secret` and `gemini_api_key`.
4. Set the following environment variables
  - `REGION_NAME` (ex. us-east-1)
  - `SECRET_NAME` (ex. gemini_lambda_emailer_secrets)
  - `SENDER_GMAIL_ADDRESS` (ex. rick.ramgattie@gmail.com)
  - `RECIPIENT_GMAIL_ADDRESS` (ex. rick.ramgattie@gmail.com)
5. Schedule Lambda with [CloudWatch Events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html).

## Notes:
- I followed least privilege when creating my Gemini API key and GMail app password. I recommend you do the same.
