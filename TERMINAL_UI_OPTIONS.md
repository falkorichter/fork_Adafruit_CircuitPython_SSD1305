# Terminal UI Library Options for MQTT Sensor Display

## Problem Statement

The current implementation using ANSI escape codes has issues:
- **Save/Restore Cursor** (`\033[s`, `\033[u`): Doesn't work reliably across terminals
- **Cursor Positioning**: Works "so so" 
- **Clear Screen** (`\033[2J\033[H`): Works but leaves many cleared screens in scroll buffer (ugly when reviewing terminal history)

## Library Options

### 1. **Textual** (Recommended)
- **Website**: https://textual.textualize.io/
- **PyPI**: `textual`
- **Description**: Modern Python framework for building sophisticated terminal UIs with CSS-like styling
- **Pros**:
  - Rich widgets (tables, panels, headers, footers)
  - Reactive updates (only redraws changed elements)
  - Clean terminal history (uses alternate screen buffer)
  - Beautiful, modern appearance
  - Active development and good documentation
  - Built on Rich library (same author)
- **Cons**:
  - Heavier dependency (~2MB)
  - More complex API (but worth it for quality)
- **Example Use Case**: Perfect for dashboard-style MQTT sensor monitoring

### 2. **Rich** (Simpler Alternative)
- **Website**: https://rich.readthedocs.io/
- **PyPI**: `rich`
- **Description**: Library for rich text and beautiful formatting in the terminal
- **Pros**:
  - Lighter weight than Textual
  - `Live` display feature for updating content
  - Tables, panels, syntax highlighting
  - Good performance
  - No need for event loop
- **Cons**:
  - Less sophisticated than Textual
  - Limited to simpler UIs
- **Example Use Case**: Good for status displays, progress bars, live updating tables

### 3. **Blessed**
- **Website**: https://blessed.readthedocs.io/
- **PyPI**: `blessed`
- **Description**: Easy, practical library for making terminal apps
- **Pros**:
  - Lightweight
  - Simple API
  - Good cross-platform support
  - Context managers for safe terminal handling
- **Cons**:
  - Less feature-rich than Textual/Rich
  - More manual work required
- **Example Use Case**: Simple cursor control and color formatting

### 4. **curses** (Standard Library)
- **Built-in**: Part of Python standard library
- **Description**: Traditional terminal control library
- **Pros**:
  - No external dependencies
  - Battle-tested
  - Efficient
- **Cons**:
  - Complex API
  - Not available on Windows (without windows-curses package)
  - Harder to use than modern alternatives
- **Example Use Case**: When no dependencies are allowed

### 5. **asciimatics**
- **Website**: https://asciimatics.readthedocs.io/
- **PyPI**: `asciimatics`
- **Description**: Framework for creating text UIs with animation support
- **Pros**:
  - Animation support
  - Widget-based
  - Good for complex UIs
- **Cons**:
  - Heavier than needed for simple displays
  - More complex API
- **Example Use Case**: Interactive terminal applications with animations

## Recommendation

For the MQTT sensor example, I recommend **Rich** or **Textual**:

### **Rich** (Best for Simple Implementation)
- Quick to implement
- `Live` display provides clean updates without screen clearing
- Minimal code changes needed
- Good balance of features and simplicity

### **Textual** (Best for Future Extensibility)
- If we want a more polished, app-like experience
- Better for complex layouts
- Uses alternate screen buffer (doesn't pollute terminal history)
- Worth the extra complexity for a professional result

## Prototype Plan

1. **Phase 1**: Implement Rich-based solution
   - Uses `rich.live.Live` for updating display
   - Convert sensor data display to Rich table/panel
   - Test on macOS to verify clean updates

2. **Phase 2** (Optional): Implement Textual-based solution
   - Full TUI with proper layout
   - Reactive updates
   - Better user experience

## Example Code Snippets

### Rich Example (Simpler)
```python
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
import time

with Live(auto_refresh=True, refresh_per_second=0.5) as live:
    while True:
        # Create table with sensor data
        table = Table(title="MQTT Sensor Data")
        table.add_column("Sensor")
        table.add_column("Value")
        
        # Add rows
        table.add_row("Temperature", "22.5 °C")
        table.add_row("Humidity", "45.0 %")
        
        # Update display
        live.update(table)
        time.sleep(2)
```

### Textual Example (More Sophisticated)
```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable

class SensorApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Sensor", "Value")
        # Update in background task
        self.set_interval(2, self.update_data)
    
    def update_data(self) -> None:
        # Fetch and update sensor data
        pass

if __name__ == "__main__":
    app = SensorApp()
    app.run()
```

## Next Steps

1. Review this comparison with user
2. Implement Rich-based prototype (recommended first step)
3. Test on macOS
4. If needed, create Textual version for comparison
