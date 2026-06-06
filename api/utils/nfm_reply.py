from api.services.ai.tool_handlers.meal_review import review_order
from api.services.ai.tool_handlers.order import place_order
from api.services.ai.tool_handlers.user_profile import update_user_profile
import json

from api.services.ai.tool_handlers.withdraw import make_withdrawal

def nfm_reply_hander(user, fields):
    print(fields, type(fields))
    fields = json.loads(fields)
    print(fields, type(fields), 'loaded')

    flow_token = fields.pop('flow_token', None)
    
    screen_name = flow_token.split('--')[1]  # screen_name
    print(screen_name, 'screen_name')

    if screen_name == 'ORDER_FLOW':
        place_order(user, **fields)

    elif screen_name == 'USER_PROFILE':
        update_user_profile(user, **fields)

    elif screen_name == 'ORDER_REVIEW':
        review_order(user, **fields)

    elif screen_name == 'WITHDRAWAL':
        make_withdrawal(user, **fields)
