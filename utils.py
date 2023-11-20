# verify slack requests
# ref: https://gist.github.com/nitrocode/288bb104893698011720d108e9841b1f

import base64

#!/usr/bin/env python3
import hashlib
import hmac
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def verify_slack_request(event: dict, slack_signing_secret) -> bool:
    """Verify slack requests.

    Borrowed from https://janikarhunen.fi/verify-slack-requests-in-aws-lambda-and-python.html

    - Removed optional args
    - Checks isBase64Encoded

    :param event: standard event handler
    :param slack_signing_secret: slack secret for the slash command
    :return: True if verification worked
    """
    slack_signature = event["headers"]["x-slack-signature"]
    slack_time = event["headers"]["x-slack-request-timestamp"]
    body = event["body"]
    if event["isBase64Encoded"]:
        body = base64.b64decode(body).decode("utf-8")

    # Form the basestring as stated in the Slack API docs. We need to make a bytestring.
    base_string = f"v0:{slack_time}:{body}".encode("utf-8")

    # Make the Signing Secret a bytestring too.
    slack_signing_secret = bytes(slack_signing_secret, "utf-8")

    # Create a new HMAC "signature", and return the string presentation.
    my_signature = (
        "v0=" + hmac.new(slack_signing_secret, base_string, hashlib.sha256).hexdigest()
    )

    """ Compare the the Slack provided signature to ours.
    If they are equal, the request should be verified successfully.
    Log the unsuccessful requests for further analysis
    (along with another relevant info about the request)."""
    result = hmac.compare_digest(my_signature, slack_signature)
    if not result:
        logger.error("Verification failed. my_signature: ")
        logger.error(f"{my_signature} != {slack_signature}")

    return result
