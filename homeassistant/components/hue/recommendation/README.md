# Hue Smart Scene Recommendation System

A Home Assistant integration that provides intelligent, context-aware scene recommendations for Philips Hue lighting systems.

## Overview

This recommendation engine analyzes various contextual factors (time of day, sun position, presence, and schedules) to automatically suggest and optionally apply the most appropriate lighting scenes for each room in your home.

## Architecture

### Core Components

#### Context System (`context/`)
Collects and aggregates environmental and situational data:

- **`HomeContext`**: Central data structure containing all contextual information
- **Context Providers**: Pluggable modules that fetch specific context data
  - `PresenceProvider`: Detects if anyone is home via `zone.home`
  - `SunProvider`: Tracks sun position and day/night state via `sun.sun`
  - `ScheduleProvider`: Monitors Home Assistant schedule entities for time-of-day periods
  - `IContextProvider`: Interface for creating custom context providers

#### Policy System (`policy/`)
Makes scene selection decisions based on context:

- **Strategies**: Score each available scene based on specific criteria
  - **`TimeOfDayStrategy`**: Scores scenes based on sun elevation
    - Morning/dawn (elevation < 10°): Prefers morning, dawn, wake scenes
    - Daytime (elevation ≥ 10°): Prefers day, bright, work scenes
    - Evening/night (elevation < 0°): Prefers evening, night, dusk scenes
  - **`WeeklyScheduleStrategy`**: Matches scenes to Home Assistant schedule periods
    - Morning: breakfast, wake, dawn scenes
    - Work: focus, concentrate, bright scenes
    - Evening: relax, dinner, sunset scenes
    - Night: sleep, dim, bedtime scenes
  - **`HomeArrivalStrategy`**: Detects away→home transitions and prefers welcoming scenes
    - Triggers on `is_anyone_home` state change
    - Prefers scenes with "arrival", "welcome", "home" keywords
    - Uses catalog-backed arrival scene sets
  - Extensible strategy framework via `IStrategy` interface
- **`PolicyService`**: Aggregates strategy scores with configurable weights and selects optimal scenes
- **`Decision`**: Represents a recommendation with confidence scores and reasoning
- **Hysteresis System**: Prevents rapid scene switching
  - **`LastDecisionStore`**: Tracks previous decisions with timestamps
  - **Inertia boost**: Adds bonus score to recently selected scenes
  - **Minimum dwell time**: Enforces time threshold before allowing switches
  - **Score delta threshold**: Requires significant improvement to override the current scene

#### Scene Catalog (`scene_catalog.py`)
Central repository for all Hue scene definitions:

- **`STATIC_SCENE_SETS`**: Loaded from `hue_scenes.json`, organized by mood/theme
- **Semantic mappings**: Links abstract concepts to concrete scene sets
  - `SCHEDULE_PERIOD_TO_SET_NAMES`: Maps schedule periods to appropriate scene sets
  - `TIME_OF_DAY_TO_SET_NAMES`: Maps sun-based periods to scene sets
  - `ARRIVAL_SET_NAMES`: Defines welcoming arrival scenes
- **Helper functions**: 
  - `get_scenes_for_arrival()`: Returns arrival-appropriate scene names
  - `get_scenes_for_schedule_period()`: Returns scenes for a given schedule period
  - `get_scenes_for_time_of_day()`: Returns scenes for sun-based time periods
- **Design principle**: Strategies reference semantic categories, concrete scene names live only in JSON

#### Strategy Results (`policy/strategy.py`)
- **`StrategyResult`**: Container for strategy output
  - `scene_scores`: Dictionary mapping scene IDs to scores (0.0-1.0)
  - `metadata`: Optional contextual information about scoring decisions
- Enables detailed logging and debugging of strategy behavior

#### Coordinator System (`coordinator/`)
Orchestrates the recommendation engine:

- **`RecommendationCoordinator`**: Manages recommendations for all rooms
  - Polls context providers periodically (default: 15 seconds)
  - Generates recommendations via policy service
  - Supports manual and automatic scene application
  - Tracks per-room and global auto-apply preferences
  - Stores last context snapshot for inspection
- **`SceneRegistry`**: Maps human-readable scene names to Hue scene IDs
  - Maintains bidirectional lookups per room
  - Enables case-insensitive name resolution
  - Strategies work with names, coordinator uses IDs
- **`SceneApplier`**: Executes scene activations on the Hue bridge
  - Handles both regular scenes and smart scenes
  - Provides error handling for missing scenes

### Platform Entities (`entities/`)

Three entity types per room/zone:

1. **Sensor** (`sensor.{room}_recommendation`): Displays currently recommended scene name
2. **Switch** (`switch.{room}_auto_apply_recommendation`): Enables/disables automatic application
3. **Button** (`button.{room}_apply_recommendation`): Manually applies the current recommendation

## Data Flow

```
┌─────────────────┐
│ Context         │
│ Providers       │──┐
└─────────────────┘  │
                     ▼
┌─────────────────┐  ┌──────────────────┐
│ Home Assistant  │──▶│ HomeContext      │
│ State Machine   │  │ (aggregated data)│
└─────────────────┘  └──────────┬───────┘
                                │
                                ▼
                     ┌──────────────────┐
                     │ Policy Service   │
                     │ + Strategies     │
                     └──────────┬───────┘
                                │
                                ▼
                     ┌──────────────────┐
                     │ Decision         │
                     │ (recommended     │
                     │  scene + scores) │
                     └──────────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
         ┌──────────────────┐   ┌──────────────────┐
         │ Sensor Entity    │   │ Auto-Apply       │
         │ (display)        │   │ (if enabled)     │
         └──────────────────┘   └──────────┬───────┘
                                           ▼
                                ┌──────────────────┐
                                │ SceneApplier     │
                                │ (activate scene) │
                                └──────────────────┘
```

## Configuration

### Coordinator Setup
```python
coordinator = RecommendationCoordinator(
    hass=hass,
    bridge=bridge,
    providers=[
        SunProvider(hass),
        PresenceProvider(hass),
        ScheduleProvider(hass, schedule_prefix="schedule.hue_")
    ],
    policy_service=policy_service,
    scene_applier=scene_applier,
    scene_registry=scene_registry,
    update_interval=timedelta(seconds=15)
)
```

### Strategy Weights
Configure via config entry options:
```python
WeightsAndParams(
    strategy_weights={
        "time_of_day": 1.0,        # DEFAULT_RECOMMENDATION_WEIGHT_TIME_OF_DAY
        "weekly_schedule": 1.5,    # DEFAULT_RECOMMENDATION_WEIGHT_WEEKLY_SCHEDULE
        "home_arrival": 2.0,       # DEFAULT_RECOMMENDATION_WEIGHT_HOME_ARRIVAL
    },
    inertia_boost=0.2,             # Bonus for current scene
    switch_delta_min=0.1,          # Minimum score improvement to switch
    min_dwell_seconds=300          # 5 minutes before allowing switch
)
```

### Schedule Integration
The `ScheduleProvider` looks for Home Assistant schedule entities with a configurable prefix (default: `schedule.hue_`):
- `schedule.hue_morning`
- `schedule.hue_work`
- `schedule.hue_evening`
- `schedule.hue_night`

## Scene Collections

The system includes predefined scene sets (`hue_scenes.json`):
- **Defaults**: Rest, Relax, Read, Concentrate, Energize, Bright, Dimmed, Nightlight
- **Refreshing**: Blossom, Crocus, Precious, Narcissa
- **Cozy**: Rolling hills, Warm embrace, Dreamy dusk, Savanna sunset, Golden pond, Ruby glow, Tropical twilight
- **Party vibes**: Miami, Cancun, Rio, Ibiza, Tokyo, Motown, Fairfax
- **Serenity**: Galaxy, Starlight, Blood moon, Arctic aurora, Moonlight, Nebula
- **Dreamy**: Still waters, Adrift, Blue lagoon, Lake Placid, Majestic morning, Sundown
- **Peaceful**: Mountain breeze, Ocean dawn, Spring blossom, Emerald isle, Frosty dawn
- **Sunrise**: Beginnings, First light, Horizon, Valley dawn, Sunflare
- **Luxurious**: Emerald flutter, Memento, Resplendent, Scarlet dream
- **Pure**: Amethyst valley, Misty ridge, Midsummer sun, Autumn gold, Spring lake, Winter mountain
- **Lush**: Amber bloom, Lily, Painted sky, Orange fields, Forest adventure, Blue Planet
- **Futuristic**: Soho, Vapor wave, Magneto, Tyrell, Disturbia, Hal

### Semantic Mappings

**Schedule Period Mappings** (`SCHEDULE_PERIOD_TO_SET_NAMES`):
- **Morning**: Sunrise, Pure
- **Work**: Refreshing, Futuristic, Pure
- **Evening**: Cozy, Dreamy, Serenity, Peaceful, Lush, Luxurious
- **Night**: Serenity, Peaceful, Cozy

**Time of Day Mappings** (`TIME_OF_DAY_TO_SET_NAMES`):
- **Morning** (sun < 10°): Sunrise, Pure
- **Day** (sun ≥ 10°): Refreshing, Futuristic, Pure
- **Evening/Night** (sun < 0°): Cozy, Dreamy, Serenity, Peaceful, Lush, Luxurious

**Arrival Scenes** (`ARRIVAL_SET_NAMES`):
- Refreshing, Pure, Luxurious

## Decision Making Process

### 1. Context Collection
All providers fetch current state:
```python
context = HomeContext()
for provider in providers:
    context = await provider.fetch(context)
```

### 2. Strategy Scoring
Each strategy scores available scenes:
```python
for strategy in strategies:
    result = await strategy.score(context, candidates)
    # result.scene_scores: {"Relax": 0.8, "Bright": 0.3, ...}
```

### 3. Weighted Aggregation
Scores combined with configurable weights:
```python
weighted_score = sum(
    strategy_score * weight 
    for strategy_id, strategy_score in strategy_scores.items()
)
```

### 4. Hysteresis Application
Prevents rapid switching:
```python
if last_decision.scene_id == candidate:
    if last_decision.age < min_dwell_seconds:
        score += inertia_boost
```

### 5. Winner Selection
Highest scoring scene wins (random tiebreaker):
```python
max_score = max(weighted_scores.values())
winners = [s for s, score in weighted_scores.items() if score == max_score]
best_scene = random.choice(winners)
```

## Extension Points

### Custom Context Provider
```python
class CustomProvider(IContextProvider):
    @property
    def provider_id(self) -> str:
        return "custom"
    
    async def fetch(self, context: HomeContext) -> HomeContext:
        # Add custom data to context
        context.metadata["custom_data"] = await self._fetch_data()
        return context
```

### Custom Strategy
```python
class CustomStrategy(IStrategy):
    @property
    def strategy_id(self) -> str:
        return "custom"
    
    async def score(
        self, 
        context: HomeContext, 
        candidates: list[str]
    ) -> StrategyResult:
        scene_scores = {}
        for scene in candidates:
            scene_scores[scene] = self._calculate_score(scene, context)
        
        return StrategyResult(
            scene_scores=scene_scores,
            metadata={"reason": "custom logic"}
        )
```

### Adding Scenes to Catalog
Edit `coordinator/hue_scenes.json`:
```json
{
    "sets": [
        {
            "name": "My Custom Set",
            "scenes": [
                "Scene One",
                "Scene Two",
                "Scene Three"
            ]
        }
    ]
}
```

Then reference in `scene_catalog.py`:
```python
SCHEDULE_PERIOD_TO_SET_NAMES = {
    "morning": ["Sunrise", "Pure", "My Custom Set"],
    ...
}
```

## Entity Naming

Entities follow the pattern:
- Sensor: `sensor.{room_name}_recommendation`
- Switch: `switch.{room_name}_auto_apply_recommendation`
- Button: `button.{room_name}_apply_recommendation`

Works for rooms, zones, and the bridge home (whole-home control).

## Auto-Apply Behavior

- **Per-room control**: Each room has an independent auto-apply switch
- **Global control**: Bridge home switch enables auto-apply for entire home
- **Precedence**: Global setting overrides individual room settings when enabled
- **Trigger**: Recommendations refresh on schedule (default 15s) or when context changes
- **Persistence**: Switch states saved in config entry options
- **Immediate effect**: Enabling auto-apply triggers instant coordinator refresh

## Logging

### Info Level
```
Recommendation for room {id} ({name}): scene_id={scene}, score={score}, confidence={conf}, strategies=[...]
Decision made: scene_id={scene}, score={score}, confidence={conf}
```

### Debug Level
```
Context for room {id} ({name}): sun_elevation=X, sun_state=Y, available_scenes=[...], occupancy=Z
Strategy {id} scores: {scores} (metadata={meta})
Aggregated score for scene {name}: total=X (contributions={...})
Hysteresis applied: keeping previous scene {name} (delta=X < Y, age=As < Bs)
Auto-applied scene {id} for room {room_id}
```

## Performance Considerations

- **Update interval**: Default 15 seconds, configurable per bridge
- **Concurrent execution**: Context providers run sequentially (may parallelize in future)
- **Scene enumeration**: Performed once per update cycle for all rooms
- **Strategy execution**: Parallel scoring possible (currently sequential)
- **Decision caching**: `LastDecisionStore` tracks previous decisions for hysteresis
- **Context snapshot**: `current_context` property provides access without re-fetching

## Error Handling

- Missing scenes: Logged as warning, continues with remaining candidates
- Provider failures: Logged but don't block other providers
- Strategy failures: Logged, strategy excluded from that decision cycle
- Apply failures: Logged as warning, doesn't affect coordinator state
- Config validation: Falls back to defaults for invalid weights

## Testing Strategies

### Unit Testing Strategies
```python
strategy = TimeOfDayStrategy()
context = HomeContext(sun=SunContext(elevation=5.0))
result = await strategy.score(context, ["Morning", "Evening"])
assert result.scene_scores["Morning"] > result.scene_scores["Evening"]
```

### Integration Testing
```python
coordinator = RecommendationCoordinator(...)
await coordinator.async_request_refresh()
decision = coordinator.get_decision(room_id)
assert decision.scene_id in expected_scenes
```
