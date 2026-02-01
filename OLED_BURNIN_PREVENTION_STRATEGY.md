# OLED Burn-in Prevention Feature - Implementation Strategy

## Problem Statement

OLED displays can suffer from burn-in when static content is displayed for extended periods. To prevent this, we want to automatically blank the display after a period of keyboard inactivity.

## Requirements

1. **Automatic Display Blanking**: When the user has not used the keyboard for a configurable timeout period (default: 10 seconds), the OLED should be blanked (turned off or filled with black).
2. **Configurable Timeout**: The timeout should be a parameter that can be configured, defaulting to 10 seconds.
3. **Activity Detection**: Any keyboard input should reset the timeout and re-activate the display.
4. **Non-breaking**: The feature should be optional and not break existing functionality.

## Affected Files

Based on the codebase analysis, the following files will need modifications:

### Primary Files to Modify
1. **`examples/ssd1305_stats.py`** - The main stats display script
   - This is the primary user-facing script that would benefit from burn-in prevention
   - Currently runs in a continuous loop updating the display

2. **`examples/ssd1305_web_simulator.py`** - The web simulator
   - Should support the same functionality for testing purposes
   - May need simulated keyboard events

### Supporting Files
3. **`examples/README.md`** - Documentation
   - Add section explaining the new burn-in prevention feature
   - Document configuration parameters

## Implementation Strategy

### Phase 1: Architecture Design

#### 1.1 Keyboard Input Detection Approach

For Linux/Raspberry Pi environments, we have several options:

**Option A: Using `pynput` library** (RECOMMENDED)
- Cross-platform keyboard monitoring
- Non-blocking event-driven approach
- Works well with systemd services
- Requires: `pip install pynput`

**Option B: Using `evdev` library**
- Linux-specific, reads from `/dev/input/event*`
- More low-level control
- Requires root permissions in some cases
- Requires: `pip install evdev`

**Option C: Using file timestamp monitoring**
- Monitor `/dev/input` device activity
- Portable but less precise
- Fallback option if other libraries unavailable

**Decision**: Start with Option A (`pynput`) as primary implementation with fallback to Option C for environments where `pynput` is not available or doesn't work (e.g., headless systems).

#### 1.2 Timeout Management

Create a simple timeout tracker class:
```python
class DisplayTimeoutManager:
    def __init__(self, timeout_seconds=10.0, enabled=True):
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.last_activity_time = time.time()
        self.display_active = True
        
    def register_activity(self):
        """Called when keyboard activity is detected"""
        self.last_activity_time = time.time()
        if not self.display_active:
            self.display_active = True
            return True  # Signal that display should be re-activated
        return False
        
    def should_display_be_active(self):
        """Check if display should be active based on timeout"""
        if not self.enabled:
            return True
        
        elapsed = time.time() - self.last_activity_time
        should_be_active = elapsed < self.timeout_seconds
        
        # Track state changes
        if self.display_active != should_be_active:
            self.display_active = should_be_active
            
        return self.display_active
```

### Phase 2: Implementation Details

#### 2.1 Command Line Arguments

Add new command-line arguments to `ssd1305_stats.py`:

```python
parser = argparse.ArgumentParser(description='SSD1305 OLED Stats Display')
parser.add_argument(
    '--blank-timeout',
    type=float,
    default=10.0,
    help='Seconds of keyboard inactivity before blanking display (default: 10.0, 0 to disable)'
)
parser.add_argument(
    '--no-blank',
    action='store_true',
    help='Disable automatic display blanking'
)
```

#### 2.2 Display Blanking Logic

Modify the main display loop to:

1. Check timeout status before updating display
2. If timed out, blank the display once and skip updates
3. If activity detected after timeout, restore display immediately

```python
while True:
    if timeout_manager.should_display_be_active():
        # Normal display update logic
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        # ... draw content ...
        disp.image(image)
        disp.show()
    else:
        # Display is timed out - blank it once
        if timeout_manager.display_active == False and previous_state == True:
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            disp.image(image)
            disp.show()
    
    time.sleep(0.1)
```

#### 2.3 Keyboard Monitoring

Implement keyboard monitoring in a separate thread:

```python
def keyboard_listener(timeout_manager):
    """Background thread to monitor keyboard activity"""
    from pynput import keyboard
    
    def on_press(key):
        timeout_manager.register_activity()
    
    # Start listening
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
```

Or fallback implementation without external libraries:

```python
def simple_activity_monitor(timeout_manager, check_interval=0.5):
    """Fallback: Monitor system for general user activity"""
    import subprocess
    last_activity = None
    
    while True:
        try:
            # Check for recent input events (Linux-specific)
            result = subprocess.run(
                ['who', '-s'],
                capture_output=True,
                text=True,
                timeout=1
            )
            # If output changes, register activity
            if result.stdout != last_activity:
                timeout_manager.register_activity()
                last_activity = result.stdout
        except Exception:
            pass
        
        time.sleep(check_interval)
```

### Phase 3: Testing Strategy

#### 3.1 Unit Tests
Create `tests/test_timeout_manager.py`:
- Test timeout calculation
- Test activity registration
- Test state transitions
- Test disabled mode

#### 3.2 Integration Tests
- Test with actual keyboard input (manual testing required)
- Test timeout behavior in ssd1305_stats.py
- Test with web simulator (simulated keyboard events)

#### 3.3 Manual Testing Checklist
- [ ] Display blanks after configured timeout
- [ ] Display restores immediately on keyboard press
- [ ] Works with systemd service
- [ ] Works with different timeout values
- [ ] Works when disabled (--no-blank flag)
- [ ] Doesn't interfere with normal display updates
- [ ] Clean shutdown clears display

### Phase 4: Web Simulator Support

For `ssd1305_web_simulator.py`:

1. Add JavaScript keyboard event listener on the web page
2. Send activity notifications to server via AJAX
3. Server updates timeout manager
4. Display reflects timeout state in browser

```javascript
// In web_simulator_template.html
document.addEventListener('keydown', function() {
    fetch('/activity', {method: 'POST'});
});
```

### Phase 5: Documentation

Update `examples/README.md`:

#### Add new section:
```markdown
## OLED Burn-in Prevention

The stats display scripts now support automatic display blanking to prevent OLED burn-in.

### Usage

**Default behavior** (10-second timeout):
```bash
python examples/ssd1305_stats.py
```

**Custom timeout** (e.g., 30 seconds):
```bash
python examples/ssd1305_stats.py --blank-timeout 30
```

**Disable blanking**:
```bash
python examples/ssd1305_stats.py --no-blank
# OR
python examples/ssd1305_stats.py --blank-timeout 0
```

### How It Works

- The display monitors keyboard activity in the background
- After the specified timeout period with no keyboard input, the display is blanked
- Any keyboard press immediately restores the display
- This helps prevent OLED burn-in from static content

### Systemd Service

When running as a systemd service, the blanking feature works automatically. Update your service file to configure the timeout:

```ini
[Service]
ExecStart=/home/user/env/bin/python3 /path/to/ssd1305_stats.py --blank-timeout 30
```
```

## Dependency Management

### Required Dependencies
- `pynput` - For keyboard monitoring (optional, fallback available)

### Installation
```bash
pip install pynput
```

Add to `optional_requirements.txt`:
```
pynput  # Optional: For keyboard activity monitoring in burn-in prevention
```

## Backward Compatibility

- Feature is **opt-in** by being enabled by default but easily disabled
- Default timeout of 10 seconds is reasonable but configurable
- Scripts work exactly as before if timeout is disabled
- No changes to core library (`adafruit_ssd1305.py`)
- All changes isolated to example scripts

## Rollout Plan

### Step 1: Core Implementation
1. Implement `DisplayTimeoutManager` class
2. Add keyboard monitoring with pynput
3. Integrate into `ssd1305_stats.py`

### Step 2: Testing
1. Write unit tests for timeout manager
2. Manual testing with physical hardware
3. Test with systemd service

### Step 3: Web Simulator
1. Add keyboard event handling to web interface
2. Test simulated timeout behavior

### Step 4: Documentation
1. Update README.md
2. Add inline code comments
3. Update systemd service examples

### Step 5: Optional Enhancements (Future)
- Add visual indicator before blanking (countdown)
- Support mouse activity detection
- Add logging for debugging
- Support for other input devices
- Configuration file support

## Potential Issues and Mitigations

### Issue 1: Keyboard Monitoring Permissions
**Problem**: Reading keyboard events may require elevated permissions
**Mitigation**: 
- Use pynput which handles permissions better
- Provide fallback to activity-based monitoring
- Document permission requirements

### Issue 2: Headless Systems
**Problem**: Keyboard monitoring might not work on headless systems
**Mitigation**:
- Implement fallback monitoring methods
- Allow disabling the feature
- Document limitations

### Issue 3: Performance Impact
**Problem**: Continuous keyboard monitoring could impact performance
**Mitigation**:
- Use efficient event-driven approach
- Minimal processing in keyboard callback
- Throttle timeout checks

### Issue 4: Thread Safety
**Problem**: Keyboard listener runs in separate thread
**Mitigation**:
- Use thread-safe operations for timeout manager
- Minimal shared state
- Proper cleanup on exit

## Success Criteria

1. ✅ Display blanks after configured timeout with no keyboard activity
2. ✅ Display restores immediately on any keyboard press  
3. ✅ Configurable timeout via command-line argument
4. ✅ Can be completely disabled if desired
5. ✅ Works correctly with systemd service
6. ✅ No breaking changes to existing functionality
7. ✅ Comprehensive documentation
8. ✅ Clean shutdown behavior

## Timeline Estimate

- **Phase 1** (Architecture): 1-2 hours
- **Phase 2** (Implementation): 3-4 hours  
- **Phase 3** (Testing): 2-3 hours
- **Phase 4** (Web Simulator): 1-2 hours
- **Phase 5** (Documentation): 1 hour

**Total Estimated Time**: 8-12 hours

## Conclusion

This implementation provides a robust, configurable solution for OLED burn-in prevention while maintaining backward compatibility and not interfering with ongoing development in other areas. The modular approach allows for future enhancements while keeping the initial implementation focused and testable.
