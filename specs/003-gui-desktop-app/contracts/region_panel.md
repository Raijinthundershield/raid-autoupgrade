# Contract: RegionPanel Component

**Module**: `src/autoraid/gui/components/region_panel.py`
**Responsibility**: Display cached region status and manage region selection via OpenCV
**UI Location**: Middle section of single-page scrollable layout

---

## Dependencies (Injected via DI)

```python
@inject
def create_region_panel(
    locate_region_service: LocateRegionService = Provide[Container.locate_region_service],
    screenshot_service: ScreenshotService = Provide[Container.screenshot_service],
    cache_service: CacheService = Provide[Container.cache_service]
) -> None:
    """Create region management UI section"""
```

**Service Dependencies**:
- `LocateRegionService`: For automatic and manual region selection
- `ScreenshotService`: For capturing Raid window screenshots and extracting ROIs
- `CacheService`: For retrieving cached region status

---

## Public Interface

### Function: `create_region_panel(...) -> None`

**Purpose**: Render region status display and selection buttons

**Returns**: None (mutates NiceGUI UI tree)

**Side Effects**:
- Adds UI elements to current NiceGUI container
- Registers event handlers for button clicks
- Sets up timer for window size monitoring

---

## UI Elements

### Status Display

#### Label: Current Window Size
- **Element**: `ui.label()` inside `@ui.refreshable` decorator
- **Format**: "Current Window Size: {width} x {height}"
- **Value**: Retrieved via `screenshot_service.get_window_size()`
- **Updates**: On component mount + every 5 seconds via `ui.timer()`

#### Label: Cached Regions Status
- **Element**: `ui.label()` inside `@ui.refreshable` decorator
- **Format**:
  - **Found**: "Cached Regions: ✓ Found (upgrade_bar, upgrade_button, artifact_icon)" (green)
  - **Not Found**: "Cached Regions: ✗ Not Found" (red)
- **Value**: Retrieved via `cache_service.get_region()` for each region name
- **Updates**: On component mount + after region selection

#### Warning Banner: Window Size Changed
- **Element**: `ui.banner()` with type='warning'
- **Message**: "⚠ Window size changed. Cached regions invalid. Please re-select regions."
- **Visibility**: Shown when current window size ≠ cached window size
- **Updates**: Every 5 seconds via `ui.timer()`

#### Warning Message: Raid Window Not Found
- **Element**: `ui.label()` with red color
- **Message**: "⚠ Raid window not found"
- **Visibility**: Shown when `screenshot_service.get_window_size()` raises `WindowNotFoundException`

---

### Action Buttons

#### Button: Show Regions
- **Element**: `ui.button('Show Regions')`
- **Enabled State**: Enabled only when cached regions exist
- **Click Handler**: `async_show_regions()`
- **Tooltip**: "Display annotated screenshot with cached regions highlighted"

#### Button: Select Regions (Auto)
- **Element**: `ui.button('Select Regions (Auto)')`
- **Enabled State**: Always enabled (Raid window check done on click)
- **Click Handler**: `async_select_regions_auto()`
- **Tooltip**: "Attempt automatic region detection. Falls back to manual selection if fails."

#### Button: Select Regions (Manual)
- **Element**: `ui.button('Select Regions (Manual)')`
- **Enabled State**: Always enabled (Raid window check done on click)
- **Click Handler**: `async_select_regions_manual()`
- **Tooltip**: "Manually draw ROIs for upgrade bar, button, and artifact icon"

---

## Event Handlers

### `async_show_regions() -> None`

**Preconditions**:
- Cached regions exist for current window size

**Workflow**:
1. Validate Raid window exists
   - If not found: show toast "Raid window not found. Check if Raid is running."
2. Get current window size via `screenshot_service.get_window_size()`
3. Retrieve cached regions via `cache_service.get_region()` for each region name
4. Capture screenshot via `screenshot_service.take_screenshot()`
5. Draw colored rectangles on screenshot for each cached region
6. Run in thread: `await asyncio.to_thread(show_opencv_window, annotated_image)`
   - OpenCV window shows image with regions overlaid
   - Blocks until user closes window via `cv2.waitKey(0)`
   - Destroys window via `cv2.destroyAllWindows()`

**Error Handling**:
- `WindowNotFoundException`: Toast "Raid window not found. Check if Raid is running."
- `CacheKeyError` (no regions): Toast "No cached regions found. Please select regions first."

**Side Effects**:
- External OpenCV window appears (not embedded in GUI)
- User must manually close OpenCV window to continue

---

### `async_select_regions_auto() -> None`

**Preconditions**:
- Raid window exists

**Workflow**:
1. Validate Raid window exists
   - If not found: show toast "Raid window not found. Check if Raid is running."
2. Run in thread: `await asyncio.to_thread(locate_region_service.get_regions, manual=False)`
   - Attempts automatic template matching
   - If automatic detection succeeds: regions cached, returns success
   - If automatic detection fails: falls back to manual selection (OpenCV ROI selection UI)
3. Refresh status display to show newly cached regions
4. Show completion toast:
   - **Success (auto)**: "Regions detected automatically"
   - **Success (manual fallback)**: "Automatic detection failed. Regions selected manually."

**Error Handling**:
- `WindowNotFoundException`: Toast "Raid window not found. Check if Raid is running."
- `RegionDetectionError`: Toast "Region detection failed. Try manual selection."

**Side Effects**:
- Regions cached in diskcache for current window size
- If fallback to manual: External OpenCV ROI selection windows appear

---

### `async_select_regions_manual() -> None`

**Preconditions**:
- Raid window exists

**Workflow**:
1. Validate Raid window exists
   - If not found: show toast "Raid window not found. Check if Raid is running."
2. Run in thread: `await asyncio.to_thread(locate_region_service.get_regions, manual=True)`
   - Opens OpenCV ROI selection UI (external windows)
   - User draws rectangles for:
     1. Upgrade bar region
     2. Upgrade button region
     3. Artifact icon region
   - User presses Enter to confirm each region, Esc to cancel
3. Refresh status display to show newly cached regions
4. Show completion toast: "Regions selected manually"

**Error Handling**:
- `WindowNotFoundException`: Toast "Raid window not found. Check if Raid is running."
- `RegionSelectionCancelled`: Toast "Region selection cancelled"

**Side Effects**:
- Regions cached in diskcache for current window size
- External OpenCV ROI selection windows appear (3 total, one per region)

---

## State Management

### Transient State (Component-Local)

| Variable | Type | Initial | Purpose |
|----------|------|---------|---------|
| `current_window_size` | `tuple[int, int] \| None` | `None` | Current Raid window size (width, height) |
| `cached_window_size` | `tuple[int, int] \| None` | `None` | Window size for which regions are cached |
| `cached_regions` | `list[str]` | `[]` | Names of cached regions (upgrade_bar, upgrade_button, artifact_icon) |
| `window_found` | `bool` | `True` | Whether Raid window detected in last check |

### Persistent State

**None** - Region caching handled by existing `diskcache` (via CacheService)

---

## Window Size Monitoring

### Timer: Check Window Size Every 5 Seconds

```python
ui.timer(interval=5.0, callback=refresh_window_status)
```

**Behavior**:
1. Attempt to get current window size via `screenshot_service.get_window_size()`
2. If successful:
   - Update `current_window_size`
   - Compare with `cached_window_size`
   - If different: show warning banner "Window size changed. Cached regions invalid."
3. If `WindowNotFoundException`:
   - Set `window_found = False`
   - Show warning "Raid window not found"

**Purpose**: Proactively warn users when window resize invalidates cached regions

---

## Acceptance Criteria

### Status Display
- ✅ Current window size displays correct dimensions
- ✅ Cached regions status shows "Found" with region names if cached, "Not Found" otherwise
- ✅ Warning banner appears when window size changes
- ✅ Warning message appears when Raid window not detected
- ✅ Status updates every 5 seconds

### Show Regions
- ✅ Button disabled when no cached regions exist
- ✅ External OpenCV window opens with annotated screenshot
- ✅ Colored rectangles highlight each cached region
- ✅ User can close window to return to GUI

### Select Regions (Auto)
- ✅ Attempts automatic template matching first
- ✅ Falls back to manual selection if automatic fails
- ✅ Toast shows "Regions detected automatically" on auto success
- ✅ Toast shows "Automatic detection failed. Regions selected manually." on fallback
- ✅ Status display updates after selection

### Select Regions (Manual)
- ✅ Opens OpenCV ROI selection UI (3 windows, one per region)
- ✅ User can draw rectangles for each region
- ✅ User can cancel selection via Esc key
- ✅ Toast shows "Regions selected manually" on success
- ✅ Status display updates after selection

### Error Handling
- ✅ Toast shown for WindowNotFoundException
- ✅ Toast shown for RegionDetectionError
- ✅ Toast shown for RegionSelectionCancelled

---

## Testing Strategy

### Smoke Tests (Unit)

```python
def test_create_region_panel_smoke():
    """Verify panel creation without errors"""
    mock_locate = Mock(spec=LocateRegionService)
    mock_screenshot = Mock(spec=ScreenshotService)
    mock_cache = Mock(spec=CacheService)

    create_region_panel(
        locate_region_service=mock_locate,
        screenshot_service=mock_screenshot,
        cache_service=mock_cache
    )
    # Verify no exceptions raised

def test_show_regions_validates_window():
    """Verify toast shown when Raid window not found"""
    mock_screenshot.get_window_size.side_effect = WindowNotFoundException()
    async_show_regions()
    # Verify toast notification emitted

def test_window_size_changed_warning():
    """Verify warning banner shown when window resized"""
    cached_window_size = (1920, 1080)
    current_window_size = (1280, 720)
    refresh_window_status()
    # Verify warning banner visible
```

### Manual Tests (Integration)

- Click Show Regions with no cached regions → Verify button disabled
- Click Select Regions (Auto) → Verify automatic detection or fallback to manual
- Click Select Regions (Manual) → Verify OpenCV ROI selection UI appears
- Resize Raid window → Verify warning banner appears within 5 seconds
- Close Raid window → Verify "Raid window not found" warning appears

---

## Implementation Notes

### Refreshable Status Display

```python
@ui.refreshable
def show_region_status(cached_regions: list[str]):
    if cached_regions:
        ui.label(f'✓ Found ({", ".join(cached_regions)})').classes('text-green-500')
    else:
        ui.label('✗ Not Found').classes('text-red-500')

# Update display
show_region_status.refresh(new_cached_regions_list)
```

### OpenCV Window Threading

```python
async def show_opencv_window(image: np.ndarray):
    await asyncio.to_thread(lambda: (
        cv2.imshow('Cached Regions', image),
        cv2.waitKey(0),
        cv2.destroyAllWindows()
    ))
```

### Window Size Change Detection

```python
def refresh_window_status():
    try:
        current_size = screenshot_service.get_window_size()
        cached_size = get_cached_window_size()  # From cache metadata

        if current_size != cached_size:
            show_warning_banner()
    except WindowNotFoundException:
        show_window_not_found_warning()
```

---

## Dependencies Summary

**From DI Container**:
- `LocateRegionService` (singleton provider)
- `ScreenshotService` (singleton provider)
- `CacheService` (singleton provider)

**From NiceGUI**:
- `ui.label()`, `ui.button()`, `ui.banner()`
- `ui.notify()` (toast notifications)
- `ui.refreshable()` (reactive updates)
- `ui.timer()` (periodic polling)

**From Python stdlib**:
- `asyncio` (threading for OpenCV)

**From OpenCV**:
- `cv2.imshow()`, `cv2.waitKey()`, `cv2.destroyAllWindows()`
- `cv2.rectangle()` (for annotating screenshot)
