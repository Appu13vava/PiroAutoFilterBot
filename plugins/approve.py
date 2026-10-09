"""Join requests are intentionally left pending for manual admin approval.

Do not register an auto-approval handler here. Force-subscription invite links use
creates_join_request=True, and channel admins decide whether to approve each request.
"""
