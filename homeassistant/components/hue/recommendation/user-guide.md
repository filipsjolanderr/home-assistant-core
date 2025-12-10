# Hue recommendation engine user guide

## What it does
- Suggests Philips Hue scenes for each room based on context: time of day, sun position, presence, and your Home Assistant schedules.
- Can auto-apply the recommended scene per room or for the whole home.
- Gives you entities to see the current recommendation, trigger it manually, and toggle auto-apply.

## What you need
- Home Assistant set up with the Hue integration (v2 bridge).
- Hue scenes already created in the Hue app for your rooms/zones.
- Optional: Home Assistant `schedule` entities if you want schedule-aware recommendations (defaults use sun + presence only).

## Entities you get (per room/zone)
- `sensor.<room>_recommendation`: Shows the currently recommended scene name.
- `switch.<room>_auto_apply_recommendation`: Enables automatic application in that room.
- `button.<room>_apply_recommendation`: Manually applies the current recommendation.
- Bridge “home” also gets an auto-apply switch that can control all rooms at once.

## How recommendations are chosen
- Time of day and sun: Prefers bright/energizing scenes during the day; cozy/serene at night.
- Weekly schedule (optional): If you have `schedule.hue_morning`, `schedule.hue_work`, `schedule.hue_evening`, `schedule.hue_night`, the engine aligns scenes to those periods.
- Arrival: If everyone was away and someone just arrived, it prefers welcoming scenes.
- Stability: It avoids rapid switching by requiring a meaningful score improvement and a minimum dwell time before changing scenes.

## Quick start
1) Ensure Hue scenes exist for each room/zone you want recommendations in.
2) (Optional) Create Home Assistant schedule entities named: `schedule.hue_morning`, `schedule.hue_work`, `schedule.hue_evening`, `schedule.hue_night`.
3) In Home Assistant, enable the per-room `switch.<room>_auto_apply_recommendation` if you want automatic changes.
4) Watch `sensor.<room>_recommendation` to see what would be applied; tap the button entity to try it manually.
5) Use the bridge-level auto-apply switch to turn auto-apply on/off for the whole home at once.

## Working with schedules
- Each schedule entity represents a period (morning, work, evening, night). The active period steers which scene sets are preferred.
- If no schedule entities exist or none are active, the engine falls back to sun position and presence.
- You can keep schedules very simple (e.g., just morning/evening) or fine-tune them with multiple time blocks inside each schedule.

## Auto-apply behavior
- Per-room switches control auto-apply locally. The bridge “home” switch, when on, overrides and enables auto-apply everywhere.
- Turning on auto-apply triggers an immediate refresh; otherwise recommendations refresh on the regular interval (about every 15 seconds).
- If a recommendation cannot be applied (missing scene, etc.), it is logged but other rooms continue to update.

## Manual control
- Press `button.<room>_apply_recommendation` to apply the current suggestion on demand.
- You can leave auto-apply off and just use the sensor + button for assisted manual control.

## Customizing emphasis
- Strategy weights (time-of-day, weekly schedule, arrival) can be adjusted in the Hue config entry options. Higher weight means more influence.
- Hysteresis settings (minimum dwell time, required score improvement, inertia boost) control how “sticky” the current scene is versus switching.

## Tips for best results
- Keep at least one bright/daytime and one cozy/evening scene per room.
- Name Hue scenes clearly so the recommendation sensor is easy to read. Use the English names and don't change them to something custom.
- Define your household schedule periods so the engine knows when you typically work, relax, or sleep.
- Start with auto-apply off, observe recommendations, then enable auto-apply once you like the behavior.

## Troubleshooting
- No recommendation shown: Ensure the room has Hue scenes and the bridge exposes them to Home Assistant.
- Wrong period: Check which schedule entity is active or verify sun position; adjust schedule time blocks if needed.
- Not switching scenes: Hysteresis may be holding the current scene; wait for the dwell time or lower the switch threshold in options.
- Errors in logs: Look for “hue_recommendation” entries; missing scenes or provider issues are logged as warnings without stopping other rooms.


