"""Constants for the Hue component."""

from aiohue.v2.models.button import ButtonEvent
from aiohue.v2.models.relative_rotary import (
    RelativeRotaryAction,
    RelativeRotaryDirection,
)

DOMAIN = "hue"

CONF_IGNORE_AVAILABILITY = "ignore_availability"

CONF_SUBTYPE = "subtype"

ATTR_HUE_EVENT = "hue_event"
SERVICE_HUE_ACTIVATE_SCENE = "hue_activate_scene"
ATTR_GROUP_NAME = "group_name"
ATTR_SCENE_NAME = "scene_name"
ATTR_TRANSITION = "transition"
ATTR_DYNAMIC = "dynamic"


# Recommendation engine constants ##################

CONF_RECOMMENDATION_AUTO_APPLY = "recommendation_auto_apply"
CONF_RECOMMENDATION_AUTO_APPLY_GLOBAL = "recommendation_auto_apply_global"

CONF_RECOMMENDATION_WEIGHT_TIME_OF_DAY = "recommendation_weight_time_of_day"
CONF_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE = "recommendation_weight_weekly_schedule"
CONF_RECOMMENDATION_WEIGHT_HOME_ARRIVAL = "recommendation_weight_home_arrival"
CONF_RECOMMENDATION_UPDATE_INTERVAL = "recommendation_update_interval"

CONF_RECOMMENDATION_INERTIA_BOOST = "recommendation_inertia_boost"
CONF_RECOMMENDATION_SWITCH_DELTA_MIN = "recommendation_switch_delta_min"
CONF_RECOMMENDATION_MIN_DWELL_SECONDS = "recommendation_min_dwell_seconds"

# Default per-strategy weight when not configured via options.
DEFAULT_RECOMMENDATION_STRATEGY_WEIGHT = 1.0
DEFAULT_RECOMMENDATION_WEIGHT_TIME_OF_DAY = 0.5
DEFAULT_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE = 1.0
DEFAULT_RECOMMENDATION_WEIGHT_HOME_ARRIVAL = 2.0
DEFAULT_RECOMMENDATION_UPDATE_INTERVAL = 15


# V1 API SPECIFIC CONSTANTS ##################

GROUP_TYPE_LIGHT_GROUP = "LightGroup"
GROUP_TYPE_ROOM = "Room"
GROUP_TYPE_LUMINAIRE = "Luminaire"
GROUP_TYPE_LIGHT_SOURCE = "LightSource"
GROUP_TYPE_ZONE = "Zone"
GROUP_TYPE_ENTERTAINMENT = "Entertainment"

CONF_ALLOW_HUE_GROUPS = "allow_hue_groups"
DEFAULT_ALLOW_HUE_GROUPS = False

CONF_ALLOW_UNREACHABLE = "allow_unreachable"
DEFAULT_ALLOW_UNREACHABLE = False

# How long to wait to actually do the refresh after requesting it.
# We wait some time so if we control multiple lights, we batch requests.
REQUEST_REFRESH_DELAY = 0.3


# V2 API SPECIFIC CONSTANTS ##################

DEFAULT_BUTTON_EVENT_TYPES = (
    # I have never ever seen the `DOUBLE_SHORT_RELEASE` event so leave it out here
    ButtonEvent.INITIAL_PRESS,
    ButtonEvent.REPEAT,
    ButtonEvent.SHORT_RELEASE,
    ButtonEvent.LONG_PRESS,
    ButtonEvent.LONG_RELEASE,
)

DEFAULT_ROTARY_EVENT_TYPES = (RelativeRotaryAction.START, RelativeRotaryAction.REPEAT)
DEFAULT_ROTARY_EVENT_SUBTYPES = (
    RelativeRotaryDirection.CLOCK_WISE,
    RelativeRotaryDirection.COUNTER_CLOCK_WISE,
)

DEVICE_SPECIFIC_EVENT_TYPES = {
    # device specific overrides of specific supported button events
    "Hue tap switch": (ButtonEvent.INITIAL_PRESS,),
}
