# Plan: Making Rich Terminal Output Work with WebSocket Streaming

## Current Status

✅ **Basic ANSI terminal output** works perfectly with WebSocket streaming  
❌ **Rich library output** does NOT stream to WebSocket clients  
❌ **Textual library output** does NOT stream to WebSocket clients

## Why Rich Doesn't Work

### Technical Root Cause

Rich's `Live` display uses advanced terminal features that bypass our capture mechanism:

1. **Direct Terminal I/O**: Rich writes directly to the terminal device (`/dev/tty`), not to `sys.stdout`
2. **Alternate Screen Buffer**: Rich may use alternate screen buffers (like `vim` or `less`)
3. **ANSI Escape Sequences**: Rich uses complex ANSI codes for cursor positioning and in-place updates
4. **File Descriptor Access**: Rich's `Console` can access the terminal via file descriptors

### What Gets Captured vs What Doesn't

```python
# ✅ THIS WORKS - captured by TerminalStreamer
print("Hello World")

# ❌ THIS DOESN'T WORK - bypasses TerminalStreamer
from rich.console import Console
from rich.live import Live

console = Console()
with Live(renderable, console=console):
    # Updates bypass stdout capture
    pass
```

## Potential Solutions

### Option 1: Force Rich to Use Captured Stdout ⭐ RECOMMENDED

**Approach**: Configure Rich's `Console` to use our captured stdout instead of detecting the terminal automatically.

**Implementation**:
```python
from rich.console import Console
import sys

# Create console that uses sys.stdout (which is our TerminalStreamer)
console = Console(file=sys.stdout, force_terminal=True, width=80)

# Disable features that bypass stdout
console = Console(
    file=sys.stdout,
    force_terminal=True,
    force_interactive=False,  # Disable interactive features
    no_color=False,           # Keep colors
    legacy_windows=False
)
```

**Pros**:
- Minimal code changes
- Works with existing WebSocket infrastructure
- Preserves Rich's formatting and colors

**Cons**:
- May lose some Rich features (progress bars, spinners)
- Live display updates might not work smoothly
- Requires modifying `mqtt_sensor_example_rich.py`

**Estimated Effort**: 2-4 hours

---

### Option 2: Capture Rich's Console Output

**Approach**: Use Rich's built-in `Console.export_text()` or capture its internal buffer.

**Implementation**:
```python
from rich.console import Console
from io import StringIO

# Create a console that writes to a StringIO buffer
buffer = StringIO()
console = Console(file=buffer, force_terminal=True, width=80)

# Render content
console.print(table)

# Get the output and broadcast it
output = buffer.getvalue()
broadcast(output)
```

**Pros**:
- More control over when output is sent
- Can buffer and send complete frames
- Easier to handle Rich's complex ANSI codes

**Cons**:
- Breaks Live display concept (no real-time updates)
- Requires polling or manual refresh triggers
- More complex integration

**Estimated Effort**: 4-6 hours

---

### Option 3: Convert Rich Output to HTML ⭐ BEST USER EXPERIENCE

**Approach**: Use Rich's HTML export feature to render directly to HTML in the browser.

**Implementation**:
```python
from rich.console import Console

# Server side - export to HTML
console = Console(record=True, width=80)
console.print(table)

# Export to HTML
html_output = console.export_html(inline_styles=True)

# Send HTML via WebSocket
websocket.send(json.dumps({
    "type": "html",
    "data": html_output
}))
```

**Browser side** (`websocket_terminal_viewer.html`):
```javascript
if (data.type === 'html') {
    outputDiv.innerHTML = data.data;
} else if (data.type === 'output') {
    // Handle plain text
}
```

**Pros**:
- Perfect rendering in browser
- Preserves all Rich styling (colors, tables, borders)
- Best visual experience for users
- Can use CSS for additional styling

**Cons**:
- Requires modifying WebSocket protocol
- Requires updating HTML viewer
- Different rendering path for Rich vs basic output

**Estimated Effort**: 6-8 hours

---

### Option 4: Use Rich's Legacy Mode

**Approach**: Configure Rich to use simpler ANSI codes that work better with streaming.

**Implementation**:
```python
from rich.console import Console

console = Console(
    file=sys.stdout,
    force_terminal=True,
    legacy_windows=True,  # Use simpler ANSI codes
    width=80,
    height=24
)

# Avoid Live displays, use regular print
console.print(table)  # Instead of Live(table)
```

**Pros**:
- Simpler than full HTML conversion
- Still uses Rich's table formatting
- Works with existing infrastructure

**Cons**:
- Loses some Rich features
- No live updates
- Still may have ANSI code issues

**Estimated Effort**: 2-3 hours

---

### Option 5: Create a Rich-Compatible Streaming Console

**Approach**: Subclass Rich's `Console` to intercept and stream output properly.

**Implementation**:
```python
from rich.console import Console
from rich.segment import Segment

class StreamingConsole(Console):
    def __init__(self, streamer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = streamer
    
    def _render_buffer(self, buffer):
        # Intercept rendering and stream it
        output = super()._render_buffer(buffer)
        self.streamer.broadcast(output)
        return output
```

**Pros**:
- Most control over Rich's output
- Can optimize for streaming
- Keeps Rich's full feature set

**Cons**:
- Complex implementation
- May break with Rich library updates
- Requires deep understanding of Rich internals

**Estimated Effort**: 10-15 hours

---

## Recommended Approach

### Phase 1: Quick Win (Merge Current Work)
✅ Current basic streaming works well
✅ Document Rich limitation clearly
✅ Merge PR with working basic mode

### Phase 2: Option 1 - Force Rich to Use Stdout (Next Sprint)
- Modify `mqtt_sensor_example_rich.py` to configure Console properly
- Replace `Live` displays with periodic `console.print()` calls
- Test streaming with Rich tables and formatting
- Document any remaining limitations

### Phase 3: Option 3 - HTML Export (Future Enhancement)
- Add HTML export mode to Rich script
- Update WebSocket protocol to support HTML messages
- Enhance web viewer to render HTML
- Provide toggle between ANSI and HTML modes

## Implementation Checklist for Option 1 (Recommended First Step)

- [ ] Create new script `mqtt_sensor_example_rich_streaming.py`
- [ ] Configure Rich Console with `file=sys.stdout, force_terminal=True`
- [ ] Replace `Live()` context manager with periodic refresh loop
- [ ] Use `console.clear()` and `console.print()` for updates
- [ ] Test with WebSocket streaming
- [ ] Compare output quality with basic script
- [ ] Document configuration in README
- [ ] Add to websocket_terminal_server.py as `--script rich-streaming`

## Code Example for Option 1

```python
#!/usr/bin/env python3
# mqtt_sensor_example_rich_streaming.py
# Rich example optimized for WebSocket streaming

from rich.console import Console
from rich.table import Table
import sys
import time

# Configure console to use stdout (which may be TerminalStreamer)
console = Console(
    file=sys.stdout,
    force_terminal=True,
    force_interactive=False,
    width=80,
    height=24,
    legacy_windows=False
)

def create_layout(data):
    """Create the Rich display layout"""
    table = Table(title="MQTT Sensor Data")
    # ... table configuration ...
    return table

def main():
    while True:
        # Get sensor data
        data = mqtt_sensor.get_data()
        
        # Clear screen (will be captured by TerminalStreamer)
        console.clear()
        
        # Print layout (will be captured by TerminalStreamer)
        layout = create_layout(data)
        console.print(layout)
        
        # Wait before next update
        time.sleep(2)
```

## Testing Plan

### Test 1: Console Configuration
```bash
python mqtt_sensor_example_rich_streaming.py
# Verify: Output appears in terminal correctly
```

### Test 2: WebSocket Streaming
```bash
python examples/websocket_terminal_server.py --script rich-streaming
# Open browser to websocket_terminal_viewer.html
# Verify: Rich tables and colors appear in browser
```

### Test 3: ANSI Code Handling
- Verify colors render correctly
- Verify tables maintain structure
- Verify screen clears work properly
- Check for escape code artifacts

## Alternative: Hybrid Approach

Create two modes:

1. **Terminal Mode**: Uses Rich's Live display for best local experience
2. **Streaming Mode**: Uses Option 1 configuration for WebSocket compatibility

Detect streaming via environment variable:
```python
import os

STREAMING_MODE = os.getenv('WEBSOCKET_STREAMING', 'false').lower() == 'true'

if STREAMING_MODE:
    # Use streaming-compatible console
    console = Console(file=sys.stdout, force_terminal=True)
    # Use periodic updates instead of Live
else:
    # Use Rich's full features
    console = Console()
    # Use Live display
```

## Success Criteria

Rich streaming is considered working when:

✅ Rich formatted tables appear in web browser  
✅ Colors are preserved in WebSocket viewer  
✅ Table structure is maintained  
✅ Updates stream in near real-time (< 3 second delay)  
✅ No ANSI escape code artifacts visible  
✅ CPU usage remains acceptable  

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Rich updates too frequently, overwhelming WebSocket | Add rate limiting/throttling |
| ANSI codes not rendering in browser | Enhance HTML viewer with ANSI parser |
| Performance degradation | Profile and optimize broadcast mechanism |
| Rich library updates break integration | Pin Rich version, add integration tests |

## Resources

- [Rich Console API](https://rich.readthedocs.io/en/latest/console.html)
- [Rich HTML Export](https://rich.readthedocs.io/en/latest/console.html#export)
- [ANSI Escape Codes](https://en.wikipedia.org/wiki/ANSI_escape_code)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)

## Timeline Estimate

- **Option 1 (Recommended)**: 1-2 days
- **Option 3 (HTML Export)**: 3-4 days
- **Full Production Ready**: 1-2 weeks with testing

## Next Steps

1. ✅ Merge current PR with working basic mode
2. Create issue for Rich streaming support
3. Implement Option 1 in separate branch
4. Test and iterate
5. Consider Option 3 for v2.0

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-07  
**Status**: Planning Phase
