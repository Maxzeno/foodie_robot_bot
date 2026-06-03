from api.services.ai.tool_handlers.order import place_order


def nfm_reply_hander(user, fields):
    flow_token = fields.pop('flow_token', None)
    screen_name = flow_token.split('--')[1]  # screen_name

    if screen_name == 'ORDER_FLOW':
        place_order(user, **fields)

    elif screen_name == 'USER_PROFILE':
        # update_user_info(user, **fields)
        pass # To be implemented in future (update_user_info)
    