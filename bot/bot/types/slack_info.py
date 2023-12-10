class SlackInfo:
    slack_bot_token: str
    slack_app_token: str
    slack_signing_secret: str
    slack_bot_member_id: str

    def __init__(
        self,
        slack_bot_token: str,
        slack_app_token: str,
        slack_signing_secret: str,
        slack_bot_member_id: str,
    ) -> None:
        self.slack_bot_token = slack_bot_token
        self.slack_app_token = slack_app_token
        self.slack_signing_secret = slack_signing_secret
        self.slack_bot_member_id = slack_bot_member_id
