from rest_framework.authtoken.models import Token
from .models import *
from django.utils.timezone import now



ADMIN_SOURCE_TYPES = ["Deed", "Mortgage", "Title", "Deed_Of_Lease", "Permit"]

base_url = "https://infobhoomiback.geoinfobox.com/" # for file path in serializer

PERMISSION_TO_LAYER_MAP = {
    80: 1,
    81: 2,
    82: 3,
    83: 4,
    84: 5,
    85: 6,
    86: 7,
    87: 8,
    88: 9,
    89: 10,
    90: 11,
    # 91: 12, # Apartment Layer
    92: 13
    # 93: 14 # Raster Data Layer
}


# ------------------------------ Login Authorization ----------------------------------------------
def verify_token_and_role(auth_header, role_id=None):
    """
    Verifies token, checks if user is active, and (optionally) checks if user is in the role.
    """
    if not auth_header.startswith("Token "):
        return None

    token_key = auth_header.split(" ")[1]

    try:
        token = Token.objects.select_related("user").get(key=token_key)
        user = token.user

        # Optional role check
        is_role_id = True
        if role_id is not None:
            try:
                role = User_Roles_Model.objects.get(role_id=role_id)
                is_role_id = user.id in role.users if role.users else False
            except User_Roles_Model.DoesNotExist:
                is_role_id = False

        return {
            "user": user,
            "is_active": user.is_active,
            "is_role_id": is_role_id,
        }

    except Token.DoesNotExist:
        return None



# ------------------------------ Update Last_Login and Last_Active --------------------------------
def update_user_last_login(user):
    if user:
        user.last_login = now()
        user.save(update_fields=['last_login'])

def update_user_last_active(user):
    if user:
        Last_Active_Model.objects.filter(user_id=user.id).update(active_time=now())