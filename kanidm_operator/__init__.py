# noqa: F401,W0611
# pylint: disable=unused-import

from .deploy.kanidm import on_create_kanidms, on_update_kanidms  # noqa
from .deploy.group import (
    on_create_group,
    #on_update_group_name,
    on_update_group_members,
    on_delete_group,
)  # noqa

from .deploy.user import (
    on_create_user, 
    on_delete_user  
) # noqa

from .deploy.oauth2client import (
    on_create_oauth2client,
    #on_update_oauth2client_name,
    on_delete_oauth2client,
)  # noqa